# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from django.contrib import admin

from django_omnibus.models import OmnibusPrice, ProductRepresentation


@admin.register(ProductRepresentation)
class ProductRepresentationAdmin(admin.ModelAdmin):
    model = ProductRepresentation
    fields = ["sku"]
    list_display = ["sku"]
    search_fields = ["sku"]


@admin.register(OmnibusPrice)
class OmnibusPriceAdmin(admin.ModelAdmin):
    model = OmnibusPrice

    list_display = [
        "product",
        "omnibus_price",
        "currency",
        "omnibus_price_status",
        "current_promotion_price",
        "modified_at",
        "channel",
        "last_promotion_price_status",
    ]
    list_filter = ["channel", "currency", "price_status", "omnibus_price_status", "last_promotion_price_status"]
    search_fields = ["product__sku"]
    readonly_fields = ("modified_at",)
