# product_stock_ledger/models/report_product_ledger.py
from odoo import models, api, fields, _
from datetime import datetime


class ReportProductStockLedger(models.AbstractModel):
    _name = 'report.product_stock_ledger.product_stock_ledger_report'
    _description = 'Product Stock Ledger Report'

    def _get_moves(self, product_id, warehouse_id, date_from, date_to):
        """Return move-like records relevant to the product in date range."""
        domain = [
            ('product_id', '=', product_id),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('state', '=', 'done'),
        ]

        if warehouse_id:
            wh = self.env['stock.warehouse'].browse(warehouse_id)
            if wh.view_location_id:
                loc_ids = self.env['stock.location'].search([
                    ('id', 'child_of', wh.view_location_id.id)
                ]).ids
                if loc_ids:
                    domain += ['|',
                               ('location_id', 'in', loc_ids),
                               ('location_dest_id', 'in', loc_ids)]

        return self.env['stock.move'].search(domain, order='date asc')

    def _compute_line_from_move(self, move, product_id, warehouse_id):
        """Convert a stock.move into ledger line dict."""
        line = {}
        line['date'] = move.date
        line['voucher'] = move.reference or move.name or ''

        # Particulars: partner or location info
        partner = move.partner_id or (move.picking_id.partner_id if move.picking_id else False)
        line['particulars'] = (partner.name + ' - ' if partner else '') + \
                              (move.location_id.complete_name or '') + ' → ' + \
                              (move.location_dest_id.complete_name or '')

        # Type
        line['type'] = move.picking_type_id.name if move.picking_type_id else 'Stock Move'

        # Quantity
        qty = move.product_uom_qty or 0.0

        # Determine incoming vs outgoing
        incoming = False
        if warehouse_id:
            wh = self.env['stock.warehouse'].browse(warehouse_id)
            if wh.view_location_id:
                wh_loc_ids = self.env['stock.location'].search([
                    ('id', 'child_of', wh.view_location_id.id)
                ]).ids

                dest_in_wh = move.location_dest_id.id in wh_loc_ids
                src_in_wh = move.location_id.id in wh_loc_ids

                if dest_in_wh and not src_in_wh:
                    incoming = True
                elif src_in_wh and not dest_in_wh:
                    incoming = False
                else:
                    incoming = dest_in_wh
        else:
            incoming = (move.location_dest_id.usage == 'internal' and
                        move.location_id.usage != 'internal')

        line['rec_qty'] = qty if incoming else 0.0
        line['issue_qty'] = qty if not incoming else 0.0

        # Rate
        rate = 0.0
        if hasattr(move, 'price_unit') and move.price_unit:
            rate = move.price_unit
        else:
            product = move.product_id
            rate = product.standard_price or 0.0

        line['rec_rate'] = rate if line['rec_qty'] else 0.0
        line['issue_rate'] = rate if line['issue_qty'] else 0.0

        # Unit
        line['unit'] = move.product_uom.name if move.product_uom else \
            (move.product_id.uom_id.name if move.product_id else '')

        return line

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data:
            data = {}

        product_id = data.get('product_id')
        warehouse_id = data.get('warehouse_id')
        date_from = data.get('date_from')
        date_to = data.get('date_to')

        product = self.env['product.product'].browse(product_id)

        # Calculate opening balance
        opening_domain = [
            ('product_id', '=', product_id),
            ('date', '<', date_from),
            ('state', '=', 'done'),
        ]

        if warehouse_id:
            wh = self.env['stock.warehouse'].browse(warehouse_id)
            if wh.view_location_id:
                loc_ids = self.env['stock.location'].search([
                    ('id', 'child_of', wh.view_location_id.id)
                ]).ids
                if loc_ids:
                    opening_domain += ['|',
                                       ('location_id', 'in', loc_ids),
                                       ('location_dest_id', 'in', loc_ids)]

        prior_moves = self.env['stock.move'].search(opening_domain)
        running_balance = 0.0

        for pm in prior_moves:
            qty = pm.product_uom_qty or 0.0

            if warehouse_id:
                wh = self.env['stock.warehouse'].browse(warehouse_id)
                if wh.view_location_id:
                    wh_loc_ids = self.env['stock.location'].search([
                        ('id', 'child_of', wh.view_location_id.id)
                    ]).ids

                    dest_in_wh = pm.location_dest_id.id in wh_loc_ids
                    src_in_wh = pm.location_id.id in wh_loc_ids

                    if dest_in_wh and not src_in_wh:
                        running_balance += qty
                    elif src_in_wh and not dest_in_wh:
                        running_balance -= qty
            else:
                incoming = (pm.location_dest_id.usage == 'internal' and
                            pm.location_id.usage != 'internal')
                running_balance += qty if incoming else -qty

        # Get moves in date range
        moves = self._get_moves(product_id, warehouse_id, date_from, date_to)
        lines = []

        # Opening line
        lines.append({
            'date': fields.Datetime.to_string(date_from) if date_from else '',
            'voucher': 'Opening Balance',
            'particulars': '',
            'type': '',
            'rec_qty': 0.0,
            'rec_rate': 0.0,
            'issue_qty': 0.0,
            'issue_rate': 0.0,
            'balance': running_balance,
            'unit': product.uom_id.name,
        })

        # Process moves
        for mv in moves:
            l = self._compute_line_from_move(mv, product_id, warehouse_id)
            if l['rec_qty']:
                running_balance += l['rec_qty']
            else:
                running_balance -= l['issue_qty']
            l['balance'] = running_balance
            l['date'] = fields.Datetime.to_string(l['date']) if l['date'] else ''
            lines.append(l)

        # Calculate totals
        total_rec = sum(l['rec_qty'] for l in lines)
        total_issue = sum(l['issue_qty'] for l in lines)

        return {
            'doc_ids': docids,
            'doc_model': 'product.product',
            'data': data,
            'product': product,
            'lines': lines,
            'total_rec': total_rec,
            'total_issue': total_issue,
            'company': self.env.company,
        }




