# AGENTS.md

Omnibus (EU price directive) lowest-price tracking — distribution `entirius-django-omnibus`,
Django app `django_omnibus`.

## Commands

| Command | Meaning |
|---|---|
| `make install` | sync dependencies (uv, incl. extras) |
| `make check` | lint + format-check (ruff) |
| `make fix` | auto-fix lint + format |
| `make test` | test suite (pytest + pytest-django) |

## Conventions

- English only: code, docs, commits, branches, PRs.
- MPL-2.0: every non-trivial source file carries the license header (pre-commit inserts it).
- Toolchain: uv + ruff + hatchling + pytest; all config in `pyproject.toml`; `uv.lock` committed.
- Git flow: `master` (production) + `develop` (integration); changes land via PR; semver tag on `master`.
- Never rename the package / Django app_label / DB table prefix `django_omnibus` — it is a schema contract.
- Migrations are part of the public contract — never edit an already released migration.
- Default: do not commit — git is the user's call.

## Architecture

```
src/django_omnibus/
├── apps.py                 # AppConfig (is_volkanos=True)
├── settings.py             # BULK_SIZE_OMNIBUS, special-price and pricelist mechanisms
├── models/                 # ProductRepresentation (sku-keyed, FK pricemanager.Channel), OmnibusPrice
├── domain/dto/             # marshmallow-dataclass DTO
├── worker/                 # calculate_omnibus_price (checkout discount cross-walk),
│                           # fill_omnibus_product_representation (from pim), CSV import
├── admin.py                # ModelAdmin registrations
├── bi.py                   # BI events (bievents)
├── management/commands/    # calculate-omnibus-price, fill-…-from-pim, import-…-from-csv
└── tests/                  # legacy in-package developer tests (not executed; see Testing)
```

## Dependencies

| Module | Purpose |
|---|---|
| `django_checkout` | discount rules (`DiscountRuleCode`), discount calc DTOs (hard import in worker) |
| `django_pricemanager` | Channel FK + price list reads |
| `django_pim` | product/`RealProduct` source for representations (worker re-raises when absent) |
| `idx_normalizator` | SKU validation on models |
| `bievents` | BI command decorators + events |

## Settings

| Setting | Default | Purpose |
|---|---|---|
| `BULK_SIZE_OMNIBUS` | `10` | bulk size for price recalculation |
| `APPLIED_SPECIAL_PRICE_WHEN_NULL_VALIDITY_DATES` | `True` | treat undated special prices as active |
| `PRICELIST_OMNIBUS_FILTER_DATE_MECHANISM` | `1` | 1=latest / 2=last 30 days / 3=all price lists |

## Testing

```bash
# Postgres required; tests/settings.py reads DATABASE_URL
# (default postgresql://postgres:postgres@localhost:5432/test).
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/test make test
```

Executed suite is an import smoke test (`tests/test_smoke.py`). The legacy developer tests in
`src/django_omnibus/tests/` are outside `testpaths` (they need `mock`/`line_profiler` and write
profiling files) — migrating them to `tests/` is a pending cleanup.

## References

- `docs/README.md` — functional description of the omnibus price algorithm (Polish; translation pending).
