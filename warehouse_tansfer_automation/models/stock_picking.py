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

        # Process automation AFTER validation with sudo to bypass record rules
        for picking in pickings_to_automate:
            # Double-check the picking is actually done and receipt not created
            if picking.state == 'done' and not picking.auto_receipt_created:
                try:
                    # Mark as processed FIRST to prevent duplicates
                    picking.write({'auto_receipt_created': True})
                    self.env.cr.commit()  # Commit immediately to prevent race conditions

                    # Use sudo to bypass record rules when creating receipt
                    new_picking = self.sudo()._create_receipt_transfer(picking)

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
        # Use sudo() context to bypass record rules
        StockPicking = self.env['stock.picking'].sudo()
        StockMove = self.env['stock.move'].sudo()
        StockMoveLine = self.env['stock.move.line'].sudo()

        # Check if receipt already exists for this picking
        existing_receipt = StockPicking.search([
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
        receiving_type = self.env['stock.picking.type'].sudo().search([
            ('warehouse_id', '=', dest_warehouse.id),
            ('code', '=', 'internal'),
            ('default_location_src_id', '=', transit_loc.id)
        ], limit=1)

        if not receiving_type:
            # Try alternative: find any internal transfer in destination warehouse
            receiving_type = self.env['stock.picking.type'].sudo().search([
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
            dest_location = self.env['stock.location'].sudo().search([
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

        new_picking = StockPicking.create(new_picking_vals)
        _logger.info('Created new picking %s in state: %s', new_picking.name, new_picking.state)

        # Copy move lines with proper product quantities
        for move in picking.move_ids:
            # Get the actual done quantity from the validated picking
            done_qty = 0
            if move.move_line_ids:
                done_qty = sum(move.move_line_ids.mapped('quantity'))

            if done_qty <= 0:
                done_qty = move.product_uom_qty

            _logger.info('Creating move for product %s with quantity: %s', move.product_id.name, done_qty)

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
                'state': 'draft',
            }
            created_move = StockMove.create(move_vals)

        # Confirm the picking to create moves
        new_picking.action_confirm()
        _logger.info('After confirm, picking %s state: %s', new_picking.name, new_picking.state)

        # Now manually create move lines and reserve quantities
        for move in new_picking.move_ids:
            _logger.info('Processing move %s, state: %s', move.product_id.name, move.state)

            # Create move line with reserved quantity
            move_line_vals = {
                'move_id': move.id,
                'product_id': move.product_id.id,
                'product_uom_id': move.product_uom.id,
                'location_id': transit_loc.id,
                'location_dest_id': dest_location.id,
                'quantity': move.product_uom_qty,
                'reserved_uom_qty': move.product_uom_qty,  # Reserve the quantity
                'picking_id': new_picking.id,
                'company_id': move.company_id.id,
            }

            move_line = StockMoveLine.create(move_line_vals)
            _logger.info('Created move line for %s with quantity: %s', move.product_id.name, move.product_uom_qty)

            # Update move state to assigned
            move.sudo().write({
                'state': 'assigned',
                'reserved_availability': move.product_uom_qty
            })

        # Force the picking to assigned (Ready) state
        new_picking.sudo().write({'state': 'assigned'})

        _logger.info('Final picking %s state: %s', new_picking.name, new_picking.state)

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

        _logger.info('Successfully created receipt transfer %s in READY state for warehouse %s',
                     new_picking.name, dest_warehouse.name)

        return new_picking

    def _notify_main_warehouse_users(self, picking):
        """Send notification to Main warehouse users about new request"""
        main_warehouse = picking.location_id.warehouse_id

        if not main_warehouse:
            _logger.warning('No main warehouse found for picking: %s', picking.name)
            return

        main_wh_users = self._get_warehouse_users(main_warehouse)

        if not main_wh_users:
            _logger.error(
                '❌ NO USERS FOUND for Main warehouse: %s. Please assign users to the "Main Warehouse User" group!',
                main_warehouse.name)
            # Post a message to the picking so the requester knows
            picking.message_post(
                body=_(
                    '⚠️ Warning: Could not send notification to Main warehouse users. No users are assigned to the Main Warehouse User group.'),
                message_type='comment',
            )
            return

        requesting_warehouse = picking.picking_type_id.warehouse_id
        product_lines = []
        for move in picking.move_ids:
            product_lines.append('%s (%s %s)' % (move.product_id.name, move.product_uom_qty, move.product_uom.name))

        message = _(
            '<p><strong>🔔 New Stock Request</strong></p>'
            '<p>Warehouse <strong>%s</strong> has requested products from your warehouse:</p>'
            '<ul>%s</ul>'
            '<p>Transfer Reference: <strong>%s</strong></p>'
            '<p>Please review and validate this request.</p>'
        ) % (
                      requesting_warehouse.name,
                      ''.join(['<li>%s</li>' % line for line in product_lines]),
                      picking.name
                  )

        _logger.info('✅ Sending notification to %d Main warehouse users: %s',
                     len(main_wh_users), ', '.join(main_wh_users.mapped('name')))

        # Method 1: Post message in chatter with notification
        picking.message_post(
            body=message,
            subject=_('New Stock Request from %s') % requesting_warehouse.name,
            partner_ids=main_wh_users.mapped('partner_id').ids,
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

        # Method 2: Create activity for each main warehouse user
        ActivityModel = self.env['mail.activity'].sudo()
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)

        for user in main_wh_users:
            try:
                ActivityModel.create({
                    'res_id': picking.id,
                    'res_model_id': self.env['ir.model']._get('stock.picking').id,
                    'activity_type_id': activity_type.id if activity_type else 1,
                    'summary': _('Stock Request: %s') % requesting_warehouse.name,
                    'note': message,
                    'user_id': user.id,
                    'date_deadline': fields.Date.today(),
                })
                _logger.info('✅ Created activity for user: %s', user.name)
            except Exception as e:
                _logger.warning('Could not create activity for user %s: %s', user.name, str(e))

        # Method 3: Send internal message (inbox notification)
        self.env['mail.message'].sudo().create({
            'subject': _('New Stock Request from %s') % requesting_warehouse.name,
            'body': message,
            'model': 'stock.picking',
            'res_id': picking.id,
            'message_type': 'notification',
            'partner_ids': [(4, pid) for pid in main_wh_users.mapped('partner_id').ids],
            'needaction_partner_ids': [(4, pid) for pid in main_wh_users.mapped('partner_id').ids],
        })

        _logger.info('✅ Notification sent successfully to Main warehouse users for picking: %s', picking.name)

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
            _logger.error('❌ NO USERS FOUND for warehouse: %s. Please assign users to the "%s Warehouse User" group!',
                          dest_warehouse.name, dest_warehouse.name)
            # Post a message to the picking
            picking.message_post(
                body=_(
                    '⚠️ Warning: Could not send notification to %s users. No users are assigned to the warehouse user group.') % dest_warehouse.name,
                message_type='comment',
            )
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
                '<p><strong>✅ Stock Request Approved</strong></p>'
                '<p>Your stock request has been approved by <strong>%s</strong>:</p>'
                '<ul>%s</ul>'
                '<p>Transfer Reference: <strong>%s</strong></p>'
                '<p><strong>⚠️ Action Required:</strong> Please validate the receipt transfer <a href="/web#id=%s&model=stock.picking&view_type=form">%s</a> to complete the stock transfer and update your inventory.</p>'
            ) % (
                          source_warehouse_name,
                          ''.join(['<li>%s</li>' % line for line in product_lines]),
                          picking.name,
                          picking.id,
                          picking.name
                      )
            subject = _('✅ Stock Request Approved - %s') % picking.name
        else:
            message = _('Stock transfer notification')
            subject = _('Stock Transfer Update')

        _logger.info('✅ Sending notification to %d %s warehouse users: %s',
                     len(warehouse_users), dest_warehouse.name, ', '.join(warehouse_users.mapped('name')))

        # Method 1: Post message in chatter with notification
        picking.message_post(
            body=message,
            subject=subject,
            partner_ids=warehouse_users.mapped('partner_id').ids,
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

        # Method 2: Create activity for each warehouse user
        ActivityModel = self.env['mail.activity'].sudo()
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)

        for user in warehouse_users:
            try:
                ActivityModel.create({
                    'res_id': picking.id,
                    'res_model_id': self.env['ir.model']._get('stock.picking').id,
                    'activity_type_id': activity_type.id if activity_type else 1,
                    'summary': _('Action Required: Validate Receipt %s') % picking.name,
                    'note': message,
                    'user_id': user.id,
                    'date_deadline': fields.Date.today(),
                })
                _logger.info('✅ Created activity for user: %s', user.name)
            except Exception as e:
                _logger.warning('Could not create activity for user %s: %s', user.name, str(e))

        # Method 3: Send internal message (inbox notification)
        self.env['mail.message'].sudo().create({
            'subject': subject,
            'body': message,
            'model': 'stock.picking',
            'res_id': picking.id,
            'message_type': 'notification',
            'partner_ids': [(4, pid) for pid in warehouse_users.mapped('partner_id').ids],
            'needaction_partner_ids': [(4, pid) for pid in warehouse_users.mapped('partner_id').ids],
        })

        _logger.info('✅ Notification sent successfully to %s warehouse users for picking: %s', dest_warehouse.name,
                     picking.name)

    def _get_warehouse_users(self, warehouse):
        """Get users who have access to this warehouse"""
        try:
            _logger.info('🔍 Looking for users for warehouse: "%s"', warehouse.name)

            # Map warehouse names to group XML IDs - try multiple variations
            warehouse_group_mapping = {
                'SSAOCO-Main Office': 'warehouse_tansfer_automation.group_main_warehouse',
                'Main Office': 'warehouse_tansfer_automation.group_main_warehouse',
                'SSAOCO - Dammam': 'warehouse_tansfer_automation.group_dammam_warehouse',
                'Dammam': 'warehouse_tansfer_automation.group_dammam_warehouse',
                'SSAOCO - Baladiya': 'warehouse_tansfer_automation.group_baladiya_warehouse',
                'Baladiya': 'warehouse_tansfer_automation.group_baladiya_warehouse',
            }

            # Find the matching group XML ID - try exact match first
            group_xmlid = warehouse_group_mapping.get(warehouse.name)

            # If no exact match, try partial matching
            if not group_xmlid:
                for key, xmlid in warehouse_group_mapping.items():
                    if key.lower() in warehouse.name.lower() or warehouse.name.lower() in key.lower():
                        group_xmlid = xmlid
                        _logger.info('  ✓ Matched warehouse "%s" with key "%s"', warehouse.name, key)
                        break

            if group_xmlid:
                try:
                    _logger.info('  🔍 Looking for group: %s', group_xmlid)
                    warehouse_group = self.env.ref(group_xmlid, raise_if_not_found=False)
                    if warehouse_group:
                        _logger.info('  ✓ Group found: %s (ID: %s)', warehouse_group.name, warehouse_group.id)

                        # Get users who are in this specific warehouse group
                        warehouse_users = self.env['res.users'].search([
                            ('groups_id', 'in', warehouse_group.id),
                            ('active', '=', True),
                            ('share', '=', False)  # Exclude portal users
                        ])

                        if warehouse_users:
                            _logger.info('  ✅ Found %d users for warehouse %s: %s',
                                         len(warehouse_users), warehouse.name,
                                         ', '.join(warehouse_users.mapped('name')))
                            return warehouse_users
                        else:
                            _logger.warning('  ❌ Group exists but NO USERS in group %s for warehouse %s',
                                            warehouse_group.name, warehouse.name)
                    else:
                        _logger.error('  ❌ Group XML ID %s not found in system', group_xmlid)
                except Exception as e:
                    _logger.error('  ❌ Error getting group %s: %s', group_xmlid, str(e))
            else:
                _logger.error('  ❌ Could not match warehouse name "%s" to any group', warehouse.name)

            # Log all available warehouse groups for debugging
            _logger.info('  📋 Available warehouse groups in system:')
            all_wh_groups = self.env['res.groups'].search([('name', 'like', 'Warehouse User')])
            for grp in all_wh_groups:
                users_count = len(self.env['res.users'].search([
                    ('groups_id', 'in', grp.id),
                    ('active', '=', True),
                    ('share', '=', False)
                ]))
                _logger.info('    - %s: %d users', grp.name, users_count)

            # Return empty recordset instead of admin
            _logger.error('  ❌ NO USERS FOUND for warehouse: %s', warehouse.name)
            return self.env['res.users'].browse([])

        except Exception as e:
            _logger.error('❌ Error in _get_warehouse_users: %s', str(e))
            import traceback
            _logger.error(traceback.format_exc())
            return self.env['res.users'].browse([])









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
#     auto_receipt_created = fields.Boolean(
#         string='Auto Receipt Created',
#         default=False,
#         copy=False,
#         help='Technical field to track if automatic receipt was already created'
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
#         # Store pickings that need automation BEFORE validation
#         pickings_to_automate = []
#         for picking in self:
#             # Check if this transfer goes to a transit location and hasn't been processed yet
#             if (picking.location_dest_id.usage == 'transit' and
#                     not picking.auto_receipt_created and
#                     picking.state in ['assigned', 'confirmed']):
#                 pickings_to_automate.append(picking)
#
#         # Call parent validation
#         res = super(StockPicking, self).button_validate()
#
#         # Process automation AFTER validation with sudo to bypass record rules
#         for picking in pickings_to_automate:
#             # Double-check the picking is actually done and receipt not created
#             if picking.state == 'done' and not picking.auto_receipt_created:
#                 try:
#                     # Mark as processed FIRST to prevent duplicates
#                     picking.write({'auto_receipt_created': True})
#                     self.env.cr.commit()  # Commit immediately to prevent race conditions
#
#                     # Use sudo to bypass record rules when creating receipt
#                     new_picking = self.sudo()._create_receipt_transfer(picking)
#
#                     # Send notification to requesting warehouse AFTER creating receipt
#                     if new_picking:
#                         self._notify_warehouse_user(new_picking, 'approved')
#
#                 except Exception as e:
#                     _logger.error('Error in warehouse automation for %s: %s', picking.name, str(e))
#                     # Rollback the flag if creation failed
#                     picking.write({'auto_receipt_created': False})
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
#
#         return res
#
#     def _create_receipt_transfer(self, picking):
#         """Auto-create the second transfer from transit to warehouse stock"""
#         # Use sudo() context to bypass record rules
#         StockPicking = self.env['stock.picking'].sudo()
#         StockMove = self.env['stock.move'].sudo()
#         StockMoveLine = self.env['stock.move.line'].sudo()
#
#         # Check if receipt already exists for this picking
#         existing_receipt = StockPicking.search([
#             ('origin', '=', picking.name),
#             ('location_id.usage', '=', 'transit')
#         ], limit=1)
#
#         if existing_receipt:
#             _logger.warning('Receipt already exists for %s: %s', picking.name, existing_receipt.name)
#             return existing_receipt
#
#         transit_loc = picking.location_dest_id
#         dest_warehouse = transit_loc.warehouse_id
#
#         if not dest_warehouse:
#             _logger.warning('No destination warehouse found for transit location: %s', transit_loc.name)
#             return False
#
#         # Find the receiving operation type
#         receiving_type = self.env['stock.picking.type'].sudo().search([
#             ('warehouse_id', '=', dest_warehouse.id),
#             ('code', '=', 'internal'),
#             ('default_location_src_id', '=', transit_loc.id)
#         ], limit=1)
#
#         if not receiving_type:
#             # Try alternative: find any internal transfer in destination warehouse
#             receiving_type = self.env['stock.picking.type'].sudo().search([
#                 ('warehouse_id', '=', dest_warehouse.id),
#                 ('code', '=', 'internal')
#             ], limit=1)
#
#             if not receiving_type:
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
#             dest_location = self.env['stock.location'].sudo().search([
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
#         new_picking = StockPicking.create(new_picking_vals)
#         _logger.info('Created new picking %s in state: %s', new_picking.name, new_picking.state)
#
#         # Copy move lines with proper product quantities
#         for move in picking.move_ids:
#             # Get the actual done quantity from the validated picking
#             done_qty = 0
#             if move.move_line_ids:
#                 done_qty = sum(move.move_line_ids.mapped('quantity'))
#
#             if done_qty <= 0:
#                 done_qty = move.product_uom_qty
#
#             _logger.info('Creating move for product %s with quantity: %s', move.product_id.name, done_qty)
#
#             move_vals = {
#                 'name': move.name,
#                 'product_id': move.product_id.id,
#                 'product_uom_qty': done_qty,
#                 'product_uom': move.product_uom.id,
#                 'picking_id': new_picking.id,
#                 'location_id': transit_loc.id,
#                 'location_dest_id': dest_location.id,
#                 'description_picking': move.description_picking,
#                 'company_id': move.company_id.id,
#                 'date': fields.Datetime.now(),
#                 'state': 'draft',
#             }
#             created_move = StockMove.create(move_vals)
#
#         # Confirm the picking to create moves
#         new_picking.action_confirm()
#         _logger.info('After confirm, picking %s state: %s', new_picking.name, new_picking.state)
#
#         # Now manually create move lines and reserve quantities
#         for move in new_picking.move_ids:
#             _logger.info('Processing move %s, state: %s', move.product_id.name, move.state)
#
#             # Create move line with reserved quantity
#             move_line_vals = {
#                 'move_id': move.id,
#                 'product_id': move.product_id.id,
#                 'product_uom_id': move.product_uom.id,
#                 'location_id': transit_loc.id,
#                 'location_dest_id': dest_location.id,
#                 'quantity': move.product_uom_qty,
#                 'reserved_uom_qty': move.product_uom_qty,  # Reserve the quantity
#                 'picking_id': new_picking.id,
#                 'company_id': move.company_id.id,
#             }
#
#             move_line = StockMoveLine.create(move_line_vals)
#             _logger.info('Created move line for %s with quantity: %s', move.product_id.name, move.product_uom_qty)
#
#             # Update move state to assigned
#             move.sudo().write({
#                 'state': 'assigned',
#                 'reserved_availability': move.product_uom_qty
#             })
#
#         # Force the picking to assigned (Ready) state
#         new_picking.sudo().write({'state': 'assigned'})
#
#         _logger.info('Final picking %s state: %s', new_picking.name, new_picking.state)
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
#         _logger.info('Successfully created receipt transfer %s in READY state for warehouse %s',
#                      new_picking.name, dest_warehouse.name)
#
#         return new_picking
#
#     def _notify_main_warehouse_users(self, picking):
#         """Send notification to Main warehouse users about new request"""
#         main_warehouse = picking.location_id.warehouse_id
#
#         if not main_warehouse:
#             _logger.warning('No main warehouse found for picking: %s', picking.name)
#             return
#
#         main_wh_users = self._get_warehouse_users(main_warehouse)
#
#         if not main_wh_users:
#             _logger.warning('No users found for Main warehouse notification')
#             return
#
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
#         dest_warehouse = picking.picking_type_id.warehouse_id
#
#         if not dest_warehouse:
#             dest_warehouse = picking.location_dest_id.warehouse_id
#
#         if not dest_warehouse:
#             _logger.warning('No destination warehouse found for notification: %s', picking.name)
#             return
#
#         warehouse_users = self._get_warehouse_users(dest_warehouse)
#
#         if not warehouse_users:
#             _logger.warning('No users found for warehouse notification: %s', dest_warehouse.name)
#             return
#
#         source_warehouse_name = 'Main Office'
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
#             warehouse_group_mapping = {
#                 'Main Office': ['Main WH', 'Main Office'],
#                 'Dammam': ['Dammam WH', 'Dammam'],
#                 'Baladiya': ['Baladiya WH', 'Baladiya'],
#             }
#
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
#                     warehouse_users = self.env['res.users'].search([
#                         ('groups_id', 'in', warehouse_groups.ids),
#                         ('active', '=', True),
#                         ('share', '=', False)
#                     ])
#                     if warehouse_users:
#                         _logger.info('Found %d users for warehouse %s', len(warehouse_users), warehouse.name)
#                         return warehouse_users
#
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
#             admin = self.env.ref('base.user_admin', raise_if_not_found=False)
#             if admin:
#                 return admin
#
#             return self.env['res.users'].browse([])
#
#         except Exception as e:
#             _logger.error('Error getting warehouse users: %s', str(e))
#             admin = self.env.ref('base.user_admin', raise_if_not_found=False)
#             return admin if admin else self.env['res.users'].browse([])
#
