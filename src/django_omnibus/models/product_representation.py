# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import logging

from django.db import IntegrityError, models
from django.db.models import UniqueConstraint
from django.db.models.functions import Lower
from idx_normalizator import validate_sku

from django_omnibus.domain.dto.product_representation import ProductRepresentation as ProductRepresentationDTO

logger_process = logging.getLogger("process")
logger = logging.getLogger(__name__)


class ProductRepresentation(models.Model):
    sku = models.CharField(db_index=True, max_length=128, null=False)
    objects = models.Manager()

    def save(self, *args, **kwargs):
        validate_sku(self.sku)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.sku}"

    class Meta:
        ordering = ["sku"]
        verbose_name_plural = "products representations"
        constraints = [UniqueConstraint(Lower("sku"), name="unique_omnibus_product_sku_in_channel")]

    @staticmethod
    def bulk_update_or_create(products: list[ProductRepresentationDTO]):
        logger.info(f"Omnibus Product Bulk Save is starting for {len(products)} products")

        records_to_update = []
        records_to_create = []
        fields_to_update = []
        product_representations_existed = ProductRepresentation.objects.count()
        cnt = 0
        total = len(products)
        for product in products:
            cnt += 1
            kwargs = {}
            find = ProductRepresentation.objects.filter(sku=product.sku).first()
            if find is None:
                records_to_create.append(ProductRepresentation(sku=product.sku, **kwargs))
            else:
                records_to_update.append(ProductRepresentation(id=find.id, sku=product.sku, **kwargs))
            if cnt % 1000 == 0:
                logger.info(f"Omnibus Product Bulk Save collecting progress {cnt} / {total}")
        logger.info(f"Omnibus Product Bulk Save starting bulk update for {len(records_to_update)} products")

        # updating data
        try:
            ProductRepresentation.objects.bulk_update(records_to_update, ["sku"] + fields_to_update, batch_size=10000)
        except IntegrityError:
            error_list = []
            for record_to_update in records_to_update:
                try:
                    record_to_update.save(update_fields=["sku"] + fields_to_update)
                except IntegrityError as e:
                    error_sku_data = {"sku": record_to_update.sku, "message": str(e)}
                    error_list.append(error_sku_data)
            logger_process.error(
                "List of errors during updating Omnibus ProductRepresentation",
                extra={"details": {"error_list": error_list}},
            )
        logger.info(f"Omnibus Product Bulk Save starting bulk create for {len(records_to_create)} products")

        # creating data
        try:
            ProductRepresentation.objects.bulk_create(records_to_create, batch_size=1000)
        except IntegrityError:
            error_list = []
            for record_to_create in records_to_create:
                try:
                    record_to_create.save()
                except IntegrityError as e:
                    error_sku_data = {"sku": record_to_create.sku, "message": str(e)}
                    error_list.append(error_sku_data)
            logger_process.error(
                "List of errors during creating Omnibus ProductRepresentation",
                extra={"details": {"error_list": error_list}},
            )

        logger.info("Omnibus Product Representation Bulk Save is done")
        report = {
            "product_representations_existed": product_representations_existed,  # to są te, które już istniały wcześniej
            "product_representations_created": len(records_to_create),  # to są te utworzone przez komendę
            "product_representations_skipped": product_representations_existed
            - len(records_to_create),  # to są te, które się nie zmieniły
        }

        return report
