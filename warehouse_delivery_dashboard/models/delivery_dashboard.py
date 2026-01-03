from odoo import models, fields, api
from datetime import datetime, timedelta


class StockPickingInherit(models.Model):
    _inherit = 'stock.picking'

    is_urgent = fields.Boolean(
        string='Urgent Delivery',
        compute='_compute_is_urgent',
        store=True
    )

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Source Warehouse',
        related='location_id.warehouse_id',
        store=True,
        readonly=True
    )

    is_today_delivery = fields.Boolean(
        string='Today Delivery',
        compute='_compute_is_today',
        store=True
    )

    days_until_delivery = fields.Integer(
        string='Days Until Delivery',
        compute='_compute_days_until_delivery'
    )

    @api.depends('priority')
    def _compute_is_urgent(self):
        for record in self:
            record.is_urgent = record.priority == '1'

    @api.depends('scheduled_date')
    def _compute_is_today(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.scheduled_date:
                record.is_today_delivery = record.scheduled_date.date() == today
            else:
                record.is_today_delivery = False

    @api.depends('scheduled_date')
    def _compute_days_until_delivery(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.scheduled_date:
                delta = record.scheduled_date.date() - today
                record.days_until_delivery = delta.days
            else:
                record.days_until_delivery = 0

    def action_open_from_dashboard(self):
        """Open delivery order form from dashboard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Delivery: {self.name}',
            'res_model': 'stock.picking',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }


class ResUsers(models.Model):
    _inherit = 'res.users'

    warehouse_ids = fields.Many2many(
        'stock.warehouse',
        'user_warehouse_rel',
        'user_id',
        'warehouse_id',
        string='Assigned Warehouses',
        help='Warehouses this user is responsible for'
    )

    default_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Default Warehouse',
        help='Primary warehouse for this user'
    )

    pending_deliveries_count = fields.Integer(
        string='Pending Deliveries',
        compute='_compute_delivery_counts'
    )

    ready_deliveries_count = fields.Integer(
        string='Ready Deliveries',
        compute='_compute_delivery_counts'
    )

    urgent_deliveries_count = fields.Integer(
        string='Urgent Deliveries',
        compute='_compute_delivery_counts'
    )

    today_deliveries_count = fields.Integer(
        string="Today's Deliveries",
        compute='_compute_delivery_counts'
    )

    def _compute_delivery_counts(self):
        for user in self:
            domain_base = [
                ('picking_type_code', '=', 'outgoing'),
                ('state', 'in', ['confirmed', 'assigned', 'waiting'])
            ]

            # Filter by user's warehouses if assigned
            if user.warehouse_ids:
                domain_base.append(('warehouse_id', 'in', user.warehouse_ids.ids))
            elif user.default_warehouse_id:
                domain_base.append(('warehouse_id', '=', user.default_warehouse_id.id))

            # Pending count
            user.pending_deliveries_count = self.env['stock.picking'].search_count(domain_base)

            # Ready count
            user.ready_deliveries_count = self.env['stock.picking'].search_count(
                domain_base + [('state', '=', 'assigned')]
            )

            # Urgent count
            user.urgent_deliveries_count = self.env['stock.picking'].search_count(
                domain_base + [('priority', '=', '1')]
            )

            # Today count
            today = fields.Date.context_today(self)
            user.today_deliveries_count = self.env['stock.picking'].search_count(
                domain_base + [('is_today_delivery', '=', True)]
            )

    def action_view_my_pending_deliveries(self):
        """Open list of pending deliveries for this user"""
        domain = [
            ('picking_type_code', '=', 'outgoing'),
            ('state', 'in', ['confirmed', 'assigned', 'waiting'])
        ]

        if self.warehouse_ids:
            domain.append(('warehouse_id', 'in', self.warehouse_ids.ids))
        elif self.default_warehouse_id:
            domain.append(('warehouse_id', '=', self.default_warehouse_id.id))

        return {
            'name': 'My Pending Deliveries',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'tree,form,kanban',
            'domain': domain,
            'context': {'create': False},
        }

    def action_view_my_ready_deliveries(self):
        """Open list of ready deliveries"""
        domain = [
            ('picking_type_code', '=', 'outgoing'),
            ('state', '=', 'assigned')
        ]

        if self.warehouse_ids:
            domain.append(('warehouse_id', 'in', self.warehouse_ids.ids))
        elif self.default_warehouse_id:
            domain.append(('warehouse_id', '=', self.default_warehouse_id.id))

        return {
            'name': 'Ready to Deliver',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'tree,form,kanban',
            'domain': domain,
            'context': {'create': False},
        }

    def action_view_my_urgent_deliveries(self):
        """Open list of urgent deliveries"""
        domain = [
            ('picking_type_code', '=', 'outgoing'),
            ('state', 'in', ['confirmed', 'assigned', 'waiting']),
            ('priority', '=', '1')
        ]

        if self.warehouse_ids:
            domain.append(('warehouse_id', 'in', self.warehouse_ids.ids))
        elif self.default_warehouse_id:
            domain.append(('warehouse_id', '=', self.default_warehouse_id.id))

        return {
            'name': 'Urgent Deliveries',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'tree,form,kanban',
            'domain': domain,
            'context': {'create': False},
        }

    def action_view_my_today_deliveries(self):
        """Open list of today's deliveries"""
        domain = [
            ('picking_type_code', '=', 'outgoing'),
            ('state', 'in', ['confirmed', 'assigned', 'waiting']),
            ('is_today_delivery', '=', True)
        ]

        if self.warehouse_ids:
            domain.append(('warehouse_id', 'in', self.warehouse_ids.ids))
        elif self.default_warehouse_id:
            domain.append(('warehouse_id', '=', self.default_warehouse_id.id))

        return {
            'name': "Today's Deliveries",
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'tree,form,kanban',
            'domain': domain,
            'context': {'create': False},
        }