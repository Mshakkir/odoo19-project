# from odoo import models, fields, api, _
# from odoo.exceptions import UserError, ValidationError
# from collections import defaultdict
# import logging
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
#         help='Warehouse from which this product will be delivered',
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
#             # Skip if already set or not a customer invoice
#             if line.warehouse_id or line.move_id.move_type not in ('out_invoice', 'out_refund'):
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
#                 # Find warehouse with stock
#                 for warehouse in warehouses:
#                     stock = line.product_id.with_context(
#                         warehouse=warehouse.id
#                     ).qty_available
#
#                     if stock > 0:
#                         line.warehouse_id = warehouse.id
#                         break
#
#                 # If no stock found, use default warehouse
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
#         string='Delivery Orders',
#         compute='_compute_delivery_count',
#     )
#
#     picking_ids = fields.Many2many(
#         'stock.picking',
#         string='Pickings',
#         compute='_compute_picking_ids',
#         store=True,
#     )
#
#     auto_create_delivery = fields.Boolean(
#         string='Auto Create Delivery',
#         default=True,
#         help='Automatically create delivery order when invoice is posted',
#     )
#
#     @api.model
#     def default_get(self, fields_list):
#         """Override to set auto_create_delivery from company settings"""
#         res = super(AccountMove, self).default_get(fields_list)
#         if 'auto_create_delivery' in fields_list:
#             try:
#                 # Try to get company setting, fallback to True if field doesn't exist yet
#                 res['auto_create_delivery'] = self.env.company.invoice_auto_create_delivery
#             except Exception:
#                 res['auto_create_delivery'] = True
#         return res
#
#     @api.depends('invoice_line_ids.product_id')
#     def _compute_picking_ids(self):
#         """Compute related picking records"""
#         for move in self:
#             # Find pickings that reference this invoice
#             pickings = self.env['stock.picking'].search([
#                 ('origin', 'ilike', move.name)
#             ]) if move.name else self.env['stock.picking']
#
#             move.picking_ids = pickings
#
#     def _compute_delivery_count(self):
#         """Count related delivery orders"""
#         for move in self:
#             move.delivery_count = len(move.picking_ids)
#
#     def action_view_delivery(self):
#         """View related delivery orders"""
#         self.ensure_one()
#         action = self.env.ref('stock.action_picking_tree_all').read()[0]
#
#         pickings = self.picking_ids
#         if len(pickings) > 1:
#             action['domain'] = [('id', 'in', pickings.ids)]
#         elif pickings:
#             action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
#             action['res_id'] = pickings.id
#         else:
#             action = {'type': 'ir.actions.act_window_close'}
#
#         return action
#
#     def action_post(self):
#         """Override to create delivery orders for direct invoices"""
#         result = super(AccountMove, self).action_post()
#
#         for move in self:
#             # Only process customer invoices without sale orders
#             if (move.move_type == 'out_invoice'
#                     and not move.invoice_line_ids.mapped('sale_line_ids')
#                     and move.auto_create_delivery):
#
#                 try:
#                     move._create_delivery_from_invoice()
#                 except Exception as e:
#                     _logger.error(f"Error creating delivery for invoice {move.name}: {str(e)}")
#                     # Don't fail the invoice posting, just log the error
#                     try:
#                         move.message_post(
#                             body=_("Could not automatically create delivery: %s") % str(e),
#                             message_type='notification',
#                         )
#                     except Exception:
#                         # If even message posting fails, just pass
#                         pass
#
#         return result
#
#     def _create_delivery_from_invoice(self):
#         """Create delivery orders based on invoice lines grouped by warehouse"""
#         self.ensure_one()
#
#         # Skip if invoice has no lines or already has deliveries
#         if not self.invoice_line_ids or self.picking_ids:
#             return
#
#         # Get stockable product lines grouped by warehouse
#         lines_by_warehouse = defaultdict(list)
#
#         for line in self.invoice_line_ids:
#             # Only process stockable products
#             if line.product_id and line.product_id.type in ('product', 'consu') and line.quantity > 0:
#                 warehouse = line.warehouse_id or self._get_default_warehouse()
#                 if warehouse:
#                     lines_by_warehouse[warehouse].append(line)
#
#         if not lines_by_warehouse:
#             return
#
#         # Create picking for each warehouse
#         pickings = self.env['stock.picking']
#
#         for warehouse, lines in lines_by_warehouse.items():
#             picking = self._create_picking_for_warehouse(warehouse, lines)
#             if picking:
#                 pickings |= picking
#
#         # Auto-validate pickings if configured
#         if self.env.company.invoice_auto_validate_delivery and pickings:
#             for picking in pickings:
#                 try:
#                     # Check availability
#                     picking.action_assign()
#
#                     # Set done quantities
#                     for move in picking.move_ids:
#                         for move_line in move.move_line_ids:
#                             move_line.quantity = move_line.product_uom_qty
#
#                     # Validate
#                     picking.button_validate()
#
#                 except Exception as e:
#                     _logger.warning(f"Could not auto-validate picking {picking.name}: {str(e)}")
#                     picking.message_post(
#                         body=_("Could not auto-validate: %s. Please validate manually.") % str(e),
#                         message_type='notification',
#                     )
#
#         if pickings:
#             self.message_post(
#                 body=_("Delivery orders created: %s") % ', '.join(pickings.mapped('name')),
#                 message_type='notification',
#             )
#
#     def _create_picking_for_warehouse(self, warehouse, lines):
#         """Create a single picking for a warehouse with given invoice lines"""
#         self.ensure_one()
#
#         # Get picking type
#         picking_type = warehouse.out_type_id
#         if not picking_type:
#             raise UserError(_("Warehouse %s has no outgoing operation type configured.") % warehouse.name)
#
#         # Prepare picking values
#         picking_vals = {
#             'picking_type_id': picking_type.id,
#             'partner_id': self.partner_id.id,
#             'origin': self.name,
#             'location_id': warehouse.lot_stock_id.id,
#             'location_dest_id': self.partner_id.property_stock_customer.id or self.env.ref(
#                 'stock.stock_location_customers').id,
#             'company_id': self.company_id.id,
#             'move_type': 'direct',  # Direct delivery
#             'scheduled_date': fields.Datetime.now(),
#         }
#
#         picking = self.env['stock.picking'].create(picking_vals)
#
#         # Create stock moves for each line
#         for line in lines:
#             if line.product_id and line.product_id.type in ('product', 'consu'):
#                 move_vals = {
#                     'name': line.product_id.display_name,
#                     'product_id': line.product_id.id,
#                     'product_uom_qty': line.quantity,
#                     'product_uom': line.product_uom_id.id,
#                     'picking_id': picking.id,
#                     'location_id': warehouse.lot_stock_id.id,
#                     'location_dest_id': picking.location_dest_id.id,
#                     'company_id': self.company_id.id,
#                     'picking_type_id': picking_type.id,
#                     'warehouse_id': warehouse.id,
#                     'origin': self.name,
#                     'description_picking': line.name,
#                 }
#
#                 self.env['stock.move'].create(move_vals)
#
#         # Confirm the picking
#         if picking.move_ids:
#             picking.action_confirm()
#             return picking
#         else:
#             picking.unlink()
#             return None
#
#     def _get_default_warehouse(self):
#         """Get default warehouse for the company"""
#         warehouse = self.env['stock.warehouse'].search([
#             ('company_id', '=', self.company_id.id)
#         ], limit=1)
#         return warehouse
#
#     def button_draft(self):
#         """Override to handle delivery cancellation"""
#         result = super(AccountMove, self).button_draft()
#
#         for move in self:
#             # Cancel related pickings if they exist and are not done
#             pickings = move.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
#             if pickings:
#                 try:
#                     pickings.action_cancel()
#                     move.message_post(
#                         body=_("Related delivery orders cancelled: %s") % ', '.join(pickings.mapped('name')),
#                         message_type='notification',
#                     )
#                 except Exception as e:
#                     _logger.warning(f"Could not cancel pickings for invoice {move.name}: {str(e)}")
#
#         return result
#
#     @api.constrains('invoice_line_ids')
#     def _check_warehouse_stock(self):
#         """Optionally check if sufficient stock is available"""
#         if not self.env.company.invoice_check_stock_availability:
#             return
#
#         for move in self:
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
        help='Warehouse from which this product will be delivered',
        domain="[('company_id', '=', company_id)]",
        copy=True,
        compute='_compute_warehouse_id',
        store=True,
        readonly=False,
    )

    @api.depends('product_id', 'move_id.move_type')
    def _compute_warehouse_id(self):
        for line in self:
            if line.warehouse_id or line.move_id.move_type not in ('out_invoice', 'out_refund'):
                continue
            if not line.product_id or line.product_id.type not in ('product', 'consu'):
                line.warehouse_id = False
                continue
            try:
                warehouses = self.env['stock.warehouse'].search([
                    ('company_id', '=', line.company_id.id or self.env.company.id)
                ])
                for warehouse in warehouses:
                    stock = line.product_id.with_context(
                        warehouse=warehouse.id
                    ).qty_available
                    if stock > 0:
                        line.warehouse_id = warehouse.id
                        break
                if not line.warehouse_id and warehouses:
                    line.warehouse_id = warehouses[0]
            except Exception as e:
                _logger.warning(f"Could not compute warehouse for line: {str(e)}")
                line.warehouse_id = False


