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

    @api.depends('location_id', 'location_dest_id', 'location_id.warehouse_id', 'location_dest_id.warehouse_id')
    def _compute_is_inter_warehouse_request(self):
        """Identify if this is an inter-warehouse request"""
        for picking in self:
            source_wh = picking.location_id.warehouse_id
            dest_wh = picking.location_dest_id.warehouse_id

            # Check if source and destination are from different warehouses
            if source_wh and dest_wh and source_wh != dest_wh:
                picking.is_inter_warehouse_request = True
            else:
                picking.is_inter_warehouse_request = False

    def action_confirm(self):
        """Override confirm to send notification to source warehouse (Main warehouse)"""
        res = super(StockPicking, self).action_confirm()

        for picking in self:
            # If this is an inter-warehouse request
            if picking.is_inter_warehouse_request:
                try:
                    # Get source and destination warehouses
                    source_wh = picking.location_id.warehouse_id
                    requesting_wh = picking.location_dest_id.warehouse_id

                    if source_wh and requesting_wh and source_wh != requesting_wh:
                        # Notify source warehouse (Main) about the request
                        self._notify_source_warehouse_users(picking, source_wh, requesting_wh)
                        _logger.info('Notification sent to %s warehouse users for request from %s',
                                     source_wh.name, requesting_wh.name)
                except Exception as e:
                    _logger.error('Error sending notification to source warehouse: %s', str(e))

        return res

    def button_validate(self):
        """Override validate to send notifications and auto-create receipts"""
        res = super(StockPicking, self).button_validate()

        for picking in self:
            if picking.is_inter_warehouse_request and picking.state == 'done':
                try:
                    source_wh = picking.location_id.warehouse_id
                    dest_wh = picking.location_dest_id.warehouse_id

                    if source_wh and dest_wh:
                        # Send approval notification to destination warehouse
                        self._notify_destination_warehouse_users(picking, source_wh, dest_wh)
                        _logger.info('Approval notification sent to %s warehouse users', dest_wh.name)

                        # Auto-create the receipt transfer in destination warehouse
                        new_picking = self._create_receipt_transfer(picking, dest_wh)
                        if new_picking:
                            _logger.info('Receipt transfer %s created for %s', new_picking.name, dest_wh.name)

                except Exception as e:
                    _logger.error('Error in warehouse automation: %s', str(e))
                    # Log but don't block the validation

        return res

    def _create_receipt_transfer(self, picking, dest_warehouse):
        """Auto-create the receipt transfer in destination warehouse"""
        if not dest_warehouse:
            _logger.warning('No destination warehouse found for picking %s', picking.name)
            return False

        # Find the internal picking type for destination warehouse
        # Look for internal transfer type that can receive goods
        receiving_type = self.env['stock.picking.type'].search([
            ('warehouse_id', '=', dest_warehouse.id),
            ('code', '=', 'internal'),
        ], limit=1)

        if not receiving_type:
            # Try to find any incoming type as fallback
            receiving_type = self.env['stock.picking.type'].search([
                ('warehouse_id', '=', dest_warehouse.id),
                ('code', 'in', ['incoming', 'internal']),
            ], limit=1)

        if not receiving_type:
            message = _('Warning: Could not find suitable operation type for warehouse %s. '
                        'Please create the receipt manually.') % dest_warehouse.name
            picking.message_post(body=message)
            _logger.warning(message)
            return False

        # Get the main stock location of destination warehouse
        dest_stock_location = dest_warehouse.lot_stock_id

        # Create the receiving transfer
        new_picking_vals = {
            'picking_type_id': receiving_type.id,
            'location_id': picking.location_dest_id.id,  # Source is where original picking delivered
            'location_dest_id': dest_stock_location.id,  # Destination is warehouse stock
            'origin': picking.name,
            'partner_id': picking.partner_id.id if picking.partner_id else False,
            'scheduled_date': fields.Datetime.now(),
        }

        new_picking = self.env['stock.picking'].create(new_picking_vals)

        # Copy move lines
        for move in picking.move_ids.filtered(lambda m: m.state == 'done'):
            move_vals = {
                'name': move.name,
                'product_id': move.product_id.id,
                'product_uom_qty': move.quantity,
                'product_uom': move.product_uom.id,
                'picking_id': new_picking.id,
                'location_id': picking.location_dest_id.id,
                'location_dest_id': dest_stock_location.id,
                'description_picking': move.description_picking,
            }
            self.env['stock.move'].create(move_vals)

        # Confirm the new picking
        if new_picking.move_ids:
            new_picking.action_confirm()
            new_picking.action_assign()
        else:
            _logger.warning('No moves created for new picking %s', new_picking.name)

        # Add message to original picking
        picking.message_post(
            body=_('Receipt transfer %s has been automatically created for %s warehouse.') %
                 (new_picking.name, dest_warehouse.name),
            message_type='notification'
        )

        # Add message to new picking with follower notification
        new_picking.message_post(
            body=_(
                'This receipt was automatically created from transfer %s. Please validate to receive the products into your warehouse.') % picking.name,
            message_type='notification',
            subtype_xmlid='mail.mt_comment'
        )

        return new_picking

    def _notify_source_warehouse_users(self, picking, source_wh, requesting_wh):
        """Send notification to source warehouse users about new request"""
        # Find users who have access to source warehouse
        source_wh_users = self._get_warehouse_users(source_wh)

        if not source_wh_users:
            _logger.warning('No users found for source warehouse %s', source_wh.name)
            return

        # Create detailed product list
        product_lines = []
        for move in picking.move_ids:
            product_lines.append('%s: %s %s' % (
                move.product_id.name,
                move.product_uom_qty,
                move.product_uom.name
            ))

        message = _(
            '<div style="font-family: Arial, sans-serif;">'
            '<h3 style="color: #875a7b;">🔔 New Stock Request</h3>'
            '<p><strong>Requesting Warehouse:</strong> %s</p>'
            '<p><strong>Transfer Reference:</strong> %s</p>'
            '<h4>Requested Products:</h4>'
            '<ul>%s</ul>'
            '<p style="margin-top: 15px; padding: 10px; background-color: #f0f0f0; border-left: 4px solid #875a7b;">'
            '<strong>Action Required:</strong> Please review and validate this request to approve the transfer.'
            '</p>'
            '</div>'
        ) % (
                      requesting_wh.name,
                      picking.name,
                      ''.join(['<li>%s</li>' % line for line in product_lines])
                  )

        # Subscribe users to the picking
        picking.message_subscribe(partner_ids=source_wh_users.mapped('partner_id').ids)

        # Post message with email notification
        picking.message_post(
            body=message,
            subject=_('🔔 New Stock Request from %s') % requesting_wh.name,
            partner_ids=source_wh_users.mapped('partner_id').ids,
            message_type='notification',
            subtype_xmlid='mail.mt_comment',
            email_layout_xmlid='mail.mail_notification_light'
        )

        # Also create activity for visibility
        for user in source_wh_users:
            self.env['mail.activity'].create({
                'res_id': picking.id,
                'res_model_id': self.env['ir.model']._get('stock.picking').id,
                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                'summary': _('Review stock request from %s') % requesting_wh.name,
                'note': _('Please review and validate the stock request for %s') % ', '.join(product_lines[:3]),
                'user_id': user.id,
            })

    def _notify_destination_warehouse_users(self, picking, source_wh, dest_wh):
        """Send approval notification to destination warehouse users"""
        # Find users who have access to destination warehouse
        dest_wh_users = self._get_warehouse_users(dest_wh)

        if not dest_wh_users:
            _logger.warning('No users found for destination warehouse %s', dest_wh.name)
            return

        # Create detailed product list
        product_lines = []
        for move in picking.move_ids.filtered(lambda m: m.state == 'done'):
            product_lines.append('%s: %s %s' % (
                move.product_id.name,
                move.quantity,
                move.product_uom.name
            ))

        message = _(
            '<div style="font-family: Arial, sans-serif;">'
            '<h3 style="color: #28a745;">✅ Stock Request Approved</h3>'
            '<p><strong>Approved by:</strong> %s</p>'
            '<p><strong>Original Request:</strong> %s</p>'
            '<h4>Approved Products:</h4>'
            '<ul>%s</ul>'
            '<p style="margin-top: 15px; padding: 10px; background-color: #d4edda; border-left: 4px solid #28a745;">'
            '<strong>Next Step:</strong> A receipt transfer has been automatically created. '
            'Please validate it to receive the products into your warehouse inventory.'
            '</p>'
            '</div>'
        ) % (
                      source_wh.name,
                      picking.name,
                      ''.join(['<li>%s</li>' % line for line in product_lines])
                  )

        # Subscribe users to the picking
        picking.message_subscribe(partner_ids=dest_wh_users.mapped('partner_id').ids)

        # Post message with email notification
        picking.message_post(
            body=message,
            subject=_('✅ Stock Request Approved - %s') % picking.name,
            partner_ids=dest_wh_users.mapped('partner_id').ids,
            message_type='notification',
            subtype_xmlid='mail.mt_comment',
            email_layout_xmlid='mail.mail_notification_light'
        )

    def _get_warehouse_users(self, warehouse):
        """Get users who have access to this warehouse"""
        try:
            # Define warehouse group mapping
            warehouse_group_mapping = {
                'Main': 'Main WH',
                'main': 'Main WH',
                'Dammam': 'Dammam WH',
                'dammam': 'Dammam WH',
                'Baladiya': 'Baladiya WH',
                'baladiya': 'Baladiya WH',
            }

            # Try to match warehouse name to group name
            group_name = None
            warehouse_name_lower = warehouse.name.lower()

            for key, value in warehouse_group_mapping.items():
                if key.lower() in warehouse_name_lower:
                    group_name = value
                    break

            if group_name:
                warehouse_groups = self.env['res.groups'].search([
                    ('name', '=', group_name)
                ])

                if warehouse_groups:
                    warehouse_users = self.env['res.users'].search([
                        ('groups_id', 'in', warehouse_groups.ids),
                        ('active', '=', True),
                        ('id', '!=', 1)  # Exclude OdooBot
                    ])
                    if warehouse_users:
                        _logger.info('Found %d users for warehouse %s via group %s',
                                     len(warehouse_users), warehouse.name, group_name)
                        return warehouse_users

            # Fallback: Get all stock managers
            stock_manager_group = self.env.ref('stock.group_stock_manager', raise_if_not_found=False)
            if stock_manager_group:
                manager_users = self.env['res.users'].search([
                    ('groups_id', 'in', stock_manager_group.id),
                    ('active', '=', True),
                    ('id', '!=', 1)
                ])
                if manager_users:
                    _logger.info('Using stock managers as fallback for warehouse %s', warehouse.name)
                    return manager_users

            # Last fallback: Get all inventory users
            inventory_group = self.env.ref('stock.group_stock_user', raise_if_not_found=False)
            if inventory_group:
                all_users = self.env['res.users'].search([
                    ('groups_id', 'in', inventory_group.id),
                    ('active', '=', True),
                    ('id', '!=', 1)
                ])
                if all_users:
                    _logger.info('Using all stock users as fallback for warehouse %s', warehouse.name)
                    return all_users

            _logger.warning('No users found for warehouse %s', warehouse.name)
            return self.env['res.users']

        except Exception as e:
            _logger.error('Error getting warehouse users: %s', str(e))
            return self.env['res.users']








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
#             # Check if this transfer goes to a transit location
#             if picking.location_dest_id.usage == 'transit' and picking.state == 'done':
#                 try:
#                     # Send notification to requesting warehouse
#                     self._notify_warehouse_user(picking, 'approved')
#
#                     # Auto-create the second transfer (receipt)
#                     self._create_receipt_transfer(picking)
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
#             return
#
#         # Find the receiving operation type
#         receiving_type = self.env['stock.picking.type'].search([
#             ('warehouse_id', '=', dest_warehouse.id),
#             ('code', '=', 'internal'),
#             ('default_location_src_id', '=', transit_loc.id)
#         ], limit=1)
#
#         if not receiving_type:
#             # Log warning but don't block
#             picking.message_post(
#                 body=_('Warning: Could not find receiving operation type for warehouse %s. '
#                        'Please create the receipt manually.') % dest_warehouse.name
#             )
#             return
#
#         # Create the receiving transfer
#         new_picking_vals = {
#             'picking_type_id': receiving_type.id,
#             'location_id': transit_loc.id,
#             'location_dest_id': receiving_type.default_location_dest_id.id,
#             'origin': picking.name,
#             'partner_id': picking.partner_id.id if picking.partner_id else False,
#         }
#
#         new_picking = self.env['stock.picking'].create(new_picking_vals)
#
#         # Copy move lines
#         for move in picking.move_ids:
#             move_vals = {
#                 'name': move.name,
#                 'product_id': move.product_id.id,
#                 'product_uom_qty': move.quantity,
#                 'product_uom': move.product_uom.id,
#                 'picking_id': new_picking.id,
#                 'location_id': transit_loc.id,
#                 'location_dest_id': receiving_type.default_location_dest_id.id,
#                 'description_picking': move.description_picking,
#             }
#             self.env['stock.move'].create(move_vals)
#
#         # Confirm the new picking
#         new_picking.action_confirm()
#
#         # Add message to original picking
#         picking.message_post(
#             body=_('Receipt transfer %s has been automatically created for %s.') %
#                  (new_picking.name, dest_warehouse.name)
#         )
#
#         # Add message to new picking
#         new_picking.message_post(
#             body=_('This receipt was automatically created from transfer %s.') % picking.name
#         )
#
#         return new_picking
#
#     def _notify_main_warehouse_users(self, picking):
#         """Send notification to Main warehouse users about new request"""
#         # Get Main warehouse (source warehouse)
#         main_warehouse = picking.location_id.warehouse_id
#
#         if not main_warehouse:
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
#         product_lines = ', '.join([
#             '%s (%s %s)' % (move.product_id.name, move.product_uom_qty, move.product_uom.name)
#             for move in picking.move_ids
#         ])
#
#         message = _(
#             '<p><strong>New Stock Request</strong></p>'
#             '<p>Warehouse <strong>%s</strong> has requested products from your warehouse:</p>'
#             '<ul>%s</ul>'
#             '<p>Transfer Reference: <strong>%s</strong></p>'
#             '<p>Please review and validate this request.</p>'
#         ) % (
#                       requesting_warehouse.name,
#                       ''.join(['<li>%s</li>' % line for line in product_lines.split(', ')]),
#                       picking.name
#                   )
#
#         # Post message and notify users
#         picking.message_post(
#             body=message,
#             subject=_('New Stock Request from %s') % requesting_warehouse.name,
#             partner_ids=main_wh_users.mapped('partner_id').ids,
#             message_type='notification',
#         )
#
#     def _notify_warehouse_user(self, picking, notification_type):
#         """Send notification to warehouse users"""
#         dest_warehouse = picking.location_dest_id.warehouse_id
#
#         if not dest_warehouse:
#             return
#
#         # Find users who have access to destination warehouse
#         warehouse_users = self._get_warehouse_users(dest_warehouse)
#
#         if not warehouse_users:
#             _logger.warning('No users found for warehouse notification')
#             return
#
#         source_warehouse = picking.location_id.warehouse_id
#         product_lines = ', '.join([
#             '%s (%s %s)' % (move.product_id.name, move.quantity, move.product_uom.name)
#             for move in picking.move_ids
#         ])
#
#         if notification_type == 'approved':
#             message = _(
#                 '<p><strong>Stock Request Approved</strong></p>'
#                 '<p>Your stock request has been approved by <strong>%s</strong>:</p>'
#                 '<ul>%s</ul>'
#                 '<p>Original Request: <strong>%s</strong></p>'
#                 '<p>Products are now in transit. Please validate the receipt to complete the transfer.</p>'
#             ) % (
#                           source_warehouse.name,
#                           ''.join(['<li>%s</li>' % line for line in product_lines.split(', ')]),
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
#         )
#
#     def _get_warehouse_users(self, warehouse):
#         """Get users who have access to this warehouse"""
#         try:
#             # Option 1: Try to find warehouse-specific group users first
#             warehouse_group_mapping = {
#                 'Main Office': 'Main WH',
#                 'Dammam': 'Dammam WH',
#                 'Baladiya': 'Baladiya WH',
#             }
#
#             # Try to match warehouse name to group name
#             group_name = None
#             for key, value in warehouse_group_mapping.items():
#                 if key in warehouse.name:
#                     group_name = value
#                     break
#
#             if group_name:
#                 warehouse_groups = self.env['res.groups'].search([
#                     ('name', '=', group_name)
#                 ])
#
#                 if warehouse_groups:
#                     # Get users who are in these groups
#                     warehouse_users = self.env['res.users'].search([
#                         ('groups_id', 'in', warehouse_groups.ids),
#                         ('active', '=', True)
#                     ])
#                     if warehouse_users:
#                         return warehouse_users
#
#             # Option 2: Fallback to all inventory users
#             inventory_group = self.env.ref('stock.group_stock_user', raise_if_not_found=False)
#             if inventory_group:
#                 all_users = self.env['res.users'].search([
#                     ('groups_id', 'in', inventory_group.id),
#                     ('active', '=', True)
#                 ])
#                 return all_users
#
#             # Option 3: Last fallback - return admin
#             return self.env.ref('base.user_admin', raise_if_not_found=False)
#
#         except Exception as e:
#             _logger.error('Error getting warehouse users: %s', str(e))
#             # Return admin user as last resort
#             return self.env['res.users'].browse(2)
#
#     @api.model
#     def _get_warehouse_for_user(self, user):
#         """Get the warehouse assigned to a user"""
#         # Check if user has a default warehouse set
#         if hasattr(user, 'property_warehouse_id') and user.property_warehouse_id:
#             return user.property_warehouse_id
#
#         # Try to find from groups
#         for group in user.groups_id:
#             if 'Main WH' in group.name or 'Main Office' in group.name:
#                 return self.env['stock.warehouse'].search([
#                     ('name', 'ilike', 'Main Office')
#                 ], limit=1)
#             elif 'Dammam' in group.name:
#                 return self.env['stock.warehouse'].search([
#                     ('name', 'ilike', 'Dammam')
#                 ], limit=1)
#             elif 'Baladiya' in group.name:
#                 return self.env['stock.warehouse'].search([
#                     ('name', 'ilike', 'Baladiya')
#                 ], limit=1)
#
#         return False







