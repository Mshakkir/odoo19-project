# product_stock_ledger/models/product_stock_ledger_line.py
from odoo import fields, models, api
from datetime import datetime


class ProductStockLedgerLine(models.Model):
    _name = 'product.stock.ledger.line'
    _description = 'Product Stock Ledger Lines'
    _order = 'date asc'

    product_id = fields.Many2one('product.product', string='Product')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    date = fields.Datetime(string='Date')
    voucher = fields.Char(string='Voucher')
    particulars = fields.Char(string='Particulars')
    type = fields.Char(string='Type')
    rec_qty = fields.Float(string='Rec. Qty')
    rec_rate = fields.Float(string='Rec. Rate')
    issue_qty = fields.Float(string='Issue Qty')
    issue_rate = fields.Float(string='Issue Rate')
    balance = fields.Float(string='Balance')
    uom = fields.Char(string='Unit')
    invoice_status = fields.Char(string='Invoice Status')

    def _get_invoice_status(self, move):
        """Determine invoice status based on move type and related documents."""
        status = 'Not Invoiced'

        if move.picking_id:
            picking = move.picking_id

            # For incoming moves (Purchase)
            if picking.picking_type_code == 'incoming':
                po_lines = self.env['purchase.order.line'].search([
                    ('move_ids', '=', move.id)
                ])

                if po_lines:
                    po = po_lines[0].order_id
                    if po.invoice_status == 'invoiced':
                        status = 'Invoiced'
                    elif po.invoice_status == 'to invoice':
                        status = 'To Invoice'
                    else:
                        status = 'Not Invoiced'
                else:
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
                            else:
                                status = 'Not Invoiced'
                    else:
                        bill_lines = self.env['account.move.line'].search([
                            ('move_id.move_type', 'in', ['in_invoice', 'in_refund']),
                            ('move_id.state', '=', 'posted'),
                            ('product_id', '=', move.product_id.id),
                        ], limit=1)
                        status = 'Invoiced' if bill_lines else 'Not Invoiced'

            # For outgoing moves (Sales)
            elif picking.picking_type_code == 'outgoing':
                so_lines = self.env['sale.order.line'].search([
                    ('move_ids', '=', move.id)
                ])

                if so_lines:
                    so = so_lines[0].order_id
                    if so.invoice_status == 'invoiced':
                        status = 'Invoiced'
                    elif so.invoice_status == 'to invoice':
                        status = 'To Invoice'
                    else:
                        status = 'Not Invoiced'
                else:
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
                            else:
                                status = 'Not Invoiced'
                    else:
                        invoice_lines = self.env['account.move.line'].search([
                            ('move_id.move_type', 'in', ['out_invoice', 'out_refund']),
                            ('move_id.state', '=', 'posted'),
                            ('product_id', '=', move.product_id.id),
                        ], limit=1)
                        status = 'Invoiced' if invoice_lines else 'Not Invoiced'

            # For internal transfers
            else:
                status = 'Internal'

        return status

    def _get_warehouse_from_location(self, location):
        """Get warehouse from location"""
        if not location:
            return False

        # Try to find warehouse from location's warehouse_id
        if hasattr(location, 'warehouse_id') and location.warehouse_id:
            return location.warehouse_id

        # Search for warehouse that contains this location
        warehouses = self.env['stock.warehouse'].search([])
        for wh in warehouses:
            if wh.view_location_id:
                wh_locations = self.env['stock.location'].search([
                    ('id', 'child_of', wh.view_location_id.id)
                ])
                if location.id in wh_locations.ids:
                    return wh
        return False

    @api.model
    def generate_ledger(self, product_id=None, warehouse_id=None, date_from=None, date_to=None):
        """Generate stock ledger lines based on filters"""
        domain = [('state', '=', 'done')]

        if product_id:
            domain.append(('product_id', '=', product_id))
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))

        wh = False
        loc_ids = []
        if warehouse_id:
            wh = self.env['stock.warehouse'].browse(warehouse_id)
            if wh.view_location_id:
                loc_ids = self.env['stock.location'].search([
                    ('id', 'child_of', wh.view_location_id.id)
                ]).ids
                domain += ['|', ('location_id', 'in', loc_ids), ('location_dest_id', 'in', loc_ids)]

        moves = self.env['stock.move'].search(domain, order='date asc')

        # Clear existing lines
        self.search([]).unlink()

        # Track balance per product-warehouse combination
        balances = {}

        lines_to_create = []
        for mv in moves:
            qty = mv.product_uom_qty or 0.0

            # Determine warehouse for this move
            move_warehouse = False
            if warehouse_id:
                move_warehouse = wh
            else:
                # Try to get warehouse from picking
                if mv.picking_id and mv.picking_id.location_id:
                    move_warehouse = self._get_warehouse_from_location(mv.picking_id.location_id)
                if not move_warehouse and mv.picking_id and mv.picking_id.location_dest_id:
                    move_warehouse = self._get_warehouse_from_location(mv.picking_id.location_dest_id)
                # Fallback: try from move locations
                if not move_warehouse:
                    move_warehouse = self._get_warehouse_from_location(mv.location_dest_id)
                if not move_warehouse:
                    move_warehouse = self._get_warehouse_from_location(mv.location_id)

            move_warehouse_id = move_warehouse.id if move_warehouse else False

            # Create unique key for product-warehouse
            key = (mv.product_id.id, move_warehouse_id)
            if key not in balances:
                balances[key] = 0.0

            # Determine move type
            if warehouse_id and wh and wh.view_location_id:
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

            # Determine rate
            rate = 0.0
            if move_type == 'incoming':
                rate = getattr(mv, 'price_unit', 0.0) or mv.product_id.standard_price or 0.0
            elif move_type == 'outgoing':
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
                    rate = mv.product_id.standard_price or 0.0
            else:
                rate = mv.product_id.standard_price or 0.0

            # Calculate quantities
            rec_qty = qty if move_type == 'incoming' else 0.0
            issue_qty = qty if move_type == 'outgoing' else 0.0

            if move_type == 'incoming':
                balances[key] += rec_qty
            elif move_type == 'outgoing':
                balances[key] -= issue_qty

            # Partner info
            partner_name = (
                    mv.partner_id.name
                    or (mv.picking_id.partner_id.name if mv.picking_id and mv.picking_id.partner_id else '')
            )
            particulars = f"{partner_name} - {mv.location_id.complete_name} → {mv.location_dest_id.complete_name}"

            # Get invoice status
            invoice_status = self._get_invoice_status(mv)

            # Prepare line data
            lines_to_create.append({
                'product_id': mv.product_id.id,
                'warehouse_id': move_warehouse_id,
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
                'balance': balances[key],
                'uom': mv.product_uom.name if mv.product_uom else mv.product_id.uom_id.name,
                'invoice_status': invoice_status,
            })

        # Batch create all lines
        if lines_to_create:
            self.create(lines_to_create)
        return True

    def action_generate_all(self):
        """Action to generate all ledger lines - called from button"""
        self.generate_ledger()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Stock Ledger Data Generated Successfully!',
                'type': 'success',
                'sticky': False,
            }
        }

    def action_refresh_ledger(self):
        """Refresh ledger data"""
        self.search([]).unlink()
        self.generate_ledger()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Refreshed',
                'message': 'Stock Ledger Data Refreshed Successfully!',
                'type': 'success',
                'sticky': False,
            }
        }