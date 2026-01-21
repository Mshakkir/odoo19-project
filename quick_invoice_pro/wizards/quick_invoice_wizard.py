# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class QuickInvoiceWizard(models.TransientModel):
    _name = 'quick.invoice.wizard'
    _description = 'Quick Invoice Wizard'

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        required=True,
        readonly=True,
    )

    create_draft = fields.Boolean(
        string='Create as Draft',
        default=True,
        help='Create invoice in draft state for review'
    )

    stock_warning = fields.Text(
        string='Stock Warning',
        related='sale_order_id.stock_warning_message',
        readonly=True,
    )

    stock_status = fields.Selection(
        related='sale_order_id.stock_availability_status',
        readonly=True,
    )

    requires_approval = fields.Boolean(
        related='sale_order_id.requires_approval',
        readonly=True,
    )

    amount_total = fields.Monetary(
        related='sale_order_id.amount_total',
        readonly=True,
    )

    currency_id = fields.Many2one(
        related='sale_order_id.currency_id',
        readonly=True,
    )

    force_create = fields.Boolean(
        string='Force Create (Ignore Warnings)',
        help='Create invoice even with stock warnings'
    )

    def action_create_invoice(self):
        """Create invoice with validation"""
        self.ensure_one()

        # Check stock warnings
        if self.stock_status in ['partial', 'none'] and not self.force_create:
            raise UserError(_(
                'Stock Warning:\n\n%s\n\n'
                'Check "Force Create" to proceed anyway.'
            ) % self.stock_warning)

        # Create invoice
        result = self.sale_order_id._create_quick_invoice(
            draft=self.create_draft
        )

        return result

    def action_cancel(self):
        """Cancel wizard"""
        return {'type': 'ir.actions.act_window_close'}