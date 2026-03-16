# Hide Cost Fields from Specific Users — Odoo 19 CE
## Module: hide_cost_fields

---

## 3 METHODS EXPLAINED

---

### ✅ METHOD 1 — Custom Module with View Inheritance (THIS MODULE)
**Best for: permanent, maintainable, upgrade-safe solution**

**How it works:**
- Creates a new security group: `Cannot See Cost Price`
- Any view that inherits from the standard product views and
  has `groups_id` pointing to that group will ONLY be applied
  to members of that group
- The inherited view sets `invisible="1"` on the cost fields

**Steps to use:**
1. Copy this module to your Odoo addons path
2. Activate Developer Mode: Settings → Developer Tools → Activate
3. Update App list: Apps → Update App List
4. Install: search "Hide Cost Fields" → Install
5. Go to Settings → Users & Companies → Groups
6. Find "Cannot See Cost Price" under Inventory category
7. Add the users you want to restrict in the "Users" tab
8. Done — those users will no longer see Cost or Total Cost Price

---

### ✅ METHOD 2 — Field-Level Security via ir.model.fields (No Module Needed)
**Best for: quick setup, hides data even from API access**

This method makes the field completely unreadable for specific groups
at the ORM level — the most secure approach.

**Steps:**
1. Enable Developer Mode
2. Go to: Settings → Technical → Database Structure → Fields
3. Search model: `product.template`, field: `standard_price`
4. Open the field record
5. In the "Groups" tab → add your restricted group to
   **"Read Access" exclusion** OR
6. Alternatively create a new group and set field access:
   - Read: only allow `product.group_manager` (not the restricted group)

**Note:** This hides data at ORM level — the column disappears
from all views AND API calls for that user group.

---

### ✅ METHOD 3 — Studio (If Odoo Enterprise / Studio installed)
**Best for: no-code approach**

If you have Odoo Studio:
1. Open the product form
2. Click Studio icon (pencil) top right
3. Click the Cost field → Properties
4. Under "Visibility" → set groups that CAN see it
   (exclude your restricted group)
5. Repeat for the list view column
6. Save

*(Studio is Enterprise only — not available in CE)*

---

## WHICH METHOD TO USE?

| Scenario | Recommended Method |
|---|---|
| Odoo CE, permanent solution | Method 1 (this module) |
| Odoo CE, quick & secure | Method 2 (ir.model.fields) |
| Odoo Enterprise with Studio | Method 3 (Studio) |
| Hide from API too | Method 2 |

---

## IMPORTANT NOTES FOR ODOO 19

### View Inheritance + groups_id behavior:
In Odoo 17+, the `groups_id` field on `ir.ui.view` means:
- The view patch is **only applied** when the current user
  belongs to one of those groups
- So setting `groups_id = group_hide_cost` on an inherited view
  that sets `invisible=1` means:
  **→ Only users in group_hide_cost see the invisible version**

### The "Total Cost Price" column:
This is a computed field `stock_value` on `product.template`
(or similar) in the Inventory list view. You need to find the
exact view XML ID for that inventory product list. Use:

```
Settings → Technical → User Interface → Views
Search: "Products" model: product.template, type: list
```

Find the view that has `stock_value` or `total_cost` column
and add a similar inherited view patch in this module.

---

## FILE STRUCTURE
```
hide_cost_fields/
├── __init__.py
├── __manifest__.py
├── security/
│   └── hide_cost_security.xml   ← defines the group
└── views/
    └── product_views.xml         ← patches the views
```
