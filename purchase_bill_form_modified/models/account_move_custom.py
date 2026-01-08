from odoo import models, fields, api
from odoo.addons.purchase.models.purchase_order import PurchaseOrder


class AccountMove(models.Model):
    _inherit = 'account.move'

    # New fields for vendor bill
    po_number = fields.Many2one(
        'purchase.order',
        string='PO Number',
        domain="[('partner_id', '=', partner_id), ('state', 'in', ['purchase', 'done'])]",
        help='Select Purchase Order'
    )
    goods_receipt_number = fields.Many2one(
        'stock.picking',
        string='Goods Receipt (Delivery In)',
        domain="[('partner_id', '=', partner_id), ('picking_type_id.code', '=', 'incoming')]",
        help='Select Goods Receipt'
    )
    awb_number = fields.Char(
        string='AWB Number',
        help='Air Waybill Number'
    )

    @api.onchange('partner_id')
    def onchange_partner_id_custom(self):
        """Update available PO when vendor is selected"""
        if self.partner_id and self.move_type in ['in_invoice', 'in_refund']:
            # Filter PO and GR based on selected vendor
            pass

    @api.onchange('po_number')
    def onchange_po_number(self):
        """Populate PO details when PO is selected"""
        if self.po_number:
            po = self.po_number
            # Show PO details
            self.ref = f"PO: {po.name}"
            if not self.invoice_date:
                self.invoice_date = fields.Date.today()

            # Optionally populate invoice lines from PO lines
            if not self.invoice_line_ids:
                lines_data = []
                for line in po.order_line:
                    lines_data.append((0, 0, {
                        'product_id': line.product_id.id,
                        'quantity': line.product_qty,
                        'price_unit': line.price_unit,
                        'name': line.name,
                    }))
                self.invoice_line_ids = lines_data

    @api.onchange('goods_receipt_number')
    def onchange_goods_receipt(self):
        """Show GR details"""
        if self.goods_receipt_number:
            gr = self.goods_receipt_number
            if not self.awb_number:
                # You can auto-populate AWB if it's stored in GR
                pass

    def get_vendor_po_numbers(self):
        """Get all unpaid PO numbers for selected vendor"""
        return self.env['purchase.order'].search([
            ('partner_id', '=', self.partner_id.id),
            ('state', 'in', ['purchase', 'done']),
        ])

    def get_vendor_goods_receipts(self):
        """Get all goods receipts for selected vendor"""
        return self.env['stock.picking'].search([
            ('partner_id', '=', self.partner_id.id),
            ('picking_type_id.code', '=', 'incoming'),
            ('state', '=', 'done'),
        ])