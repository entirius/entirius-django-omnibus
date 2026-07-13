# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
from datetime import timedelta
from decimal import Decimal
from itertools import groupby

from django.db.models import Max, Min, OuterRef, Q, Subquery
from django.utils import timezone
from django_checkout.domain.dto.discount_items import DiscountItemData, DiscountItems, ValidatedDiscountData
from django_checkout.models import DiscountRuleCode
from django_checkout.worker.discount_calc import calc_discount
from django_pricemanager.models import Price, PriceList, PriceListStatus, SaleChannel

from django_omnibus.bi import FillOmnibusPricesForChannelEvent, FillSingleOmnibusPriceEvent
from django_omnibus.models import OmnibusPrice, PriceFromStatus, ProductRepresentation
from django_omnibus.settings import (
    APPLIED_SPECIAL_PRICE_WHEN_NULL_VALIDITY_DATES,
    BULK_SIZE_OMNIBUS,
    PRICELIST_OMNIBUS_FILTER_DATE_MECHANISM,
)

logger_process = logging.getLogger("process")
logger = logging.getLogger(__name__)

try:
    from django_pricemanager.models import Channel as PMChannel
    from django_pricemanager.models import CurrentPrice, PriceHistory
    from django_pricemanager.output import read_from_current
except ImportError:
    logger.warning("CurrentPrice/PriceHistory not available — omnibus will use legacy PriceList path")

    def read_from_current() -> bool:
        return False


def create_structured_data(data, base):
    key_func_currency = lambda x: x["pricelist__currency__iso3"]
    grouped_data_currency = groupby(sorted(data, key=key_func_currency), key=key_func_currency)
    for key_currency, group in grouped_data_currency:
        key_func_sku = lambda x: x["product__sku"]
        grouped_data_sku = groupby(sorted(group, key=key_func_sku), key=key_func_sku)
        for key_sku, group in grouped_data_sku:
            for elem in group:
                base.setdefault(key_currency, {}).setdefault(key_sku, [])
                item = {}
                for k, v in elem.items():
                    item[k] = v
                base[key_currency][key_sku].append(item)
    return base


def generate_items_data(products):
    list_of_data = []
    for each_product in products:
        item_data = DiscountItemData(sku=each_product, quantity=1)
        list_of_products = [item_data]
        items_data = DiscountItems(items=list_of_products)
        list_of_data.append(items_data)
    return list_of_data


def get_newest_normal_prices(all_prices, prices_30_days):
    newest_base_price = (
        all_prices.annotate(latest_created_on=Max("pricelist__created_on"))
        .filter(
            pricelist__created_on=Subquery(
                Price.objects.filter(product=OuterRef("product"), pricelist=OuterRef("pricelist"))
                .order_by("-pricelist__created_on")[:1]
                .values("pricelist__created_on")
            )
        )
        .values(
            "pk",
            "product__sku",
            "gross_value",
            "pricelist__currency__iso3",
            "pricelist__created_on",
            "special_from_date",
            "special_to_date",
        )
    )
    prices_result = create_structured_data(newest_base_price, prices_30_days)
    return prices_result


def get_last_prices_30_days(all_prices, discounted_prices):
    today = timezone.now()
    thirty_days_ago = today - timedelta(days=30)
    filter_conditions = Q(special_from_date__lte=today, special_to_date__gte=thirty_days_ago) | Q(
        special_from_date__lte=thirty_days_ago, special_to_date__gte=today
    )
    if APPLIED_SPECIAL_PRICE_WHEN_NULL_VALIDITY_DATES:
        filter_conditions = filter_conditions | Q(
            special_from_date__isnull=True, special_to_date__isnull=True, special_gross_value__isnull=False
        )
    prices = all_prices.filter(filter_conditions).values(
        "pk",
        "product__sku",
        "pricelist__currency__iso3",
        "special_gross_value",
        "pricelist__created_on",
        "special_from_date",
        "special_to_date",
    )
    prices_result = create_structured_data(prices, discounted_prices)
    return prices_result


