# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from bievents import BiEventAbstract
from django.conf import settings

BI_SOURCE = "django-omnibus"
BI_ENVIRONMENT = settings.BI_ENVIRONMENT
BI_BUSINESS_UNIT = settings.BI_BUSINESS_UNIT


class EventAbstract(BiEventAbstract):
    details_type = "Event Abstract"
    version = 1

    def __init__(self, **kwargs):
        kwargs["source"] = BI_SOURCE
        kwargs["environment"] = BI_ENVIRONMENT
        kwargs["business_unit"] = BI_BUSINESS_UNIT
        super().__init__(**kwargs)


class FillOmnibusPricesEvent(EventAbstract):
    version = 1

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class FillOmnibusPricesForChannelEvent(EventAbstract):
    version = 1

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class FillSingleOmnibusPriceEvent(EventAbstract):
    details_type = "Fill Single Omnibus Price"
    version = 1

    def __init__(
        self,
        channel_idx: str = None,
        product: str = None,
        lowest_price: str = None,
        omnibus_price_status: str = None,
        currency: str = None,
        **kwargs,
    ):
        self.details = {
            "channel_idx": channel_idx,
            "sku": product,
            "omnibus_price": lowest_price,
            "omnibus_price_status": omnibus_price_status,
            "currency": currency,
        }
        super().__init__(**kwargs)


class FillProductRepresentationOmnibusEvent(EventAbstract):
    details_type = "Fill Omnibus Product Representation From PIM"
    version = 1

    def __init__(self, channel_idx, **kwargs):
        self.details = {
            "channel_idx": channel_idx,
            "product_representations_existed": None,
            "product_representations_created": None,
            "product_representations_updated": None,
            "product_representations_skipped": None,
        }
        super().__init__(**kwargs)


class ImportOmnibusPriceFromCsvEvent(EventAbstract):
    details_type = "Import Omnibus Price From CSV"
    version = 1

    def __init__(self, channel_idx, **kwargs):
        self.details = {"channel_idx": channel_idx, "omnibus_prices_imported": None, "omnibus_prices_skipped": None}
        super().__init__(**kwargs)
