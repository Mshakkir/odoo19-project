from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    sale_customer_reference = fields.Char(
        string="Customer Reference",
        compute="_compute_sale_customer_reference",
        store=True,
        readonly=False,   # Allow manual edits after compute populates it
    )

    # Computed Many2one to the sale order — makes origin clickable
    sale_order_link_id = fields.Many2one(
        comodel_name='sale.order',
        string="Sales Order",
        compute="_compute_sale_customer_reference",
        store=True,
        readonly=True,
    )

    @api.depends('sale_id', 'sale_id.client_order_ref', 'origin')
    def _compute_sale_customer_reference(self):
        for picking in self:
            ref = False
            sale = False

            # Method 1: via direct sale_id link (most reliable)
            if picking.sale_id:
                sale = picking.sale_id
                ref = picking.sale_id.client_order_ref or False

            # Method 2: via origin field (works for existing/older records)
            if not sale and picking.origin:
                sale = self.env['sale.order'].sudo().search(
                    [('name', '=', picking.origin)],
                    limit=1
                )
                if sale and sale.client_order_ref:
                    ref = sale.client_order_ref

            picking.sale_customer_reference = ref
            picking.sale_order_link_id = sale.id if sale else False