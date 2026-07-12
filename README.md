# entirius-django-omnibus

Omnibus (EU price directive) lowest-price tracking for Volkanos: keeps a product price history
and computes the lowest price of the last 30 days across non-exclusive, admin-flagged
omnibus promotions. Integrates with `django_checkout` (cart discount rules),
`django_pricemanager` (price lists) and `django_pim` (product data).

## Installation

```shell
pip install entirius-django-omnibus
```

## Configuration

Optional settings (see `src/django_omnibus/settings.py`): `BULK_SIZE_OMNIBUS`,
`APPLIED_SPECIAL_PRICE_WHEN_NULL_VALIDITY_DATES`, `PRICELIST_OMNIBUS_FILTER_DATE_MECHANISM`.

## Development

```shell
make install   # uv sync (incl. extras)
make test      # run tests
make check     # ruff lint + format-check
```

## Docs

Functional description: `docs/README.md`.

## License

MPL-2.0
