# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.


from django_omnibus.bi import FillProductRepresentationOmnibusEvent
from django_omnibus.domain.dto.product_representation import ProductRepresentation
from django_omnibus.models import ProductRepresentation as ProductRepresentationModel


def fill_omnibus_product_representation_from_pim(pim_shop_idx: str):
    bev = FillProductRepresentationOmnibusEvent(channel_idx=pim_shop_idx, is_ongoing_event=True)
    try:
        from django_pim.models import ConfigurableLink, Product, RealProduct
    except ImportError:
        bev.finish_with_exception(Exception("Does not have access to django_pim module"))
        raise Exception("fill_omnibus_product_representation_from_pim does not have access to django_pim module")
    try:
        products = []
        pim_products: list[Product] = Product.objects.filter(shop__idx=pim_shop_idx)
        for pim_product in pim_products:
            product = ProductRepresentation(sku=pim_product.sku)
            products.append(product)
        report = ProductRepresentationModel.bulk_update_or_create(products)
        bev.set_details(report)
        bev.finish_with_success(finish_tag="Product Representation in Omnibus has been filled")
    except Exception as e:
        bev.finish_with_exception(e)
        raise e
