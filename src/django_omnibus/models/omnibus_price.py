# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging
from enum import unique

from django.db import models
from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


@unique
class PriceFromStatus(TextChoices):
    NOT_DEFINED = "Not defined", _("Not defined")
    DISCOUNT = "Discounted price", _("Discounted price")
    NORMAL_PRICE = "Normal price", _("Normal price")
    SPECIAL_PRICE = "Special price", _("Special price")


class OmnibusPrice(models.Model):
    product = models.ForeignKey(
        "ProductRepresentation", related_name="omnibus_products", null=False, blank=False, on_delete=models.CASCADE
    )
    omnibus_price = models.DecimalField(max_digits=19, decimal_places=4, null=True, blank=True)
    price_status = models.CharField(max_length=20, default=PriceFromStatus.NOT_DEFINED, choices=PriceFromStatus.choices)
    omnibus_price_status = models.CharField(
        max_length=20, default=PriceFromStatus.NOT_DEFINED, choices=PriceFromStatus.choices
    )
    current_promotion_date_start = models.DateTimeField(null=True, blank=True)
    current_promotion_price = models.DecimalField(max_digits=19, decimal_places=4, null=True, blank=True)
    last_promotion_date_end = models.DateTimeField(null=True, blank=True)
    last_promotion_price = models.DecimalField(max_digits=19, decimal_places=4, null=True, blank=True)
    last_promotion_price_status = models.CharField(
        max_length=20, default=PriceFromStatus.NOT_DEFINED, choices=PriceFromStatus.choices, null=True, blank=True
    )
    modified_at = models.DateTimeField(auto_now=True)
    currency = models.CharField(max_length=3)
    channel = models.ForeignKey(
        "django_pricemanager.Channel",
        related_name="omnibus_products_channel",
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        default=None,
    )
    objects = models.Manager()

    def modify_modified_at_by_raw_sql(self, modified_at):
        # This method is used to modify the modified_at field by raw SQL query. I cant override the save method because it's too complicated.
        from django.db import connection

        if modified_at is None:
            return

        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE django_omnibus_omnibusprice SET modified_at = %s WHERE id = %s", [modified_at, self.pk]
            )
