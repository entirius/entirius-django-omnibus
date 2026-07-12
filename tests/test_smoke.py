# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Smoke test: every public submodule imports cleanly under a configured Django."""

import importlib

import pytest

MODULES = [
    "django_omnibus.apps",
    "django_omnibus.settings",
    "django_omnibus.models",
    "django_omnibus.models.omnibus_price",
    "django_omnibus.models.product_representation",
    "django_omnibus.admin",
    "django_omnibus.bi",
    "django_omnibus.domain.dto.product_representation",
    "django_omnibus.worker.calculate_omnibus_price",
    "django_omnibus.worker.fill_omnibus_product_representation",
    "django_omnibus.worker.import_omnibus_prices_from_csv",
    "django_omnibus.management.commands.calculate-omnibus-price",
    "django_omnibus.management.commands.fill-omnibus-product-representation-from-pim",
    "django_omnibus.management.commands.import-omnibus-prices-from-csv",
]


@pytest.mark.parametrize("module", MODULES)
def test_module_imports(module):
    importlib.import_module(module)
