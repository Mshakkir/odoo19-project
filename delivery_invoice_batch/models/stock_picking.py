from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockPickingInvoiceWizard(models.TransientModel):
    _name = 'stock.picking.invoice.wizard'
    _description = 'Create Invoice from Delivery Notes'

    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    picking_ids = fields.Many2many('stock.picking', string='Delivery Notes')
    invoice_date = fields.Date(string='Invoice Date', default=fields.Date.context_today)
    journal_id = fields.Many2one('account.journal', string='Journal',
                                 domain=[('type', '=', 'sale')])

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_ids = self.env.context.get('active_ids', [])
        pickings = self.env['stock.picking'].browse(active_ids)

        if not pickings:
            raise UserError(_('No delivery notes selected.'))

        not_done = pickings.filtered(lambda p: p.state != 'done')
        if not_done:
            raise UserError(_('All delivery notes must be in Done state.'))

        partners = pickings.mapped('partner_id')
        if len(partners) > 1:
            raise UserError(_('All delivery notes must belong to the same customer.'))

        not_outgoing = pickings.filtered(lambda p: p.picking_type_code != 'outgoing')
        if not_outgoing:
            raise UserError(_('Only outgoing delivery orders can be invoiced.'))

        res['partner_id'] = partners[0].id if partners else False
        res['picking_ids'] = [(6, 0, active_ids)]

        journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
        res['journal_id'] = journal.id if journal else False

        return res

    def action_create_invoice(self):
        self.ensure_one()

        # Join all selected delivery note names
        picking_names = self.picking_ids.mapped('name')
        delivery_note_value = ', '.join(picking_names)

        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': self.invoice_date,
            'invoice_origin': delivery_note_value,
            'journal_id': self.journal_id.id,
            # Confirmed field name from odoo-mates module on account.move
            'delivery_note_number': delivery_note_value,
            'invoice_line_ids': [],
        }

        # Collect products from all delivery notes
        for picking in self.picking_ids:
            moves = picking.move_ids if hasattr(picking, 'move_ids') else picking.move_lines

            for move in moves:
                if move.state == 'done':
                    price_unit = move.product_id.list_price or move.product_id.standard_price

                    line_vals = {
                        'product_id': move.product_id.id,
                        'name': move.product_id.display_name,
                        'quantity': move.quantity,
                        'product_uom_id': move.product_uom.id,
                        'price_unit': price_unit,
                        'tax_ids': [(6, 0, move.product_id.taxes_id.ids)],
                    }
                    invoice_vals['invoice_line_ids'].append((0, 0, line_vals))

        if not invoice_vals['invoice_line_ids']:
            raise UserError(_('No products found in the selected delivery notes to invoice.'))

        invoice = self.env['account.move'].create(invoice_vals)

        return {
            'name': _('Invoice'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
        }