# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.conf import settings

BULK_SIZE_OMNIBUS = getattr(settings, "BULK_SIZE_OMNIBUS", 10)
APPLIED_SPECIAL_PRICE_WHEN_NULL_VALIDITY_DATES = getattr(
    settings, "APPLIED_SPECIAL_PRICE_WHEN_NULL_VALIDITY_DATES", True
)


# In some cases we need to get more than one pricelist to search for omnibus price
# 1 - get only latest pricelist to search for price
# 2 - get last 30 days pricelist to search for price
# 3 - get all pricelists to search for price
PRICELIST_OMNIBUS_FILTER_DATE_MECHANISM = getattr(settings, "PRICELIST_OMNIBUS_FILTER_DATE_MECHANISM", 1)