# product_stock_ledger/models/report_product_ledger.py
# from odoo import models, api, _
# from datetime import datetime
#
# class ReportProductStockLedger(models.AbstractModel):
#     _name = 'report.product_stock_ledger.product_stock_ledger_report'
#     _description = 'Product Stock Ledger Report'
#
#     def _get_moves(self, product_id, warehouse_id, date_from, date_to):
#         """Return move-like records relevant to the product in date range.
#            This implementation uses stock.move records. Adjust for your flows."""
#         domain = [
#             ('product_id', '=', product_id),
#             ('date', '>=', date_from),
#             ('date', '<=', date_to),
#             ('state', 'in', ('done',)),
#         ]
#         # optionally filter by warehouse (internal locations belonging to warehouse)
#         if warehouse_id:
#             wh = self.env['stock.warehouse'].browse(warehouse_id)
#             # restrict to moves where source or dest location is within this warehouse's view locations
#             loc_ids = wh.view_location_id and wh.view_location_id._get_child_locations() or None
#             if loc_ids:
#                 domain += ['|', ('location_id', 'child_of', loc_ids.id), ('location_dest_id', 'child_of', loc_ids.id)]
#         return self.env['stock.move'].search(domain, order='date asc')
#
#     def _compute_line_from_move(self, move, product_id, warehouse_id):
#         """Convert a stock.move into ledger line dict.
#            We decide whether it's incoming or outgoing relative to warehouse internal locs."""
#         line = {}
#         line['date'] = move.date
#         line['voucher'] = move.picking_name or move._origin.name or (move.origin or '')
#         # Particulars: partner or company contextual text
#         partner = move.partner_id or (move.picking_id.partner_id if move.picking_id else None)
#         line['particulars'] = (partner.name + ' - ' if partner else '') + (move.location_id.name or '') + ' → ' + (move.location_dest_id.name or '')
#         # Type
#         line['type'] = move.picking_code or (move.picking_type_id and move.picking_type_id.name) or 'Stock Move'
#         # qty: if move is into warehouse internal location -> received (positive)
#         qty = move.product_qty if hasattr(move, 'product_qty') else (move.quantity_done if hasattr(move, 'quantity_done') else 0.0)
#         # Determine incoming vs outgoing relative to warehouse (if provided)
#         incoming = True
#         if warehouse_id:
#             # treat move dest internal as incoming; if src internal as outgoing
#             wh = self.env['stock.warehouse'].browse(warehouse_id)
#             wh_loc = wh.view_location_id
#             # child_of check:
#             if move.location_dest_id and move.location_dest_id.id and move.location_dest_id.id in wh_loc._get_child_locations().ids:
#                 incoming = True
#             elif move.location_id and move.location_id.id and move.location_id.id in wh_loc._get_child_locations().ids:
#                 incoming = False
#             else:
#                 # fallback: decide by comparing usage
#                 incoming = (move.location_dest_id.usage == 'internal')
#         else:
#             incoming = (move.location_dest_id.usage == 'internal') and (move.location_id.usage != 'internal')
#
#         line['rec_qty'] = qty if incoming else 0.0
#         line['issue_qty'] = qty if not incoming else 0.0
#
#         # Rate: try to get a monetary rate. stock.move may have 'price_unit' if injected by integrations.
#         rate = 0.0
#         # try purchase price or move valuation_layer
#         if hasattr(move, 'price_unit') and move.price_unit:
#             rate = move.price_unit
#         else:
#             # fallbacks: try the product standard_price (cost) — user may want actual valuation layer
#             product = move.product_id
#             rate = product.standard_price or 0.0
#
#         line['rec_rate'] = rate if line['rec_qty'] else 0.0
#         line['issue_rate'] = rate if line['issue_qty'] else 0.0
#
#         # quantity unit name
#         line['unit'] = move.product_uom and move.product_uom.name or (move.product_id.uom_id.name if move.product_id else '')
#
#         return line
#
#     def _get_report_values(self, docids, data=None):
#         # data contains wizard selections
#         product_id = data.get('product_id')
#         warehouse_id = data.get('warehouse_id')
#         date_from = data.get('date_from')
#         date_to = data.get('date_to')
#
#         product = self.env['product.product'].browse(product_id)
#
#         moves = self._get_moves(product_id, warehouse_id, date_from, date_to)
#         lines = []
#         running_balance = 0.0
#
#         # optionally compute opening balance by summing moves before date_from
#         # We'll compute opening as the net qty before date_from
#         opening_domain = [
#             ('product_id', '=', product_id),
#             ('date', '<', date_from),
#             ('state', 'in', ('done',)),
#         ]
#         if warehouse_id:
#             wh = self.env['stock.warehouse'].browse(warehouse_id)
#             loc_ids = wh.view_location_id and wh.view_location_id._get_child_locations() or None
#             if loc_ids:
#                 opening_domain += ['|', ('location_id', 'child_of', loc_ids.id), ('location_dest_id', 'child_of', loc_ids.id)]
#         prior_moves = self.env['stock.move'].search(opening_domain)
#         for pm in prior_moves:
#             # similar logic as _compute_line_from_move but only accumulate net
#             qty = pm.product_qty if hasattr(pm, 'product_qty') else (pm.quantity_done if hasattr(pm, 'quantity_done') else 0.0)
#             incoming = (pm.location_dest_id.usage == 'internal') and (pm.location_id.usage != 'internal')
#             if warehouse_id:
#                 wh_loc = wh.view_location_id
#                 if pm.location_dest_id and pm.location_dest_id.id in wh_loc._get_child_locations().ids:
#                     incoming = True
#                 elif pm.location_id and pm.location_id.id in wh_loc._get_child_locations().ids:
#                     incoming = False
#             running_balance += qty if incoming else -qty
#
#         # Opening line
#         lines.append({
#             'date': date_from,
#             'voucher': 'Opening Balance',
#             'particulars': '',
#             'type': '',
#             'rec_qty': 0.0,
#             'rec_rate': 0.0,
#             'issue_qty': 0.0,
#             'issue_rate': 0.0,
#             'balance': running_balance,
#             'unit': product.uom_id.name,
#         })
#
#         # Now iterate actual moves
#         for mv in moves:
#             l = self._compute_line_from_move(mv, product_id, warehouse_id)
#             if l['rec_qty']:
#                 running_balance += l['rec_qty']
#             else:
#                 running_balance -= l['issue_qty']
#             l['balance'] = running_balance
#             # format date string
#             l['date'] = l['date'] and fields.Datetime.to_string(l['date']) or ''
#             lines.append(l)
#
#         # subtotals
#         total_rec = sum(l['rec_qty'] for l in lines)
#         total_issue = sum(l['issue_qty'] for l in lines)
#
#         return {
#             'doc_ids': docids,
#             'doc_model': 'product.product',
#             'data': data,
#             'product': product,
#             'lines': lines,
#             'total_rec': total_rec,
#             'total_issue': total_issue,
#             'company': self.env.user.company_id,
#         }
