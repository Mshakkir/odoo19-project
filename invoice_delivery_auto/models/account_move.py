#
#
# from odoo import models, fields, api, _
# from odoo.exceptions import UserError, ValidationError
# from collections import defaultdict
# import logging
# import traceback
#
# _logger = logging.getLogger(__name__)
#
#
# class AccountMoveLine(models.Model):
#     _inherit = 'account.move.line'
#
#     warehouse_id = fields.Many2one(
#         'stock.warehouse',
#         string='Warehouse',
#         help='Warehouse for delivery (customer invoice) or receipt (vendor bill)',
#         domain="[('company_id', '=', company_id)]",
#         copy=True,
#         compute='_compute_warehouse_id',
#         store=True,
#         readonly=False,
#     )
#
#     @api.depends('product_id', 'move_id.move_type')
#     def _compute_warehouse_id(self):
#         """Auto-select warehouse with available stock for new lines"""
#         for line in self:
#             # Skip if already set or not an invoice/bill
#             if line.warehouse_id or line.move_id.move_type not in ('out_invoice', 'out_refund', 'in_invoice',
#                                                                    'in_refund'):
#                 continue
#
#             # Skip non-stockable products
#             if not line.product_id or line.product_id.type not in ('product', 'consu'):
#                 line.warehouse_id = False
#                 continue
#
#             # Get company's warehouses
#             try:
#                 warehouses = self.env['stock.warehouse'].search([
#                     ('company_id', '=', line.company_id.id or self.env.company.id)
#                 ])
#
#                 # For outgoing (customer invoices), find warehouse with stock
#                 if line.move_id.move_type in ('out_invoice', 'out_refund'):
#                     for warehouse in warehouses:
#                         stock = line.product_id.with_context(
#                             warehouse=warehouse.id
#                         ).qty_available
#                         if stock > 0:
#                             line.warehouse_id = warehouse.id
#                             break
#
#                 # If no stock found (or incoming bill), use default warehouse
#                 if not line.warehouse_id and warehouses:
#                     line.warehouse_id = warehouses[0]
#             except Exception as e:
#                 _logger.warning(f"Could not compute warehouse for line: {str(e)}")
#                 line.warehouse_id = False
#
#
# class AccountMove(models.Model):
#     _inherit = 'account.move'
#
#     delivery_count = fields.Integer(
#         string='Deliveries',
#         compute='_compute_stock_picking_count',
#         store=False,
#     )
#
#     receipt_count = fields.Integer(
#         string='Receipts',
#         compute='_compute_stock_picking_count',
#         store=False,
#     )
#
#     picking_ids = fields.One2many(
#         'stock.picking',
#         'invoice_id',
#         string='Stock Pickings',
#         readonly=True,
#     )
#
#     auto_create_delivery = fields.Boolean(
#         string='Auto Create Delivery/Receipt',
#         default=True,
#         help='Automatically create delivery (customer invoice) or receipt (vendor bill) when posted',
#     )
#
#     @api.model
#     def default_get(self, fields_list):
#         res = super(AccountMove, self).default_get(fields_list)
#         if 'auto_create_delivery' in fields_list:
#             try:
#                 res['auto_create_delivery'] = self.env.company.invoice_auto_create_delivery
#             except Exception:
#                 res['auto_create_delivery'] = True
#         return res
#
#     def _compute_stock_picking_count(self):
#         """Count deliveries and receipts separately"""
#         for move in self:
#             if move.name:
#                 pickings = self.env['stock.picking'].search([('invoice_id', '=', move.id)])
#
#                 # Separate by picking type code
#                 deliveries = pickings.filtered(lambda p: p.picking_type_code == 'outgoing')
#                 receipts = pickings.filtered(lambda p: p.picking_type_code == 'incoming')
#
#                 move.delivery_count = len(deliveries)
#                 move.receipt_count = len(receipts)
#
#                 _logger.info(
#                     f"[DEBUG] _compute_stock_picking_count: invoice={move.name} "
#                     f"deliveries={move.delivery_count} receipts={move.receipt_count}"
#                 )
#             else:
#                 move.delivery_count = 0
#                 move.receipt_count = 0
#
#     def action_view_delivery(self):
#         """View delivery orders (customer invoices)"""
#         self.ensure_one()
#         return self._action_view_pickings('outgoing', 'Deliveries')
#
#     def action_view_receipt(self):
#         """View receipts (vendor bills)"""
#         self.ensure_one()
#         return self._action_view_pickings('incoming', 'Receipts')
#
#     def _action_view_pickings(self, picking_type_code, title):
#         """Generic method to view pickings of a specific type"""
#         self.ensure_one()
#         action = self.env['ir.actions.act_window']._for_xml_id('stock.action_picking_tree_all')
#         action['name'] = title
#
#         pickings = self.env['stock.picking'].search([
#             ('invoice_id', '=', self.id),
#             ('picking_type_code', '=', picking_type_code)
#         ])
#
#         _logger.info(
#             f"[DEBUG] _action_view_pickings: invoice={self.name} type={picking_type_code} "
#             f"picking_ids={pickings.ids} picking_names={pickings.mapped('name')}"
#         )
#
#         if len(pickings) > 1:
#             action['domain'] = [('id', 'in', pickings.ids)]
#         elif pickings:
#             form_view = self.env.ref('stock.view_picking_form', raise_if_not_found=False)
#             action['views'] = [(form_view.id if form_view else False, 'form')]
#             action['res_id'] = pickings.id
#         else:
#             action = {'type': 'ir.actions.act_window_close'}
#
#         return action
#
#     def action_post(self):
#         """Override to create stock pickings for direct invoices/bills"""
#         result = super(AccountMove, self).action_post()
#
#         for move in self:
#             _logger.info(
#                 f"[DEBUG] action_post: invoice={move.name} "
#                 f"move_type={move.move_type} "
#                 f"has_sale_lines={bool(move.invoice_line_ids.mapped('sale_line_ids'))} "
#                 f"has_purchase_lines={bool(move.invoice_line_ids.mapped('purchase_line_id'))} "
#                 f"auto_create={move.auto_create_delivery}"
#             )
#
#             # Customer Invoice - Create Deliveries
#             if (move.move_type == 'out_invoice'
#                     and not move.invoice_line_ids.mapped('sale_line_ids')
#                     and move.auto_create_delivery):
#                 try:
#                     move._create_delivery_from_invoice()
#                 except Exception as e:
#                     _logger.error(
#                         f"[DEBUG] action_post DELIVERY EXCEPTION for {move.name}: {str(e)}\n"
#                         f"{traceback.format_exc()}"
#                     )
#                     try:
#                         move.message_post(
#                             body=_("Could not automatically create delivery: %s") % str(e),
#                             message_type='notification',
#                         )
#                     except Exception:
#                         pass
#
#             # Vendor Bill - Create Receipts
#             elif (move.move_type == 'in_invoice'
#                   and not move.invoice_line_ids.mapped('purchase_line_id')
#                   and move.auto_create_delivery):
#                 try:
#                     move._create_receipt_from_bill()
#                 except Exception as e:
#                     _logger.error(
#                         f"[DEBUG] action_post RECEIPT EXCEPTION for {move.name}: {str(e)}\n"
#                         f"{traceback.format_exc()}"
#                     )
#                     try:
#                         move.message_post(
#                             body=_("Could not automatically create receipt: %s") % str(e),
#                             message_type='notification',
#                         )
#                     except Exception:
#                         pass
#
#         return result
#
#     def _create_delivery_from_invoice(self):
#         """Create delivery orders based on customer invoice lines grouped by warehouse"""
#         self.ensure_one()
#         _logger.info(
#             f"[DEBUG] _create_delivery_from_invoice: START invoice={self.name} "
#             f"line_count={len(self.invoice_line_ids)}"
#         )
#
#         if not self.invoice_line_ids:
#             _logger.info(f"[DEBUG] _create_delivery_from_invoice: NO invoice_line_ids, returning")
#             return
#
#         lines_by_warehouse = defaultdict(list)
#
#         for line in self.invoice_line_ids:
#             _logger.info(
#                 f"[DEBUG] scanning line: product={line.product_id.display_name if line.product_id else None} "
#                 f"type={line.product_id.type if line.product_id else None} "
#                 f"quantity={line.quantity} warehouse={line.warehouse_id.name if line.warehouse_id else None}"
#             )
#
#             if line.product_id and line.product_id.type in ('product', 'consu') and line.quantity > 0:
#                 warehouse = line.warehouse_id or self._get_default_warehouse()
#                 if warehouse:
#                     lines_by_warehouse[warehouse].append(line)
#
#         _logger.info(
#             f"[DEBUG] lines_by_warehouse: {[(wh.name, len(lines)) for wh, lines in lines_by_warehouse.items()]}"
#         )
#
#         if not lines_by_warehouse:
#             return
#
#         pickings = self.env['stock.picking']
#
#         for warehouse, lines in lines_by_warehouse.items():
#             _logger.info(f"[DEBUG] Creating DELIVERY for warehouse={warehouse.name}")
#             picking = self._create_picking_for_warehouse(warehouse, lines, 'outgoing')
#             if picking:
#                 pickings |= picking
#
#         self._finalize_pickings(pickings, 'Delivery')
#
#     def _create_receipt_from_bill(self):
#         """Create receipt orders based on vendor bill lines grouped by warehouse"""
#         self.ensure_one()
#         _logger.info(
#             f"[DEBUG] _create_receipt_from_bill: START bill={self.name} "
#             f"line_count={len(self.invoice_line_ids)}"
#         )
#
#         if not self.invoice_line_ids:
#             _logger.info(f"[DEBUG] _create_receipt_from_bill: NO invoice_line_ids, returning")
#             return
#
#         lines_by_warehouse = defaultdict(list)
#
#         for line in self.invoice_line_ids:
#             _logger.info(
#                 f"[DEBUG] scanning line: product={line.product_id.display_name if line.product_id else None} "
#                 f"type={line.product_id.type if line.product_id else None} "
#                 f"quantity={line.quantity} warehouse={line.warehouse_id.name if line.warehouse_id else None}"
#             )
#
#             if line.product_id and line.product_id.type in ('product', 'consu') and line.quantity > 0:
#                 warehouse = line.warehouse_id or self._get_default_warehouse()
#                 if warehouse:
#                     lines_by_warehouse[warehouse].append(line)
#
#         _logger.info(
#             f"[DEBUG] lines_by_warehouse: {[(wh.name, len(lines)) for wh, lines in lines_by_warehouse.items()]}"
#         )
#
#         if not lines_by_warehouse:
#             return
#
#         pickings = self.env['stock.picking']
#
#         for warehouse, lines in lines_by_warehouse.items():
#             _logger.info(f"[DEBUG] Creating RECEIPT for warehouse={warehouse.name}")
#             picking = self._create_picking_for_warehouse(warehouse, lines, 'incoming')
#             if picking:
#                 pickings |= picking
#
#         self._finalize_pickings(pickings, 'Receipt')
#
#     def _create_picking_for_warehouse(self, warehouse, lines, direction='outgoing'):
#         """
#         Create a single picking for a warehouse with given invoice lines.
#
#         Args:
#             warehouse: stock.warehouse record
#             lines: account.move.line records
#             direction: 'outgoing' for deliveries, 'incoming' for receipts
#         """
#         self.ensure_one()
#
#         # Get picking type based on direction
#         if direction == 'outgoing':
#             picking_type = warehouse.out_type_id
#             source_location = warehouse.lot_stock_id
#             if self.partner_id.property_stock_customer:
#                 dest_location = self.partner_id.property_stock_customer
#             else:
#                 dest_location = self.env.ref('stock.stock_location_customers')
#         else:  # incoming
#             picking_type = warehouse.in_type_id
#             if self.partner_id.property_stock_supplier:
#                 source_location = self.partner_id.property_stock_supplier
#             else:
#                 source_location = self.env.ref('stock.stock_location_suppliers')
#             dest_location = warehouse.lot_stock_id
#
#         if not picking_type:
#             raise UserError(
#                 _("Warehouse %s has no %s operation type configured.") %
#                 (warehouse.name, direction)
#             )
#
#         _logger.info(
#             f"[DEBUG] _create_picking_for_warehouse: warehouse={warehouse.name} direction={direction} "
#             f"picking_type={picking_type.name} "
#             f"source={source_location.complete_name} dest={dest_location.complete_name}"
#         )
#
#         # Build move commands
#         move_commands = []
#         for line in lines:
#             if line.product_id and line.product_id.type in ('product', 'consu') and line.quantity > 0:
#                 cmd = {
#                     'product_id': line.product_id.id,
#                     'product_uom_qty': line.quantity,
#                     'product_uom': line.product_uom_id.id,
#                     'location_id': source_location.id,
#                     'location_dest_id': dest_location.id,
#                     'company_id': self.company_id.id,
#                     'picking_type_id': picking_type.id,
#                     'warehouse_id': warehouse.id,
#                 }
#                 move_commands.append((0, 0, cmd))
#                 _logger.info(
#                     f"[DEBUG]   move_command: product={line.product_id.display_name} qty={line.quantity}"
#                 )
#
#         if not move_commands:
#             _logger.warning(f"[DEBUG] No move_commands, returning None")
#             return None
#
#         _logger.info(f"[DEBUG] Creating picking with {len(move_commands)} moves")
#
#         picking_vals = {
#             'picking_type_id': picking_type.id,
#             'partner_id': self.partner_id.id,
#             'origin': self.name,
#             'location_id': source_location.id,
#             'location_dest_id': dest_location.id,
#             'company_id': self.company_id.id,
#             'move_type': 'direct',
#             'scheduled_date': fields.Datetime.now(),
#             'invoice_id': self.id,
#             'move_ids': move_commands,
#         }
#
#         picking = self.env['stock.picking'].create(picking_vals)
#
#         _logger.info(
#             f"[DEBUG] Picking created: id={picking.id} name={picking.name} "
#             f"state={picking.state} move_count={len(picking.move_ids)}"
#         )
#
#         # Confirm
#         picking.action_confirm()
#
#         _logger.info(
#             f"[DEBUG] Picking confirmed: state={picking.state} move_count={len(picking.move_ids)}"
#         )
#
#         return picking
#
#     def _finalize_pickings(self, pickings, picking_type_name):
#         """Auto-validate pickings if configured and post message"""
#         if self.env.company.invoice_auto_validate_delivery and pickings:
#             for picking in pickings:
#                 try:
#                     picking.action_assign()
#                     for move in picking.move_ids:
#                         for move_line in move.move_line_ids:
#                             move_line.quantity = move_line.product_uom_qty
#                     picking.button_validate()
#                     _logger.info(f"[DEBUG] Auto-validated: {picking.name}")
#                 except Exception as e:
#                     _logger.warning(f"Could not auto-validate {picking.name}: {str(e)}")
#                     picking.message_post(
#                         body=_("Could not auto-validate: %s. Please validate manually.") % str(e),
#                         message_type='notification',
#                     )
#
#         _logger.info(
#             f"[DEBUG] _finalize_pickings: total={len(pickings)} names={pickings.mapped('name')}"
#         )
#
#         if pickings:
#             self.message_post(
#                 body=_("%s orders created: %s") % (picking_type_name, ', '.join(pickings.mapped('name'))),
#                 message_type='notification',
#             )
#
#     def _get_default_warehouse(self):
#         """Get default warehouse for the company"""
#         warehouse = self.env['stock.warehouse'].search([
#             ('company_id', '=', self.company_id.id)
#         ], limit=1)
#         return warehouse
#
#     def button_draft(self):
#         """Override to handle picking cancellation"""
#         result = super(AccountMove, self).button_draft()
#
#         for move in self:
#             pickings = move.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
#             if pickings:
#                 try:
#                     pickings.action_cancel()
#                     move.message_post(
#                         body=_("Related stock operations cancelled: %s") % ', '.join(pickings.mapped('name')),
#                         message_type='notification',
#                     )
#                 except Exception as e:
#                     _logger.warning(f"Could not cancel pickings for {move.name}: {str(e)}")
#
#         return result
#
#     @api.constrains('invoice_line_ids')
#     def _check_warehouse_stock(self):
#         """Optionally check if sufficient stock is available (for customer invoices only)"""
#         if not self.env.company.invoice_check_stock_availability:
#             return
#
#         for move in self:
#             # Only check stock for outgoing (customer invoices)
#             if move.move_type != 'out_invoice' or move.state != 'draft':
#                 continue
#
#             for line in move.invoice_line_ids:
#                 if line.product_id and line.product_id.type == 'product' and line.warehouse_id:
#                     available = line.product_id.with_context(
#                         warehouse=line.warehouse_id.id
#                     ).qty_available
#
#                     if available < line.quantity:
#                         raise ValidationError(_(
#                             "Insufficient stock for product '%s' in warehouse '%s'.\n"
#                             "Required: %s, Available: %s"
#                         ) % (
#                                                   line.product_id.display_name,
#                                                   line.warehouse_id.name,
#                                                   line.quantity,
#                                                   available
#                                               ))
#
#
# class StockPicking(models.Model):
#     _inherit = 'stock.picking'
#
#     invoice_id = fields.Many2one(
#         'account.move',
#         string='Invoice/Bill',
#         help='Invoice or Bill that created this stock operation',
#         readonly=True,
#         copy=False,
#     )

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from collections import defaultdict
import logging
import traceback

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        help='Warehouse for delivery (customer invoice) or receipt (vendor bill)',
        domain="[('company_id', '=', company_id)]",
        copy=True,
        compute='_compute_warehouse_id',
        store=True,
        readonly=False,
    )

    @api.depends('product_id', 'move_id.move_type')
    def _compute_warehouse_id(self):
        """Auto-select warehouse with available stock for new lines"""
        for line in self:
            # Skip if already set or not an invoice/bill
            if line.warehouse_id or line.move_id.move_type not in ('out_invoice', 'out_refund', 'in_invoice',
                                                                   'in_refund'):
                continue

            # Skip non-stockable products
            if not line.product_id or line.product_id.type not in ('product', 'consu'):
                line.warehouse_id = False
                continue

            # Get company's warehouses
            try:
                warehouses = self.env['stock.warehouse'].search([
                    ('company_id', '=', line.company_id.id or self.env.company.id)
                ])

                # For outgoing (customer invoices), find warehouse with stock
                if line.move_id.move_type in ('out_invoice', 'out_refund'):
                    for warehouse in warehouses:
                        stock = line.product_id.with_context(
                            warehouse=warehouse.id
                        ).qty_available
                        if stock > 0:
                            line.warehouse_id = warehouse.id
                            break

                # If no stock found (or incoming bill), use default warehouse
                if not line.warehouse_id and warehouses:
                    line.warehouse_id = warehouses[0]
            except Exception as e:
                _logger.warning(f"Could not compute warehouse for line: {str(e)}")
                line.warehouse_id = False


