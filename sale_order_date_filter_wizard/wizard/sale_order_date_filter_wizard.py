# -*- coding: utf-8 -*-

from odoo import models, fields, api


class SaleOrderDateFilterWizard(models.TransientModel):
    _name = 'sale.order.date.filter.wizard'
    _description = 'Sale Order Date Filter Wizard'

    date_from = fields.Date(
        string='Date From',
        required=True,
        default=lambda self: fields.Date.today().replace(day=1)
    )
    date_to = fields.Date(
        string='Date To',
        required=True,
        default=fields.Date.today
    )

    def action_apply_filter(self):
        """Apply the date filter and return to sale orders with domain"""
        self.ensure_one()

        # Build the domain for filtering
        domain = [
            ('date_order', '>=', self.date_from),
            ('date_order', '<=', self.date_to),
        ]

        # Get the sale order action
        action = self.env.ref('sale.action_orders').read()[0]

        # Update the action with our domain
        action.update({
            'domain': domain,
            'context': {
                'search_default_date_from': self.date_from,
                'search_default_date_to': self.date_to,
            },
            'display_name': f'Sale Orders ({self.date_from} to {self.date_to})',
        })

        return action