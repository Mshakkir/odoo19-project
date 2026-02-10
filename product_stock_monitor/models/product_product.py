from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def get_product_stock_monitor(self, product_id):
        """
        Fetch stock information for a product across all warehouses
        Returns list with warehouse name, quantity, purchase rate, and sales rate
        """
        if not product_id:
            return []

        product = self.env['product.product'].browse(product_id)
        if not product.exists():
            return []

        # Get all warehouses
        warehouses = self.env['stock.warehouse'].search([])

        stock_data = []
        for warehouse in warehouses:
            # Get stock quantity for this warehouse location
            stock_quant = self.env['stock.quant'].search([
                ('product_id', '=', product_id),
                ('location_id', 'child_of', warehouse.lot_stock_id.id),
            ])

            # Sum up quantities
            total_qty = sum(stock_quant.mapped('quantity'))

            # Get purchase rate (standard price / cost price)
            purchase_rate = product.standard_price or 0.0

            # Get sales rate (list price)
            sales_rate = product.list_price or 0.0

            stock_data.append({
                'id': warehouse.id,
                'warehouse_name': warehouse.name,
                'location_stock': warehouse.lot_stock_id.complete_name or '',
                'qty': total_qty,
                'purchase_rate': purchase_rate,
                'sales_rate': sales_rate,
            })

        return stock_data