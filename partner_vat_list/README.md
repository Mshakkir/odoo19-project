# Partner VAT List (Sales & Purchase)
### Odoo 19 CE Custom Module

---

## Overview

This module adds two **VAT tax list** fields to the Partner (Customer/Vendor) form and automatically applies those taxes to order/invoice lines when a product is selected.

---

## Features

| Feature | Description |
|---|---|
| **Sales VAT List** | Many2many field on partner → Sales section. Holds sale-type taxes. |
| **Purchase VAT List** | Many2many field on partner → Purchase section. Holds purchase-type taxes. |
| **Auto-apply on Sale Orders** | When a product is added to a Sale Order line, the customer's `Sales VAT List` taxes replace the product default taxes. |
| **Auto-apply on Purchase Orders** | When a product is added to a Purchase Order line, the vendor's `Purchase VAT List` taxes replace the product default taxes. |
| **Auto-apply on Invoices/Bills** | Same logic for Customer Invoices / Vendor Bills and their refunds. |

---

## Installation

1. Copy the `partner_vat_list` folder into your Odoo `addons` path.
2. Restart the Odoo server:
   ```bash
   sudo systemctl restart odoo
   # or
   python odoo-bin -c odoo.conf -u partner_vat_list
   ```
3. In the Odoo backend go to **Settings → Apps**, search for **Partner VAT List**, and click **Install**.

---

## Usage

### Step 1 — Configure the partner
1. Open a Customer or Vendor record.
2. Go to the **Sales & Purchase** tab.
3. Under **SALES**, find **Sales VAT List** — select one or more sale taxes.
4. Under **PURCHASE**, find **Purchase VAT List** — select one or more purchase taxes.
5. Save the partner.

### Step 2 — Create a Sale Order / Purchase Order / Invoice
1. Create a new Sale Order and select the configured Customer.
2. Add a product line — the taxes in the line will automatically be replaced by the **Sales VAT List** from the customer.
3. Same applies for Purchase Orders (vendor's **Purchase VAT List**) and Invoices/Bills.

> **Note:** If the partner has no VAT list configured, the product's default taxes are used (standard Odoo behaviour is preserved).

---

## Technical Details

| File | Purpose |
|---|---|
| `models/res_partner.py` | Adds `sale_tax_ids` and `purchase_tax_ids` Many2many fields to `res.partner` |
| `models/sale_order.py` | `@api.onchange('product_id')` on `sale.order.line` — applies partner sale taxes |
| `models/purchase_order.py` | `@api.onchange('product_id')` on `purchase.order.line` — applies partner purchase taxes |
| `models/account_move.py` | `@api.onchange('product_id')` on `account.move.line` — applies partner taxes based on move type |
| `views/res_partner_views.xml` | Inherits `base.view_partner_form` to inject the two fields in the correct groups |

---

## Dependencies

- `base`
- `account`
- `sale`
- `purchase`

---

## License
LGPL-3
