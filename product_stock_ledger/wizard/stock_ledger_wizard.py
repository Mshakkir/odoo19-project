# from odoo import fields, models, api, _
# from odoo.exceptions import UserError
#
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
#     # -------------------------
#     # PDF Report
#     # -------------------------
#     def action_print_report(self):
#         data = {
#             'product_id': self.product_id.id,
#             'warehouse_id': self.warehouse_id.id if self.warehouse_id else False,
#             'date_from': self.date_from,
#             'date_to': self.date_to,
#         }
#         return self.env.ref('product_stock_ledger.action_report_product_stock_ledger').report_action(self, data=data)
#
#     # -------------------------
#     # Helper: Remove Old Lines
#     # -------------------------
#     def _clear_old_lines(self):
#         self.env['product.stock.ledger.line'].search([('wizard_id', '=', self.id)]).unlink()
#
#     # -------------------------
#     # View Ledger Lines
#     # -------------------------
#     def action_view_moves(self):
#         self.ensure_one()
#         self._clear_old_lines()
#
#         product = self.product_id
#         date_from = self.date_from
#         date_to = self.date_to
#         warehouse_id = self.warehouse_id.id if self.warehouse_id else False
#
#         # Build stock.move domain
#         domain = [
#             ('product_id', '=', product.id),
#             ('date', '>=', date_from),
#             ('date', '<=', date_to),
#             ('state', '=', 'done'),
#         ]
#         loc_ids = []
#         wh = False
#
#         if warehouse_id:
#             wh = self.env['stock.warehouse'].browse(warehouse_id)
#             if wh.view_location_id:
#                 loc_ids = self.env['stock.location'].search([('id', 'child_of', wh.view_location_id.id)]).ids
#                 domain = [
#                     ('product_id', '=', product.id),
#                     ('date', '>=', date_from),
#                     ('date', '<=', date_to),
#                     ('state', '=', 'done'),
#                     '|',
#                     ('location_id', 'in', loc_ids),
#                     ('location_dest_id', 'in', loc_ids),
#                 ]
#
#         moves = self.env['stock.move'].search(domain, order='date asc')
#
#         running = 0.0  # start balance from 0 (opening removed)
#
#         for mv in moves:
#             qty = mv.product_uom_qty or 0.0
#
#             # Determine incoming/outgoing
#             incoming = False
#             if warehouse_id and wh.view_location_id:
#                 dest_in_wh = mv.location_dest_id.id in loc_ids
#                 src_in_wh = mv.location_id.id in loc_ids
#                 incoming = dest_in_wh and not src_in_wh
#             else:
#                 incoming = (mv.location_dest_id.usage == 'internal' and mv.location_id.usage != 'internal')
#
#             rec_qty = qty if incoming else 0.0
#             issue_qty = qty if not incoming else 0.0
#
#             # Rate
#             rate = getattr(mv, 'price_unit', 0.0) or mv.product_id.standard_price or 0.0
#
#             if rec_qty:
#                 running += rec_qty
#             else:
#                 running -= issue_qty
#
#             # Build particulars
#             partner_name = mv.partner_id.name or (mv.picking_id.partner_id.name if mv.picking_id and mv.picking_id.partner_id else '')
#             particulars = f"{partner_name} - {mv.location_id.complete_name} → {mv.location_dest_id.complete_name}"
#
#             # Create line
#             self.env['product.stock.ledger.line'].create({
#                 'wizard_id': self.id,
#                 'product_id': product.id,
#                 'date': mv.date,
#                 'voucher': mv.reference or mv.name or '',
#                 'particulars': particulars,
#                 'type': mv.picking_type_id.name if mv.picking_type_id else 'Stock Move',
#                 'rec_qty': rec_qty,
#                 'rec_rate': rate if rec_qty else 0.0,
#                 'issue_qty': issue_qty,
#                 'issue_rate': rate if issue_qty else 0.0,
#                 'balance': running,
#                 'uom': mv.product_uom.name if mv.product_uom else product.uom_id.name,
#             })
#
#         # Open list view
#         view = self.env.ref('product_stock_ledger.view_ledger_line_list')
#         return {
#             'name': _('Product Stock Ledger: %s') % (product.display_name,),
#             'type': 'ir.actions.act_window',
#             'res_model': 'product.stock.ledger.line',
#             'view_mode': 'list,form',
#             'views': [(view.id, 'list')],
#             'domain': [('wizard_id', '=', self.id)],
#             'target': 'current',
#             'context': {'create': False, 'edit': False, 'delete': False},
#         }


