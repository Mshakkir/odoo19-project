from odoo import models, fields, api


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    @api.model
    def get_reorder_notifications(self, warehouse_id=False):
        """Get all reordering notifications for dashboard"""
        domain = []

        # Filter by warehouse if specified
        if warehouse_id:
            domain.append(('warehouse_id', '=', warehouse_id))

        # Get user's warehouses if not admin
        user = self.env.user
        if not user.has_group('stock.group_stock_manager'):
            # Get warehouses where user has access
            allowed_warehouses = self.env['stock.warehouse'].search([
                '|', ('company_id', '=', user.company_id.id),
                ('company_id', '=', False)
            ])
            if allowed_warehouses:
                domain.append(('warehouse_id', 'in', allowed_warehouses.ids))

        orderpoints = self.search(domain)
        notifications = []

        for orderpoint in orderpoints:
            product = orderpoint.product_id
            location = orderpoint.location_id

            # Get on-hand quantity
            qty_available = product.with_context(location=location.id).qty_available

            notification_type = False
            message = ""

            # Check if below minimum
            if qty_available < orderpoint.product_min_qty:
                notification_type = 'below_min'
                shortage = orderpoint.product_min_qty - qty_available
                message = f"Below minimum! Current: {qty_available:.2f}, Min: {orderpoint.product_min_qty:.2f}, Shortage: {shortage:.2f}"

            # Check if above maximum
            elif qty_available > orderpoint.product_max_qty:
                notification_type = 'above_max'
                excess = qty_available - orderpoint.product_max_qty
                message = f"Above maximum! Current: {qty_available:.2f}, Max: {orderpoint.product_max_qty:.2f}, Excess: {excess:.2f}"

            # Only add if there's a notification
            if notification_type:
                notifications.append({
                    'id': orderpoint.id,
                    'product_id': product.id,
                    'product_name': product.name,
                    'product_code': product.default_code or '',
                    'warehouse_id': orderpoint.warehouse_id.id,
                    'warehouse_name': orderpoint.warehouse_id.name,
                    'location_name': location.complete_name,
                    'qty_available': qty_available,
                    'product_min_qty': orderpoint.product_min_qty,
                    'product_max_qty': orderpoint.product_max_qty,
                    'product_uom': product.uom_id.name,
                    'notification_type': notification_type,
                    'message': message,
                })

        return notifications

    @api.model
    def get_notification_count(self, warehouse_id=False):
        """Get count of reordering notifications"""
        notifications = self.get_reorder_notifications(warehouse_id)
        return {
            'total': len(notifications),
            'below_min': len([n for n in notifications if n['notification_type'] == 'below_min']),
            'above_max': len([n for n in notifications if n['notification_type'] == 'above_max']),
        }
