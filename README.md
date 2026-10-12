# entirius-django-omnibus

A Django module that tracks the lowest recent price of each product in Entirius, the open-source modular ecommerce
platform. It implements the EU Omnibus directive: when a product is on promotion, the storefront shows the lowest
price of the 30 days before it, computed here from the price history.

[![PyPI](https://img.shields.io/pypi/v/entirius-django-omnibus.svg)](https://pypi.org/project/entirius-django-omnibus/)
[![Python](https://img.shields.io/pypi/pyversions/entirius-django-omnibus.svg)](https://pypi.org/project/entirius-django-omnibus/)
[![License: MPL-2.0](https://img.shields.io/badge/license-MPL--2.0-blue.svg)](https://github.com/entirius/entirius-django-omnibus/blob/develop/LICENSE)

## What it does

- Computes the lowest gross price of the last 30 days per product, currency and sales channel.
- Detects whether the current price is a promotion and records the omnibus status.
- Takes cart discount rules flagged for omnibus into account.
- Keeps its own SKU-keyed product list, filled from the product module.
- Imports omnibus prices from a CSV file.

## Installation

```shell
uv add entirius-django-omnibus
pip install entirius-django-omnibus
```

```python
INSTALLED_APPS = [
    ...
    "django_pim",
    "django_pricemanager",
    "django_checkout",
    "django_omnibus",
]
```

The module has no HTTP endpoints, so there is no URL include. Required settings: `BI_ENVIRONMENT` and
`BI_BUSINESS_UNIT` (read at import). Optional settings (`BULK_SIZE_OMNIBUS`,
`APPLIED_SPECIAL_PRICE_WHEN_NULL_VALIDITY_DATES`, `PRICELIST_OMNIBUS_FILTER_DATE_MECHANISM`) are described in
https://github.com/entirius/entirius-django-omnibus/blob/develop/AGENTS.md (section Settings).

## Quick start

```python
from django_omnibus.worker.fill_omnibus_product_representation import fill_omnibus_product_representation_from_pim

fill_omnibus_product_representation_from_pim(pim_shop_idx="default")
```

Then calculate the prices, for every channel or for one:

```shell
python manage.py calculate-omnibus-price
python manage.py calculate-omnibus-price --channel_idx default
```

## Requirements

- Python 3.11 or newer, Django 5.0 or newer.
- PostgreSQL.
- Entirius packages pulled in: `entirius-django-checkout` (discount rules), `entirius-django-pricemanager` (channels,
  price lists, price history), `entirius-django-pim` (products), `entirius-py-idx-normalizator` (SKU validation),
  `entirius-py-bievents` (events).

## Documentation

- Module docs: https://github.com/entirius/entirius-django-omnibus/tree/develop/docs
- Entirius documentation: https://docs.entirius.com/
- Changelog: https://github.com/entirius/entirius-django-omnibus/blob/develop/CHANGELOG.md

## Part of Entirius

This module runs inside the Entirius backend service (Volkanos), next to the pricing, checkout and product modules.

- Backend service: https://github.com/entirius/entirius-service-volkanos
- Docker harness: https://github.com/entirius/entirius-zeno
- Sibling modules: https://github.com/entirius/entirius-django-pricemanager,
  https://github.com/entirius/entirius-django-checkout, https://github.com/entirius/entirius-django-matrix

## Development

```shell
make install     # sync dependencies (uv)
make check       # lint + format check (ruff)
make test        # test suite (pytest + pytest-django, needs PostgreSQL via DATABASE_URL)
```

Development and agent instructions: https://github.com/entirius/entirius-django-omnibus/blob/develop/AGENTS.md

## License

Mozilla Public License 2.0 (MPL-2.0) — see https://github.com/entirius/entirius-django-omnibus/blob/develop/LICENSE.