def prepare_items(rule, product, code):
    if hasattr(ValidatedDiscountData, "factory"):
        discount = ValidatedDiscountData.factory()
        discount.code = code.code
        product.discounts = [discount]
        return product
    else:
        return product


def get_discounted_prices(products: list, currencies: list, channel_idx: str):
    rules = DiscountRuleCode.objects.filter(is_omnibus=True)
    items_data = generate_items_data(products)

    result = {}
    for currency in currencies:
        for rule in rules:
            for product in items_data:
                try:
                    code = rule.codes.all().first()
                    if not code:
                        continue
                    product = prepare_items(rule, product, code)
                    discount_result = calc_discount(rule, product, currency, channel_idx=channel_idx)
                    result.setdefault(currency, {}).setdefault(product.items[0].sku, [])
                    if discount_result.items[0].discount_amount:
                        result[currency][product.items[0].sku].append(
                            {
                                "discounted_price": discount_result.items[0].total_price
                                - discount_result.items[0].discount_amount
                            }
                        )
                except Exception as e:
                    logger_process.exception(e)
                    continue
    return result


def skip_omnibus_price_update(bev_product, product, omnibus_price, currency, channel):
    bev_product.set_details(
        {
            "sku": product.sku,
            "omnibus_price": omnibus_price.omnibus_price,
            "omnibus_price_status": omnibus_price.omnibus_price_status,
            "currency": currency,
            "channel": channel.idx,
        }
    )
    bev_product.finish_with_success(
        finish_tag=f"Omnibus Price for {product} is skipped, bcs previous omnibus price is lower"
    )


OMNIBUS_LOOKBACK_DAYS = 30


def _bulk_min_gross(qs, group_fields: list[str]) -> dict[tuple, "Decimal"]:
    """Aggregate Min(gross_value) grouped by given fields. Returns {(sku, currency): min_gross}."""
    rows = qs.values(*group_fields).annotate(min_gross=Min("gross_value"))
    return {tuple(r[f] for f in group_fields): r["min_gross"] for r in rows if r["min_gross"] is not None}


def _determine_omnibus_status(
    current_min: "Decimal | None",
    history_min: "Decimal | None",
    has_active_special: bool,
) -> str:
    """Determine omnibus price_status based on where the lowest price comes from."""
    if has_active_special:
        return PriceFromStatus.SPECIAL_PRICE
    if history_min is not None and (current_min is None or history_min < current_min):
        return PriceFromStatus.NORMAL_PRICE  # historical price was lower
    return PriceFromStatus.NORMAL_PRICE


