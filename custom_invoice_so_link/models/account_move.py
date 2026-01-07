from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Field to select sales order
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        domain="[('partner_id', '=', partner_id), ('invoice_status', 'in', ['to invoice', 'invoiced'])]",
        help="Select a sales order to create invoice from"
    )

    # Field to display related delivery notes
    delivery_note_ids = fields.Many2many(
        'stock.picking',
        string='Delivery Notes',
        compute='_compute_delivery_notes',
        help="Delivery notes related to this customer"
    )

    @api.depends('partner_id')
    def _compute_delivery_notes(self):
        """Compute delivery notes for the selected customer"""
        for record in self:
            if record.partner_id:
                # Find deliveries for this customer
                deliveries = self.env['stock.picking'].search([
                    ('partner_id', '=', record.partner_id.id),
                    ('picking_type_code', '=', 'outgoing'),
                    ('state', '=', 'done')
                ])
                record.delivery_note_ids = deliveries
            else:
                record.delivery_note_ids = False

    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        """Populate invoice lines from selected sales order"""
        if self.sale_order_id:
            # Clear existing lines
            self.invoice_line_ids = [(5, 0, 0)]

            # Create invoice lines from sales order lines
            invoice_lines = []
            for line in self.sale_order_id.order_line:
                # Only add lines that need to be invoiced
                qty_to_invoice = line.product_uom_qty - line.qty_invoiced

                if qty_to_invoice > 0:
                    invoice_line_vals = {
                        'product_id': line.product_id.id,
                        'name': line.name,
                        'quantity': qty_to_invoice,
                        'price_unit': line.price_unit,
                        'tax_ids': [(6, 0, line.tax_id.ids)],
                        'sale_line_ids': [(6, 0, [line.id])],  # Link to SO line
                    }
                    invoice_lines.append((0, 0, invoice_line_vals))

            self.invoice_line_ids = invoice_lines

            # Set other invoice fields from SO
            self.invoice_origin = self.sale_order_id.name
            self.payment_reference = self.sale_order_id.name

    @api.onchange('partner_id')
    def _onchange_partner_id_custom(self):
        """Clear sales order when customer changes"""
        if self.partner_id:
            self.sale_order_id = False