class AccountMove(models.Model):
    _inherit = 'account.move'

    delivery_count = fields.Integer(
        string='Delivery Orders',
        compute='_compute_delivery_count',
        store=False,
    )

    picking_ids = fields.One2many(
        'stock.picking',
        'invoice_id',
        string='Pickings',
        readonly=True,
    )

    auto_create_delivery = fields.Boolean(
        string='Auto Create Delivery',
        default=True,
        help='Automatically create delivery order when invoice is posted',
    )

    @api.model
    def default_get(self, fields_list):
        res = super(AccountMove, self).default_get(fields_list)
        if 'auto_create_delivery' in fields_list:
            try:
                res['auto_create_delivery'] = self.env.company.invoice_auto_create_delivery
            except Exception:
                res['auto_create_delivery'] = True
        return res

    def _compute_delivery_count(self):
        for move in self:
            if move.name:
                count = self.env['stock.picking'].search_count([
                    ('invoice_id', '=', move.id)
                ])
                _logger.info(
                    f"[DEBUG] _compute_delivery_count: invoice={move.name} "
                    f"id={move.id} count={count}"
                )
                move.delivery_count = count
            else:
                move.delivery_count = 0

    def action_view_delivery(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('stock.action_picking_tree_all')

        pickings = self.env['stock.picking'].search([
            ('invoice_id', '=', self.id)
        ])
        _logger.info(
            f"[DEBUG] action_view_delivery: invoice={self.name} "
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
        result = super(AccountMove, self).action_post()

        for move in self:
            _logger.info(
                f"[DEBUG] action_post: invoice={move.name} "
                f"move_type={move.move_type} "
                f"has_sale_lines={bool(move.invoice_line_ids.mapped('sale_line_ids'))} "
                f"auto_create={move.auto_create_delivery}"
            )

            if (move.move_type == 'out_invoice'
                    and not move.invoice_line_ids.mapped('sale_line_ids')
                    and move.auto_create_delivery):
                try:
                    move._create_delivery_from_invoice()
                except Exception as e:
                    _logger.error(
                        f"[DEBUG] action_post EXCEPTION for {move.name}: {str(e)}\n"
                        f"{traceback.format_exc()}"
                    )
                    try:
                        move.message_post(
                            body=_("Could not automatically create delivery: %s") % str(e),
                            message_type='notification',
                        )
                    except Exception:
                        pass

        return result

    def _create_delivery_from_invoice(self):
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
                f"product_id={line.product_id.id if line.product_id else None} "
                f"product_type={line.product_id.type if line.product_id else None} "
                f"quantity={line.quantity} "
                f"warehouse_id={line.warehouse_id.id if line.warehouse_id else None} "
                f"warehouse_name={line.warehouse_id.name if line.warehouse_id else None}"
            )

            if line.product_id and line.product_id.type in ('product', 'consu') and line.quantity > 0:
                warehouse = line.warehouse_id or self._get_default_warehouse()
                _logger.info(
                    f"[DEBUG] line ACCEPTED -> warehouse={warehouse.name if warehouse else None} "
                    f"warehouse_id={warehouse.id if warehouse else None}"
                )
                if warehouse:
                    lines_by_warehouse[warehouse].append(line)
            else:
                _logger.info(f"[DEBUG] line SKIPPED (not stockable or qty<=0)")

        _logger.info(
            f"[DEBUG] lines_by_warehouse grouping: "
            f"{[(wh.name, wh.id, len(lines)) for wh, lines in lines_by_warehouse.items()]}"
        )

        if not lines_by_warehouse:
            _logger.info(f"[DEBUG] _create_delivery_from_invoice: lines_by_warehouse is empty, returning")
            return

        pickings = self.env['stock.picking']

        for warehouse, lines in lines_by_warehouse.items():
            _logger.info(
                f"[DEBUG] creating picking for warehouse={warehouse.name} "
                f"warehouse_id={warehouse.id} line_count={len(lines)}"
            )
            picking = self._create_picking_for_warehouse(warehouse, lines)
            if picking:
                _logger.info(
                    f"[DEBUG] picking created successfully: name={picking.name} id={picking.id} "
                    f"state={picking.state} "
                    f"move_ids={picking.move_ids.ids} "
                    f"move_count={len(picking.move_ids)}"
                )
                for sm in picking.move_ids:
                    _logger.info(
                        f"[DEBUG]   stock.move on picking: id={sm.id} product={sm.product_id.display_name} "
                        f"product_uom_qty={sm.product_uom_qty} state={sm.state}"
                    )
                pickings |= picking
            else:
                _logger.warning(
                    f"[DEBUG] _create_picking_for_warehouse returned None for warehouse={warehouse.name}"
                )

        # Auto-validate pickings if configured
        if self.env.company.invoice_auto_validate_delivery and pickings:
            for picking in pickings:
                try:
                    picking.action_assign()
                    for move in picking.move_ids:
                        for move_line in move.move_line_ids:
                            move_line.quantity = move_line.product_uom_qty
                    picking.button_validate()
                except Exception as e:
                    _logger.warning(f"Could not auto-validate picking {picking.name}: {str(e)}")
                    picking.message_post(
                        body=_("Could not auto-validate: %s. Please validate manually.") % str(e),
                        message_type='notification',
                    )

        _logger.info(
            f"[DEBUG] _create_delivery_from_invoice: DONE invoice={self.name} "
            f"total_pickings_created={len(pickings)} picking_ids={pickings.ids} "
            f"picking_names={pickings.mapped('name')}"
        )

        if pickings:
            self.message_post(
                body=_("Delivery orders created: %s") % ', '.join(pickings.mapped('name')),
                message_type='notification',
            )

    def _create_picking_for_warehouse(self, warehouse, lines):
        self.ensure_one()

        picking_type = warehouse.out_type_id
        if not picking_type:
            raise UserError(_("Warehouse %s has no outgoing operation type configured.") % warehouse.name)

        customer_location = self.partner_id.property_stock_customer
        if not customer_location:
            customer_location = self.env.ref('stock.stock_location_customers')

        _logger.info(
            f"[DEBUG] _create_picking_for_warehouse: warehouse={warehouse.name} "
            f"picking_type={picking_type.name} picking_type_id={picking_type.id} "
            f"source_location={warehouse.lot_stock_id.complete_name} "
            f"dest_location={customer_location.complete_name if customer_location else None} "
            f"lines_to_process={len(lines)}"
        )

        # Build move commands
        move_commands = []
        for line in lines:
            if line.product_id and line.product_id.type in ('product', 'consu') and line.quantity > 0:
                cmd = {
                    'name': line.name or line.product_id.display_name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.quantity,
                    'product_uom': line.product_uom_id.id,
                    'location_id': warehouse.lot_stock_id.id,
                    'location_dest_id': customer_location.id,
                    'company_id': self.company_id.id,
                    'picking_type_id': picking_type.id,
                    'warehouse_id': warehouse.id,
                    'origin': self.name,
                }
                move_commands.append((0, 0, cmd))
                _logger.info(
                    f"[DEBUG]   move_command added: product={line.product_id.display_name} "
                    f"qty={line.quantity} uom={line.product_uom_id.id}"
                )

        if not move_commands:
            _logger.warning(f"[DEBUG] _create_picking_for_warehouse: no move_commands built, returning None")
            return None

        _logger.info(
            f"[DEBUG] _create_picking_for_warehouse: move_commands count={len(move_commands)}, "
            f"about to create picking with move_ids inline"
        )

        picking_vals = {
            'picking_type_id': picking_type.id,
            'partner_id': self.partner_id.id,
            'origin': self.name,
            'location_id': warehouse.lot_stock_id.id,
            'location_dest_id': customer_location.id,
            'company_id': self.company_id.id,
            'move_type': 'direct',
            'scheduled_date': fields.Datetime.now(),
            'invoice_id': self.id,
            'move_ids': move_commands,
        }

        picking = self.env['stock.picking'].create(picking_vals)

        _logger.info(
            f"[DEBUG] picking AFTER create BEFORE confirm: "
            f"id={picking.id} name={picking.name} state={picking.state} "
            f"move_ids={picking.move_ids.ids} move_count={len(picking.move_ids)}"
        )
        for sm in picking.move_ids:
            _logger.info(
                f"[DEBUG]   move BEFORE confirm: id={sm.id} product={sm.product_id.display_name} "
                f"qty={sm.product_uom_qty} state={sm.state}"
            )

        # Confirm
        picking.action_confirm()

        _logger.info(
            f"[DEBUG] picking AFTER confirm: "
            f"id={picking.id} name={picking.name} state={picking.state} "
            f"move_ids={picking.move_ids.ids} move_count={len(picking.move_ids)}"
        )
        for sm in picking.move_ids:
            _logger.info(
                f"[DEBUG]   move AFTER confirm: id={sm.id} product={sm.product_id.display_name} "
                f"qty={sm.product_uom_qty} state={sm.state}"
            )

        return picking

    def _get_default_warehouse(self):
        warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        return warehouse

    def button_draft(self):
        result = super(AccountMove, self).button_draft()

        for move in self:
            pickings = move.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
            if pickings:
                try:
                    pickings.action_cancel()
                    move.message_post(
                        body=_("Related delivery orders cancelled: %s") % ', '.join(pickings.mapped('name')),
                        message_type='notification',
                    )
                except Exception as e:
                    _logger.warning(f"Could not cancel pickings for invoice {move.name}: {str(e)}")

        return result

    @api.constrains('invoice_line_ids')
    def _check_warehouse_stock(self):
        if not self.env.company.invoice_check_stock_availability:
            return

        for move in self:
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
        string='Invoice',
        help='Invoice that created this delivery',
        readonly=True,
        copy=False,
    )