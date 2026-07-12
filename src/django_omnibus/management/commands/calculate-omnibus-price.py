# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from bievents import bi_django_command_decorator
from django.core.management.base import BaseCommand
from django_pricemanager.models import Channel

from django_omnibus.bi import FillOmnibusPricesEvent
from django_omnibus.worker.calculate_omnibus_price import calculate_omnibus_price


class Command(BaseCommand):
    help = "Calculate Omnibus Price"

    def add_arguments(self, parser):
        parser.add_argument("--channel_idx", type=str)
        parser.add_argument("--sku", type=str)

    @bi_django_command_decorator
    def handle(self, *args, **options):
        channel_idx = options["channel_idx"]
        sku = options["sku"]
        if channel_idx is None:
            channel = Channel.objects.all()
        else:
            channel = Channel.objects.filter(idx=channel_idx)
        if not channel:
            self.stdout.write("Zero channel to calculate")
        else:
            self.stdout.write("Start calculate Omnibus Prices")
        bev = FillOmnibusPricesEvent(is_ongoing_event=True)
        calculate_omnibus_price(channel, sku, self)
        bev.finish_with_success(finish_tag="Omnibus Price has been filled")