# from odoo import fields, models, api, _
# from odoo.exceptions import UserError
#
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
#         """Generate PDF report"""
#         data = {
#             'product_id': self.product_id.id,
#             'warehouse_id': self.warehouse_id.id if self.warehouse_id else False,
#             'date_from': self.date_from,
#             'date_to': self.date_to,
#         }
#         return self.env.ref('product_stock_ledger.action_report_product_stock_ledger').report_action(self, data=data)
#
#     def _clear_old_lines(self):
#         # remove any lines tied to this wizard (safety)
#         self.env['product.stock.ledger.line'].search([('wizard_id', '=', self.id)]).unlink()
#
#     def action_view_moves(self):
#         """Compute ledger rows (same logic you used for PDF) and create transient lines,
#            then open a list view of product.stock.ledger.line filtered by this wizard."""
#         self.ensure_one()
#         # remove old lines for this wizard (if any)
#         self._clear_old_lines()
#
#         # reuse your existing report logic to get moves and running balances
#         # For brevity, we'll recompute similar to your report_product_ledger._get_moves/_compute_line_from_move
#         # You can call that logic instead if available.
#
#         product = self.product_id
#         date_from = self.date_from
#         date_to = self.date_to
#         warehouse_id = self.warehouse_id.id if self.warehouse_id else False
#
#         # Build domain for stock.move similar to the report
#         domain = [
#             ('product_id', '=', product.id),
#             ('date', '>=', date_from),
#             ('date', '<=', date_to),
#             ('state', '=', 'done'),
#         ]
#         if warehouse_id:
#             wh = self.env['stock.warehouse'].browse(warehouse_id)
#             if wh.view_location_id:
#                 loc_ids = self.env['stock.location'].search([('id', 'child_of', wh.view_location_id.id)]).ids
#                 if loc_ids:
#                     domain = [
#                         ('product_id', '=', product.id),
#                         ('date', '>=', date_from),
#                         ('date', '<=', date_to),
#                         ('state', '=', 'done'),
#                         '|',
#                         ('location_id', 'in', loc_ids),
#                         ('location_dest_id', 'in', loc_ids),
#                     ]
#
#         moves = self.env['stock.move'].search(domain, order='date asc')
#
#         # Compute opening balance (moves before date_from)
#         opening_domain = [
#             ('product_id', '=', product.id),
#             ('date', '<', date_from),
#             ('state', '=', 'done'),
#         ]
#         if warehouse_id:
#             wh = self.env['stock.warehouse'].browse(warehouse_id)
#             if wh.view_location_id:
#                 loc_ids = self.env['stock.location'].search([('id', 'child_of', wh.view_location_id.id)]).ids
#                 if loc_ids:
#                     opening_domain += ['|',
#                                        ('location_id', 'in', loc_ids),
#                                        ('location_dest_id', 'in', loc_ids)]
#         prior_moves = self.env['stock.move'].search(opening_domain)
#         running = 0.0
#         for pm in prior_moves:
#             qty = pm.product_uom_qty or 0.0
#             if warehouse_id and wh.view_location_id:
#                 wh_loc_ids = loc_ids
#                 dest_in_wh = pm.location_dest_id.id in wh_loc_ids
#                 src_in_wh = pm.location_id.id in wh_loc_ids
#                 if dest_in_wh and not src_in_wh:
#                     running += qty
#                 elif src_in_wh and not dest_in_wh:
#                     running -= qty
#             else:
#                 incoming = (pm.location_dest_id.usage == 'internal' and pm.location_id.usage != 'internal')
#                 running += qty if incoming else -qty
#
#         # Create an opening balance line
#         self.env['product.stock.ledger.line'].create({
#             'wizard_id': self.id,
#             'product_id': product.id,
#             'date': date_from,
#             'voucher': 'Opening Balance',
#             'particulars': '',
#             'type': '',
#             'rec_qty': 0.0,
#             'rec_rate': 0.0,
#             'issue_qty': 0.0,
#             'issue_rate': 0.0,
#             'balance': running,
#             'uom': product.uom_id.name,
#         })
#
#         # Now process moves to create lines with running balance
#         for mv in moves:
#             qty = mv.product_uom_qty or 0.0
#             # Determine incoming/outgoing
#             incoming = False
#             if warehouse_id and wh.view_location_id:
#                 wh_loc_ids = loc_ids
#                 dest_in_wh = mv.location_dest_id.id in wh_loc_ids
#                 src_in_wh = mv.location_id.id in wh_loc_ids
#                 if dest_in_wh and not src_in_wh:
#                     incoming = True
#                 elif src_in_wh and not dest_in_wh:
#                     incoming = False
#                 else:
#                     incoming = dest_in_wh
#             else:
#                 incoming = (mv.location_dest_id.usage == 'internal' and mv.location_id.usage != 'internal')
#
#             rec_qty = qty if incoming else 0.0
#             issue_qty = qty if not incoming else 0.0
#
#             # Rate fallback
#             rate = mv.price_unit if hasattr(mv, 'price_unit') and mv.price_unit else (mv.product_id.standard_price or 0.0)
#
#             if rec_qty:
#                 running += rec_qty
#             else:
#                 running -= issue_qty
#
#             particulars = (mv.partner_id.name if mv.partner_id else (mv.picking_id.partner_id.name if mv.picking_id and mv.picking_id.partner_id else '')) \
#                           + ' - ' + (mv.location_id.complete_name or '') + ' → ' + (mv.location_dest_id.complete_name or '')
#
#             self.env['product.stock.ledger.line'].create({
#                 'wizard_id': self.id,
#                 'product_id': product.id,
#                 'date': mv.date,
#                 'voucher': mv.reference or mv.name or '',
#                 'particulars': particulars,
#                 'type': mv.picking_type_id.name if mv.picking_type_id else 'Stock Move',
#                 'rec_qty': rec_qty,
#                 'rec_rate': rate if rec_qty else 0.0,
#                 'issue_qty': issue_qty,
#                 'issue_rate': rate if issue_qty else 0.0,
#                 'balance': running,
#                 'uom': mv.product_uom.name if mv.product_uom else (product.uom_id.name if product.uom_id else ''),
#             })
#
#         # finally open an action on the transient ledger lines for this wizard
#         view = self.env.ref('product_stock_ledger.view_ledger_line_list')
#         return {
#             'name': _('Product Stock Ledger: %s') % (product.display_name,),
#             'type': 'ir.actions.act_window',
#             'res_model': 'product.stock.ledger.line',
#             'view_mode': 'list,form',
#             'views': [(view.id, 'list')],
#             'domain': [('wizard_id', '=', self.id)],
#             'target': 'current',
#             'context': {'create': False, 'edit': False, 'delete': False},
#         }