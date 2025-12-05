# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_inter_warehouse_request = fields.Boolean(
        string='Inter-Warehouse Request',
        compute='_compute_is_inter_warehouse_request',
        store=True
    )

    auto_receipt_created = fields.Boolean(
        string='Auto Receipt Created',
        default=False,
        copy=False,
        help='Technical field to track if automatic receipt was already created'
    )

    @api.depends('location_id', 'location_dest_id', 'location_id.warehouse_id', 'location_dest_id.usage')
    def _compute_is_inter_warehouse_request(self):
        """Identify if this is an inter-warehouse request"""
        for picking in self:
            # Check if source is from another warehouse and destination is transit
            if (picking.location_id.warehouse_id and
                    picking.location_dest_id.usage == 'transit' and
                    picking.location_id.warehouse_id != picking.picking_type_id.warehouse_id):
                picking.is_inter_warehouse_request = True
            else:
                picking.is_inter_warehouse_request = False

    def button_validate(self):
        """Override validate to add notifications and auto-create receipts"""
        # Store pickings that need automation BEFORE validation
        pickings_to_automate = []
        for picking in self:
            # Check if this transfer goes to a transit location and hasn't been processed yet
            if (picking.location_dest_id.usage == 'transit' and
                    not picking.auto_receipt_created and
                    picking.state in ['assigned', 'confirmed']):
                pickings_to_automate.append(picking)

        # Call parent validation
        res = super(StockPicking, self).button_validate()

        # Process automation AFTER validation
        for picking in pickings_to_automate:
            # Double-check the picking is actually done and receipt not created
            if picking.state == 'done' and not picking.auto_receipt_created:
                try:
                    # Mark as processed FIRST to prevent duplicates
                    picking.write({'auto_receipt_created': True})
                    self.env.cr.commit()  # Commit immediately to prevent race conditions

                    # Auto-create the second transfer (receipt)
                    new_picking = self._create_receipt_transfer(picking)

                    # Send notification to requesting warehouse AFTER creating receipt
                    if new_picking:
                        self._notify_warehouse_user(new_picking, 'approved')

                except Exception as e:
                    _logger.error('Error in warehouse automation for %s: %s', picking.name, str(e))
                    # Rollback the flag if creation failed
                    picking.write({'auto_receipt_created': False})

        return res

    def action_confirm(self):
        """Override confirm to send notification to Main warehouse"""
        res = super(StockPicking, self).action_confirm()

        for picking in self:
            # If this is a request from branch to main warehouse
            if picking.is_inter_warehouse_request and picking.location_dest_id.usage == 'transit':
                try:
                    # Notify Main warehouse users
                    self._notify_main_warehouse_users(picking)
                except Exception as e:
                    _logger.error('Error sending notification to main warehouse: %s', str(e))

        return res

    def _create_receipt_transfer(self, picking):
        """Auto-create the second transfer from transit to warehouse stock"""
        # Check if receipt already exists for this picking
        existing_receipt = self.env['stock.picking'].search([
            ('origin', '=', picking.name),
            ('location_id.usage', '=', 'transit')
        ], limit=1)

        if existing_receipt:
            _logger.warning('Receipt already exists for %s: %s', picking.name, existing_receipt.name)
            return existing_receipt

        transit_loc = picking.location_dest_id
        dest_warehouse = transit_loc.warehouse_id

        if not dest_warehouse:
            _logger.warning('No destination warehouse found for transit location: %s', transit_loc.name)
            return False

        # Find the receiving operation type
        receiving_type = self.env['stock.picking.type'].search([
            ('warehouse_id', '=', dest_warehouse.id),
            ('code', '=', 'internal'),
            ('default_location_src_id', '=', transit_loc.id)
        ], limit=1)

        if not receiving_type:
            # Try alternative: find any internal transfer in destination warehouse
            receiving_type = self.env['stock.picking.type'].search([
                ('warehouse_id', '=', dest_warehouse.id),
                ('code', '=', 'internal')
            ], limit=1)

            if not receiving_type:
                picking.message_post(
                    body=_('Warning: Could not find receiving operation type for warehouse %s. '
                           'Please create the receipt manually.') % dest_warehouse.name
                )
                return False

        # Get the final destination location (warehouse stock location)
        dest_location = receiving_type.default_location_dest_id

        # If no default, try to find the main stock location of the warehouse
        if not dest_location:
            dest_location = self.env['stock.location'].search([
                ('warehouse_id', '=', dest_warehouse.id),
                ('usage', '=', 'internal'),
                ('location_id.usage', '=', 'view')
            ], limit=1)

        if not dest_location:
            _logger.error('Could not determine destination location for warehouse: %s', dest_warehouse.name)
            return False

        # Create the receiving transfer
        new_picking_vals = {
            'picking_type_id': receiving_type.id,
            'location_id': transit_loc.id,
            'location_dest_id': dest_location.id,
            'origin': picking.name,
            'partner_id': picking.partner_id.id if picking.partner_id else False,
        }

        new_picking = self.env['stock.picking'].create(new_picking_vals)

        # Copy move lines with proper product quantities
        for move in picking.move_ids:
            # Use the actual done quantity
            done_qty = move.quantity if hasattr(move, 'quantity') and move.quantity > 0 else move.product_uom_qty

            move_vals = {
                'name': move.name,
                'product_id': move.product_id.id,
                'product_uom_qty': done_qty,
                'product_uom': move.product_uom.id,
                'picking_id': new_picking.id,
                'location_id': transit_loc.id,
                'location_dest_id': dest_location.id,
                'description_picking': move.description_picking,
                'company_id': move.company_id.id,
                'date': fields.Datetime.now(),
            }
            self.env['stock.move'].create(move_vals)

        # Confirm the new picking
        new_picking.action_confirm()

        # Assign availability
        new_picking.action_assign()

        # Add message to original picking
        picking.message_post(
            body=_('Receipt transfer %s has been automatically created for %s.') %
                 (new_picking.name, dest_warehouse.name)
        )

        # Add message to new picking
        new_picking.message_post(
            body=_(
                'This receipt was automatically created from transfer %s. Please validate to receive products.') % picking.name
        )

        _logger.info('Created receipt transfer %s for warehouse %s from picking %s',
                     new_picking.name, dest_warehouse.name, picking.name)

        return new_picking

    def _notify_main_warehouse_users(self, picking):
        """Send notification to Main warehouse users about new request"""
        main_warehouse = picking.location_id.warehouse_id

        if not main_warehouse:
            _logger.warning('No main warehouse found for picking: %s', picking.name)
            return

        main_wh_users = self._get_warehouse_users(main_warehouse)

        if not main_wh_users:
            _logger.warning('No users found for Main warehouse notification')
            return

        requesting_warehouse = picking.picking_type_id.warehouse_id
        product_lines = []
        for move in picking.move_ids:
            product_lines.append('%s (%s %s)' % (move.product_id.name, move.product_uom_qty, move.product_uom.name))

        message = _(
            '<p><strong>New Stock Request</strong></p>'
            '<p>Warehouse <strong>%s</strong> has requested products from your warehouse:</p>'
            '<ul>%s</ul>'
            '<p>Transfer Reference: <strong>%s</strong></p>'
            '<p>Please review and validate this request.</p>'
        ) % (
                      requesting_warehouse.name,
                      ''.join(['<li>%s</li>' % line for line in product_lines]),
                      picking.name
                  )

        picking.message_post(
            body=message,
            subject=_('New Stock Request from %s') % requesting_warehouse.name,
            partner_ids=main_wh_users.mapped('partner_id').ids,
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

        _logger.info('Sent notification to Main warehouse users for picking: %s', picking.name)

    def _notify_warehouse_user(self, picking, notification_type):
        """Send notification to warehouse users"""
        dest_warehouse = picking.picking_type_id.warehouse_id

        if not dest_warehouse:
            dest_warehouse = picking.location_dest_id.warehouse_id

        if not dest_warehouse:
            _logger.warning('No destination warehouse found for notification: %s', picking.name)
            return

        warehouse_users = self._get_warehouse_users(dest_warehouse)

        if not warehouse_users:
            _logger.warning('No users found for warehouse notification: %s', dest_warehouse.name)
            return

        source_warehouse_name = 'Main Office'
        if picking.origin:
            origin_picking = self.env['stock.picking'].search([('name', '=', picking.origin)], limit=1)
            if origin_picking and origin_picking.location_id.warehouse_id:
                source_warehouse_name = origin_picking.location_id.warehouse_id.name

        product_lines = []
        for move in picking.move_ids:
            qty = move.product_uom_qty
            product_lines.append('%s (%s %s)' % (move.product_id.name, qty, move.product_uom.name))

        if notification_type == 'approved':
            message = _(
                '<p><strong>Stock Request Approved</strong></p>'
                '<p>Your stock request has been approved by <strong>%s</strong>:</p>'
                '<ul>%s</ul>'
                '<p>Transfer Reference: <strong>%s</strong></p>'
                '<p><strong>Action Required:</strong> Please validate the receipt transfer to complete the stock transfer and update your inventory.</p>'
            ) % (
                          source_warehouse_name,
                          ''.join(['<li>%s</li>' % line for line in product_lines]),
                          picking.name
                      )
            subject = _('Stock Request Approved - %s') % picking.name
        else:
            message = _('Stock transfer notification')
            subject = _('Stock Transfer Update')

        picking.message_post(
            body=message,
            subject=subject,
            partner_ids=warehouse_users.mapped('partner_id').ids,
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

        _logger.info('Sent approval notification to %s users for picking: %s', dest_warehouse.name, picking.name)

    def _get_warehouse_users(self, warehouse):
        """Get users who have access to this warehouse"""
        try:
            warehouse_group_mapping = {
                'Main Office': ['Main WH', 'Main Office'],
                'Dammam': ['Dammam WH', 'Dammam'],
                'Baladiya': ['Baladiya WH', 'Baladiya'],
            }

            group_names = []
            for key, values in warehouse_group_mapping.items():
                if key.lower() in warehouse.name.lower():
                    group_names = values
                    break

            if group_names:
                warehouse_groups = self.env['res.groups'].search([
                    '|', ('name', 'in', group_names),
                    ('name', 'ilike', warehouse.name.split(' ')[0])
                ])

                if warehouse_groups:
                    warehouse_users = self.env['res.users'].search([
                        ('groups_id', 'in', warehouse_groups.ids),
                        ('active', '=', True),
                        ('share', '=', False)
                    ])
                    if warehouse_users:
                        _logger.info('Found %d users for warehouse %s', len(warehouse_users), warehouse.name)
                        return warehouse_users

            inventory_group = self.env.ref('stock.group_stock_user', raise_if_not_found=False)
            if inventory_group:
                all_users = self.env['res.users'].search([
                    ('groups_id', 'in', inventory_group.id),
                    ('active', '=', True),
                    ('share', '=', False)
                ])
                if all_users:
                    _logger.info('Using fallback: Found %d inventory users', len(all_users))
                    return all_users

            admin = self.env.ref('base.user_admin', raise_if_not_found=False)
            if admin:
                return admin

            return self.env['res.users'].browse([])

        except Exception as e:
            _logger.error('Error getting warehouse users: %s', str(e))
            admin = self.env.ref('base.user_admin', raise_if_not_found=False)
            return admin if admin else self.env['res.users'].browse([])





# # -*- coding: utf-8 -*-
# from odoo import models, fields, api, _
# from odoo.exceptions import UserError
# import logging
#
# _logger = logging.getLogger(__name__)
#
#
# class StockPicking(models.Model):
#     _inherit = 'stock.picking'
#
#     is_inter_warehouse_request = fields.Boolean(
#         string='Inter-Warehouse Request',
#         compute='_compute_is_inter_warehouse_request',
#         store=True
#     )
#
#     @api.depends('location_id', 'location_dest_id', 'location_id.warehouse_id', 'location_dest_id.usage')
#     def _compute_is_inter_warehouse_request(self):
#         """Identify if this is an inter-warehouse request"""
#         for picking in self:
#             # Check if source is from another warehouse and destination is transit
#             if (picking.location_id.warehouse_id and
#                     picking.location_dest_id.usage == 'transit' and
#                     picking.location_id.warehouse_id != picking.picking_type_id.warehouse_id):
#                 picking.is_inter_warehouse_request = True
#             else:
#                 picking.is_inter_warehouse_request = False
#
#     def button_validate(self):
#         """Override validate to add notifications and auto-create receipts"""
#         res = super(StockPicking, self).button_validate()
#
#         for picking in self:
#             # Check if this transfer goes to a transit location (Main warehouse validates)
#             if picking.location_dest_id.usage == 'transit' and picking.state == 'done':
#                 try:
#                     # Auto-create the second transfer (receipt) first
#                     new_picking = self._create_receipt_transfer(picking)
#
#                     # Send notification to requesting warehouse AFTER creating receipt
#                     if new_picking:
#                         self._notify_warehouse_user(new_picking, 'approved')
#
#                 except Exception as e:
#                     _logger.error('Error in warehouse automation: %s', str(e))
#                     # Continue even if notification fails
#
#         return res
#
#     def action_confirm(self):
#         """Override confirm to send notification to Main warehouse"""
#         res = super(StockPicking, self).action_confirm()
#
#         for picking in self:
#             # If this is a request from branch to main warehouse
#             if picking.is_inter_warehouse_request and picking.location_dest_id.usage == 'transit':
#                 try:
#                     # Notify Main warehouse users
#                     self._notify_main_warehouse_users(picking)
#                 except Exception as e:
#                     _logger.error('Error sending notification to main warehouse: %s', str(e))
#                     # Continue even if notification fails
#
#         return res
#
#     def _create_receipt_transfer(self, picking):
#         """Auto-create the second transfer from transit to warehouse stock"""
#         transit_loc = picking.location_dest_id
#         dest_warehouse = transit_loc.warehouse_id
#
#         if not dest_warehouse:
#             _logger.warning('No destination warehouse found for transit location: %s', transit_loc.name)
#             return False
#
#         # Find the receiving operation type
#         receiving_type = self.env['stock.picking.type'].search([
#             ('warehouse_id', '=', dest_warehouse.id),
#             ('code', '=', 'internal'),
#             ('default_location_src_id', '=', transit_loc.id)
#         ], limit=1)
#
#         if not receiving_type:
#             # Try alternative: find any internal transfer in destination warehouse
#             receiving_type = self.env['stock.picking.type'].search([
#                 ('warehouse_id', '=', dest_warehouse.id),
#                 ('code', '=', 'internal')
#             ], limit=1)
#
#             if not receiving_type:
#                 # Log warning but don't block
#                 picking.message_post(
#                     body=_('Warning: Could not find receiving operation type for warehouse %s. '
#                            'Please create the receipt manually.') % dest_warehouse.name
#                 )
#                 return False
#
#         # Get the final destination location (warehouse stock location)
#         dest_location = receiving_type.default_location_dest_id
#
#         # If no default, try to find the main stock location of the warehouse
#         if not dest_location:
#             dest_location = self.env['stock.location'].search([
#                 ('warehouse_id', '=', dest_warehouse.id),
#                 ('usage', '=', 'internal'),
#                 ('location_id.usage', '=', 'view')
#             ], limit=1)
#
#         if not dest_location:
#             _logger.error('Could not determine destination location for warehouse: %s', dest_warehouse.name)
#             return False
#
#         # Create the receiving transfer
#         new_picking_vals = {
#             'picking_type_id': receiving_type.id,
#             'location_id': transit_loc.id,
#             'location_dest_id': dest_location.id,
#             'origin': picking.name,
#             'partner_id': picking.partner_id.id if picking.partner_id else False,
#         }
#
#         new_picking = self.env['stock.picking'].create(new_picking_vals)
#
#         # Copy move lines with proper product quantities
#         for move in picking.move_ids:
#             # Use the actual done quantity, not the initial requested quantity
#             done_qty = move.quantity if hasattr(move, 'quantity') else move.product_uom_qty
#
#             move_vals = {
#                 'name': move.name,
#                 'product_id': move.product_id.id,
#                 'product_uom_qty': done_qty,  # Use actual done quantity
#                 'product_uom': move.product_uom.id,
#                 'picking_id': new_picking.id,
#                 'location_id': transit_loc.id,
#                 'location_dest_id': dest_location.id,
#                 'description_picking': move.description_picking,
#                 'company_id': move.company_id.id,
#                 'date': fields.Datetime.now(),
#             }
#             self.env['stock.move'].create(move_vals)
#
#         # Confirm the new picking
#         new_picking.action_confirm()
#
#         # Assign availability
#         new_picking.action_assign()
#
#         # Add message to original picking
#         picking.message_post(
#             body=_('Receipt transfer %s has been automatically created for %s.') %
#                  (new_picking.name, dest_warehouse.name)
#         )
#
#         # Add message to new picking
#         new_picking.message_post(
#             body=_(
#                 'This receipt was automatically created from transfer %s. Please validate to receive products.') % picking.name
#         )
#
#         _logger.info('Created receipt transfer %s for warehouse %s', new_picking.name, dest_warehouse.name)
#
#         return new_picking
#
#     def _notify_main_warehouse_users(self, picking):
#         """Send notification to Main warehouse users about new request"""
#         # Get Main warehouse (source warehouse)
#         main_warehouse = picking.location_id.warehouse_id
#
#         if not main_warehouse:
#             _logger.warning('No main warehouse found for picking: %s', picking.name)
#             return
#
#         # Find users who have access to Main warehouse
#         main_wh_users = self._get_warehouse_users(main_warehouse)
#
#         if not main_wh_users:
#             _logger.warning('No users found for Main warehouse notification')
#             return
#
#         # Create notification message
#         requesting_warehouse = picking.picking_type_id.warehouse_id
#         product_lines = []
#         for move in picking.move_ids:
#             product_lines.append('%s (%s %s)' % (move.product_id.name, move.product_uom_qty, move.product_uom.name))
#
#         message = _(
#             '<p><strong>New Stock Request</strong></p>'
#             '<p>Warehouse <strong>%s</strong> has requested products from your warehouse:</p>'
#             '<ul>%s</ul>'
#             '<p>Transfer Reference: <strong>%s</strong></p>'
#             '<p>Please review and validate this request.</p>'
#         ) % (
#                       requesting_warehouse.name,
#                       ''.join(['<li>%s</li>' % line for line in product_lines]),
#                       picking.name
#                   )
#
#         # Post message and notify users
#         picking.message_post(
#             body=message,
#             subject=_('New Stock Request from %s') % requesting_warehouse.name,
#             partner_ids=main_wh_users.mapped('partner_id').ids,
#             message_type='notification',
#             subtype_xmlid='mail.mt_note',
#         )
#
#         _logger.info('Sent notification to Main warehouse users for picking: %s', picking.name)
#
#     def _notify_warehouse_user(self, picking, notification_type):
#         """Send notification to warehouse users"""
#         # Get destination warehouse from picking type (more reliable)
#         dest_warehouse = picking.picking_type_id.warehouse_id
#
#         # Alternative: try from location
#         if not dest_warehouse:
#             dest_warehouse = picking.location_dest_id.warehouse_id
#
#         if not dest_warehouse:
#             _logger.warning('No destination warehouse found for notification: %s', picking.name)
#             return
#
#         # Find users who have access to destination warehouse
#         warehouse_users = self._get_warehouse_users(dest_warehouse)
#
#         if not warehouse_users:
#             _logger.warning('No users found for warehouse notification: %s', dest_warehouse.name)
#             return
#
#         # Get source from original picking's origin field
#         source_warehouse_name = 'Main Office'  # Default
#         if picking.origin:
#             origin_picking = self.env['stock.picking'].search([('name', '=', picking.origin)], limit=1)
#             if origin_picking and origin_picking.location_id.warehouse_id:
#                 source_warehouse_name = origin_picking.location_id.warehouse_id.name
#
#         product_lines = []
#         for move in picking.move_ids:
#             qty = move.product_uom_qty
#             product_lines.append('%s (%s %s)' % (move.product_id.name, qty, move.product_uom.name))
#
#         if notification_type == 'approved':
#             message = _(
#                 '<p><strong>Stock Request Approved</strong></p>'
#                 '<p>Your stock request has been approved by <strong>%s</strong>:</p>'
#                 '<ul>%s</ul>'
#                 '<p>Transfer Reference: <strong>%s</strong></p>'
#                 '<p><strong>Action Required:</strong> Please validate the receipt transfer to complete the stock transfer and update your inventory.</p>'
#             ) % (
#                           source_warehouse_name,
#                           ''.join(['<li>%s</li>' % line for line in product_lines]),
#                           picking.name
#                       )
#             subject = _('Stock Request Approved - %s') % picking.name
#         else:
#             message = _('Stock transfer notification')
#             subject = _('Stock Transfer Update')
#
#         # Post message and notify users
#         picking.message_post(
#             body=message,
#             subject=subject,
#             partner_ids=warehouse_users.mapped('partner_id').ids,
#             message_type='notification',
#             subtype_xmlid='mail.mt_note',
#         )
#
#         _logger.info('Sent approval notification to %s users for picking: %s', dest_warehouse.name, picking.name)
#
#     def _get_warehouse_users(self, warehouse):
#         """Get users who have access to this warehouse"""
#         try:
#             # Try to find users based on warehouse-specific groups
#             warehouse_group_mapping = {
#                 'Main Office': ['Main WH', 'Main Office'],
#                 'Dammam': ['Dammam WH', 'Dammam'],
#                 'Baladiya': ['Baladiya WH', 'Baladiya'],
#             }
#
#             # Try to match warehouse name to group name
#             group_names = []
#             for key, values in warehouse_group_mapping.items():
#                 if key.lower() in warehouse.name.lower():
#                     group_names = values
#                     break
#
#             if group_names:
#                 warehouse_groups = self.env['res.groups'].search([
#                     '|', ('name', 'in', group_names),
#                     ('name', 'ilike', warehouse.name.split(' ')[0])
#                 ])
#
#                 if warehouse_groups:
#                     # Get users who are in these groups and active
#                     warehouse_users = self.env['res.users'].search([
#                         ('groups_id', 'in', warehouse_groups.ids),
#                         ('active', '=', True),
#                         ('share', '=', False)  # Exclude portal users
#                     ])
#                     if warehouse_users:
#                         _logger.info('Found %d users for warehouse %s', len(warehouse_users), warehouse.name)
#                         return warehouse_users
#
#             # Fallback to all inventory users
#             inventory_group = self.env.ref('stock.group_stock_user', raise_if_not_found=False)
#             if inventory_group:
#                 all_users = self.env['res.users'].search([
#                     ('groups_id', 'in', inventory_group.id),
#                     ('active', '=', True),
#                     ('share', '=', False)
#                 ])
#                 if all_users:
#                     _logger.info('Using fallback: Found %d inventory users', len(all_users))
#                     return all_users
#
#             # Last fallback - return admin
#             admin = self.env.ref('base.user_admin', raise_if_not_found=False)
#             if admin:
#                 return admin
#
#             return self.env['res.users'].browse([])
#
#         except Exception as e:
#             _logger.error('Error getting warehouse users: %s', str(e))
#             # Return admin user as last resort
#             admin = self.env.ref('base.user_admin', raise_if_not_found=False)
#             return admin if admin else self.env['res.users'].browse([])