def _calculate_omnibus_from_price_history(
    channel,
    sku: str | None,
    handler,
) -> tuple[int, int]:
    """Calculate omnibus prices using PriceHistory (CurrentPrice architecture).

    OmnibusPrice is per product+currency+channel (no country dimension).
    Uses 2 bulk queries (not per-row) for current and historical minimums.
    """
    cutoff = timezone.now() - timedelta(days=OMNIBUS_LOOKBACK_DAYS)

    base_filters = {
        "channel__idx": channel.idx,
        "customer_representation__isnull": True,
        "product_parent__isnull": True,
    }
    if sku:
        base_filters["product__sku"] = sku

    # 2 bulk queries — one per table, grouped by (sku, currency)
    group = ["product__sku", "currency__iso3"]
    current_mins = _bulk_min_gross(CurrentPrice.objects.filter(**base_filters), group)
    history_mins = _bulk_min_gross(
        PriceHistory.objects.filter(
            channel__idx=channel.idx,
            customer_representation__isnull=True,
            created_at__gte=cutoff,
            **({"product__sku": sku} if sku else {}),
        ),
        group,
    )

    # Check which SKU+currency combos have active special prices
    active_specials = set(
        CurrentPrice.objects.filter(
            **base_filters,
            special_gross_value__isnull=False,
        )
        .values_list("product__sku", "currency__iso3")
        .distinct()
    )

    # Resolve channel + product reps once (not per row)
    pm_channel = PMChannel.objects.get(idx=channel.idx)
    all_skus = {key[0] for key in current_mins} | {key[0] for key in history_mins}
    rep_by_sku = {r.sku: r for r in ProductRepresentation.objects.filter(sku__in=all_skus)}

    all_keys = set(current_mins) | set(history_mins)
    created_count = 0
    updated_count = 0

    for key in all_keys:
        product_sku, currency_iso3 = key
        cur = current_mins.get(key)
        hist = history_mins.get(key)
        candidates = [v for v in (cur, hist) if v is not None]
        if not candidates:
            continue

        omnibus_gross = min(candidates)
        has_special = key in active_specials
        status = _determine_omnibus_status(cur, hist, has_special)

        product_rep = rep_by_sku.get(product_sku)
        if not product_rep:
            product_rep, _ = ProductRepresentation.objects.get_or_create(sku=product_sku)
            rep_by_sku[product_sku] = product_rep

        _, created = OmnibusPrice.objects.update_or_create(
            product=product_rep,
            currency=currency_iso3,
            channel=pm_channel,
            defaults={
                "omnibus_price": omnibus_gross,
                "price_status": status,
                "omnibus_price_status": status,
            },
        )
        if created:
            created_count += 1
        else:
            updated_count += 1

    handler.stdout.write(f"[PriceHistory] Channel {channel.idx}: created={created_count}, updated={updated_count}")
    return created_count, updated_count


