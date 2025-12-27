# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # Changed from compute field to regular stored field
    transfer_type = fields.Selection(
        [('outgoing', 'Outgoing Request'),
         ('incoming', 'Incoming Receipt'),
         ('normal', 'Normal Transfer')],
        string='Transfer Type',
        default='normal',
        store=True,
        help='Identifies if this is an outgoing request or incoming receipt'
    )

    # Make these fields compute AND store
    source_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Source Warehouse',
        compute='_compute_warehouse_fields',
        store=True,
        help='Warehouse that is sending the products'
    )

    dest_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Destination Warehouse',
        compute='_compute_warehouse_fields',
        store=True,
        help='Warehouse that will receive the products'
    )

    is_multi_wh_transfer = fields.Boolean(
        string='Multi-WH Transfer',
        compute='_compute_warehouse_fields',
        store=True,
        help='Is this a multi-warehouse transfer?'
    )

    auto_receipt_created = fields.Boolean(
        string='Auto Receipt Created',
        default=False,
        copy=False,
        help='Tracks if automatic receipt was created'
    )

    related_picking_id = fields.Many2one(
        'stock.picking',
        string='Related Transfer',
        copy=False,
        help='Links outgoing transfer to incoming receipt'
    )

    @api.depends('location_id', 'location_dest_id', 'picking_type_id')
    def _compute_warehouse_fields(self):
        """Compute all warehouse-related fields at once"""
        for picking in self:
            src_wh = picking.location_id.warehouse_id
            dest_wh = picking.location_dest_id.warehouse_id

            # Set multi-warehouse flag
            if src_wh and dest_wh and src_wh != dest_wh:
                picking.is_multi_wh_transfer = True
            else:
                picking.is_multi_wh_transfer = False

            # Set transfer type
            if picking.is_multi_wh_transfer:
                if picking.location_dest_id.usage == 'transit':
                    picking.transfer_type = 'outgoing'
                elif picking.location_id.usage == 'transit':
                    picking.transfer_type = 'incoming'
                else:
                    picking.transfer_type = 'normal'
            else:
                picking.transfer_type = 'normal'

            # Set source warehouse
            if picking.transfer_type == 'incoming':
                picking.source_warehouse_id = picking.location_id.warehouse_id
            else:
                picking.source_warehouse_id = src_wh

            # Set destination warehouse
            if picking.transfer_type == 'outgoing':
                picking.dest_warehouse_id = picking.location_dest_id.warehouse_id
            else:
                picking.dest_warehouse_id = dest_wh

    # Alternative: Create a method to update transfer type on specific triggers
    @api.model
    def create(self, vals):
        """Override create to set initial transfer type"""
        record = super(StockPicking, self).create(vals)
        record._update_transfer_type()
        return record

    def write(self, vals):
        """Override write to update transfer type when relevant fields change"""
        res = super(StockPicking, self).write(vals)
        if any(field in vals for field in ['location_id', 'location_dest_id', 'picking_type_id']):
            self._update_transfer_type()
        return res

    def _update_transfer_type(self):
        """Update transfer type for records"""
        for picking in self:
            src_wh = picking.location_id.warehouse_id
            dest_wh = picking.location_dest_id.warehouse_id

            if src_wh and dest_wh and src_wh != dest_wh:
                if picking.location_dest_id.usage == 'transit':
                    picking.transfer_type = 'outgoing'
                elif picking.location_id.usage == 'transit':
                    picking.transfer_type = 'incoming'
                else:
                    picking.transfer_type = 'normal'
            else:
                picking.transfer_type = 'normal'








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
#     # New fields for multi-warehouse transfers
#     transfer_type = fields.Selection(
#         [('outgoing', 'Outgoing Request'),
#          ('incoming', 'Incoming Receipt')],
#         string='Transfer Type',
#         compute='_compute_transfer_type',
#         store=True,
#         help='Identifies if this is an outgoing request or incoming receipt'
#     )
#
#     source_warehouse_id = fields.Many2one(
#         'stock.warehouse',
#         string='Source Warehouse',
#         compute='_compute_source_warehouse',
#         store=True,
#         help='Warehouse that is sending the products'
#     )
#
#     dest_warehouse_id = fields.Many2one(
#         'stock.warehouse',
#         string='Destination Warehouse',
#         compute='_compute_dest_warehouse',
#         store=True,
#         help='Warehouse that will receive the products'
#     )
#
#     is_multi_wh_transfer = fields.Boolean(
#         string='Multi-WH Transfer',
#         compute='_compute_is_multi_wh_transfer',
#         store=True,
#         help='Is this a multi-warehouse transfer?'
#     )
#
#     auto_receipt_created = fields.Boolean(
#         string='Auto Receipt Created',
#         default=False,
#         copy=False,
#         help='Tracks if automatic receipt was created'
#     )
#
#     related_picking_id = fields.Many2one(
#         'stock.picking',
#         string='Related Transfer',
#         copy=False,
#         help='Links outgoing transfer to incoming receipt'
#     )
#
#     @api.depends('location_id', 'location_dest_id', 'location_id.warehouse_id', 'location_dest_id.warehouse_id')
#     def _compute_transfer_type(self):
#         """Determine if this is outgoing request or incoming receipt"""
#         for picking in self:
#             src_wh = picking.location_id.warehouse_id
#             dest_wh = picking.location_dest_id.warehouse_id
#
#             if src_wh and dest_wh and src_wh != dest_wh:
#                 # If destination is transit, it's outgoing
#                 if picking.location_dest_id.usage == 'transit':
#                     picking.transfer_type = 'outgoing'
#                 # If source is transit, it's incoming
#                 elif picking.location_id.usage == 'transit':
#                     picking.transfer_type = 'incoming'
#                 else:
#                     picking.transfer_type = False
#             else:
#                 picking.transfer_type = False
#
#     @api.depends('location_id', 'transfer_type')
#     def _compute_source_warehouse(self):
#         """Get source warehouse"""
#         for picking in self:
#             picking.source_warehouse_id = picking.location_id.warehouse_id or False
#
#     @api.depends('location_dest_id', 'transfer_type')
#     def _compute_dest_warehouse(self):
#         """Get destination warehouse"""
#         for picking in self:
#             if picking.transfer_type == 'outgoing':
#                 # For outgoing, destination warehouse is linked to transit
#                 picking.dest_warehouse_id = picking.location_dest_id.warehouse_id or False
#             elif picking.transfer_type == 'incoming':
#                 # For incoming, destination warehouse is from picking_type
#                 picking.dest_warehouse_id = picking.picking_type_id.warehouse_id or False
#             else:
#                 picking.dest_warehouse_id = False
#
#     @api.depends('is_multi_wh_transfer', 'location_id', 'location_dest_id')
#     def _compute_is_multi_wh_transfer(self):
#         """Check if this is multi-warehouse transfer"""
#         for picking in self:
#             src_wh = picking.location_id.warehouse_id
#             dest_wh = picking.location_dest_id.warehouse_id
#             if src_wh and dest_wh and src_wh != dest_wh:
#                 picking.is_multi_wh_transfer = True
#             else:
#                 picking.is_multi_wh_transfer = False
#
#     def button_validate(self):
#         """Override validate to handle multi-warehouse automation"""
#         pickings_to_automate = []
#
#         for picking in self:
#             # Check if this is outgoing transfer to transit location
#             if (picking.transfer_type == 'outgoing' and
#                     picking.location_dest_id.usage == 'transit' and
#                     not picking.auto_receipt_created and
#                     picking.state in ['assigned', 'confirmed']):
#                 pickings_to_automate.append(picking)
#
#         # Call parent validation
#         res = super(StockPicking, self).button_validate()
#
#         # Process automation AFTER validation
#         for picking in pickings_to_automate:
#             if picking.state == 'done' and not picking.auto_receipt_created:
#                 try:
#                     # Mark as processed
#                     picking.write({'auto_receipt_created': True})
#                     self.env.cr.commit()
#
#                     # Create return receipt and link it
#                     new_picking = self.sudo()._create_return_receipt(picking)
#
#                     if new_picking:
#                         # Send approval notification to receiving warehouse
#                         self._notify_destination_warehouse(picking, new_picking, 'request_approved')
#
#                 except Exception as e:
#                     _logger.error('Error in automation for %s: %s', picking.name, str(e))
#                     picking.write({'auto_receipt_created': False})
#
#         return res
#
#     def action_confirm(self):
#         """Send notification to source warehouse when request is confirmed"""
#         res = super(StockPicking, self).action_confirm()
#
#         for picking in self:
#             if picking.transfer_type == 'outgoing' and picking.location_dest_id.usage == 'transit':
#                 try:
#                     self._notify_source_warehouse(picking, 'request_received')
#                 except Exception as e:
#                     _logger.error('Error sending notification: %s', str(e))
#
#         return res
#
#     def _create_return_receipt(self, picking):
#         """Create incoming receipt from outgoing transfer"""
#         StockPicking = self.env['stock.picking'].sudo()
#         StockMove = self.env['stock.move'].sudo()
#         StockMoveLine = self.env['stock.move.line'].sudo()
#
#         # Check if receipt already exists
#         existing_receipt = StockPicking.search([
#             ('origin', '=', picking.name),
#             ('transfer_type', '=', 'incoming')
#         ], limit=1)
#
#         if existing_receipt:
#             _logger.warning('📋 Receipt already exists for %s: %s', picking.name, existing_receipt.name)
#             return existing_receipt
#
#         transit_loc = picking.location_dest_id
#         dest_warehouse = transit_loc.warehouse_id
#
#         if not dest_warehouse:
#             _logger.error('❌ No destination warehouse for transit location: %s', transit_loc.name)
#             picking.message_post(
#                 body=_('❌ Error: Could not determine destination warehouse for receipt'),
#                 message_type='comment'
#             )
#             return False
#
#         _logger.info('📍 Creating receipt for warehouse: %s', dest_warehouse.name)
#
#         # Find receiving operation type
#         receiving_type = self.env['stock.picking.type'].sudo().search([
#             ('warehouse_id', '=', dest_warehouse.id),
#             ('code', '=', 'internal'),
#         ], limit=1)
#
#         if not receiving_type:
#             _logger.error('❌ No receiving operation type for warehouse: %s', dest_warehouse.name)
#             picking.message_post(
#                 body=_('⚠️ Warning: Could not find receiving operation type. Create internal transfer type first.'),
#                 message_type='comment'
#             )
#             return False
#
#         dest_location = receiving_type.default_location_dest_id
#         if not dest_location:
#             dest_location = self.env['stock.location'].sudo().search([
#                 ('warehouse_id', '=', dest_warehouse.id),
#                 ('usage', '=', 'internal'),
#             ], limit=1)
#
#         if not dest_location:
#             _logger.error('❌ No destination location for warehouse: %s', dest_warehouse.name)
#             return False
#
#         # Create receipt picking
#         new_picking_vals = {
#             'picking_type_id': receiving_type.id,
#             'location_id': transit_loc.id,
#             'location_dest_id': dest_location.id,
#             'origin': picking.name,
#             'partner_id': picking.partner_id.id if picking.partner_id else False,
#         }
#
#         new_picking = StockPicking.create(new_picking_vals)
#         picking.write({'related_picking_id': new_picking.id})
#         new_picking.write({'related_picking_id': picking.id})
#
#         _logger.info('✅ Created receipt %s for %s', new_picking.name, picking.name)
#
#         # Copy moves from outgoing transfer
#         for move in picking.move_ids:
#             done_qty = sum(move.move_line_ids.mapped('quantity')) if move.move_line_ids else move.product_uom_qty
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
#             StockMove.create(move_vals)
#
#         # Confirm and reserve
#         new_picking.action_confirm()
#
#         for move in new_picking.move_ids:
#             move_line_vals = {
#                 'move_id': move.id,
#                 'product_id': move.product_id.id,
#                 'product_uom_id': move.product_uom.id,
#                 'location_id': transit_loc.id,
#                 'location_dest_id': dest_location.id,
#                 'quantity': move.product_uom_qty,
#                 'reserved_uom_qty': move.product_uom_qty,
#                 'picking_id': new_picking.id,
#                 'company_id': move.company_id.id,
#             }
#             StockMoveLine.create(move_line_vals)
#
#             move.sudo().write({
#                 'state': 'assigned',
#                 'reserved_availability': move.product_uom_qty
#             })
#
#         new_picking.sudo().write({'state': 'assigned'})
#
#         picking.message_post(
#             body=_('✅ Receipt transfer %s auto-created for warehouse %s') % (new_picking.name, dest_warehouse.name)
#         )
#
#         new_picking.message_post(
#             body=_('📥 This receipt was auto-created from transfer %s. Validate to receive products.') % picking.name
#         )
#
#         _logger.info('✅ Receipt %s ready for validation in warehouse %s', new_picking.name, dest_warehouse.name)
#         return new_picking
#
#     def _notify_source_warehouse(self, picking, notification_type):
#         """Notify source warehouse when request is received"""
#         source_warehouse = picking.source_warehouse_id
#
#         if not source_warehouse:
#             _logger.warning('⚠️ No source warehouse found for picking: %s', picking.name)
#             return
#
#         source_users = self._get_warehouse_users(source_warehouse)
#
#         if not source_users:
#             _logger.error('❌ NO USERS for source warehouse: %s', source_warehouse.name)
#             picking.message_post(
#                 body=_('⚠️ No users assigned to source warehouse group'),
#                 message_type='comment'
#             )
#             return
#
#         dest_warehouse = picking.dest_warehouse_id
#
#         product_lines = []
#         for move in picking.move_ids:
#             product_lines.append(
#                 '%s (%s %s)' % (move.product_id.name, move.product_uom_qty, move.product_uom.name)
#             )
#
#         message = _(
#             '<p><strong>📤 Outgoing Request Confirmed</strong></p>'
#             '<p>Warehouse <strong>%s</strong> has confirmed request for products:</p>'
#             '<ul>%s</ul>'
#             '<p><strong>Transfer:</strong> %s</p>'
#             '<p>Please validate to process the stock transfer.</p>'
#         ) % (
#                       dest_warehouse.name if dest_warehouse else 'Unknown',
#                       ''.join(['<li>%s</li>' % line for line in product_lines]),
#                       picking.name
#                   )
#
#         self._create_notifications(picking, source_users, message,
#                                    'Request Confirmed - ' + (dest_warehouse.name if dest_warehouse else 'Unknown'))
#
#     def _notify_destination_warehouse(self, outgoing_picking, incoming_picking, notification_type):
#         """Notify destination warehouse when transfer is approved"""
#         dest_warehouse = incoming_picking.dest_warehouse_id
#
#         if not dest_warehouse:
#             _logger.warning('⚠️ No destination warehouse found')
#             return
#
#         dest_users = self._get_warehouse_users(dest_warehouse)
#
#         if not dest_users:
#             _logger.error('❌ NO USERS for destination warehouse: %s', dest_warehouse.name)
#             incoming_picking.message_post(
#                 body=_('⚠️ No users assigned to destination warehouse group'),
#                 message_type='comment'
#             )
#             return
#
#         source_warehouse = outgoing_picking.source_warehouse_id
#
#         product_lines = []
#         for move in incoming_picking.move_ids:
#             product_lines.append(
#                 '%s (%s %s)' % (move.product_id.name, move.product_uom_qty, move.product_uom.name)
#             )
#
#         message = _(
#             '<p><strong>✅ Stock Request Approved</strong></p>'
#             '<p>Your request has been approved by <strong>%s</strong></p>'
#             '<ul>%s</ul>'
#             '<p><strong>Receipt:</strong> <a href="/web#id=%s&model=stock.picking&view_type=form">%s</a></p>'
#             '<p>⚠️ Please validate the receipt to complete the stock transfer and increase your inventory.</p>'
#         ) % (
#                       source_warehouse.name if source_warehouse else 'Unknown',
#                       ''.join(['<li>%s</li>' % line for line in product_lines]),
#                       incoming_picking.id,
#                       incoming_picking.name
#                   )
#
#         self._create_notifications(incoming_picking, dest_users, message, '✅ Request Approved - Action Required')
#
#     def _create_notifications(self, picking, users, message, subject):
#         """Create multiple notification methods"""
#         if not users:
#             return
#
#         _logger.info('📢 Sending notification to %d users for %s: %s',
#                      len(users), picking.name, ', '.join(users.mapped('name')))
#
#         # Message in chatter
#         picking.message_post(
#             body=message,
#             subject=subject,
#             partner_ids=users.mapped('partner_id').ids,
#             message_type='notification',
#             subtype_xmlid='mail.mt_note',
#         )
#
#         # Create activities
#         activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
#         ActivityModel = self.env['mail.activity'].sudo()
#
#         for user in users:
#             try:
#                 ActivityModel.create({
#                     'res_id': picking.id,
#                     'res_model_id': self.env['ir.model']._get('stock.picking').id,
#                     'activity_type_id': activity_type.id if activity_type else 1,
#                     'summary': subject,
#                     'note': message,
#                     'user_id': user.id,
#                     'date_deadline': fields.Date.today(),
#                 })
#                 _logger.info('✅ Activity created for user: %s', user.name)
#             except Exception as e:
#                 _logger.warning('⚠️ Could not create activity for %s: %s', user.name, str(e))
#
#         # Internal message
#         self.env['mail.message'].sudo().create({
#             'subject': subject,
#             'body': message,
#             'model': 'stock.picking',
#             'res_id': picking.id,
#             'message_type': 'notification',
#             'partner_ids': [(4, pid) for pid in users.mapped('partner_id').ids],
#             'needaction_partner_ids': [(4, pid) for pid in users.mapped('partner_id').ids],
#         })
#
#     def _get_warehouse_users(self, warehouse):
#         """Get users for a specific warehouse by name matching"""
#         try:
#             _logger.info('🔍 Looking for users of warehouse: "%s"', warehouse.name)
#
#             # Search for group by warehouse name (SSAOCO-Main, SSAOCO-Dammam, SSAOCO-Baladiya)
#             warehouse_group = self.env['res.groups'].search([
#                 ('name', 'like', warehouse.name)
#             ], limit=1)
#
#             if not warehouse_group:
#                 _logger.warning('⚠️ No group found with name like "%s"', warehouse.name)
#                 # Try alternative matching
#                 warehouse_group = self.env['res.groups'].search([
#                     ('name', 'ilike', warehouse.name.replace('SSAOCO-', ''))
#                 ], limit=1)
#
#             if warehouse_group:
#                 _logger.info('✅ Found group: %s', warehouse_group.name)
#
#                 warehouse_users = self.env['res.users'].search([
#                     ('group_ids', 'in', warehouse_group.id),
#                     ('active', '=', True),
#                     ('share', '=', False)
#                 ])
#
#                 if warehouse_users:
#                     _logger.info('✅ Found %d users for warehouse %s: %s',
#                                  len(warehouse_users), warehouse.name,
#                                  ', '.join(warehouse_users.mapped('name')))
#                     return warehouse_users
#                 else:
#                     _logger.warning('⚠️ Group %s exists but has NO USERS assigned', warehouse_group.name)
#             else:
#                 _logger.error('❌ Could not find group for warehouse: %s', warehouse.name)
#                 # Log all available groups for debugging
#                 all_groups = self.env['res.groups'].search([('name', 'ilike', 'SSAOCO')])
#                 _logger.info('📋 Available SSAOCO groups: %s', ', '.join([g.name for g in all_groups]))
#
#             _logger.error('❌ NO USERS FOUND for warehouse: %s', warehouse.name)
#             return self.env['res.users'].browse([])
#
#         except Exception as e:
#             _logger.error('❌ Error getting warehouse users: %s', str(e))
#             import traceback
#             _logger.error(traceback.format_exc())
#             return self.env['res.users'].browse([])