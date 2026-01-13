from odoo import fields, models, api, _
from odoo.exceptions import UserError


class StockLedgerWizard(models.TransientModel):
    _name = "product.stock.ledger.wizard"
    _description = "Product Stock Ledger Wizard"

    product_id = fields.Many2one('product.product', string='Product', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    date_from = fields.Datetime(string='Date From', required=True, default=fields.Datetime.now)
    date_to = fields.Datetime(string='Date To', required=True, default=fields.Datetime.now)

    # -------------------------
    # PDF Report
    # -------------------------
    def action_print_report(self):
        data = {
            'product_id': self.product_id.id,
            'warehouse_id': self.warehouse_id.id if self.warehouse_id else False,
            'date_from': self.date_from,
            'date_to': self.date_to,
        }
        return self.env.ref('product_stock_ledger.action_report_product_stock_ledger').report_action(self, data=data)

    # -------------------------
    # Helper: Remove Old Lines
    # -------------------------
    def _clear_old_lines(self):
        self.env['product.stock.ledger.line'].search([('wizard_id', '=', self.id)]).unlink()

    # -------------------------
    # Helper: Get Invoice Status
    # -------------------------
    def _get_invoice_status(self, move):
        """Determine invoice status based on move type and related documents."""
        status = 'N/A'

        if move.picking_id:
            picking = move.picking_id

            # For incoming moves (Purchase)
            if picking.picking_type_code == 'incoming':
                # Check for Purchase Order invoicing status
                # Search via purchase order lines linked to this move
                po_lines = self.env['purchase.order.line'].search([
                    ('move_ids', '=', move.id)
                ])

                if po_lines:
                    po = po_lines[0].order_id
                    if po.invoice_status == 'invoiced':
                        status = 'Invoiced'
                    elif po.invoice_status == 'to invoice':
                        status = 'To Invoice'
                    elif po.invoice_status == 'no':
                        status = 'No Invoice'
                    else:
                        status = po.invoice_status.title()
                else:
                    # Try searching by origin
                    if picking.origin:
                        purchase_orders = self.env['purchase.order'].search([
                            ('name', '=', picking.origin)
                        ])
                        if purchase_orders:
                            po = purchase_orders[0]
                            if po.invoice_status == 'invoiced':
                                status = 'Invoiced'
                            elif po.invoice_status == 'to invoice':
                                status = 'To Invoice'
                            elif po.invoice_status == 'no':
                                status = 'No Invoice'
                            else:
                                status = po.invoice_status.title()
                        else:
                            status = 'No PO'
                    else:
                        status = 'No PO'

            # For outgoing moves (Sales)
            elif picking.picking_type_code == 'outgoing':
                # Check for Sales Order invoicing status
                # Search via sale order lines linked to this move
                so_lines = self.env['sale.order.line'].search([
                    ('move_ids', '=', move.id)
                ])

                if so_lines:
                    so = so_lines[0].order_id
                    if so.invoice_status == 'invoiced':
                        status = 'Invoiced'
                    elif so.invoice_status == 'to invoice':
                        status = 'To Invoice'
                    elif so.invoice_status == 'no':
                        status = 'No Invoice'
                    else:
                        status = so.invoice_status.title()
                else:
                    # Try searching by origin
                    if picking.origin:
                        sales_orders = self.env['sale.order'].search([
                            ('name', '=', picking.origin)
                        ])
                        if sales_orders:
                            so = sales_orders[0]
                            if so.invoice_status == 'invoiced':
                                status = 'Invoiced'
                            elif so.invoice_status == 'to invoice':
                                status = 'To Invoice'
                            elif so.invoice_status == 'no':
                                status = 'No Invoice'
                            else:
                                status = so.invoice_status.title()
                        else:
                            status = 'No SO'
                    else:
                        status = 'No SO'

            # For internal transfers
            else:
                status = 'Internal'

        return status

    # -------------------------
    # View Ledger Lines
    # -------------------------
    def action_view_moves(self):
        self.ensure_one()
        self._clear_old_lines()

        product = self.product_id
        date_from = self.date_from
        date_to = self.date_to
        warehouse_id = self.warehouse_id.id if self.warehouse_id else False

        # Build stock.move domain
        domain = [
            ('product_id', '=', product.id),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('state', '=', 'done'),
        ]

        wh = False
        loc_ids = []
        if warehouse_id:
            wh = self.env['stock.warehouse'].browse(warehouse_id)
            if wh.view_location_id:
                loc_ids = self.env['stock.location'].search([
                    ('id', 'child_of', wh.view_location_id.id)
                ]).ids
                domain = [
                    ('product_id', '=', product.id),
                    ('date', '>=', date_from),
                    ('date', '<=', date_to),
                    ('state', '=', 'done'),
                    '|',
                    ('location_id', 'in', loc_ids),
                    ('location_dest_id', 'in', loc_ids),
                ]

        moves = self.env['stock.move'].search(domain, order='date asc')

        running = 0.0  # start balance from 0

        for mv in moves:
            qty = mv.product_uom_qty or 0.0

            # -------------------------
            # Determine Move Type
            # -------------------------
            if warehouse_id and wh.view_location_id:
                dest_in_wh = mv.location_dest_id.id in loc_ids
                src_in_wh = mv.location_id.id in loc_ids

                if dest_in_wh and not src_in_wh:
                    move_type = 'incoming'
                elif src_in_wh and not dest_in_wh:
                    move_type = 'outgoing'
                else:
                    move_type = 'internal'
            else:
                if mv.location_dest_id.usage == 'internal' and mv.location_id.usage != 'internal':
                    move_type = 'incoming'
                elif mv.location_id.usage == 'internal' and mv.location_dest_id.usage != 'internal':
                    move_type = 'outgoing'
                else:
                    move_type = 'internal'

            # -------------------------
            # Determine Rate
            # -------------------------
            rate = 0.0
            if move_type == 'incoming':
                # Purchase move → price from PO or cost
                rate = getattr(mv, 'price_unit', 0.0) or mv.product_id.standard_price or 0.0

            elif move_type == 'outgoing':
                # Sales move → price from Sale Order line
                sale_line = False
                if hasattr(mv, 'sale_line_id') and mv.sale_line_id:
                    sale_line = mv.sale_line_id
                elif mv.picking_id and mv.picking_id.origin:
                    sale_line = self.env['sale.order.line'].search([
                        ('order_id.name', '=', mv.picking_id.origin),
                        ('product_id', '=', mv.product_id.id)
                    ], limit=1)
                if sale_line:
                    rate = sale_line.price_unit
                else:
                    # fallback: product cost
                    rate = mv.product_id.standard_price or 0.0
            else:
                # Internal transfers
                rate = mv.product_id.standard_price or 0.0

            # -------------------------
            # Quantities & Balance
            # -------------------------
            rec_qty = qty if move_type == 'incoming' else 0.0
            issue_qty = qty if move_type == 'outgoing' else 0.0

            if move_type == 'incoming':
                running += rec_qty
            elif move_type == 'outgoing':
                running -= issue_qty

            # -------------------------
            # Particulars / Partner Info
            # -------------------------
            partner_name = (
                    mv.partner_id.name
                    or (mv.picking_id.partner_id.name if mv.picking_id and mv.picking_id.partner_id else '')
            )
            particulars = f"{partner_name} - {mv.location_id.complete_name} → {mv.location_dest_id.complete_name}"

            # -------------------------
            # Get Invoice Status
            # -------------------------
            invoice_status = self._get_invoice_status(mv)

            # -------------------------
            # Create Ledger Line
            # -------------------------
            self.env['product.stock.ledger.line'].create({
                'wizard_id': self.id,
                'product_id': product.id,
                'date': mv.date,
                'voucher': mv.reference or mv.name or '',
                'particulars': particulars,
                'type': (
                    'Receipts' if move_type == 'incoming'
                    else 'Delivery' if move_type == 'outgoing'
                    else 'Internal Transfer'
                ),
                'rec_qty': rec_qty,
                'rec_rate': rate if rec_qty else 0.0,
                'issue_qty': issue_qty,
                'issue_rate': rate if issue_qty else 0.0,
                'balance': running,
                'uom': mv.product_uom.name if mv.product_uom else product.uom_id.name,
                'invoice_status': invoice_status,
            })

        # -------------------------
        # Open Ledger Lines View
        # -------------------------
        view = self.env.ref('product_stock_ledger.view_ledger_line_list')
        return {
            'name': _('Product Stock Ledger: %s') % (product.display_name,),
            'type': 'ir.actions.act_window',
            'res_model': 'product.stock.ledger.line',
            'view_mode': 'list,form',
            'views': [(view.id, 'list')],
            'domain': [('wizard_id', '=', self.id)],
            'target': 'current',
            'context': {'create': False, 'edit': False, 'delete': False},
        }








# from odoo import fields, models, api, _
# from odoo.exceptions import UserError
#
#
# class StockLedgerWizard(models.TransientModel):
#     _name = "product.stock.ledger.wizard"
#     _description = "Product Stock Ledger Wizard"
#
#     product_id = fields.Many2one('product.product', string='Product', required=True)
#     warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
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
#
#         wh = False
#         loc_ids = []
#         if warehouse_id:
#             wh = self.env['stock.warehouse'].browse(warehouse_id)
#             if wh.view_location_id:
#                 loc_ids = self.env['stock.location'].search([
#                     ('id', 'child_of', wh.view_location_id.id)
#                 ]).ids
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
#         running = 0.0  # start balance from 0
#
#         for mv in moves:
#             qty = mv.product_uom_qty or 0.0
#
#             # -------------------------
#             # Determine Move Type
#             # -------------------------
#             if warehouse_id and wh.view_location_id:
#                 dest_in_wh = mv.location_dest_id.id in loc_ids
#                 src_in_wh = mv.location_id.id in loc_ids
#
#                 if dest_in_wh and not src_in_wh:
#                     move_type = 'incoming'
#                 elif src_in_wh and not dest_in_wh:
#                     move_type = 'outgoing'
#                 else:
#                     move_type = 'internal'
#             else:
#                 if mv.location_dest_id.usage == 'internal' and mv.location_id.usage != 'internal':
#                     move_type = 'incoming'
#                 elif mv.location_id.usage == 'internal' and mv.location_dest_id.usage != 'internal':
#                     move_type = 'outgoing'
#                 else:
#                     move_type = 'internal'
#
#             # -------------------------
#             # Determine Rate
#             # -------------------------
#             rate = 0.0
#             if move_type == 'incoming':
#                 # Purchase move → price from PO or cost
#                 rate = getattr(mv, 'price_unit', 0.0) or mv.product_id.standard_price or 0.0
#
#             elif move_type == 'outgoing':
#                 # Sales move → price from Sale Order line
#                 sale_line = False
#                 if hasattr(mv, 'sale_line_id') and mv.sale_line_id:
#                     sale_line = mv.sale_line_id
#                 elif mv.picking_id and mv.picking_id.origin:
#                     sale_line = self.env['sale.order.line'].search([
#                         ('order_id.name', '=', mv.picking_id.origin),
#                         ('product_id', '=', mv.product_id.id)
#                     ], limit=1)
#                 if sale_line:
#                     rate = sale_line.price_unit
#                 else:
#                     # fallback: product cost
#                     rate = mv.product_id.standard_price or 0.0
#             else:
#                 # Internal transfers
#                 rate = mv.product_id.standard_price or 0.0
#
#             # -------------------------
#             # Quantities & Balance
#             # -------------------------
#             rec_qty = qty if move_type == 'incoming' else 0.0
#             issue_qty = qty if move_type == 'outgoing' else 0.0
#
#             if move_type == 'incoming':
#                 running += rec_qty
#             elif move_type == 'outgoing':
#                 running -= issue_qty
#
#             # -------------------------
#             # Particulars / Partner Info
#             # -------------------------
#             partner_name = (
#                 mv.partner_id.name
#                 or (mv.picking_id.partner_id.name if mv.picking_id and mv.picking_id.partner_id else '')
#             )
#             particulars = f"{partner_name} - {mv.location_id.complete_name} → {mv.location_dest_id.complete_name}"
#
#             # -------------------------
#             # Create Ledger Line
#             # -------------------------
#             self.env['product.stock.ledger.line'].create({
#                 'wizard_id': self.id,
#                 'product_id': product.id,
#                 'date': mv.date,
#                 'voucher': mv.reference or mv.name or '',
#                 'particulars': particulars,
#                 'type': (
#                     'Receipts' if move_type == 'incoming'
#                     else 'Delivery' if move_type == 'outgoing'
#                     else 'Internal Transfer'
#                 ),
#                 'rec_qty': rec_qty,
#                 'rec_rate': rate if rec_qty else 0.0,
#                 'issue_qty': issue_qty,
#                 'issue_rate': rate if issue_qty else 0.0,
#                 'balance': running,
#                 'uom': mv.product_uom.name if mv.product_uom else product.uom_id.name,
#             })
#
#         # -------------------------
#         # Open Ledger Lines View
#         # -------------------------
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
