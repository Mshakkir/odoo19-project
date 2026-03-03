from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    sale_customer_reference = fields.Char(
        string="Customer Reference",
        compute="_compute_sale_customer_reference",
        store=True,
        readonly=True,
    )

    @api.depends('sale_id', 'sale_id.client_order_ref', 'origin')
    def _compute_sale_customer_reference(self):
        for picking in self:
            # First try via sale_id (direct Many2one set by sale_stock module)
            if picking.sale_id:
                picking.sale_customer_reference = picking.sale_id.client_order_ref or False
            else:
                # Fallback: search by origin field
                sale = self.env['sale.order'].search(
                    [('name', '=', picking.origin)],
                    limit=1
                )
                picking.sale_customer_reference = sale.client_order_ref if sale else False