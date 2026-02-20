from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


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

    def _get_delivery_note_field(self):
        """
        Dynamically find the correct field name for Delivery Note Number
        on account.move (added by odoo-mates module).
        Logs all candidate fields to help identify the correct one.
        """
        move_fields = self.env['account.move']._fields

        # Log ALL fields containing 'delivery' or 'note' for debugging
        candidate_fields = [
            fname for fname in move_fields
            if 'delivery' in fname.lower() or 'note' in fname.lower()
        ]
        _logger.info(
            "DELIVERY_INVOICE_BATCH: Fields on account.move containing "
            "'delivery' or 'note': %s", candidate_fields
        )

        # Try known possible field names used by odoo-mates
        possible_names = [
            'delivery_note_number',
            'delivery_note_no',
            'delivery_note',
            'dn_number',
            'note_number',
            'delivery_number',
            'l10n_delivery_note_number',
            'x_delivery_note_number',
        ]

        for fname in possible_names:
            if fname in move_fields:
                _logger.info(
                    "DELIVERY_INVOICE_BATCH: Found delivery note field: %s", fname
                )
                return fname

        _logger.warning(
            "DELIVERY_INVOICE_BATCH: Could not find delivery note number field. "
            "Candidate fields were: %s. "
            "Please check your server log and update possible_names list.",
            candidate_fields
        )
        return None

    def action_create_invoice(self):
        self.ensure_one()

        picking_names = self.picking_ids.mapped('name')
        delivery_note_value = ', '.join(picking_names)

        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': self.invoice_date,
            'invoice_origin': delivery_note_value,
            'journal_id': self.journal_id.id,
            'invoice_line_ids': [],
        }

        # Dynamically find and set the Delivery Note Number field
        dn_field = self._get_delivery_note_field()
        if dn_field:
            invoice_vals[dn_field] = delivery_note_value
            _logger.info(
                "DELIVERY_INVOICE_BATCH: Setting %s = %s",
                dn_field, delivery_note_value
            )
        else:
            _logger.warning(
                "DELIVERY_INVOICE_BATCH: Delivery note number field NOT set. "
                "Check server logs for candidate field names."
            )

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