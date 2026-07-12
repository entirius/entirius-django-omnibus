# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from bievents import bi_django_command_decorator
from django.core.management.base import BaseCommand

from django_omnibus.worker.import_omnibus_prices_from_csv import import_omnibus_prices_from_csv


class Command(BaseCommand):
    help = "Import omnibus price from CSV"

    def add_arguments(self, parser):
        parser.add_argument("file", type=str)
        parser.add_argument("pim_shop_idx", type=str)
        parser.add_argument("currency", type=str)

    @bi_django_command_decorator
    def handle(self, *args, **options):
        file = options["file"]
        pim_shop_idx = options["pim_shop_idx"]
        currency = options["currency"]
        import_omnibus_prices_from_csv(file=file, pim_shop_idx=pim_shop_idx, currency=currency)
