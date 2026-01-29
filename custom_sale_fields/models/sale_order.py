from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    awb_number = fields.Char(
        string='Shipping Ref #',
        help='Air Waybill Number',
        copy=False
    )



    def _prepare_invoice(self):
        """Override to pass PO Number, AWB, and delivery note to invoice"""
        invoice_vals = super()._prepare_invoice()

        # Transfer PO Number (client_order_ref) to invoice ref field
        if self.client_order_ref:
            invoice_vals['ref'] = self.client_order_ref

        # Transfer AWB Number from Sale Order
        if self.awb_number:
            invoice_vals['awb_number'] = self.awb_number

        # Auto-populate Delivery Note Number from completed delivery orders
        completed_pickings = self.picking_ids.filtered(
            lambda p: p.state == 'done' and p.picking_type_code == 'outgoing'
        )

        if completed_pickings:
            # Use the delivery order NAME (reference) as the delivery note number
            # If there's a custom delivery_note_number field, use that, otherwise use the name
            delivery_note_numbers = []

            for picking in completed_pickings:
                # Priority 1: Custom delivery note number (if manually entered)
                if hasattr(picking, 'delivery_note_number') and picking.delivery_note_number:
                    delivery_note_numbers.append(picking.delivery_note_number)
                # Priority 2: Use the delivery order reference (MAIN/OUT/00029)
                elif picking.name:
                    delivery_note_numbers.append(picking.name)

            # Join multiple delivery notes with comma if there are multiple deliveries
            if delivery_note_numbers:
                invoice_vals['delivery_note_number'] = ', '.join(delivery_note_numbers)

            # Get AWB from delivery if not set on sale order
            if not self.awb_number:
                for picking in completed_pickings:
                    if hasattr(picking, 'awb_number') and picking.awb_number:
                        invoice_vals['awb_number'] = picking.awb_number
                        break

        return invoice_vals

    def action_confirm(self):
        """Copy AWB number to delivery orders when sale order is confirmed"""
        result = super().action_confirm()

        # Transfer AWB to delivery orders
        if self.awb_number:
            for picking in self.picking_ids.filtered(lambda p: p.picking_type_code == 'outgoing'):
                if not picking.awb_number:
                    picking.awb_number = self.awb_number

        return result