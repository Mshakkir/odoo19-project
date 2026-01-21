# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Quick Invoice Settings
    quick_invoice_approval_required = fields.Boolean(
        string='Require Approval for Large Orders',
        config_parameter='quick_invoice_pro.approval_required',
        default=True,
    )

    quick_invoice_approval_threshold = fields.Float(
        string='Approval Threshold Amount',
        config_parameter='quick_invoice_pro.approval_threshold',
        default=500.0,
        help='Orders above this amount require manager approval'
    )

    quick_invoice_check_stock = fields.Boolean(
        string='Check Stock Before Invoice',
        config_parameter='quick_invoice_pro.check_stock',
        default=True,
    )

    quick_invoice_allow_draft = fields.Boolean(
        string='Create Draft Invoices',
        config_parameter='quick_invoice_pro.allow_draft',
        default=True,
        help='Create invoices in draft state for review before posting'
    )

    quick_invoice_auto_payment = fields.Boolean(
        string='Auto-open Payment Wizard',
        config_parameter='quick_invoice_pro.auto_payment',
        default=True,
    )

    quick_invoice_partial_delivery = fields.Selection([
        ('block', 'Block Invoice Creation'),
        ('warn', 'Warn User'),
        ('allow', 'Allow Partial Invoice'),
    ], string='When Stock Unavailable',
        config_parameter='quick_invoice_pro.partial_delivery',
        default='warn',
    )