class AccountMove(models.Model):
    _inherit = 'account.move'

    delivery_count = fields.Integer(
        string='Deliveries',
        compute='_compute_stock_picking_count',
        store=False,
    )

    receipt_count = fields.Integer(
        string='Receipts',
        compute='_compute_stock_picking_count',
        store=False,
    )

    picking_ids = fields.One2many(
        'stock.picking',
        'invoice_id',
        string='Stock Pickings',
        readonly=True,
    )

    auto_create_delivery = fields.Boolean(
        string='Auto Create Delivery/Receipt',
        default=True,
        help='Automatically create delivery (customer invoice) or receipt (vendor bill) when posted',
    )

    is_direct_invoice = fields.Boolean(
        string='Is Direct Invoice/Bill',
        compute='_compute_is_direct_invoice',
        store=True,
        help='True when the invoice/bill is created directly (not from a sale/purchase order)',
    )

    @api.depends('invoice_line_ids.sale_line_ids', 'invoice_line_ids.purchase_line_id')
    def _compute_is_direct_invoice(self):
        """Check if the invoice/bill was created directly (not from sale/purchase order)"""
        for move in self:
            has_sale_lines = bool(move.invoice_line_ids.mapped('sale_line_ids'))
            has_purchase_lines = bool(move.invoice_line_ids.filtered('purchase_line_id'))
            move.is_direct_invoice = not (has_sale_lines or has_purchase_lines)

    @api.model
    def default_get(self, fields_list):
        res = super(AccountMove, self).default_get(fields_list)
        if 'auto_create_delivery' in fields_list:
            try:
                res['auto_create_delivery'] = self.env.company.invoice_auto_create_delivery
            except Exception:
                res['auto_create_delivery'] = True
        return res

    def _compute_stock_picking_count(self):
        """Count deliveries and receipts separately"""
        for move in self:
            if move.name:
                pickings = self.env['stock.picking'].search([('invoice_id', '=', move.id)])

                # Separate by picking type code
                deliveries = pickings.filtered(lambda p: p.picking_type_code == 'outgoing')
                receipts = pickings.filtered(lambda p: p.picking_type_code == 'incoming')

                move.delivery_count = len(deliveries)
                move.receipt_count = len(receipts)

                _logger.info(
                    f"[DEBUG] _compute_stock_picking_count: invoice={move.name} "
                    f"deliveries={move.delivery_count} receipts={move.receipt_count}"
                )
            else:
                move.delivery_count = 0
                move.receipt_count = 0

    def action_view_delivery(self):
        """View delivery orders (customer invoices)"""
        self.ensure_one()
        return self._action_view_pickings('outgoing', 'Deliveries')

    def action_view_receipt(self):
        """View receipts (vendor bills)"""
        self.ensure_one()
        return self._action_view_pickings('incoming', 'Receipts')

    def _action_view_pickings(self, picking_type_code, title):
        """Generic method to view pickings of a specific type"""
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('stock.action_picking_tree_all')
        action['name'] = title

        pickings = self.env['stock.picking'].search([
            ('invoice_id', '=', self.id),
            ('picking_type_code', '=', picking_type_code)
        ])

        _logger.info(
            f"[DEBUG] _action_view_pickings: invoice={self.name} type={picking_type_code} "
            f"picking_ids={pickings.ids} picking_names={pickings.mapped('name')}"
        )

        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            form_view = self.env.ref('stock.view_picking_form', raise_if_not_found=False)
            action['views'] = [(form_view.id if form_view else False, 'form')]
            action['res_id'] = pickings.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        return action

    def action_post(self):
        """Override to create stock pickings for direct invoices/bills"""
        result = super(AccountMove, self).action_post()

        for move in self:
            _logger.info(
                f"[DEBUG] action_post: invoice={move.name} "
                f"move_type={move.move_type} "
                f"has_sale_lines={bool(move.invoice_line_ids.mapped('sale_line_ids'))} "
                f"has_purchase_lines={bool(move.invoice_line_ids.mapped('purchase_line_id'))} "
                f"auto_create={move.auto_create_delivery}"
            )

            # Customer Invoice - Create Deliveries
            if (move.move_type == 'out_invoice'
                    and not move.invoice_line_ids.mapped('sale_line_ids')
                    and move.auto_create_delivery):
                try:
                    move._create_delivery_from_invoice()
                except Exception as e:
                    _logger.error(
                        f"[DEBUG] action_post DELIVERY EXCEPTION for {move.name}: {str(e)}\n"
                        f"{traceback.format_exc()}"
                    )
                    try:
                        move.message_post(
                            body=_("Could not automatically create delivery: %s") % str(e),
                            message_type='notification',
                        )
                    except Exception:
                        pass

            # Vendor Bill - Create Receipts
            elif (move.move_type == 'in_invoice'
                  and not move.invoice_line_ids.mapped('purchase_line_id')
                  and move.auto_create_delivery):
                try:
                    move._create_receipt_from_bill()
                except Exception as e:
                    _logger.error(
                        f"[DEBUG] action_post RECEIPT EXCEPTION for {move.name}: {str(e)}\n"
                        f"{traceback.format_exc()}"
                    )
                    try:
                        move.message_post(
                            body=_("Could not automatically create receipt: %s") % str(e),
                            message_type='notification',
                        )
                    except Exception:
                        pass

        return result

    def _create_delivery_from_invoice(self):
        """Create delivery orders based on customer invoice lines grouped by warehouse"""
        self.ensure_one()
        _logger.info(
            f"[DEBUG] _create_delivery_from_invoice: START invoice={self.name} "
            f"line_count={len(self.invoice_line_ids)}"
        )

        if not self.invoice_line_ids:
            _logger.info(f"[DEBUG] _create_delivery_from_invoice: NO invoice_line_ids, returning")
            return

        lines_by_warehouse = defaultdict(list)

        for line in self.invoice_line_ids:
            _logger.info(
                f"[DEBUG] scanning line: product={line.product_id.display_name if line.product_id else None} "
                f"type={line.product_id.type if line.product_id else None} "
                f"quantity={line.quantity} warehouse={line.warehouse_id.name if line.warehouse_id else None}"
            )

            if line.product_id and line.product_id.type in ('product', 'consu') and line.quantity > 0:
                warehouse = line.warehouse_id or self._get_default_warehouse()
                if warehouse:
                    lines_by_warehouse[warehouse].append(line)

        _logger.info(
            f"[DEBUG] lines_by_warehouse: {[(wh.name, len(lines)) for wh, lines in lines_by_warehouse.items()]}"
        )

        if not lines_by_warehouse:
            return

        pickings = self.env['stock.picking']

        for warehouse, lines in lines_by_warehouse.items():
            _logger.info(f"[DEBUG] Creating DELIVERY for warehouse={warehouse.name}")
            picking = self._create_picking_for_warehouse(warehouse, lines, 'outgoing')
            if picking:
                pickings |= picking

        self._finalize_pickings(pickings, 'Delivery')

    def _create_receipt_from_bill(self):
        """Create receipt orders based on vendor bill lines grouped by warehouse"""
        self.ensure_one()
        _logger.info(
            f"[DEBUG] _create_receipt_from_bill: START bill={self.name} "
            f"line_count={len(self.invoice_line_ids)}"
        )

        if not self.invoice_line_ids:
            _logger.info(f"[DEBUG] _create_receipt_from_bill: NO invoice_line_ids, returning")
            return

        lines_by_warehouse = defaultdict(list)

        for line in self.invoice_line_ids:
            _logger.info(
                f"[DEBUG] scanning line: product={line.product_id.display_name if line.product_id else None} "
                f"type={line.product_id.type if line.product_id else None} "
                f"quantity={line.quantity} warehouse={line.warehouse_id.name if line.warehouse_id else None}"
            )

            if line.product_id and line.product_id.type in ('product', 'consu') and line.quantity > 0:
                warehouse = line.warehouse_id or self._get_default_warehouse()
                if warehouse:
                    lines_by_warehouse[warehouse].append(line)

        _logger.info(
            f"[DEBUG] lines_by_warehouse: {[(wh.name, len(lines)) for wh, lines in lines_by_warehouse.items()]}"
        )

        if not lines_by_warehouse:
            return

        pickings = self.env['stock.picking']

        for warehouse, lines in lines_by_warehouse.items():
            _logger.info(f"[DEBUG] Creating RECEIPT for warehouse={warehouse.name}")
            picking = self._create_picking_for_warehouse(warehouse, lines, 'incoming')
            if picking:
                pickings |= picking

        self._finalize_pickings(pickings, 'Receipt')

    def _create_picking_for_warehouse(self, warehouse, lines, direction='outgoing'):
        """
        Create a single picking for a warehouse with given invoice lines.

        Args:
            warehouse: stock.warehouse record
            lines: account.move.line records
            direction: 'outgoing' for deliveries, 'incoming' for receipts
        """
        self.ensure_one()

        # Get picking type based on direction
        if direction == 'outgoing':
            picking_type = warehouse.out_type_id
            source_location = warehouse.lot_stock_id
            if self.partner_id.property_stock_customer:
                dest_location = self.partner_id.property_stock_customer
            else:
                dest_location = self.env.ref('stock.stock_location_customers')
        else:  # incoming
            picking_type = warehouse.in_type_id
            if self.partner_id.property_stock_supplier:
                source_location = self.partner_id.property_stock_supplier
            else:
                source_location = self.env.ref('stock.stock_location_suppliers')
            dest_location = warehouse.lot_stock_id

        if not picking_type:
            raise UserError(
                _("Warehouse %s has no %s operation type configured.") %
                (warehouse.name, direction)
            )

        _logger.info(
            f"[DEBUG] _create_picking_for_warehouse: warehouse={warehouse.name} direction={direction} "
            f"picking_type={picking_type.name} "
            f"source={source_location.complete_name} dest={dest_location.complete_name}"
        )

        # Build move commands
        move_commands = []
        for line in lines:
            if line.product_id and line.product_id.type in ('product', 'consu') and line.quantity > 0:
                cmd = {
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.quantity,
                    'product_uom': line.product_uom_id.id,
                    'location_id': source_location.id,
                    'location_dest_id': dest_location.id,
                    'company_id': self.company_id.id,
                    'picking_type_id': picking_type.id,
                    'warehouse_id': warehouse.id,
                }
                move_commands.append((0, 0, cmd))
                _logger.info(
                    f"[DEBUG]   move_command: product={line.product_id.display_name} qty={line.quantity}"
                )

        if not move_commands:
            _logger.warning(f"[DEBUG] No move_commands, returning None")
            return None

        _logger.info(f"[DEBUG] Creating picking with {len(move_commands)} moves")

        picking_vals = {
            'picking_type_id': picking_type.id,
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'location_id': source_location.id,
            'location_dest_id': dest_location.id,
            'company_id': self.company_id.id,
            'move_type': 'direct',
            'scheduled_date': fields.Datetime.now(),
            'invoice_id': self.id,
            'move_ids': move_commands,
        }

        picking = self.env['stock.picking'].create(picking_vals)

        _logger.info(
            f"[DEBUG] Picking created: id={picking.id} name={picking.name} "
            f"state={picking.state} move_count={len(picking.move_ids)}"
        )

        # Confirm
        picking.action_confirm()

        _logger.info(
            f"[DEBUG] Picking confirmed: state={picking.state} move_count={len(picking.move_ids)}"
        )

        return picking

    def _finalize_pickings(self, pickings, picking_type_name):
        """Auto-validate pickings if configured and post message"""
        if self.env.company.invoice_auto_validate_delivery and pickings:
            for picking in pickings:
                try:
                    picking.action_assign()
                    for move in picking.move_ids:
                        for move_line in move.move_line_ids:
                            move_line.quantity = move_line.product_uom_qty
                    picking.button_validate()
                    _logger.info(f"[DEBUG] Auto-validated: {picking.name}")
                except Exception as e:
                    _logger.warning(f"Could not auto-validate {picking.name}: {str(e)}")
                    picking.message_post(
                        body=_("Could not auto-validate: %s. Please validate manually.") % str(e),
                        message_type='notification',
                    )

        _logger.info(
            f"[DEBUG] _finalize_pickings: total={len(pickings)} names={pickings.mapped('name')}"
        )

        if pickings:
            self.message_post(
                body=_("%s orders created: %s") % (picking_type_name, ', '.join(pickings.mapped('name'))),
                message_type='notification',
            )

    def _get_default_warehouse(self):
        """Get default warehouse for the company"""
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        return warehouse

    def button_draft(self):
        """Override to handle picking cancellation"""
        result = super(AccountMove, self).button_draft()

        for move in self:
            pickings = move.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
            if pickings:
                try:
                    pickings.action_cancel()
                    move.message_post(
                        body=_("Related stock operations cancelled: %s") % ', '.join(pickings.mapped('name')),
                        message_type='notification',
                    )
                except Exception as e:
                    _logger.warning(f"Could not cancel pickings for {move.name}: {str(e)}")

        return result

    @api.constrains('invoice_line_ids')
    def _check_warehouse_stock(self):
        """Optionally check if sufficient stock is available (for customer invoices only)"""
        if not self.env.company.invoice_check_stock_availability:
            return

        for move in self:
            # Only check stock for outgoing (customer invoices)
            if move.move_type != 'out_invoice' or move.state != 'draft':
                continue

            for line in move.invoice_line_ids:
                if line.product_id and line.product_id.type == 'product' and line.warehouse_id:
                    available = line.product_id.with_context(
                        warehouse=line.warehouse_id.id
                    ).qty_available

                    if available < line.quantity:
                        raise ValidationError(_(
                            "Insufficient stock for product '%s' in warehouse '%s'.\n"
                            "Required: %s, Available: %s"
                        ) % (
                                                  line.product_id.display_name,
                                                  line.warehouse_id.name,
                                                  line.quantity,
                                                  available
                                              ))


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice/Bill',
        help='Invoice or Bill that created this stock operation',
        readonly=True,
        copy=False,
    )