# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import datetime
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from django_checkout.models.channel import Channel as CheckoutChannel
from django_checkout.models.discount_code import DiscountCode
from django_checkout.models.discount_rule_code import DiscountRuleCode
from django_checkout.models.product_representation import ProductRepresentation
from django_pim.models import FeatureSet, Product, RealProduct, Shop
from django_pricemanager.models import Channel, Price, PriceList, PriceListStatus, SaleChannel, TaxClass, TaxRate
from django_pricemanager.models import ProductRepresentation as PRPricemanager
from django_regional.models import Country, Currency, Language
from django_regional.models import Currency as RegionalCurrency

from django_omnibus.models import OmnibusPrice
from django_omnibus.models import ProductRepresentation as PROmnibus
from django_omnibus.worker.calculate_omnibus_price import (  # Adjust the import according to your app structure
    calculate_omnibus_price,
)


class CalculateOmnibusPriceTest(TestCase):
    def mid_season_sale_pricelist(self):
        print("configuring mid season sale pricelist - special 179 PLN from 2023-06-01 to 2023-06-15")
        self.mid_season_sale_pricelist = PriceList.objects.create(
            sale_channel=self.sale_channel,
            currency=self.currency,
            status=PriceListStatus.enumClass.READY,
            created_on=timezone.datetime(2023, 6, 1),
        )
        Price.objects.create(
            product=self.product_pricemanger,
            pricelist=self.mid_season_sale_pricelist,
            gross_value=199.0,
            net_value=162.6,
            special_gross_value=179.0,
            tax_rate=self.tax_rate,
            special_net_value=138.2,
            special_from_date=timezone.datetime(2023, 6, 1),
            special_to_date=timezone.datetime(2023, 6, 15),
        )

    def regular_pricelist(self):
        print("configuring regular pricelist - regular price 199 PLN from 2023-06-16 to 2023-07-15")
        self.regular_pricelist = PriceList.objects.create(
            sale_channel=self.sale_channel,
            currency=self.currency,
            country=self.country,
            status=PriceListStatus.enumClass.READY,
            created_on=timezone.datetime(2023, 6, 16),
        )

        Price.objects.create(
            product=self.product_pricemanger,
            pricelist=self.regular_pricelist,
            gross_value=199.0,
            net_value=162.6,
            special_gross_value=None,
            tax_rate=self.tax_rate,
            special_net_value=None,
            special_from_date=None,
            special_to_date=None,
        )

    def sale_pricelist(self):
        print("configuring sale pricelist - special 169 PLN from 2023-07-01 to 2023-07-30")
        self.sale_pricelist = PriceList.objects.create(
            sale_channel=self.sale_channel,
            currency=self.currency,
            country=self.country,
            status=PriceListStatus.enumClass.READY,
            created_on=timezone.datetime(2023, 7, 1),
        )
        Price.objects.create(
            product=self.product_pricemanger,
            pricelist=self.sale_pricelist,
            gross_value=199.0,
            net_value=162.6,
            special_gross_value=169.0,
            tax_rate=self.tax_rate,
            special_net_value=138.2,
            special_from_date=timezone.datetime(2023, 7, 1),
            special_to_date=timezone.datetime(2023, 7, 30),
        )

    def regular_pricelist_second_with_code(self):
        print("configuring regular pricelist with 40% percent code- regular price 199 PLN from 2023-07-16")
        self.regular_pricelist_second_with_code = PriceList.objects.create(
            sale_channel=self.sale_channel,
            currency=self.currency,
            country=self.country,
            status=PriceListStatus.enumClass.READY,
            created_on=timezone.datetime(2023, 7, 16),
        )
        self.rule.is_omnibus = True
        self.rule.save()

        Price.objects.create(
            product=self.product_pricemanger,
            pricelist=self.regular_pricelist_second_with_code,
            gross_value=199.0,
            net_value=162.6,
            tax_rate=self.tax_rate,
            special_gross_value=None,
            special_net_value=None,
            special_from_date=None,
            special_to_date=None,
        )

    def special_pricelist_second(self):
        print("configuring special pricelist with 40% percent code - regular price 199 PLN from 2023-08-01")
        self.special_pricelist_second = PriceList.objects.create(
            sale_channel=self.sale_channel,
            currency=self.currency,
            country=self.country,
            status=PriceListStatus.enumClass.READY,
            created_on=timezone.datetime(2023, 8, 1),
        )

        Price.objects.create(
            product=self.product_pricemanger,
            pricelist=self.special_pricelist_second,
            gross_value=199.0,
            net_value=162.6,
            special_gross_value=169.0,
            tax_rate=self.tax_rate,
            special_net_value=138.2,
            special_from_date=timezone.datetime(2023, 8, 1),
            special_to_date=timezone.datetime(2023, 8, 10),
        )

    def regular_pricelist_second(self):
        print("configuring regular pricelist - regular price 199 PLN from 2023-08-10")
        self.special_pricelist_second = PriceList.objects.create(
            sale_channel=self.sale_channel,
            currency=self.currency,
            country=self.country,
            status=PriceListStatus.enumClass.READY,
            created_on=timezone.datetime(2023, 8, 10),
        )

        self.rule.is_omnibus = False
        self.rule.save()

        Price.objects.create(
            product=self.product_pricemanger,
            pricelist=self.special_pricelist_second,
            gross_value=199.0,
            net_value=162.6,
            special_gross_value=None,
            tax_rate=self.tax_rate,
            special_net_value=None,
            special_from_date=None,
            special_to_date=None,
        )

    def setUp(self):

        lang, created = Language.objects.get_or_create(
            iso2="pl", iso3="pol", defaults={"name_en": "Polish", "name_pl": "Polski"}
        )
        currency, created = RegionalCurrency.objects.get_or_create(
            iso3="PLN", defaults={"name_en": "Polish Zloty", "name_pl": "Złoty"}
        )
        country, created = Country.objects.get_or_create(
            iso2="PL", iso3="POL", defaults={"name_en": "Polish", "name_pl": "Polski"}
        )

        channel = CheckoutChannel.objects.create(
            idx="test_channel",
            label="Test Channel",
            default_language=lang,
            default_currency=currency,
            default_country=country,
        )
        channel.save()
        channel.languages.set([lang])
        channel.currencies.set([currency])
        channel.countries.set([country])
        channel.save()
        many_channels = False
        additional = {}
        if hasattr(DiscountRuleCode, "channel"):
            additional = {"channel": channel}
        elif hasattr(DiscountRuleCode, "channels"):
            many_channels = True

        try:
            from django_checkout.models.discount_mode_of_actions import DiscountModeOfAction
            from django_checkout.models.discount_rule_code import ModifiersForDiscountRule

            self.rule = DiscountRuleCode.objects.create(
                **additional,
                name="Test Discount Rule",
                min_order_amount=0,
                is_omnibus=False,
                modifier=ModifiersForDiscountRule.PERCENT_DISCOUNT,
                extra_value=40,
            )
            if many_channels:
                self.rule.channels.add(channel)

            DiscountCode.objects.create(
                **additional,
                code="TESTCODE",
                rule=self.rule,
                max_used=10000,
                active_from=datetime.datetime(2023, 7, 16),
                active_to=datetime.datetime(2023, 7, 30),
            )
        except ImportError:
            self.rule = DiscountRuleCode.objects.create(
                **additional, name="Test Discount Rule", min_order_amount=0, is_omnibus=False, percent_discount=40
            )
            if many_channels:
                self.rule.channels.add(channel)

            DiscountCode.objects.create(
                **additional,
                code="TESTCODE",
                rule=self.rule,
                max_used=10000,
                active_from=datetime.datetime(2023, 7, 16),
                active_to=datetime.datetime(2023, 7, 30),
            )

        shop = Shop.objects.create(
            idx="test_channel", name="Test Channel", default_language=lang, default_currency=currency
        )
        real_product = RealProduct.objects.create(sku="T-SHIRT-VALE-NAVY")
        test_feature_set = FeatureSet.objects.create(idx="test_feature_set", name="Test Feature Set")
        pim_product = Product.objects.create(
            real_product=real_product, shop=shop, product_class=1, is_enabled=True, feature_set=test_feature_set
        )
        product = ProductRepresentation.objects.create(sku="T-SHIRT-VALE-NAVY", channel=channel)

        self.channel = Channel.objects.create(idx="test_channel", name="Test Channel")
        self.sale_channel = SaleChannel.objects.create(name="Test Channel", idx="test_channel", channel=self.channel)
        self.currency, _ = Currency.objects.get_or_create(
            iso3="PLN", defaults={"name_en": "Polish zloty", "name_pl": "Polski złoty", "symbol": "zł"}
        )
        self.country = "PL"
        self.tax_class = TaxClass.objects.create(name="Standard", idx="standard")
        self.tax_rate = TaxRate.objects.create(rate=0.23, tax_class=self.tax_class, country=self.country)
        self.product_pricemanger = PRPricemanager.objects.create(sku="T-SHIRT-VALE-NAVY", tax_class=self.tax_class)
        self.product_omnibus = PROmnibus.objects.create(sku="T-SHIRT-VALE-NAVY")
        self.days = [
            (6, 1, None, self.mid_season_sale_pricelist),
            (6, 2, None, None),
            (6, 3, None, None),
            (6, 4, None, None),
            (6, 5, None, None),
            (6, 6, None, None),
            (6, 7, None, None),
            (6, 8, None, None),
            (6, 9, None, None),
            (6, 10, None, None),
            (6, 11, None, None),
            (6, 12, None, None),
            (6, 13, None, None),
            (6, 14, None, None),
            (6, 15, None, None),
            (6, 16, None, self.regular_pricelist),
            (6, 17, None, None),
            (6, 18, None, None),
            (6, 19, None, None),
            (6, 20, None, None),
            (6, 20, None, None),
            (6, 21, None, None),
            (6, 22, None, None),
            (6, 23, None, None),
            (6, 24, None, None),
            (6, 25, None, None),
            (6, 26, None, None),
            (6, 27, None, None),
            (6, 28, None, None),
            (6, 29, None, None),
            (6, 30, None, None),
            (7, 1, 179, self.sale_pricelist),
            (7, 2, 179, None),
            (7, 3, 179, None),
            (7, 4, 179, None),
            (7, 5, 179, None),
            (7, 6, 179, None),
            (7, 7, 179, None),
            (7, 8, 179, None),
            (7, 9, 179, None),
            (7, 10, 179, None),
            (7, 11, 179, None),
            (7, 12, 179, None),
            (7, 13, 179, None),
            (7, 14, 179, None),
            (7, 15, 179, None),
            (7, 16, 169.0, self.regular_pricelist_second_with_code),
            (7, 17, 169.0, None),
            (7, 18, 169.0, None),
            (7, 19, 169.0, None),
            (7, 20, 169.0, None),
            (7, 21, 169.0, None),
            (7, 22, 169.0, None),
            (7, 23, 169.0, None),
            (7, 24, 169.0, None),
            (7, 25, 169.0, None),
            (7, 26, 169.0, None),
            (7, 27, 169.0, None),
            (7, 28, 169.0, None),
            (7, 29, 169.0, None),
            (7, 30, 169.0, None),
            (8, 1, 119.4, self.special_pricelist_second),
            (8, 2, 119.4, None),
            (8, 3, 119.4, None),
            (8, 4, 119.4, None),
            (8, 5, 119.4, None),
            (8, 6, 119.4, None),
            (8, 7, 119.4, None),
            (8, 8, 119.4, None),
            (8, 9, 119.4, None),
            (8, 10, None, self.regular_pricelist_second),
            (8, 11, None, None),
        ]

    def print_table_header(self):
        print(
            "________________________________________________________________________________________________________________________________________________________________________________________________________________________"
        )
        print(
            "| month/day | expected price | calculated price | omnibus_price_status | price_status | current_promotion_price | last_promotion_price | last_promotion_price_status | last_promotion_date_end     | current_promotion_date_start |"
        )
        print(
            "________________________________________________________________________________________________________________________________________________________________________________________________________________________"
        )

    def print_table_row(self, month, day, price, omnibus_price):
        print(
            f"| {str(month).zfill(2)}/{str(day).zfill(2)}  | {str(price).ljust(14)} | {str(omnibus_price.omnibus_price).ljust(17)} | {str(omnibus_price.omnibus_price_status).ljust(20)} | {str(omnibus_price.price_status).ljust(12)} | {str(omnibus_price.current_promotion_price).ljust(23)} | {str(omnibus_price.last_promotion_price).ljust(20)} | {str(omnibus_price.last_promotion_price_status).ljust(24)} | {str(omnibus_price.last_promotion_date_end).ljust(24)} | {str(omnibus_price.current_promotion_date_start).ljust(27)} |"
        )

    def test_calculate_omnibus_price(self):
        self.print_table_header()
        for month, day, price, config_function in self.days:
            with patch.object(timezone, "now", return_value=timezone.make_aware(timezone.datetime(2023, month, day))):
                if config_function:
                    config_function()
                handler = MockHandler()
                from line_profiler import LineProfiler

                profiler = LineProfiler()
                profiler.add_function(calculate_omnibus_price)
                profiler.enable_by_count()

                calculate_omnibus_price([self.channel], None, handler)

                profiler.disable_by_count()
                with open("calculate_omnibus_price.txt", "w") as f:
                    profiler.print_stats(f)

                omnibus_price = OmnibusPrice.objects.get(
                    product=self.product_omnibus, currency=self.currency, channel=self.channel
                )
                self.print_table_row(month, day, price, omnibus_price)


class MockHandler:
    class Output:
        def write(self, message):
            pass

    stdout = Output()
