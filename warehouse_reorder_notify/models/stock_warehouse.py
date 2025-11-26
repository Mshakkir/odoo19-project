from odoo import models, fields, api
from datetime import date

class StockWarehouse(models.Model):
    _inherit = "stock.warehouse"

    @api.model
    def run_reorder_activity(self):
        admin = self.env.ref("base.user_admin")

        warehouses = self.search([])

        for wh in warehouses:

            # Warehouse users (only see their warehouse notifications)
            wh_users = self.env['res.users'].search([
                ('warehouse_id', '=', wh.id)
            ])

            # Reordering rules
            rules = self.env['stock.warehouse.orderpoint'].search([
                ('warehouse_id', '=', wh.id)
            ])

            for rule in rules:
                product = rule.product_id
                qty = product.qty_available
                min_qty = rule.qty_min

                # Skip if enough stock
                if qty >= min_qty:
                    continue

                # Notification text
                note_text = f"""
<b>Warehouse:</b> {wh.name}<br/>
<b>Product:</b> {product.display_name}<br/>
<b>Current Qty:</b> {qty}<br/>
<b>Minimum Required:</b> {min_qty}
"""

                # Users: admin + warehouse users
                notify_users = wh_users | admin

                # Create activity for each user
                activity_type = self.env.ref('mail.mail_activity_data_todo')

                for user in notify_users:
                    self.env['mail.activity'].create({
                        'res_model_id': self.env.ref('product.model_product_product').id,
                        'res_id': product.id,
                        'activity_type_id': activity_type.id,
                        'summary': f"Low Stock: {product.display_name}",
                        'note': note_text,
                        'user_id': user.id,
                        'date_deadline': date.today(),
                    })