def calculate_omnibus_price(channels, sku, handler, bulk_size=BULK_SIZE_OMNIBUS):
    # Use PriceHistory-based calculation when CurrentPrice architecture is active
    if read_from_current():
        total_created, total_updated = 0, 0
        for channel in channels:
            created, updated = _calculate_omnibus_from_price_history(channel, sku, handler)
            total_created += created
            total_updated += updated
        return total_created, total_updated

    # Legacy: PriceList snapshot-based calculation
    omnibuses_created = []
    omnibuses_updated = []
    for channel in channels:
        bev_channel = FillOmnibusPricesForChannelEvent(is_ongoing_event=True)
        handler.stdout.write(f"Start calculate Omnibus Prices for channel: {channel.idx} with bulk_size = {bulk_size}")
        currencies = Price.objects.filter(pricelist__sale_channel__channel__idx=channel.idx).values_list(
            "pricelist__currency__iso3", flat=True
        )
        currencies = list(set(currencies))
        report = {"channel": channel.idx, "currencies": list(currencies)}

        # this make the newest omnibus module compatible with the old pricemanager
        field_exists = hasattr(SaleChannel, "customer_representation")

        # weź wszytskie najnowsze pricelisty dla konfiguracji country-cuurency
        subquery = (
            PriceList.objects.filter(
                sale_channel__channel=channel,
                status=PriceListStatus.enumClass.READY,
                **({"sale_channel__customer_representation__isnull": True} if field_exists else {}),
            )
            .values("country", "currency")
            .annotate(latest_created_on=Max("created_on"))
            .order_by()
        )

        price_lists = PriceList.objects.filter(
            sale_channel__channel=channel,
            status=PriceListStatus.enumClass.READY,
            **({"sale_channel__customer_representation__isnull": True} if field_exists else {}),
        )

        if PRICELIST_OMNIBUS_FILTER_DATE_MECHANISM == 1:
            price_list_query_all = price_lists.filter(created_on__in=Subquery(subquery.values("latest_created_on")))
            price_list_query = price_list_query_all.filter(name__icontains="import").order_by("-created_on")
            if not price_list_query:
                price_list_query = price_list_query_all.order_by("-created_on")

            currencies_added = []
            price_lists = []
            for price_list in price_list_query:
                if price_list.currency.iso3 in currencies_added:
                    continue
                price_lists.append(price_list.id)
                currencies_added.append(price_list.currency.iso3)

        elif PRICELIST_OMNIBUS_FILTER_DATE_MECHANISM == 2:
            price_lists = list(
                price_lists.filter(created_on__gte=timezone.now() - timedelta(days=30))
                .order_by("-created_on")
                .values_list("id", flat=True)
            )
        elif PRICELIST_OMNIBUS_FILTER_DATE_MECHANISM == 3:
            pass

        if not price_lists:
            bev_channel.finish_with_exception(Exception(f"There is no pricelist with READY status for {currencies}"))
            continue

        all_products = ProductRepresentation.objects.all()
        if sku:
            all_products = all_products.filter(sku=sku)
        all_products = all_products.values_list("sku", flat=True)
        product_count = all_products.count()
        total_batches = (product_count + bulk_size - 1) // bulk_size

        for batch in range(total_batches):
            start_index = batch * bulk_size
            end_index = min((batch + 1) * bulk_size, product_count)
            products = all_products[start_index:end_index]

            handler.stdout.write(
                f"Start calculating Omnibus Prices for channel: {channel.idx} - Batch {batch + 1}/{total_batches}"
            )

            all_prices = Price.objects.filter(product__sku__in=products, pricelist__id__in=price_lists)
            if not all_prices:
                logger_process.error(
                    f"There is no Prices associated with pricelist: {price_lists} status for {currencies}"
                )
                continue
            discounted_prices = get_discounted_prices(products, currencies, channel.idx)
            prices_30_days = get_last_prices_30_days(all_prices, discounted_prices)
            newest_normal_prices = get_newest_normal_prices(all_prices, prices_30_days)
            for currency, products in newest_normal_prices.items():
                total = len(products)
                cnt = 0
                handler.stdout.write(
                    f"Start calculate {channel.idx} Omnibus Prices for currency: {currency} - items: {total}"
                )
                for product, data in products.items():
                    cnt += 1
                    if cnt % 1000 == 0:
                        logger_process.info(
                            f"Calculate {channel.idx} Omnibus Prices for currency: {currency} -  {cnt} / {total}"
                        )
                    bev_product = FillSingleOmnibusPriceEvent(channel_idx=channel.idx, is_ongoing_event=True)
                    product = ProductRepresentation.objects.filter(sku=product).first()
                    if product is None:
                        continue
                    calculated_price = None
                    calculated_status = PriceFromStatus.NOT_DEFINED
                    prices = []
                    special_list = []
                    gross_list = []
                    discount_list = []
                    newest_record_gross = []
                    discount = None
                    for each in data:
                        discount = each.get("discounted_price", None)
                        special = each.get("special_gross_value", None)
                        gross = each.get("gross_value", None)
                        price_date = each.get("pricelist__created_on", None)
                        special_from_date = each.get("special_from_date", None)
                        special_to_date = each.get("special_to_date", None)

                        if discount:
                            discount_list.append((discount, price_date, PriceFromStatus.DISCOUNT, None, None))
                        if special:
                            special_list.append(
                                (special, price_date, PriceFromStatus.SPECIAL_PRICE, special_from_date, special_to_date)
                            )
                        if gross:
                            gross_list.append((gross, price_date, PriceFromStatus.NORMAL_PRICE, None, None))
                    newest_record_special = None
                    # get the newest record from special and gross list
                    if discount_list:
                        newest_record_discount = max(discount_list, key=lambda x: x[1])
                        prices.append(newest_record_discount)
                    if special_list:
                        newest_record_special = max(special_list, key=lambda x: x[1])
                        prices.append(newest_record_special)
                    if gross_list:
                        newest_record_gross = max(gross_list, key=lambda x: x[1])
                        prices.append(newest_record_gross)
                    # get the lowest price from all prices
                    if prices:
                        price = min(prices, key=lambda x: x[0])
                        calculated_price = price[0]
                        calculated_status = price[2]
                    try:
                        omnibus_price: OmnibusPrice = OmnibusPrice.objects.get(
                            product=product, currency=currency, channel=channel
                        )

                        is_status_changed_normal_to_special = (
                            True
                            if calculated_status in [PriceFromStatus.SPECIAL_PRICE, PriceFromStatus.DISCOUNT]
                            and omnibus_price.price_status == PriceFromStatus.NORMAL_PRICE
                            else False
                        )

                        is_status_changed_special_to_normal = (
                            True
                            if calculated_status == PriceFromStatus.NORMAL_PRICE
                            and omnibus_price.price_status in [PriceFromStatus.SPECIAL_PRICE, PriceFromStatus.DISCOUNT]
                            else False
                        )
                        is_status_changed_special_to_special_with_lower_price = (
                            True
                            if calculated_status in [PriceFromStatus.SPECIAL_PRICE, PriceFromStatus.DISCOUNT]
                            and omnibus_price.price_status in [PriceFromStatus.SPECIAL_PRICE, PriceFromStatus.DISCOUNT]
                            and (
                                omnibus_price.current_promotion_price != calculated_price
                                if omnibus_price.current_promotion_price
                                else False
                            )
                            else False
                        )

                        # Jeżeli status jest special i nie ma daty rozpoczęcia promocji to zapisz datę rozpoczęcia promocji i wymuś zapisanie ceny normalnej (cena omnibus nie jest ceną aktualnej promocji)
                        # przypadek występuję tylko gdy przechodzimy z niższej wersji omnibus
                        if (
                            any(
                                [
                                    not omnibus_price.current_promotion_date_start,
                                    not omnibus_price.current_promotion_price,
                                ]
                            )
                            and newest_record_special
                            and not omnibus_price.last_promotion_price
                            and any([omnibus_price.omnibus_price_status, discount])
                            and calculated_status in [PriceFromStatus.DISCOUNT, PriceFromStatus.SPECIAL_PRICE]
                        ):
                            special_to_date = newest_record_special[4]
                            special_from_date = newest_record_special[3]
                            timezone_now = timezone.now()

                            if special_to_date and special_from_date:
                                if special_to_date < timezone_now:
                                    omnibus_price.last_promotion_date_end = special_to_date
                                    omnibus_price.last_promotion_price = calculated_price
                                    omnibus_price.last_promotion_price_status = PriceFromStatus.SPECIAL_PRICE
                                    omnibus_price.omnibus_price_status = PriceFromStatus.SPECIAL_PRICE
                                    omnibus_price.omnibus_price = calculated_price
                                    omnibus_price.save()
                                    continue
                                elif special_from_date > timezone_now:
                                    continue

                            start_promotion = (
                                special_from_date or newest_record_special[1] if newest_record_special else timezone_now
                            )

                            omnibus_price.current_promotion_date_start = start_promotion
                            omnibus_price.current_promotion_price = calculated_price
                            omnibus_price.omnibus_price_status = PriceFromStatus.NORMAL_PRICE
                            omnibus_price.omnibus_price = newest_record_gross[0]
                            omnibus_price.save()
                            continue

                        # Jeżeli zmienił się status z normal na special to zapisz datę rozpoczęcia promocji
                        if is_status_changed_normal_to_special:
                            omnibus_price.current_promotion_date_start = timezone.now()
                            omnibus_price.current_promotion_price = calculated_price

                        # Jeżeli promocja się skończyła lub zmieniła się to zapisz datę zakończenia promocji
                        if is_status_changed_special_to_normal or is_status_changed_special_to_special_with_lower_price:
                            omnibus_price.last_promotion_price = omnibus_price.current_promotion_price
                            omnibus_price.last_promotion_price_status = omnibus_price.price_status
                            omnibus_price.last_promotion_date_end = timezone.now()
                            omnibus_price.current_promotion_date_start = None
                            omnibus_price.current_promotion_price = None

                        # Jeżeli zmienił się status z special na special z niższą ceną to zapisz nową cenę promocyjną
                        if is_status_changed_special_to_special_with_lower_price:
                            omnibus_price.current_promotion_price = calculated_price
                            omnibus_price.current_promotion_date_start = timezone.now()

                        omnibus_price.price_status = calculated_status
                        omnibus_price.save()
                        # if calculated price is a discount or special price and the last promotion was less than 30 days ago than first day of new promotion - omni price = last promotion price
                        if omnibus_price.last_promotion_date_end and calculated_status in [
                            PriceFromStatus.DISCOUNT,
                            PriceFromStatus.SPECIAL_PRICE,
                        ]:
                            if (
                                omnibus_price.current_promotion_date_start
                                or timezone.now() - omnibus_price.last_promotion_date_end <= timedelta(days=30)
                            ):
                                calculated_price = omnibus_price.last_promotion_price
                                calculated_status = omnibus_price.last_promotion_price_status
                            else:
                                omnibus_price.last_promotion_price = None
                                omnibus_price.last_promotion_price_status = None
                                omnibus_price.last_promotion_date_end = None
                        elif calculated_status in [PriceFromStatus.DISCOUNT, PriceFromStatus.SPECIAL_PRICE]:
                            calculated_price = newest_record_gross[0] if newest_record_gross else None
                            calculated_status = PriceFromStatus.NORMAL_PRICE

                        omnibus_price.save()

                        if not omnibus_price.current_promotion_price:
                            calculated_price = None

                        if omnibus_price.current_promotion_price and not calculated_price:
                            calculated_price = newest_record_gross[0]

                        omnibus_price.omnibus_price_status = calculated_status
                        omnibus_price.omnibus_price = calculated_price
                        omnibus_price.save()
                        omnibuses_updated.append(omnibus_price.product.sku)
                    except OmnibusPrice.DoesNotExist:
                        current_promotion_price = (
                            calculated_price
                            if calculated_status in [PriceFromStatus.DISCOUNT, PriceFromStatus.SPECIAL_PRICE]
                            else None
                        )
                        current_promotion_date_start = (
                            newest_record_special[1]
                            if calculated_status in [PriceFromStatus.DISCOUNT, PriceFromStatus.SPECIAL_PRICE]
                            and newest_record_special
                            else timezone.now()
                            if discount
                            else None
                        )

                        omnibus_price = OmnibusPrice.objects.create(
                            product=product,
                            currency=currency,
                            omnibus_price_status=PriceFromStatus.NORMAL_PRICE,
                            price_status=calculated_status,
                            omnibus_price=(
                                newest_record_gross[0] if newest_record_gross and current_promotion_price else None
                            ),
                            channel=channel,
                            last_promotion_price=None,
                            last_promotion_date_end=None,
                            last_promotion_price_status=None,
                            current_promotion_price=current_promotion_price,
                            current_promotion_date_start=current_promotion_date_start,
                        )
                        omnibuses_created.append(omnibus_price)
                    bev_product.set_details(
                        {
                            "sku": product.sku,
                            "omnibus_price": calculated_price,
                            "omnibus_price_status": calculated_status,
                            "currency": currency,
                            "channel": channel.idx,
                        }
                    )
                    bev_product.finish_with_success(finish_tag=f"Omnibus Price for {product} successfully calculated")
        logger_process.info(
            f"Channel: {channel.idx} Omnibus prices are updated.",
            extra={"details": {"omnibuses_updated": omnibuses_updated}},
        )
        logger_process.info(
            f"Channel: {channel.idx} Omnibus prices are created.",
            extra={"details": {"omnibuses_created": omnibuses_created}},
        )
        report["omnibuses_updated"] = len(omnibuses_updated)
        report["omnibuses_created"] = len(omnibuses_created)
        bev_channel.set_details(report)
        bev_channel.finish_with_success(finish_tag=f"Omnibus Price for {channel.idx} has been filled")
