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
        res = super(StockPicking, self).button_validate()

        for picking in self:
            # Check if this transfer goes to a transit location
            if picking.location_dest_id.usage == 'transit' and picking.state == 'done':
                try:
                    # Auto-create the second transfer (receipt)
                    new_transfer = self._create_receipt_transfer(picking)

                    # Send notification to requesting warehouse
                    if new_transfer:
                        self._notify_warehouse_user(picking, new_transfer, 'approved')
                except Exception as e:
                    _logger.error('Error in warehouse automation: %s', str(e))
                    # Continue even if notification fails

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
                    # Continue even if notification fails

        return res

    def _create_receipt_transfer(self, picking):
        """Auto-create the second transfer from transit to warehouse stock"""
        transit_loc = picking.location_dest_id
        dest_warehouse = transit_loc.warehouse_id

        if not dest_warehouse:
            return False

        # Find the receiving operation type
        receiving_type = self.env['stock.picking.type'].search([
            ('warehouse_id', '=', dest_warehouse.id),
            ('code', '=', 'internal'),
            ('default_location_src_id', '=', transit_loc.id)
        ], limit=1)

        if not receiving_type:
            # Log warning but don't block
            picking.message_post(
                body=_('Warning: Could not find receiving operation type for warehouse %s. '
                       'Please create the receipt manually.') % dest_warehouse.name,
                subtype_xmlid='mail.mt_note',
            )
            return False

        # Create the receiving transfer in DRAFT state
        new_picking_vals = {
            'picking_type_id': receiving_type.id,
            'location_id': transit_loc.id,
            'location_dest_id': receiving_type.default_location_dest_id.id,
            'origin': picking.name,
            'partner_id': picking.partner_id.id if picking.partner_id else False,
        }

        new_picking = self.env['stock.picking'].create(new_picking_vals)

        # Copy move lines with correct quantities
        for move in picking.move_ids:
            # Use quantity_done (actual validated quantity) not product_uom_qty
            actual_qty = move.quantity_done if move.quantity_done > 0 else move.product_uom_qty

            move_vals = {
                'name': move.name,
                'product_id': move.product_id.id,
                'product_uom_qty': actual_qty,
                'product_uom': move.product_uom.id,
                'picking_id': new_picking.id,
                'location_id': transit_loc.id,
                'location_dest_id': receiving_type.default_location_dest_id.id,
                'description_picking': move.description_picking,
            }
            self.env['stock.move'].create(move_vals)

        # IMPORTANT: Only confirm, do NOT validate automatically
        # This keeps it in "Ready" state waiting for warehouse user to validate
        new_picking.action_confirm()

        # Set quantities to available so user can validate immediately
        for move in new_picking.move_ids:
            move.quantity_done = 0  # Reset to 0, user must set quantity when validating

        # Add message to original picking
        picking.message_post(
            body=_('Receipt transfer %s has been automatically created for %s.') %
                 (new_picking.name, dest_warehouse.name),
            subtype_xmlid='mail.mt_note',
        )

        # Add message to new picking
        new_picking.message_post(
            body=_(
                'This receipt was automatically created from transfer %s. Please validate to receive the products.') % picking.name,
            subtype_xmlid='mail.mt_note',
        )

        return new_picking

    def _notify_main_warehouse_users(self, picking):
        """Send notification to Main warehouse users about new request"""
        # Get Main warehouse (source warehouse)
        main_warehouse = picking.location_id.warehouse_id

        if not main_warehouse:
            _logger.warning('No source warehouse found for picking %s', picking.name)
            return

        _logger.info('=== NOTIFICATION DEBUG ===')
        _logger.info('Picking: %s', picking.name)
        _logger.info('Source warehouse: %s', main_warehouse.name)
        _logger.info('Requesting warehouse: %s', picking.picking_type_id.warehouse_id.name)

        # Find users who have access to Main warehouse
        main_wh_users = self._get_warehouse_users(main_warehouse)

        if not main_wh_users:
            _logger.warning('No users found for Main warehouse notification')
            return

        _logger.info('Found %s users for notification', len(main_wh_users))

        # Create notification message
        requesting_warehouse = picking.picking_type_id.warehouse_id
        product_lines = []
        for move in picking.move_ids:
            product_lines.append(
                '<li>%s (%s %s)</li>' % (move.product_id.name, move.product_uom_qty, move.product_uom.name)
            )

        message = _(
            '<p><strong>New Stock Request</strong></p>'
            '<p>Warehouse <strong>%s</strong> has requested products from your warehouse:</p>'
            '<ul>%s</ul>'
            '<p>Transfer Reference: <strong>%s</strong></p>'
            '<p>Please review and validate this request.</p>'
        ) % (
                      requesting_warehouse.name,
                      ''.join(product_lines),
                      picking.name
                  )

        # Post message as internal note (no email)
        picking.message_post(
            body=message,
            subject=_('New Stock Request from %s') % requesting_warehouse.name,
            partner_ids=main_wh_users.mapped('partner_id').ids,
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

        _logger.info('Message posted to picking %s', picking.name)

        # Create activity for each Main warehouse user with sudo to bypass permissions
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not activity_type:
            activity_type = self.env['mail.activity.type'].search([('name', '=', 'To Do')], limit=1)

        if not activity_type:
            _logger.error('Could not find To Do activity type')
            return

        for user in main_wh_users:
            try:
                # Use sudo() to ensure activity is created regardless of current user permissions
                activity = self.env['mail.activity'].sudo().create({
                    'res_id': picking.id,
                    'res_model_id': self.env['ir.model']._get('stock.picking').id,
                    'activity_type_id': activity_type.id,
                    'summary': _('Review Stock Request from %s') % requesting_warehouse.name,
                    'note': message,
                    'user_id': user.id,
                    'date_deadline': fields.Date.today(),
                })
                _logger.info('Created activity %s for user: %s (ID: %s)', activity.id, user.name, user.id)
            except Exception as e:
                _logger.error('Error creating activity for user %s: %s', user.name, str(e))

    def _notify_warehouse_user(self, picking, receipt_transfer, notification_type):
        """Send notification to warehouse users"""
        dest_warehouse = picking.location_dest_id.warehouse_id

        if not dest_warehouse:
            _logger.warning('No destination warehouse found for picking %s', picking.name)
            return

        _logger.info('=== APPROVAL NOTIFICATION DEBUG ===')
        _logger.info('Picking: %s', picking.name)
        _logger.info('Destination warehouse: %s', dest_warehouse.name)
        _logger.info('Receipt transfer: %s', receipt_transfer.name if receipt_transfer else 'None')

        # Find users who have access to destination warehouse
        warehouse_users = self._get_warehouse_users(dest_warehouse)

        if not warehouse_users:
            _logger.warning('No users found for warehouse notification')
            return

        _logger.info('Found %s users for notification', len(warehouse_users))

        source_warehouse = picking.location_id.warehouse_id
        product_lines = []
        for move in picking.move_ids:
            actual_qty = move.quantity_done if move.quantity_done > 0 else move.product_uom_qty
            product_lines.append(
                '<li>%s (%s %s)</li>' % (move.product_id.name, actual_qty, move.product_uom.name)
            )

        if notification_type == 'approved':
            message = _(
                '<p><strong>Stock Request Approved</strong></p>'
                '<p>Your stock request has been approved by <strong>%s</strong>:</p>'
                '<ul>%s</ul>'
                '<p>Original Request: <strong>%s</strong></p>'
                '<p>Receipt Transfer: <strong>%s</strong></p>'
                '<p>Products are now in transit. Please validate the receipt to complete the transfer.</p>'
            ) % (
                          source_warehouse.name,
                          ''.join(product_lines),
                          picking.name,
                          receipt_transfer.name if receipt_transfer else 'N/A'
                      )
            subject = _('Stock Request Approved - %s') % picking.name
        else:
            message = _('Stock transfer notification')
            subject = _('Stock Transfer Update')

        # Post message to the RECEIPT transfer (not the original picking)
        if receipt_transfer:
            receipt_transfer.message_post(
                body=message,
                subject=subject,
                partner_ids=warehouse_users.mapped('partner_id').ids,
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
            _logger.info('Message posted to receipt transfer %s', receipt_transfer.name)

        # Create activity for warehouse users on the RECEIPT transfer
        if notification_type == 'approved' and receipt_transfer:
            activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
            if not activity_type:
                activity_type = self.env['mail.activity.type'].search([('name', '=', 'To Do')], limit=1)

            if not activity_type:
                _logger.error('Could not find To Do activity type')
                return

            for user in warehouse_users:
                try:
                    # Use sudo() to ensure activity is created
                    activity = self.env['mail.activity'].sudo().create({
                        'res_id': receipt_transfer.id,
                        'res_model_id': self.env['ir.model']._get('stock.picking').id,
                        'activity_type_id': activity_type.id,
                        'summary': _('Validate Receipt from %s') % source_warehouse.name,
                        'note': message,
                        'user_id': user.id,
                        'date_deadline': fields.Date.today(),
                    })
                    _logger.info('Created receipt activity %s for user: %s (ID: %s)', activity.id, user.name, user.id)
                except Exception as e:
                    _logger.error('Error creating activity for user %s: %s', user.name, str(e))

    def _get_warehouse_users(self, warehouse):
        """Get users who have access to this warehouse"""
        try:
            _logger.info('=== GET WAREHOUSE USERS DEBUG ===')
            _logger.info('Looking for users for warehouse: %s', warehouse.name)

            # Warehouse name to group name mapping - use flexible matching
            warehouse_name = warehouse.name.strip()

            # Determine group name based on warehouse name
            if 'Main Office' in warehouse_name or 'Main' in warehouse_name:
                group_name = 'Main WH'
            elif 'Dammam' in warehouse_name:
                group_name = 'Dammam WH'
            elif 'Baladiya' in warehouse_name:
                group_name = 'Baladiya WH'
            else:
                group_name = None
                _logger.warning('Could not determine group name for warehouse: %s', warehouse_name)

            if group_name:
                _logger.info('Searching for group: %s', group_name)
                warehouse_groups = self.env['res.groups'].search([
                    ('name', '=', group_name)
                ])

                _logger.info('Found %s groups matching "%s"', len(warehouse_groups), group_name)

                if warehouse_groups:
                    # Get users who are in these groups
                    # Use correct syntax for many2many field search
                    warehouse_users = self.env['res.users'].search([
                        ('groups_id', 'in', warehouse_groups.ids),
                        ('active', '=', True),
                        ('share', '=', False)  # Exclude portal users
                    ])

                    _logger.info('Search query: groups_id in %s', warehouse_groups.ids)

                    _logger.info('Found %s users in group', len(warehouse_users))

                    if warehouse_users:
                        for user in warehouse_users:
                            _logger.info('  - User: %s (ID: %s, Login: %s)', user.name, user.id, user.login)
                        return warehouse_users
                    else:
                        _logger.warning('No users found in group: %s', group_name)
                else:
                    _logger.warning('No groups found with name: %s', group_name)

            # Fallback: Get all inventory users
            _logger.info('Using fallback: getting all inventory users')
            inventory_group = self.env.ref('stock.group_stock_user', raise_if_not_found=False)
            if inventory_group:
                all_users = self.env['res.users'].sudo().search([
                    ('groups_id', 'in', inventory_group.id),
                    ('active', '=', True),
                    ('share', '=', False)
                ])
                _logger.info('Found %s inventory users', len(all_users))
                for user in all_users:
                    _logger.info('  - User: %s (ID: %s)', user.name, user.id)
                return all_users

            # Last resort: return admin
            _logger.warning('Returning admin user as last resort')
            return self.env.ref('base.user_admin', raise_if_not_found=False)

        except Exception as e:
            _logger.error('Error getting warehouse users: %s', str(e))
            return self.env['res.users'].browse(2)

    @api.model
    def _get_warehouse_for_user(self, user):
        """Get the warehouse assigned to a user"""
        # Check if user has a default warehouse set
        if hasattr(user, 'property_warehouse_id') and user.property_warehouse_id:
            return user.property_warehouse_id

        # Try to find from groups
        for group in user.groups_id:
            if 'Main WH' in group.name or 'Main Office' in group.name:
                return self.env['stock.warehouse'].search([
                    ('name', 'ilike', 'Main Office')
                ], limit=1)
            elif 'Dammam' in group.name:
                return self.env['stock.warehouse'].search([
                    ('name', 'ilike', 'Dammam')
                ], limit=1)
            elif 'Baladiya' in group.name:
                return self.env['stock.warehouse'].search([
                    ('name', 'ilike', 'Baladiya')
                ], limit=1)

        return False





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
#                     # Auto-create the second transfer (receipt)
#                     new_transfer = self._create_receipt_transfer(picking)
#
#                     # Send notification to requesting warehouse
#                     if new_transfer:
#                         self._notify_warehouse_user(picking, new_transfer, 'approved')
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
#             # Log warning but don't block
#             picking.message_post(
#                 body=_('Warning: Could not find receiving operation type for warehouse %s. '
#                        'Please create the receipt manually.') % dest_warehouse.name,
#                 subtype_xmlid='mail.mt_note',
#             )
#             return False
#
#         # Create the receiving transfer in DRAFT state
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
#         # Copy move lines with correct quantities
#         for move in picking.move_ids:
#             # Use quantity_done (actual validated quantity) not product_uom_qty
#             actual_qty = move.quantity_done if move.quantity_done > 0 else move.product_uom_qty
#
#             move_vals = {
#                 'name': move.name,
#                 'product_id': move.product_id.id,
#                 'product_uom_qty': actual_qty,
#                 'product_uom': move.product_uom.id,
#                 'picking_id': new_picking.id,
#                 'location_id': transit_loc.id,
#                 'location_dest_id': receiving_type.default_location_dest_id.id,
#                 'description_picking': move.description_picking,
#             }
#             self.env['stock.move'].create(move_vals)
#
#         # IMPORTANT: Only confirm, do NOT validate automatically
#         # This keeps it in "Ready" state waiting for warehouse user to validate
#         new_picking.action_confirm()
#
#         # Set quantities to available so user can validate immediately
#         for move in new_picking.move_ids:
#             move.quantity_done = 0  # Reset to 0, user must set quantity when validating
#
#         # Add message to original picking
#         picking.message_post(
#             body=_('Receipt transfer %s has been automatically created for %s.') %
#                  (new_picking.name, dest_warehouse.name),
#             subtype_xmlid='mail.mt_note',
#         )
#
#         # Add message to new picking
#         new_picking.message_post(
#             body=_(
#                 'This receipt was automatically created from transfer %s. Please validate to receive the products.') % picking.name,
#             subtype_xmlid='mail.mt_note',
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
#         product_lines = []
#         for move in picking.move_ids:
#             product_lines.append(
#                 '<li>%s (%s %s)</li>' % (move.product_id.name, move.product_uom_qty, move.product_uom.name)
#             )
#
#         message = _(
#             '<p><strong>New Stock Request</strong></p>'
#             '<p>Warehouse <strong>%s</strong> has requested products from your warehouse:</p>'
#             '<ul>%s</ul>'
#             '<p>Transfer Reference: <strong>%s</strong></p>'
#             '<p>Please review and validate this request.</p>'
#         ) % (
#                       requesting_warehouse.name,
#                       ''.join(product_lines),
#                       picking.name
#                   )
#
#         # Post message as internal note (no email)
#         picking.message_post(
#             body=message,
#             subject=_('New Stock Request from %s') % requesting_warehouse.name,
#             partner_ids=main_wh_users.mapped('partner_id').ids,
#             message_type='notification',
#             subtype_xmlid='mail.mt_note',
#         )
#
#         # Create activity for each Main warehouse user with sudo to bypass permissions
#         activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
#         if not activity_type:
#             activity_type = self.env['mail.activity.type'].search([('name', '=', 'To Do')], limit=1)
#
#         if not activity_type:
#             _logger.error('Could not find To Do activity type')
#             return
#
#         for user in main_wh_users:
#             try:
#                 # Use sudo() to ensure activity is created regardless of current user permissions
#                 self.env['mail.activity'].sudo().create({
#                     'res_id': picking.id,
#                     'res_model_id': self.env['ir.model']._get('stock.picking').id,
#                     'activity_type_id': activity_type.id,
#                     'summary': _('Review Stock Request from %s') % requesting_warehouse.name,
#                     'note': message,
#                     'user_id': user.id,
#                     'date_deadline': fields.Date.today(),
#                 })
#                 _logger.info('Created activity for user: %s (ID: %s)', user.name, user.id)
#             except Exception as e:
#                 _logger.error('Error creating activity for user %s: %s', user.name, str(e))
#
#     def _notify_warehouse_user(self, picking, receipt_transfer, notification_type):
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
#         product_lines = []
#         for move in picking.move_ids:
#             actual_qty = move.quantity_done if move.quantity_done > 0 else move.product_uom_qty
#             product_lines.append(
#                 '<li>%s (%s %s)</li>' % (move.product_id.name, actual_qty, move.product_uom.name)
#             )
#
#         if notification_type == 'approved':
#             message = _(
#                 '<p><strong>Stock Request Approved</strong></p>'
#                 '<p>Your stock request has been approved by <strong>%s</strong>:</p>'
#                 '<ul>%s</ul>'
#                 '<p>Original Request: <strong>%s</strong></p>'
#                 '<p>Receipt Transfer: <strong>%s</strong></p>'
#                 '<p>Products are now in transit. Please validate the receipt to complete the transfer.</p>'
#             ) % (
#                           source_warehouse.name,
#                           ''.join(product_lines),
#                           picking.name,
#                           receipt_transfer.name if receipt_transfer else 'N/A'
#                       )
#             subject = _('Stock Request Approved - %s') % picking.name
#         else:
#             message = _('Stock transfer notification')
#             subject = _('Stock Transfer Update')
#
#         # Post message to the RECEIPT transfer (not the original picking)
#         if receipt_transfer:
#             receipt_transfer.message_post(
#                 body=message,
#                 subject=subject,
#                 partner_ids=warehouse_users.mapped('partner_id').ids,
#                 message_type='notification',
#                 subtype_xmlid='mail.mt_note',
#             )
#
#         # Create activity for warehouse users on the RECEIPT transfer
#         if notification_type == 'approved' and receipt_transfer:
#             activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
#             if not activity_type:
#                 activity_type = self.env['mail.activity.type'].search([('name', '=', 'To Do')], limit=1)
#
#             if not activity_type:
#                 _logger.error('Could not find To Do activity type')
#                 return
#
#             for user in warehouse_users:
#                 try:
#                     # Use sudo() to ensure activity is created
#                     self.env['mail.activity'].sudo().create({
#                         'res_id': receipt_transfer.id,
#                         'res_model_id': self.env['ir.model']._get('stock.picking').id,
#                         'activity_type_id': activity_type.id,
#                         'summary': _('Validate Receipt from %s') % source_warehouse.name,
#                         'note': message,
#                         'user_id': user.id,
#                         'date_deadline': fields.Date.today(),
#                     })
#                     _logger.info('Created receipt activity for user: %s (ID: %s)', user.name, user.id)
#                 except Exception as e:
#                     _logger.error('Error creating activity for user %s: %s', user.name, str(e))
#
#     def _get_warehouse_users(self, warehouse):
#         """Get users who have access to this warehouse"""
#         try:
#             # Warehouse name to group name mapping - use exact warehouse names
#             warehouse_group_mapping = {
#                 'SSAOCO-Main Office': 'Main WH',
#                 'SSAOCO - Dammam': 'Dammam WH',
#                 'SSAOCO - Baladiya': 'Baladiya WH',
#             }
#
#             # Get the exact group name for this warehouse
#             group_name = warehouse_group_mapping.get(warehouse.name)
#
#             if group_name:
#                 _logger.info('Looking for users in group: %s for warehouse: %s', group_name, warehouse.name)
#                 warehouse_groups = self.env['res.groups'].search([
#                     ('name', '=', group_name)
#                 ])
#
#                 if warehouse_groups:
#                     # Get users who are in these groups
#                     warehouse_users = self.env['res.users'].search([
#                         ('groups_id', 'in', warehouse_groups.ids),
#                         ('active', '=', True),
#                         ('share', '=', False)  # Exclude portal users
#                     ])
#
#                     if warehouse_users:
#                         _logger.info('Found %s users for warehouse %s: %s',
#                                      len(warehouse_users), warehouse.name,
#                                      ', '.join(warehouse_users.mapped('name')))
#                         return warehouse_users
#                     else:
#                         _logger.warning('No users found in group: %s', group_name)
#             else:
#                 _logger.warning('No group mapping found for warehouse: %s', warehouse.name)
#
#             # Fallback: Get all inventory users
#             _logger.info('Using fallback: getting all inventory users')
#             inventory_group = self.env.ref('stock.group_stock_user', raise_if_not_found=False)
#             if inventory_group:
#                 all_users = self.env['res.users'].search([
#                     ('groups_id', 'in', inventory_group.id),
#                     ('active', '=', True),
#                     ('share', '=', False)
#                 ])
#                 _logger.info('Found %s inventory users', len(all_users))
#                 return all_users
#
#             # Last resort: return admin
#             _logger.warning('Returning admin user as last resort')
#             return self.env.ref('base.user_admin', raise_if_not_found=False)
#
#         except Exception as e:
#             _logger.error('Error getting warehouse users: %s', str(e))
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
