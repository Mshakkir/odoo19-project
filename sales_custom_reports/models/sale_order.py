# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def get_sales_report_data(self, report_type, record_id=None, date_from=None, date_to=None):
        """
        Get sales report data based on report type
        """
        domain = [('state', 'in', ['sale', 'done'])]

        if date_from:
            domain.append(('date_order', '>=', date_from))
        if date_to:
            domain.append(('date_order', '<=', date_to))

        if report_type == 'product' and record_id:
            # Get sale order lines with specific product
            order_lines = self.env['sale.order.line'].search([
                ('product_id', '=', record_id),
                ('order_id.state', 'in', ['sale', 'done'])
            ])
            if date_from:
                order_lines = order_lines.filtered(
                    lambda l: l.order_id.date_order >= fields.Date.from_string(date_from))
            if date_to:
                order_lines = order_lines.filtered(lambda l: l.order_id.date_order <= fields.Date.from_string(date_to))

            orders = order_lines.mapped('order_id')

        elif report_type == 'category' and record_id:
            # Get products in category
            products = self.env['product.product'].search([
                ('categ_id', '=', record_id)
            ])
            order_lines = self.env['sale.order.line'].search([
                ('product_id', 'in', products.ids),
                ('order_id.state', 'in', ['sale', 'done'])
            ])
            if date_from:
                order_lines = order_lines.filtered(
                    lambda l: l.order_id.date_order >= fields.Date.from_string(date_from))
            if date_to:
                order_lines = order_lines.filtered(lambda l: l.order_id.date_order <= fields.Date.from_string(date_to))

            orders = order_lines.mapped('order_id')

        elif report_type == 'partner' and record_id:
            domain.append(('partner_id', '=', record_id))
            orders = self.search(domain)

        elif report_type == 'warehouse' and record_id:
            domain.append(('warehouse_id', '=', record_id))
            orders = self.search(domain)

        elif report_type == 'salesman' and record_id:
            domain.append(('user_id', '=', record_id))
            orders = self.search(domain)
        else:
            orders = self.browse()

        return orders