# -*- coding: utf-8 -*-
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
#             # Check if this transfer goes to a transit location
#             if picking.location_dest_id.usage == 'transit' and picking.state == 'done':
#                 try:
#                     # Send notification to requesting warehouse
#                     self._notify_warehouse_user(picking, 'approved')
#
#                     # Auto-create the second transfer (receipt)
#                     self._create_receipt_transfer(picking)
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
#             return
#
#         # Find the receiving operation type
#         receiving_type = self.env['stock.picking.type'].search([
#             ('warehouse_id', '=', dest_warehouse.id),
#             ('code', '=', 'internal'),
#             ('default_location_src_id', '=', transit_loc.id)
#         ], limit=1)
#
#         if not receiving_type:
#             # Log warning but don't block
#             picking.message_post(
#                 body=_('Warning: Could not find receiving operation type for warehouse %s. '
#                        'Please create the receipt manually.') % dest_warehouse.name
#             )
#             return
#
#         # Create the receiving transfer
#         new_picking_vals = {
#             'picking_type_id': receiving_type.id,
#             'location_id': transit_loc.id,
#             'location_dest_id': receiving_type.default_location_dest_id.id,
#             'origin': picking.name,
#             'partner_id': picking.partner_id.id if picking.partner_id else False,
#         }
#
#         new_picking = self.env['stock.picking'].create(new_picking_vals)
#
#         # Copy move lines
#         for move in picking.move_ids:
#             move_vals = {
#                 'name': move.name,
#                 'product_id': move.product_id.id,
#                 'product_uom_qty': move.quantity,
#                 'product_uom': move.product_uom.id,
#                 'picking_id': new_picking.id,
#                 'location_id': transit_loc.id,
#                 'location_dest_id': receiving_type.default_location_dest_id.id,
#                 'description_picking': move.description_picking,
#             }
#             self.env['stock.move'].create(move_vals)
#
#         # Confirm the new picking
#         new_picking.action_confirm()
#
#         # Add message to original picking
#         picking.message_post(
#             body=_('Receipt transfer %s has been automatically created for %s.') %
#                  (new_picking.name, dest_warehouse.name)
#         )
#
#         # Add message to new picking
#         new_picking.message_post(
#             body=_('This receipt was automatically created from transfer %s.') % picking.name
#         )
#
#         return new_picking
#     def _notify_main_warehouse_users(self, picking):
#         """Send notification to Main warehouse users about new request"""
#         # Get Main warehouse (source warehouse)
#         main_warehouse = picking.location_id.warehouse_id
#
#         if not main_warehouse:
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
#         product_lines = ', '.join([
#             '%s (%s %s)' % (move.product_id.name, move.product_uom_qty, move.product_uom.name)
#             for move in picking.move_ids
#         ])
#
#         message = _(
#             '<p><strong>New Stock Request</strong></p>'
#             '<p>Warehouse <strong>%s</strong> has requested products from your warehouse:</p>'
#             '<ul>%s</ul>'
#             '<p>Transfer Reference: <strong>%s</strong></p>'
#             '<p>Please review and validate this request.</p>'
#         ) % (
#                       requesting_warehouse.name,
#                       ''.join(['<li>%s</li>' % line for line in product_lines.split(', ')]),
#                       picking.name
#                   )
#
#         # Post message as internal note (no email)
#         picking.message_post(
#             body=message,
#             subject=_('New Stock Request from %s') % requesting_warehouse.name,
#             partner_ids=main_wh_users.mapped('partner_id').ids,
#             message_type='notification',
#             subtype_xmlid='mail.mt_note',  # Internal note - no email
#         )
#
#         # Also create activity for each user (appears in their "To Do" list)
#         for user in main_wh_users:
#             self.env['mail.activity'].create({
#                 'res_id': picking.id,
#                 'res_model_id': self.env['ir.model']._get('stock.picking').id,
#                 'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
#                 'summary': _('Review Stock Request from %s') % requesting_warehouse.name,
#                 'note': message,
#                 'user_id': user.id,
#             })
#
#     def _notify_warehouse_user(self, picking, notification_type):
#         """Send notification to warehouse users"""
#         dest_warehouse = picking.location_dest_id.warehouse_id
#
#         if not dest_warehouse:
#             return
#
#         # Find users who have access to destination warehouse
#         warehouse_users = self._get_warehouse_users(dest_warehouse)
#
#         if not warehouse_users:
#             _logger.warning('No users found for warehouse notification')
#             return
#
#         source_warehouse = picking.location_id.warehouse_id
#         product_lines = ', '.join([
#             '%s (%s %s)' % (move.product_id.name, move.quantity, move.product_uom.name)
#             for move in picking.move_ids
#         ])
#
#         if notification_type == 'approved':
#             message = _(
#                 '<p><strong>Stock Request Approved</strong></p>'
#                 '<p>Your stock request has been approved by <strong>%s</strong>:</p>'
#                 '<ul>%s</ul>'
#                 '<p>Original Request: <strong>%s</strong></p>'
#                 '<p>Products are now in transit. Please validate the receipt to complete the transfer.</p>'
#             ) % (
#                           source_warehouse.name,
#                           ''.join(['<li>%s</li>' % line for line in product_lines.split(', ')]),
#                           picking.name
#                       )
#             subject = _('Stock Request Approved - %s') % picking.name
#         else:
#             message = _('Stock transfer notification')
#             subject = _('Stock Transfer Update')
#
#         # Post message as internal note (no email)
#         picking.message_post(
#             body=message,
#             subject=subject,
#             partner_ids=warehouse_users.mapped('partner_id').ids,
#             message_type='notification',
#             subtype_xmlid='mail.mt_note',  # Internal note - no email
#         )
#
#         # Create activity for warehouse users
#         if notification_type == 'approved':
#             # Find the second transfer (receipt)
#             receipt_transfer = self.env['stock.picking'].search([
#                 ('origin', '=', picking.name),
#                 ('location_id', '=', picking.location_dest_id.id),
#                 ('state', '!=', 'done')
#             ], limit=1)
#
#             if receipt_transfer:
#                 for user in warehouse_users:
#                     self.env['mail.activity'].create({
#                         'res_id': receipt_transfer.id,
#                         'res_model_id': self.env['ir.model']._get('stock.picking').id,
#                         'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
#                         'summary': _('Validate Receipt from %s') % source_warehouse.name,
#                         'note': message,
#                         'user_id': user.id,
#                     })




    # def _notify_main_warehouse_users(self, picking):
    #     """Send notification to Main warehouse users about new request"""
    #     # Get Main warehouse (source warehouse)
    #     main_warehouse = picking.location_id.warehouse_id
    #
    #     if not main_warehouse:
    #         return
    #
    #     # Find users who have access to Main warehouse
    #     main_wh_users = self._get_warehouse_users(main_warehouse)
    #
    #     if not main_wh_users:
    #         _logger.warning('No users found for Main warehouse notification')
    #         return
    #
    #     # Create notification message
    #     requesting_warehouse = picking.picking_type_id.warehouse_id
    #     product_lines = ', '.join([
    #         '%s (%s %s)' % (move.product_id.name, move.product_uom_qty, move.product_uom.name)
    #         for move in picking.move_ids
    #     ])
    #
    #     message = _(
    #         '<p><strong>New Stock Request</strong></p>'
    #         '<p>Warehouse <strong>%s</strong> has requested products from your warehouse:</p>'
    #         '<ul>%s</ul>'
    #         '<p>Transfer Reference: <strong>%s</strong></p>'
    #         '<p>Please review and validate this request.</p>'
    #     ) % (
    #                   requesting_warehouse.name,
    #                   ''.join(['<li>%s</li>' % line for line in product_lines.split(', ')]),
    #                   picking.name
    #               )
    #
    #     # Post message and notify users
    #     picking.message_post(
    #         body=message,
    #         subject=_('New Stock Request from %s') % requesting_warehouse.name,
    #         partner_ids=main_wh_users.mapped('partner_id').ids,
    #         message_type='notification',
    #     )
    #
    # def _notify_warehouse_user(self, picking, notification_type):
    #     """Send notification to warehouse users"""
    #     dest_warehouse = picking.location_dest_id.warehouse_id
    #
    #     if not dest_warehouse:
    #         return
    #
    #     # Find users who have access to destination warehouse
    #     warehouse_users = self._get_warehouse_users(dest_warehouse)
    #
    #     if not warehouse_users:
    #         _logger.warning('No users found for warehouse notification')
    #         return
    #
    #     source_warehouse = picking.location_id.warehouse_id
    #     product_lines = ', '.join([
    #         '%s (%s %s)' % (move.product_id.name, move.quantity, move.product_uom.name)
    #         for move in picking.move_ids
    #     ])
    #
    #     if notification_type == 'approved':
    #         message = _(
    #             '<p><strong>Stock Request Approved</strong></p>'
    #             '<p>Your stock request has been approved by <strong>%s</strong>:</p>'
    #             '<ul>%s</ul>'
    #             '<p>Original Request: <strong>%s</strong></p>'
    #             '<p>Products are now in transit. Please validate the receipt to complete the transfer.</p>'
    #         ) % (
    #                       source_warehouse.name,
    #                       ''.join(['<li>%s</li>' % line for line in product_lines.split(', ')]),
    #                       picking.name
    #                   )
    #         subject = _('Stock Request Approved - %s') % picking.name
    #     else:
    #         message = _('Stock transfer notification')
    #         subject = _('Stock Transfer Update')
    #
    #     # Post message and notify users
    #     picking.message_post(
    #         body=message,
    #         subject=subject,
    #         partner_ids=warehouse_users.mapped('partner_id').ids,
    #         message_type='notification',
    #     )
    #
    # def _get_warehouse_users(self, warehouse):
    #     """Get users who have access to this warehouse"""
    #     try:
    #         # Option 1: Try to find warehouse-specific group users first
    #         warehouse_group_mapping = {
    #             'Main Office': 'Main WH',
    #             'Dammam': 'Dammam WH',
    #             'Baladiya': 'Baladiya WH',
    #         }
    #
    #         # Try to match warehouse name to group name
    #         group_name = None
    #         for key, value in warehouse_group_mapping.items():
    #             if key in warehouse.name:
    #                 group_name = value
    #                 break
    #
    #         if group_name:
    #             warehouse_groups = self.env['res.groups'].search([
    #                 ('name', '=', group_name)
    #             ])
    #
    #             if warehouse_groups:
    #                 # Get users who are in these groups
    #                 warehouse_users = self.env['res.users'].search([
    #                     ('groups_id', 'in', warehouse_groups.ids),
    #                     ('active', '=', True)
    #                 ])
    #                 if warehouse_users:
    #                     return warehouse_users
    #
    #         # Option 2: Fallback to all inventory users
    #         inventory_group = self.env.ref('stock.group_stock_user', raise_if_not_found=False)
    #         if inventory_group:
    #             all_users = self.env['res.users'].search([
    #                 ('groups_id', 'in', inventory_group.id),
    #                 ('active', '=', True)
    #             ])
    #             return all_users
    #
    #         # Option 3: Last fallback - return admin
    #         return self.env.ref('base.user_admin', raise_if_not_found=False)
    #
    #     except Exception as e:
    #         _logger.error('Error getting warehouse users: %s', str(e))
    #         # Return admin user as last resort
    #         return self.env['res.users'].browse(2)
    #
    # @api.model
    # def _get_warehouse_for_user(self, user):
    #     """Get the warehouse assigned to a user"""
    #     # Check if user has a default warehouse set
    #     if hasattr(user, 'property_warehouse_id') and user.property_warehouse_id:
    #         return user.property_warehouse_id
    #
    #     # Try to find from groups
    #     for group in user.groups_id:
    #         if 'Main WH' in group.name or 'Main Office' in group.name:
    #             return self.env['stock.warehouse'].search([
    #                 ('name', 'ilike', 'Main Office')
    #             ], limit=1)
    #         elif 'Dammam' in group.name:
    #             return self.env['stock.warehouse'].search([
    #                 ('name', 'ilike', 'Dammam')
    #             ], limit=1)
    #         elif 'Baladiya' in group.name:
    #             return self.env['stock.warehouse'].search([
    #                 ('name', 'ilike', 'Baladiya')
    #             ], limit=1)
    #
    #     return False
