# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import csv
import logging
from datetime import datetime
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist
from django_pricemanager.models import Channel

from django_omnibus.bi import ImportOmnibusPriceFromCsvEvent
from django_omnibus.models import OmnibusPrice, PriceFromStatus
from django_omnibus.models import ProductRepresentation as ProductRepresentationModel

process_logger = logging.getLogger("process")


def import_omnibus_prices_from_csv(file: str, pim_shop_idx: str, currency: str):
    bev = ImportOmnibusPriceFromCsvEvent(channel_idx=pim_shop_idx, is_ongoing_event=True)

    with open(file) as csvfile:
        reader = csv.DictReader(csvfile)
        try:
            for row in reader:
                sku = row["sku"]
                omnibus_price = row["omnibus_price"]
                date_from = row["date_from"]
                date_from = datetime.strptime(date_from, "%d.%m.%Y") if date_from else None

                try:
                    product = ProductRepresentationModel.objects.get(sku=sku)
                except ObjectDoesNotExist:
                    print(f"E[{sku}],", end="")
                    process_logger.error(f"Product with sku {sku} does not exist in Omnibus")
                    continue

                try:
                    channel = Channel.objects.get(idx=pim_shop_idx)
                except ObjectDoesNotExist:
                    print(f"E[{sku}],", end="")
                    process_logger.error(f"Channel with idx {pim_shop_idx} does not exist in Omnibus")
                    continue

                try:
                    op = OmnibusPrice.objects.get(product=product, channel=channel, currency=currency.upper())
                    op.omnibus_price = Decimal(omnibus_price)
                    op.price_from_status = PriceFromStatus.SPECIAL_PRICE
                    op.save()
                    print("U,", end="")
                except ObjectDoesNotExist:
                    op = OmnibusPrice.objects.create(
                        product=product,
                        channel=channel,
                        currency=currency.upper(),
                        omnibus_price=omnibus_price,
                        price_from_status=PriceFromStatus.SPECIAL_PRICE,
                    )
                    print("C,", end="")

                if date_from:
                    op.modify_modified_at_by_raw_sql(date_from)

        except Exception as e:
            process_logger.exception(e)
            bev.finish_with_error(finish_tag="Error")
            return
