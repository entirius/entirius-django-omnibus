# Changelog

## 3.0.1 — 2026-07-13

- Fix `NameError` on the pricemanager import fallback in the worker.
- Drop phantom marshmallow extras.

## 3.0.0 — 2026-07-13

- Initial public release: EU Omnibus directive compliance — for every
  `(product_sku, currency)` pair active in a channel, computes the lowest
  gross price observed in the last 30 days (configurable) from PriceManager
  price history and writes it to `OmnibusPrice` rows the storefront reads.
- Omnibus display only when a promotion is active; admin decides per cart
  rule whether it counts as an omnibus promotion.
- `Currency` sourced from `django_regional` (single source of truth).
- Migrations squashed into a single initial migration for the Entirius epoch.
