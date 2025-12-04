# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
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
        """Identify if this is an inter-warehouse request."""
        for picking in self:
            try:
                if (picking.location_id.warehouse_id and
                        picking.location_dest_id.usage == 'transit' and
                        picking.location_id.warehouse_id != picking.picking_type_id.warehouse_id):
                    picking.is_inter_warehouse_request = True
                else:
                    picking.is_inter_warehouse_request = False
            except Exception:
                picking.is_inter_warehouse_request = False

    @api.model_create_multi
    def create(self, vals_list):
        """
        When a picking is created (branch requests), subscribe the target Main WH users
        so they will see the transfer and get notifications/activities.
        """
        pickings = super(StockPicking, self).create(vals_list)

        for picking in pickings:
            try:
                # If it's a branch -> transit (inter-warehouse) request, subscribe main warehouse users
                if picking.location_dest_id and picking.location_dest_id.usage == 'transit':
                    # Determine the source/main warehouse (the warehouse that should be notified)
                    main_wh = picking.location_id.warehouse_id
                    if main_wh:
                        users = self._get_warehouse_users(main_wh)
                        if users:
                            partners = users.mapped('partner_id').ids
                            if partners:
                                picking.sudo().message_subscribe(partner_ids=partners)
                                _logger.info('Subscribe partners %s to picking %s', partners, picking.name)
                                # create an activity for each user so it appears in their inbox
                                activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
                                if not activity_type:
                                    activity_type = self.env['mail.activity.type'].sudo().search([('name', '=', 'To Do')], limit=1)
                                if activity_type:
                                    for user in users:
                                        try:
                                            self.env['mail.activity'].sudo().create({
                                                'res_id': picking.id,
                                                'res_model_id': self.env['ir.model']._get('stock.picking').id,
                                                'activity_type_id': activity_type.id,
                                                'summary': _('📦 Review Stock Request'),
                                                'note': _('New stock request created: %s') % (picking.name,),
                                                'user_id': user.id,
                                                'date_deadline': fields.Date.today(),
                                            })
                                        except Exception as e:
                                            _logger.warning('Failed to create activity for user %s: %s', user.name, e)
            except Exception as e:
                _logger.error('Error in create override for picking %s: %s', picking.name if picking else 'n/a', e)

        return pickings

    def action_confirm(self):
        """Override confirm to send notification to Main warehouse users"""
        res = super(StockPicking, self).action_confirm()

        for picking in self:
            try:
                # If this is a request from branch to main warehouse
                if picking.is_inter_warehouse_request and picking.location_dest_id.usage == 'transit':
                    self._notify_main_warehouse_users(picking)
            except Exception as e:
                _logger.error('Error sending notification to main warehouse for %s: %s', picking.name, e)

        return res

    def button_validate(self):
        """Override validate to add notifications and auto-create receipts"""
        res = super(StockPicking, self).button_validate()

        for picking in self:
            try:
                # Only act when transfer goes to transit and is completed (done)
                if picking.location_dest_id.usage == 'transit' and picking.state == 'done':
                    new_transfer = self._create_receipt_transfer(picking)
                    if new_transfer:
                        # notify destination warehouse users that receipt is ready (approved)
                        try:
                            self._notify_warehouse_user(picking, new_transfer, 'approved')
                        except Exception as e:
                            _logger.error('Error notifying destination warehouse for %s: %s', picking.name, e)
            except Exception as e:
                _logger.error('Error in button_validate hook for %s: %s', picking.name if picking else 'n/a', e)

        return res

    def _create_receipt_transfer(self, picking):
        """Auto-create the second transfer from transit to warehouse stock"""
        transit_loc = picking.location_dest_id
        dest_warehouse = transit_loc.warehouse_id

        if not dest_warehouse:
            _logger.warning('No destination warehouse for picking %s', picking.name)
            return False

        # Find the receiving operation type (internal / receipt for that warehouse with transit as default src)
        receiving_type = self.env['stock.picking.type'].search([
            ('warehouse_id', '=', dest_warehouse.id),
            ('code', '=', 'internal'),
            ('default_location_src_id', '=', transit_loc.id)
        ], limit=1)

        if not receiving_type:
            # fallback: look for any internal type for the warehouse
            receiving_type = self.env['stock.picking.type'].search([
                ('warehouse_id', '=', dest_warehouse.id),
                ('code', '=', 'internal'),
            ], limit=1)

        if not receiving_type:
            picking.sudo().message_post(
                body=_('Warning: Could not find receiving operation type for warehouse %s. Please create the receipt manually.') % dest_warehouse.name,
                subtype_xmlid='mail.mt_note',
            )
            return False

        new_picking_vals = {
            'picking_type_id': receiving_type.id,
            'location_id': transit_loc.id,
            'location_dest_id': receiving_type.default_location_dest_id.id if receiving_type.default_location_dest_id else dest_warehouse.lot_stock_id.id,
            'origin': picking.name,
            'partner_id': picking.partner_id.id if picking.partner_id else False,
        }

        new_picking = self.env['stock.picking'].create(new_picking_vals)

        # Copy moves
        for move in picking.move_ids:
            actual_qty = move.quantity_done if move.quantity_done > 0 else move.product_uom_qty
            move_vals = {
                'name': move.name,
                'product_id': move.product_id.id,
                'product_uom_qty': actual_qty,
                'product_uom': move.product_uom.id,
                'picking_id': new_picking.id,
                'location_id': transit_loc.id,
                'location_dest_id': receiving_type.default_location_dest_id.id if receiving_type.default_location_dest_id else dest_warehouse.lot_stock_id.id,
                'description_picking': getattr(move, 'description_picking', False),
            }
            self.env['stock.move'].create(move_vals)

        # Confirm the receipt (do not validate)
        try:
            new_picking.action_confirm()
        except Exception:
            # if already confirmed or cannot confirm, ignore
            pass

        # Reset quantity_done for manual validation by warehouse user
        for m in new_picking.move_ids:
            try:
                m.quantity_done = 0
            except Exception:
                pass

        # Add messages to both pickings
        picking.sudo().message_post(
            body=_('Receipt transfer %s has been automatically created for %s.') % (new_picking.name, dest_warehouse.name),
            subtype_xmlid='mail.mt_note',
        )
        new_picking.sudo().message_post(
            body=_('This receipt was automatically created from transfer %s. Please validate to receive the products.') % picking.name,
            subtype_xmlid='mail.mt_note',
        )

        return new_picking

    def _notify_main_warehouse_users(self, picking):
        """Send notification to Main warehouse users about new request"""
        main_warehouse = picking.location_id.warehouse_id
        if not main_warehouse:
            _logger.warning('No source warehouse found for picking %s', picking.name)
            return

        _logger.info('Notify main warehouse: picking=%s, source=%s', picking.name, main_warehouse.name)

        main_wh_users = self._get_warehouse_users(main_warehouse)
        if not main_wh_users:
            _logger.warning('No users found for main warehouse %s', main_warehouse.name)
            return

        # Build message
        requesting_wh = picking.picking_type_id.warehouse_id or picking.location_dest_id.warehouse_id
        product_lines = []
        for mv in picking.move_ids:
            product_lines.append('<li>%s (%s %s)</li>' % (mv.product_id.name, mv.product_uom_qty, mv.product_uom.name))

        message = _(
            '<p><strong>🔔 New Stock Request</strong></p>'
            '<p>Warehouse <strong>%s</strong> has requested products from your warehouse:</p>'
            '<ul>%s</ul>'
            '<p>Transfer Reference: <strong>%s</strong></p>'
            '<p><strong>Action Required:</strong> Please review and validate this request.</p>'
        ) % (requesting_wh.name if requesting_wh else _('Unknown'), ''.join(product_lines), picking.name)

        try:
            partners = main_wh_users.mapped('partner_id').ids
            if partners:
                picking.sudo().message_subscribe(partner_ids=partners)
                picking.sudo().message_post(
                    body=message,
                    subject=_('New Stock Request from %s') % (requesting_wh.name if requesting_wh else _('Branch')),
                    partner_ids=partners,
                    message_type='notification',
                    subtype_xmlid='mail.mt_comment',
                    email_from=self.env.user.email_formatted,
                )
        except Exception as e:
            _logger.error('Error posting message for picking %s: %s', picking.name, e)

        # create activities
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not activity_type:
            activity_type = self.env['mail.activity.type'].sudo().search([('name', '=', 'To Do')], limit=1)
        if not activity_type:
            _logger.warning('No To Do activity type found, skipping activity creation')
            return

        for user in main_wh_users:
            try:
                self.env['mail.activity'].sudo().create({
                    'res_id': picking.id,
                    'res_model_id': self.env['ir.model']._get('stock.picking').id,
                    'activity_type_id': activity_type.id,
                    'summary': _('📦 Review Stock Request from %s') % (requesting_wh.name if requesting_wh else _('Branch')),
                    'note': message,
                    'user_id': user.id,
                    'date_deadline': fields.Date.today(),
                })
            except Exception as e:
                _logger.error('Failed to create activity for user %s: %s', getattr(user, 'login', user), e)

    def _notify_warehouse_user(self, picking, receipt_transfer, notification_type):
        """Send notification to destination warehouse users (receipt created or approved)"""
        dest_warehouse = picking.location_dest_id.warehouse_id
        if not dest_warehouse:
            _logger.warning('No dest warehouse for picking %s', picking.name)
            return

        warehouse_users = self._get_warehouse_users(dest_warehouse)
        if not warehouse_users:
            _logger.warning('No users found for destination warehouse %s', dest_warehouse.name)
            return

        # build message
        source_wh = picking.location_id.warehouse_id
        product_lines = []
        for mv in picking.move_ids:
            qty = mv.quantity_done if mv.quantity_done and mv.quantity_done > 0 else mv.product_uom_qty
            product_lines.append('<li>%s (%s %s)</li>' % (mv.product_id.name, qty, mv.product_uom.name))

        if notification_type == 'approved':
            body = _(
                '<p><strong>✅ Stock Request Approved</strong></p>'
                '<p>Your stock request has been approved by <strong>%s</strong>:</p>'
                '<ul>%s</ul>'
                '<p>Original Request: <strong>%s</strong></p>'
                '<p>Receipt Transfer: <strong>%s</strong></p>'
                '<p><strong>Action Required:</strong> Products are now in transit. Please validate the receipt to complete the transfer.</p>'
            ) % (source_wh.name if source_wh else _('Main'), ''.join(product_lines), picking.name, receipt_transfer.name if receipt_transfer else _('N/A'))
            subject = _('✅ Stock Request Approved - %s') % picking.name
        else:
            body = _('Stock transfer update for %s') % picking.name
            subject = _('Stock Transfer Update - %s') % picking.name

        try:
            partners = warehouse_users.mapped('partner_id').ids
            if receipt_transfer and partners:
                receipt_transfer.sudo().message_subscribe(partner_ids=partners)
                receipt_transfer.sudo().message_post(
                    body=body,
                    subject=subject,
                    partner_ids=partners,
                    message_type='notification',
                    subtype_xmlid='mail.mt_comment',
                    email_from=self.env.user.email_formatted,
                )
        except Exception as e:
            _logger.error('Error posting to receipt %s: %s', getattr(receipt_transfer, 'name', 'n/a'), e)

        # create activities for receipt validation if approved
        if notification_type == 'approved' and receipt_transfer:
            activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
            if not activity_type:
                activity_type = self.env['mail.activity.type'].sudo().search([('name', '=', 'To Do')], limit=1)
            if not activity_type:
                _logger.warning('No To Do activity type found for receipt activities')
                return

            for user in warehouse_users:
                try:
                    self.env['mail.activity'].sudo().create({
                        'res_id': receipt_transfer.id,
                        'res_model_id': self.env['ir.model']._get('stock.picking').id,
                        'activity_type_id': activity_type.id,
                        'summary': _('📥 Validate Receipt from %s') % (source_wh.name if source_wh else _('Main')),
                        'note': body,
                        'user_id': user.id,
                        'date_deadline': fields.Date.today(),
                    })
                except Exception as e:
                    _logger.error('Failed to create receipt activity for %s: %s', getattr(user, 'login', user), e)

    def _get_warehouse_users(self, warehouse):
        """
        Return users who belong to the corresponding group for the given warehouse.
        Uses robust matching: checks warehouse.code, then keywords in warehouse.name.
        Replace the XML IDs below if your module name differs.
        """
        try:
            _logger.info('Getting users for warehouse: %s', warehouse.name)

            # Map keywords and codes to group XML IDs (update module name if required)
            # If your module folder is named 'warehouse_transfer_automation' keep these XML IDs.
            # If the module is named differently, change 'warehouse_transfer_automation' to your module name.
            module_prefix = 'warehouse_transfer_automation'
            mapping = {
                'baladiya': '%s.group_baladiya_wh' % module_prefix,
                'balad': '%s.group_baladiya_wh' % module_prefix,
                'dammam': '%s.group_dammam_wh' % module_prefix,
                'dw': '%s.group_dammam_wh' % module_prefix,
                'main': '%s.group_main_wh' % module_prefix,
                'main office': '%s.group_main_wh' % module_prefix,
                'ssaoco-main': '%s.group_main_wh' % module_prefix,
            }

            # 1) try to match on warehouse.code (most reliable)
            code = False
            if hasattr(warehouse, 'code') and warehouse.code:
                code = warehouse.code.strip().lower()

            if code and code in mapping:
                xml_id = mapping[code]
            else:
                # 2) match by name keywords
                name = (warehouse.name or '').strip().lower()
                xml_id = None
                for key, xid in mapping.items():
                    if key in name:
                        xml_id = xid
                        break

            if not xml_id:
                _logger.warning('No group mapping found for warehouse %s (name: %s, code: %s)', warehouse.id, getattr(warehouse, 'name', ''), code)
                # As last resort return admin user to avoid breaking flows
                admin = self.env.ref('base.user_admin', raise_if_not_found=False)
                return admin if admin else self.env['res.users'].sudo().browse([2])

            # load the group
            try:
                group = self.env.ref(xml_id)
            except Exception:
                _logger.error('Group %s not found in system', xml_id)
                admin = self.env.ref('base.user_admin', raise_if_not_found=False)
                return admin if admin else self.env['res.users'].sudo().browse([2])

            # return active non-portal users in the group
            users = self.env['res.users'].sudo().search([
                ('groups_id', 'in', group.id),
                ('active', '=', True),
                ('share', '=', False),
            ])
            if users:
                return users
            else:
                _logger.warning('No users found in group %s, returning admin fallback', xml_id)
                admin = self.env.ref('base.user_admin', raise_if_not_found=False)
                return admin if admin else self.env['res.users'].sudo().browse([2])
        except Exception as e:
            _logger.error('Error getting warehouse users: %s', e, exc_info=True)
            admin = self.env.ref('base.user_admin', raise_if_not_found=False)
            return admin if admin else self.env['res.users'].sudo().browse([2])






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
