from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class WarehouseTransferRequest(models.Model):
    _name = 'warehouse.transfer.request'
    _description = 'Warehouse Transfer Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = seq = fields.Char(
        string='Request Number',
        required=True,
        copy=False,
        readonly=True,
        default='New'
    )

    source_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Source Warehouse',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        tracking=True
    )

    dest_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Destination Warehouse',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        tracking=True
    )

    request_date = fields.Datetime(
        string='Request Date',
        default=fields.Datetime.now,
        readonly=True,
        tracking=True
    )

    user_id = fields.Many2one(
        'res.users',
        string='Requested By',
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('in_transit', 'In Transit'),
        ('received', 'Received'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True, readonly=True)

    line_ids = fields.One2many(
        'warehouse.transfer.request.line',
        'request_id',
        string='Products',
        readonly=True,
        states={'draft': [('readonly', False)]}
    )

    delivery_picking_id = fields.Many2one(
        'stock.picking',
        string='Delivery Order',
        readonly=True,
        copy=False
    )

    receipt_picking_id = fields.Many2one(
        'stock.picking',
        string='Receipt Order',
        readonly=True,
        copy=False
    )

    notes = fields.Text(string='Notes')

    rejection_reason = fields.Text(
        string='Rejection Reason',
        readonly=True,
        states={'submitted': [('readonly', False)]}
    )

    transit_location_id = fields.Many2one(
        'stock.location',
        string='Transit Location',
        compute='_compute_transit_location',
        store=True
    )

    @api.depends('source_warehouse_id', 'dest_warehouse_id')
    def _compute_transit_location(self):
        for record in self:
            if record.source_warehouse_id and record.dest_warehouse_id:
                # Find or create transit location
                transit_loc = self.env['stock.location'].search([
                    ('name', '=', 'Inter-Warehouse Transit'),
                    ('usage', '=', 'transit')
                ], limit=1)

                if not transit_loc:
                    # Create virtual transit location
                    parent_loc = self.env['stock.location'].search([
                        ('name', '=', 'Virtual Locations')
                    ], limit=1)

                    if not parent_loc:
                        parent_loc = self.env['stock.location'].search([
                            ('usage', '=', 'view')
                        ], limit=1)

                    transit_loc = self.env['stock.location'].create({
                        'name': 'Inter-Warehouse Transit',
                        'usage': 'transit',
                        'location_id': parent_loc.id if parent_loc else False,
                    })

                record.transit_location_id = transit_loc
            else:
                record.transit_location_id = False

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('warehouse.transfer.request') or 'New'
        return super().create(vals)

    def action_submit(self):
        """Submit request for approval"""
        for record in self:
            if not record.line_ids:
                raise UserError(_('Please add at least one product line.'))

            record.state = 'submitted'
            record.message_post(
                body=_('Transfer request submitted for approval.'),
                subject=_('Request Submitted')
            )

            # Send notification email to source warehouse manager
            record._send_notification_email('submit')

    def action_approve(self):
        """Approve request and create pickings"""
        for record in self:
            if record.state != 'submitted':
                raise UserError(_('Only submitted requests can be approved.'))

            # Create delivery picking (from source warehouse to transit)
            delivery_picking = record._create_delivery_picking()

            # Create receipt picking (from transit to destination warehouse)
            receipt_picking = record._create_receipt_picking()

            record.write({
                'state': 'approved',
                'delivery_picking_id': delivery_picking.id,
                'receipt_picking_id': receipt_picking.id,
            })

            record.message_post(
                body=_('Transfer request approved. Delivery: %s, Receipt: %s') % (
                    delivery_picking.name, receipt_picking.name
                ),
                subject=_('Request Approved')
            )

            # Send notification to requester
            record._send_notification_email('approve')

    def action_reject(self):
        """Reject the request"""
        for record in self:
            if record.state != 'submitted':
                raise UserError(_('Only submitted requests can be rejected.'))

            if not record.rejection_reason:
                raise UserError(_('Please provide a rejection reason.'))

            record.state = 'rejected'
            record.message_post(
                body=_('Transfer request rejected. Reason: %s') % record.rejection_reason,
                subject=_('Request Rejected')
            )

            # Send notification to requester
            record._send_notification_email('reject')

    def action_cancel(self):
        """Cancel the request"""
        for record in self:
            if record.state in ['in_transit', 'received']:
                raise UserError(_('Cannot cancel request in transit or received state.'))

            record.state = 'cancelled'
            record.message_post(
                body=_('Transfer request cancelled.'),
                subject=_('Request Cancelled')
            )

    def _create_delivery_picking(self):
        """Create delivery picking from source warehouse to transit"""
        self.ensure_one()

        picking_type = self.source_warehouse_id.out_type_id

        picking_vals = {
            'picking_type_id': picking_type.id,
            'location_id': self.source_warehouse_id.lot_stock_id.id,
            'location_dest_id': self.transit_location_id.id,
            'origin': self.name,
            'partner_id': self.dest_warehouse_id.partner_id.id if self.dest_warehouse_id.partner_id else False,
            'move_ids_without_package': [
                (0, 0, {
                    'name': line.product_id.name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.quantity,
                    'product_uom': line.product_id.uom_id.id,
                    'location_id': self.source_warehouse_id.lot_stock_id.id,
                    'location_dest_id': self.transit_location_id.id,
                }) for line in self.line_ids
            ]
        }

        picking = self.env['stock.picking'].create(picking_vals)
        picking.action_confirm()

        return picking

    def _create_receipt_picking(self):
        """Create receipt picking from transit to destination warehouse"""
        self.ensure_one()

        picking_type = self.dest_warehouse_id.in_type_id

        picking_vals = {
            'picking_type_id': picking_type.id,
            'location_id': self.transit_location_id.id,
            'location_dest_id': self.dest_warehouse_id.lot_stock_id.id,
            'origin': self.name,
            'partner_id': self.source_warehouse_id.partner_id.id if self.source_warehouse_id.partner_id else False,
            'move_ids_without_package': [
                (0, 0, {
                    'name': line.product_id.name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.quantity,
                    'product_uom': line.product_id.uom_id.id,
                    'location_id': self.transit_location_id.id,
                    'location_dest_id': self.dest_warehouse_id.lot_stock_id.id,
                }) for line in self.line_ids
            ]
        }

        picking = self.env['stock.picking'].create(picking_vals)
        picking.action_confirm()

        return picking

    def _send_notification_email(self, action_type):
        """Send email notification based on action"""
        self.ensure_one()

        template_ref = {
            'submit': 'warehouse_transfer_request.email_template_request_submit',
            'approve': 'warehouse_transfer_request.email_template_request_approve',
            'reject': 'warehouse_transfer_request.email_template_request_reject',
        }

        template = self.env.ref(template_ref.get(action_type), False)
        if template:
            template.send_mail(self.id, force_send=True)

    def action_view_delivery(self):
        """View delivery picking"""
        self.ensure_one()
        return {
            'name': _('Delivery Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.delivery_picking_id.id,
            'target': 'current',
        }

    def action_view_receipt(self):
        """View receipt picking"""
        self.ensure_one()
        return {
            'name': _('Receipt Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.receipt_picking_id.id,
            'target': 'current',
        }


class WarehouseTransferRequestLine(models.Model):
    _name = 'warehouse.transfer.request.line'
    _description = 'Warehouse Transfer Request Line'

    request_id = fields.Many2one(
        'warehouse.transfer.request',
        string='Request',
        required=True,
        ondelete='cascade'
    )

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        domain=[('type', 'in', ['product', 'consu'])]
    )

    quantity = fields.Float(
        string='Quantity',
        required=True,
        default=1.0,
        digits='Product Unit of Measure'
    )

    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        related='product_id.uom_id',
        readonly=True
    )

    available_qty = fields.Float(
        string='Available Quantity',
        compute='_compute_available_qty',
        digits='Product Unit of Measure'
    )

    @api.depends('product_id', 'request_id.source_warehouse_id')
    def _compute_available_qty(self):
        for line in self:
            if line.product_id and line.request_id.source_warehouse_id:
                location = line.request_id.source_warehouse_id.lot_stock_id
                line.available_qty = line.product_id.with_context(
                    location=location.id
                ).qty_available
            else:
                line.available_qty = 0.0

    @api.constrains('quantity')
    def _check_quantity(self):
        for line in self:
            if line.quantity <= 0:
                raise ValidationError(_('Quantity must be greater than zero.'))