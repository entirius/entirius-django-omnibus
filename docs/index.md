---
title: Omnibus
description: EU Omnibus directive compliance — computes the lowest price from the last 30 days for promotion display.
sidebar:
  label: Overview
  collapsed: true
---

django-omnibus implements the EU Omnibus directive — when a product is on promotion, the storefront must display the lowest price from the 30 days preceding the promotion. This module computes that price from PriceManager's `PriceHistory` and writes it to `OmnibusPrice` rows that the storefront reads.

## What It Does

- Reads `CurrentPrice` (active prices) and `PriceHistory` (audit log) from `django-pricemanager`
- For every `(product_sku, currency)` pair active in a channel, computes the minimum gross price observed in the last 30 days (configurable)
- Detects whether the current price is a promotion (`special_*` fields set) and determines omnibus status
- Writes one `OmnibusPrice` row per `(product, currency, channel)` — single source of truth for storefront display

## Architecture

```
django_omnibus/
├── models/omnibus_price.py        # OmnibusPrice (product, currency, channel, omnibus_price, status)
├── worker/calculate_omnibus_price.py  # Bulk min-gross calculator
└── management/commands/calculate-omnibus-price.py
```

Triggered via management command on a Celery beat schedule (typically nightly).

## Consumers

- `django-pim` — `RealProduct.omnibus_price` synced via `fill-omnibus-product-representation-from-pim` (django-matrix command)
- `django-matrix` — `ProductRepresentation.omnibus_price` exposed in storefront read model
- Storefront — reads `omnibus_price` from Matrix product feed, displays alongside special price

## Dependencies

- `django-pricemanager` — reads `CurrentPrice` + `PriceHistory`
- `django-pim` — `Product`, `RealProduct`, `Shop` reference
- `django-regional` — `Currency` reference (since 2.0.0)
