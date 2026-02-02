# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_inter_warehouse_transfer = fields.Boolean(
        string='Inter-Warehouse Transfer',
        compute='_compute_is_inter_warehouse_transfer',
        store=True
    )

    auto_receipt_created = fields.Boolean(
        string='Auto Receipt Created',
        default=False,
        copy=False,
        help='Technical field to track if automatic receipt was created'
    )

    source_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Source Warehouse',
        compute='_compute_warehouses',
        store=True
    )

    dest_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Destination Warehouse',
        compute='_compute_warehouses',
        store=True
    )

    @api.depends('location_id', 'location_dest_id', 'picking_type_id')
    def _compute_warehouses(self):
        """Compute source and destination warehouses"""
        for picking in self:
            if picking.location_id.warehouse_id:
                picking.source_warehouse_id = picking.location_id.warehouse_id
            else:
                picking.source_warehouse_id = False

            if picking.location_dest_id.warehouse_id:
                picking.dest_warehouse_id = picking.location_dest_id.warehouse_id
            else:
                picking.dest_warehouse_id = False

    @api.depends('location_id', 'location_dest_id')
    def _compute_is_inter_warehouse_transfer(self):
        """Identify if this is an inter-warehouse transfer"""
        for picking in self:
            is_inter_wh = False

            # Check if destination is transit location
            if picking.location_dest_id.usage == 'transit':
                dest_loc_name = picking.location_dest_id.complete_name or picking.location_dest_id.name
                source_loc_name = picking.location_id.complete_name or picking.location_id.name

                _logger.info('🔍 Analyzing inter-WH transfer: %s', picking.name if picking.name else 'NEW')
                _logger.info('   Source loc: %s', source_loc_name)
                _logger.info('   Dest loc: %s', dest_loc_name)

                # Extract warehouse keywords from location names
                source_upper = source_loc_name.upper()
                dest_upper = dest_loc_name.upper()

                # Identify source warehouse
                source_wh_key = None
                # if 'MAIN' in source_upper:
                #     source_wh_key = 'main'
                # elif 'DAMMA' in source_upper or 'DAMMAM' in source_upper:
                #     source_wh_key = 'damma'
                # elif 'BALAD' in source_upper or 'BALADIYA' in source_upper:
                #     source_wh_key = 'balad'
                if 'FYH' in source_upper:
                    source_wh_key = 'fyh'
                elif 'DMM' in source_upper or 'DAMMAM' in source_upper:
                    source_wh_key = 'dmm'
                elif 'BLD' in source_upper or 'BALAD' in source_upper:
                    source_wh_key = 'bld'

                # Identify destination warehouse
                dest_wh_key = None
                if 'MAIN' in dest_upper:
                    dest_wh_key = 'main'
                elif 'DAMMA' in dest_upper or 'DAMMAM' in dest_upper:
                    dest_wh_key = 'damma'
                elif 'BALAD' in dest_upper or 'BALADIYA' in dest_upper:
                    dest_wh_key = 'balad'

                _logger.info('   Source key: %s, Dest key: %s', source_wh_key, dest_wh_key)

                # Inter-warehouse if both have keys and they're different
                if source_wh_key and dest_wh_key and source_wh_key != dest_wh_key:
                    is_inter_wh = True
                    _logger.info('   ✅ INTER-WAREHOUSE TRANSFER DETECTED')
                else:
                    if not source_wh_key:
                        _logger.info('   ⚠️ Could not identify source warehouse')
                    elif not dest_wh_key:
                        _logger.info('   ⚠️ Could not identify dest warehouse')
                    else:
                        _logger.info('   ⚠️ Source and dest are same warehouse: %s == %s', source_wh_key, dest_wh_key)

            picking.is_inter_warehouse_transfer = is_inter_wh

    def button_validate(self):
        """Override validate to add auto-receipt creation"""
        pickings_to_automate = []

        for picking in self:
            _logger.info('🔍 Checking picking for automation: %s', picking.name)
            _logger.info('   - is_inter_warehouse_transfer: %s', picking.is_inter_warehouse_transfer)
            _logger.info('   - location_dest usage: %s', picking.location_dest_id.usage)
            _logger.info('   - auto_receipt_created: %s', picking.auto_receipt_created)
            _logger.info('   - state: %s', picking.state)

            if (picking.location_dest_id.usage == 'transit' and
                    not picking.auto_receipt_created and
                    picking.state in ['assigned', 'confirmed']):

                dest_loc_name = picking.location_dest_id.complete_name or picking.location_dest_id.name
                # if any(wh in dest_loc_name.upper() for wh in ['DAMMA', 'BALAD', 'MAIN']):
                if any(wh in dest_loc_name.upper() for wh in ['FYH', 'BLD', 'DMM']):
                    pickings_to_automate.append(picking)
                    _logger.info('✅ Picking %s WILL BE automated', picking.name)
                else:
                    _logger.info('⚠️ Picking %s skipped - not inter-warehouse transit', picking.name)
            else:
                _logger.info('⚠️ Picking %s skipped - conditions not met', picking.name)

        # Call parent validation
        res = super(StockPicking, self).button_validate()

        # Create auto receipts and notify
        for picking in pickings_to_automate:
            if picking.state == 'done' and not picking.auto_receipt_created:
                try:
                    _logger.info('🚀 Starting automation for picking: %s', picking.name)
                    _logger.info('   Source warehouse: %s',
                                 picking.source_warehouse_id.name if picking.source_warehouse_id else 'None')
                    _logger.info('   Dest warehouse: %s',
                                 picking.dest_warehouse_id.name if picking.dest_warehouse_id else 'None')
                    _logger.info('   Transit location: %s', picking.location_dest_id.complete_name)

                    picking.write({'auto_receipt_created': True})
                    self.env.cr.commit()

                    new_picking = self.sudo()._create_receipt_transfer(picking)

                    if new_picking:
                        _logger.info('✅ Auto-receipt created: %s', new_picking.name)
                        self._notify_destination_warehouse(picking, new_picking)
                    else:
                        _logger.error('❌ Failed to create auto-receipt for: %s', picking.name)
                        picking.write({'auto_receipt_created': False})

                except Exception as e:
                    _logger.error('❌ Error in warehouse automation for %s: %s', picking.name, str(e))
                    import traceback
                    _logger.error(traceback.format_exc())
                    picking.write({'auto_receipt_created': False})

        return res

    def action_confirm(self):
        """Override confirm to send notification to source warehouse"""
        _logger.info('=' * 80)
        _logger.info('📋 action_confirm STARTING for: %s', self.name if self.name else 'NEW')
        _logger.info('=' * 80)

        # CRITICAL FIX: Recompute is_inter_warehouse_transfer to ensure it's up-to-date
        self._compute_is_inter_warehouse_transfer()

        # Log picking details BEFORE confirm
        for picking in self:
            _logger.info('   Picking Details BEFORE super().action_confirm():')
            _logger.info('     - name: %s', picking.name if picking.name else 'NEW')
            _logger.info('     - location_id: %s', picking.location_id.complete_name if picking.location_id else 'None')
            _logger.info('     - location_dest_id: %s',
                         picking.location_dest_id.complete_name if picking.location_dest_id else 'None')
            _logger.info('     - location_dest usage: %s', picking.location_dest_id.usage)
            _logger.info('     - is_inter_warehouse_transfer: %s', picking.is_inter_warehouse_transfer)

        res = super(StockPicking, self).action_confirm()

        _logger.info('   Picking Details AFTER super().action_confirm():')
        for picking in self:
            _logger.info('     - name: %s', picking.name if picking.name else 'NEW')
            _logger.info('     - is_inter_warehouse_transfer: %s', picking.is_inter_warehouse_transfer)
            _logger.info('     - location_dest usage: %s', picking.location_dest_id.usage)

            if picking.is_inter_warehouse_transfer and picking.location_dest_id.usage == 'transit':
                _logger.info('   ✅ Conditions met - Sending notification to source warehouse')
                try:
                    self._notify_source_warehouse(picking)
                except Exception as e:
                    _logger.error('❌ Error sending notification to source warehouse: %s', str(e))
                    import traceback
                    _logger.error(traceback.format_exc())
            else:
                _logger.info('   ⚠️ Notification not sent - conditions not met')
                _logger.info('       is_inter_warehouse_transfer: %s', picking.is_inter_warehouse_transfer)
                _logger.info('       location_dest.usage: %s', picking.location_dest_id.usage)

        _logger.info('=' * 80)
        _logger.info('📋 action_confirm COMPLETED')
        _logger.info('=' * 80)
        return res

    def _create_receipt_transfer(self, picking):
        """Auto-create receipt transfer from transit to destination warehouse"""
        StockPicking = self.env['stock.picking'].sudo()
        StockMove = self.env['stock.move'].sudo()
        # StockMoveLine = self.env['stock.move.line'].sudo()

        existing_receipt = StockPicking.search([
            ('origin', '=', picking.name),
            ('location_id.usage', '=', 'transit')
        ], limit=1)

        if existing_receipt:
            _logger.warning('Receipt already exists for %s: %s', picking.name, existing_receipt.name)
            return existing_receipt

        transit_loc = picking.location_dest_id
        dest_warehouse = picking.dest_warehouse_id

        if not dest_warehouse:
            _logger.error('No destination warehouse found for picking: %s', picking.name)
            return False

        receiving_type = self.env['stock.picking.type'].sudo().search([
            ('warehouse_id', '=', dest_warehouse.id),
            ('code', '=', 'internal'),
            ('default_location_src_id', '=', transit_loc.id)
        ], limit=1)

        if not receiving_type:
            receiving_type = self.env['stock.picking.type'].sudo().search([
                ('warehouse_id', '=', dest_warehouse.id),
                ('code', '=', 'internal')
            ], limit=1)

        if not receiving_type:
            _logger.error('No internal operation type found for warehouse: %s', dest_warehouse.name)
            picking.message_post(
                body=_('⚠️ Warning: Could not find receiving operation type for warehouse %s. '
                       'Please create the receipt manually.') % dest_warehouse.name
            )
            return False

        dest_location = receiving_type.default_location_dest_id

        if not dest_location:
            dest_location = self.env['stock.location'].sudo().search([
                ('warehouse_id', '=', dest_warehouse.id),
                ('usage', '=', 'internal'),
                ('location_id.usage', '=', 'view')
            ], limit=1)

        if not dest_location:
            _logger.error('Could not determine destination location for warehouse: %s', dest_warehouse.name)
            return False

        new_picking_vals = {
            'picking_type_id': receiving_type.id,
            'location_id': transit_loc.id,
            'location_dest_id': dest_location.id,
            'origin': picking.name,
            'partner_id': picking.partner_id.id if picking.partner_id else False,
        }

        new_picking = StockPicking.create(new_picking_vals)
        _logger.info('✅ Created receipt picking %s for warehouse %s', new_picking.name, dest_warehouse.name)

        for move in picking.move_ids:
            # CRITICAL FIX: Get the ACTUAL confirmed/done quantity from the original move
            # The move.product_uom_qty is what was requested/planned
            # We need to use this exact quantity for the receipt

            # When a picking is confirmed, the product_uom_qty is the quantity that was confirmed
            # Don't sum move_lines as they may have reserved differently
            done_qty = move.product_uom_qty

            _logger.info('📦 Creating move for product %s with qty %s (original request qty)',
                         move.product_id.name, done_qty)

            move_vals = {
                'product_id': move.product_id.id,
                'product_uom_qty': done_qty,  # Use the exact confirmed quantity
                'product_uom': move.product_uom.id,
                'picking_id': new_picking.id,
                'location_id': transit_loc.id,
                'location_dest_id': dest_location.id,
                'description_picking': move.description_picking if hasattr(move, 'description_picking') else False,
                'company_id': move.company_id.id,
                'date': fields.Datetime.now(),
                'state': 'draft',
            }
            new_move = StockMove.create(move_vals)
            _logger.info('✅ Created move: %s with qty %s', new_move.id, done_qty)

        new_picking.action_confirm()
        _logger.info('✅ Confirmed receipt picking: %s', new_picking.name)

        # for move in new_picking.move_ids:
        #     move_line_vals = {
        #         'move_id': move.id,
        #         'product_id': move.product_id.id,
        #         'product_uom_id': move.product_uom.id,
        #         'location_id': transit_loc.id,
        #         'location_dest_id': dest_location.id,
        #         'quantity': move.product_uom_qty,
        #         'picking_id': new_picking.id,
        #         'company_id': move.company_id.id,
        #     }
        #     StockMoveLine.create(move_line_vals)
        #     _logger.info('✅ Created move line for move %s', move.id)
        #
        #     move.sudo().write({
        #         'state': 'assigned',
        #     })

        # new_picking.sudo().write({'state': 'assigned'})
        # _logger.info('✅ Receipt picking set to assigned state')
        new_picking.action_assign()
        _logger.info('✅ Receipt picking assigned and ready: %s', new_picking.name)

        picking.message_post(
            body=_('📦 Receipt transfer %s has been automatically created for %s warehouse.') %
                 (new_picking.name, dest_warehouse.name)
        )

        new_picking.message_post(
            body=_('📥 This receipt was automatically created from transfer %s. '
                   'Validate to receive products into your warehouse.') % picking.name
        )

        _logger.info('✅ Receipt %s created and ready for warehouse %s', new_picking.name, dest_warehouse.name)

        return new_picking

    def _notify_source_warehouse(self, picking):
        """Send notification to source warehouse users about new request"""
        _logger.info('=' * 80)
        _logger.info('📢 _notify_source_warehouse called for: %s', picking.name)
        _logger.info('=' * 80)

        source_warehouse = picking.source_warehouse_id
        dest_warehouse = picking.dest_warehouse_id

        if not source_warehouse or not dest_warehouse:
            _logger.warning('Missing warehouse info for picking: %s', picking.name)
            return

        _logger.info('📢 Starting source warehouse notification for picking: %s', picking.name)
        _logger.info('   Source: %s, Destination: %s', source_warehouse.name, dest_warehouse.name)

        source_users = self._get_warehouse_users(source_warehouse)

        if not source_users:
            _logger.error('❌ NO USERS FOUND for %s warehouse - Notifications cannot be sent', source_warehouse.name)
            picking.message_post(
                body=_('⚠️ Warning: Could not send notification to %s warehouse users. '
                       'No users assigned to the warehouse group.') % source_warehouse.name,
                message_type='comment',
            )
            return

        _logger.info('✅ Found %d users for %s warehouse', len(source_users), source_warehouse.name)

        product_lines = []
        for move in picking.move_ids:
            product_lines.append('%s (%s %s)' % (
                move.product_id.name,
                move.product_uom_qty,
                move.product_uom.name
            ))

        message = _(
            '<p><strong>🔔 New Stock Request</strong></p>'
            '<p><strong>%s</strong> warehouse has requested products from your warehouse:</p>'
            '<ul>%s</ul>'
            '<p><strong>Transfer Reference:</strong> %s</p>'
            '<p><strong>Action Required:</strong> Please review and validate this request.</p>'
        ) % (
                      dest_warehouse.name,
                      ''.join(['<li>%s</li>' % line for line in product_lines]),
                      picking.name
                  )

        _logger.info('✅ Sending notification to %d %s warehouse users',
                     len(source_users), source_warehouse.name)

        for user in source_users:
            _logger.info('   → Notifying user: %s (ID: %s, Email: %s)', user.name, user.id, user.email)

        try:
            picking.message_post(
                body=message,
                subject=_('New Stock Request from %s') % dest_warehouse.name,
                partner_ids=source_users.mapped('partner_id').ids,
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
            _logger.info('✅ Message posted on picking')
        except Exception as e:
            _logger.error('❌ Error posting message: %s', str(e))
            import traceback
            _logger.error(traceback.format_exc())

        try:
            self._create_activities(picking, source_users, message,
                                    _('Stock Request: %s') % dest_warehouse.name)
            _logger.info('✅ Activities created')
        except Exception as e:
            _logger.error('❌ Error creating activities: %s', str(e))
            import traceback
            _logger.error(traceback.format_exc())

        _logger.info('✅ Notification and activities sent to %s warehouse users', source_warehouse.name)
        _logger.info('=' * 80)

    def _notify_destination_warehouse(self, origin_picking, receipt_picking):
        """Send notification to destination warehouse users about approved request"""
        _logger.info('=' * 80)
        _logger.info('📢 _notify_destination_warehouse called for: %s', receipt_picking.name)
        _logger.info('=' * 80)

        source_warehouse = origin_picking.source_warehouse_id
        dest_warehouse = origin_picking.dest_warehouse_id

        if not dest_warehouse:
            _logger.warning('No destination warehouse for picking: %s', receipt_picking.name)
            return

        _logger.info('📢 Starting destination warehouse notification for receipt: %s', receipt_picking.name)
        _logger.info('   Source: %s, Destination: %s', source_warehouse.name if source_warehouse else 'None',
                     dest_warehouse.name)

        dest_users = self._get_warehouse_users(dest_warehouse)

        if not dest_users:
            _logger.error('❌ NO USERS FOUND for %s warehouse - Notifications cannot be sent', dest_warehouse.name)
            receipt_picking.message_post(
                body=_('⚠️ Warning: Could not send notification to %s warehouse users.') % dest_warehouse.name,
                message_type='comment',
            )
            return

        _logger.info('✅ Found %d users for %s warehouse', len(dest_users), dest_warehouse.name)

        product_lines = []
        for move in receipt_picking.move_ids:
            product_lines.append('%s (%s %s)' % (
                move.product_id.name,
                move.product_uom_qty,
                move.product_uom.name
            ))

        message = _(
            '<p><strong>✅ Stock Request Approved</strong></p>'
            '<p>Your stock request from <strong>%s</strong> has been approved:</p>'
            '<ul>%s</ul>'
            '<p><strong>Receipt Reference:</strong> <a href="/web#id=%s&model=stock.picking&view_type=form">%s</a></p>'
            '<p><strong>⚠️ Action Required:</strong> Please validate the receipt to receive products into your warehouse.</p>'
        ) % (
                      source_warehouse.name if source_warehouse else 'Source Warehouse',
                      ''.join(['<li>%s</li>' % line for line in product_lines]),
                      receipt_picking.id,
                      receipt_picking.name
                  )

        _logger.info('✅ Sending approval notification to %d %s warehouse users',
                     len(dest_users), dest_warehouse.name)

        for user in dest_users:
            _logger.info('   → Notifying user: %s (ID: %s, Email: %s)', user.name, user.id, user.email)

        try:
            receipt_picking.message_post(
                body=message,
                subject=_('✅ Stock Request Approved - %s') % receipt_picking.name,
                partner_ids=dest_users.mapped('partner_id').ids,
                message_type='notification',
                subtype_xmlid='mail.mt_note',
            )
            _logger.info('✅ Message posted on receipt')
        except Exception as e:
            _logger.error('❌ Error posting message: %s', str(e))
            import traceback
            _logger.error(traceback.format_exc())

        try:
            self._create_activities(receipt_picking, dest_users, message,
                                    _('Action Required: Validate Receipt %s') % receipt_picking.name)
            _logger.info('✅ Activities created')
        except Exception as e:
            _logger.error('❌ Error creating activities: %s', str(e))
            import traceback
            _logger.error(traceback.format_exc())

        _logger.info('✅ Approval notification and activities sent to %s warehouse', dest_warehouse.name)
        _logger.info('=' * 80)

    def _create_activities(self, picking, users, message, summary):
        """Create activities for users"""
        ActivityModel = self.env['mail.activity'].sudo()
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)

        _logger.info('📋 Creating activities for %d users on picking %s', len(users), picking.name)

        if not activity_type:
            _logger.warning('⚠️ Activity type not found, using default')

        for user in users:
            try:
                _logger.info('   Creating activity for user: %s (ID: %s)', user.name, user.id)
                activity = ActivityModel.create({
                    'res_id': picking.id,
                    'res_model_id': self.env['ir.model']._get('stock.picking').id,
                    'activity_type_id': activity_type.id if activity_type else 1,
                    'summary': summary,
                    'note': message,
                    'user_id': user.id,
                    'date_deadline': fields.Date.today(),
                })
                _logger.info('   ✅ Activity created (ID: %s)', activity.id)
            except Exception as e:
                _logger.error('❌ Could not create activity for user %s: %s', user.name, str(e))
                import traceback
                _logger.error(traceback.format_exc())

    def _get_warehouse_users(self, warehouse):
        """Get users assigned to specific warehouse"""
        try:
            _logger.info('🔍 Looking for users for warehouse: "%s"', warehouse.name)
            _logger.info('   Warehouse ID: %s', warehouse.id)

            # warehouse_group_mapping = {
            #     'main': 'warehouse_transfer_automation.group_main_warehouse',
            #     'dammam': 'warehouse_transfer_automation.group_dammam_warehouse',
            #     'damma': 'warehouse_transfer_automation.group_dammam_warehouse',
            #     'baladiya': 'warehouse_transfer_automation.group_baladiya_warehouse',
            #     'balad': 'warehouse_transfer_automation.group_baladiya_warehouse',
            # }

            warehouse_group_mapping = {
                'fyh': 'warehouse_transfer_automation.group_fyh_warehouse',
                'jed-fyh': 'warehouse_transfer_automation.group_fyh_warehouse',
                'dmm': 'warehouse_transfer_automation.group_dmm_warehouse',
                'dmmam': 'warehouse_transfer_automation.group_dmm_warehouse',
                'dmm-wh1': 'warehouse_transfer_automation.group_dmm_warehouse',
                'bld': 'warehouse_transfer_automation.group_bld_warehouse',
                'balad': 'warehouse_transfer_automation.group_bld_warehouse',
                'jed-bld': 'warehouse_transfer_automation.group_bld_warehouse',
            }

            group_xmlid = None
            warehouse_name_lower = warehouse.name.lower()

            for key, xmlid in warehouse_group_mapping.items():
                if key in warehouse_name_lower:
                    group_xmlid = xmlid
                    _logger.info('✓ Matched warehouse "%s" with key "%s"', warehouse.name, key)
                    break

            if not group_xmlid:
                _logger.error('❌ Could not match warehouse "%s" to any group', warehouse.name)
                return self.env['res.users'].browse([])

            _logger.info('   Looking for group: %s', group_xmlid)
            warehouse_group = self.env.ref(group_xmlid, raise_if_not_found=False)

            if not warehouse_group:
                _logger.error('❌ Group %s not found in system', group_xmlid)
                return self.env['res.users'].browse([])

            _logger.info('   Found group: %s (ID: %s)', warehouse_group.name, warehouse_group.id)

            warehouse_users = self.env['res.users'].sudo().search([
                ('active', '=', True),
                ('share', '=', False),
            ])

            filtered_users = self.env['res.users'].browse()
            for user in warehouse_users:
                try:
                    if user.has_group(group_xmlid):
                        filtered_users |= user
                        _logger.info('   + User %s has group %s', user.name, warehouse_group.name)
                except Exception as user_error:
                    _logger.warning('   Warning checking user %s: %s', user.name, str(user_error))
                    continue

            _logger.info('✅ Found %d users for %s warehouse', len(filtered_users), warehouse.name)

            if filtered_users:
                for user in filtered_users:
                    _logger.info('   ✓ User: %s (ID: %s) - Email: %s', user.name, user.id, user.email)
                return filtered_users
            else:
                _logger.warning('⚠️ No users found in group %s for warehouse %s', warehouse_group.name, warehouse.name)
                return self.env['res.users'].browse([])

        except Exception as e:
            _logger.error('❌ Error in _get_warehouse_users: %s', str(e))
            import traceback
            _logger.error(traceback.format_exc())
            return self.env['res.users'].browse([])
