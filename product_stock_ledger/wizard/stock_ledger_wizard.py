from odoo import fields, models, api
from odoo.exceptions import UserError
from datetime import datetime

class StockLedgerLine(models.TransientModel):
    _name = 'product.stock.ledger.line'
    _description = 'Product Stock Ledger Line (Transient)'

    wizard_id = fields.Many2one('product.stock.ledger.wizard', ondelete='cascade')
    date = fields.Datetime(string='Date')
    voucher = fields.Char(string='Voucher')
    particulars = fields.Char(string='Particulars')
    move_type = fields.Char(string='Type')
    rec_qty = fields.Float(string='Rec. Qty')
    rec_rate = fields.Float(string='Rec. Rate')
    issue_qty = fields.Float(string='Issue Qty')
    issue_rate = fields.Float(string='Issue Rate')
    balance = fields.Float(string='Balance')
    unit = fields.Char(string='Unit')


class StockLedgerWizard(models.TransientModel):
    _name = "product.stock.ledger.wizard"
    _description = "Product Stock Ledger Wizard"

    product_id = fields.Many2one('product.product', string='Product', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    date_from = fields.Datetime(string='Date From', required=True, default=fields.Datetime.now)
    date_to = fields.Datetime(string='Date To', required=True, default=fields.Datetime.now)

    line_ids = fields.One2many('product.stock.ledger.line', 'wizard_id', string='Ledger Lines')

    def _compute_moves_for_wizard(self):
        """Re-use logic similar to your report code to fetch moves and calculate running balance."""
        product_id = self.product_id.id
        warehouse_id = self.warehouse_id.id if self.warehouse_id else False
        date_from = self.date_from
        date_to = self.date_to

        # Use the same helpers as in your report model — simplified here inline
        StockMove = self.env['stock.move']
        # prepare domain for moves in range
        domain = [
            ('product_id', '=', product_id),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('state', '=', 'done'),
        ]
        if warehouse_id:
            wh = self.env['stock.warehouse'].browse(warehouse_id)
            if wh.view_location_id:
                loc_ids = self.env['stock.location'].search([('id', 'child_of', wh.view_location_id.id)]).ids
                if loc_ids:
                    domain += ['|', ('location_id', 'in', loc_ids), ('location_dest_id', 'in', loc_ids)]

        moves = StockMove.search(domain, order='date asc')

        # calculate opening running balance (same idea as your report)
        opening_domain = [
            ('product_id', '=', product_id),
            ('date', '<', date_from),
            ('state', '=', 'done'),
        ]
        if warehouse_id:
            wh = self.env['stock.warehouse'].browse(warehouse_id)
            if wh.view_location_id:
                loc_ids = self.env['stock.location'].search([('id', 'child_of', wh.view_location_id.id)]).ids
                if loc_ids:
                    opening_domain += ['|', ('location_id', 'in', loc_ids), ('location_dest_id', 'in', loc_ids)]

        prior_moves = StockMove.search(opening_domain)
        running_balance = 0.0
        for pm in prior_moves:
            qty = pm.product_uom_qty or 0.0
            if warehouse_id:
                wh_loc_ids = self.env['stock.location'].search([('id', 'child_of', wh.view_location_id.id)]).ids if wh.view_location_id else []
                dest_in_wh = pm.location_dest_id.id in wh_loc_ids
                src_in_wh = pm.location_id.id in wh_loc_ids
                if dest_in_wh and not src_in_wh:
                    running_balance += qty
                elif src_in_wh and not dest_in_wh:
                    running_balance -= qty
            else:
                incoming = (pm.location_dest_id.usage == 'internal' and pm.location_id.usage != 'internal')
                running_balance += qty if incoming else -qty

        # build line dicts
        product = self.product_id
        lines = []
        # Opening line
        lines.append({
            'date': date_from,
            'voucher': 'Opening Balance',
            'particulars': '',
            'move_type': '',
            'rec_qty': 0.0,
            'rec_rate': 0.0,
            'issue_qty': 0.0,
            'issue_rate': 0.0,
            'balance': running_balance,
            'unit': product.uom_id.name or '',
        })

        # process moves
        for mv in moves:
            # determine incoming/outgoing similar to your implementation
            qty = mv.product_uom_qty or 0.0
            incoming = False
            if warehouse_id:
                wh_loc_ids = self.env['stock.location'].search([('id', 'child_of', wh.view_location_id.id)]).ids if wh.view_location_id else []
                dest_in_wh = mv.location_dest_id.id in wh_loc_ids
                src_in_wh = mv.location_id.id in wh_loc_ids
                if dest_in_wh and not src_in_wh:
                    incoming = True
                elif src_in_wh and not dest_in_wh:
                    incoming = False
                else:
                    incoming = dest_in_wh
            else:
                incoming = (mv.location_dest_id.usage == 'internal' and mv.location_id.usage != 'internal')

            rec_qty = qty if incoming else 0.0
            issue_qty = qty if not incoming else 0.0

            rate = mv.price_unit if hasattr(mv, 'price_unit') and mv.price_unit else (mv.product_id.standard_price or 0.0)

            if rec_qty:
                running_balance += rec_qty
            else:
                running_balance -= issue_qty

            lines.append({
                'date': mv.date,
                'voucher': mv.reference or mv.name or '',
                'particulars': (mv.partner_id.name + ' - ' if mv.partner_id else '') + (mv.location_id.complete_name or '') + ' → ' + (mv.location_dest_id.complete_name or ''),
                'move_type': mv.picking_type_id.name if mv.picking_type_id else 'Stock Move',
                'rec_qty': rec_qty,
                'rec_rate': rate if rec_qty else 0.0,
                'issue_qty': issue_qty,
                'issue_rate': rate if issue_qty else 0.0,
                'balance': running_balance,
                'unit': mv.product_uom.name if mv.product_uom else (product.uom_id.name or ''),
            })

        return lines

    def action_preview(self):
        """Fill wizard One2many with computed lines and stay on modal (preview)."""
        self.ensure_one()
        # remove existing transient lines
        self.line_ids.unlink()
        lines = self._compute_moves_for_wizard()
        to_create = []
        for ln in lines:
            to_create.append((0, 0, {
                'date': ln['date'],
                'voucher': ln['voucher'],
                'particulars': ln['particulars'],
                'move_type': ln['move_type'],
                'rec_qty': ln['rec_qty'],
                'rec_rate': ln['rec_rate'],
                'issue_qty': ln['issue_qty'],
                'issue_rate': ln['issue_rate'],
                'balance': ln['balance'],
                'unit': ln['unit'],
            }))
        self.line_ids = to_create
        # return nothing so wizard stays open — the user sees lines in the modal

    def action_print_report(self):
        """Print PDF using existing report action; pass data as before."""
        data = {
            'product_id': self.product_id.id,
            'warehouse_id': self.warehouse_id.id if self.warehouse_id else False,
            'date_from': self.date_from,
            'date_to': self.date_to,
        }
        return self.env.ref('product_stock_ledger.action_report_product_stock_ledger').report_action(self, data=data)







# # product_stock_ledger/wizard/stock_ledger_wizard.py
# from odoo import fields, models, api, _
# from odoo.exceptions import UserError
#
# class StockLedgerWizard(models.TransientModel):
#     _name = "product.stock.ledger.wizard"
#     _description = "Product Stock Ledger Wizard"
#
#     product_id = fields.Many2one('product.product', string='Product', required=True)
#     warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=False)
#     date_from = fields.Datetime(string='Date From', required=True, default=fields.Datetime.now)
#     date_to = fields.Datetime(string='Date To', required=True, default=fields.Datetime.now)
#
#     def action_print_report(self):
#         data = {
#             'product_id': self.product_id.id,
#             'warehouse_id': self.warehouse_id.id if self.warehouse_id else False,
#             'date_from': self.date_from,
#             'date_to': self.date_to,
#         }
#         return self.env.ref('product_stock_ledger.action_report_product_stock_ledger').report_action(self, data=data)
