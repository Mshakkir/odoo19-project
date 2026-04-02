# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class PurchaseSalesComparisonWizard(models.TransientModel):
    _name = 'purchase.sales.comparison.wizard'
    _description = 'Purchase Sales Comparison Report Wizard'

    form_type = fields.Selection([
        ('default', 'Default'),
        ('detailed', 'Detailed'),
    ], string='Form Type', default='default', required=True)

    bill_mode = fields.Selection([
        ('all', 'All'),
        ('billed', 'Billed'),
        ('unbilled', 'Unbilled'),
    ], string='Bill Mode', default='all')

    product_filter = fields.Selection([
        ('all', 'All'),
        ('by_product', 'By Product'),
    ], string='Product Filter', default='all', required=True)

    product_id = fields.Many2one(
        'product.product',
        string='Product',
    )

    date_from = fields.Date(
        string='From',
        required=True,
        default=fields.Date.context_today,
    )

    date_to = fields.Date(
        string='To',
        required=True,
        default=fields.Date.context_today,
    )

    @api.onchange('product_filter')
    def _onchange_product_filter(self):
        if self.product_filter == 'all':
            self.product_id = False

    def action_show_report(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError('From date cannot be greater than To date.')

        data = {
            'form_type': self.form_type,
            'bill_mode': self.bill_mode,
            'product_filter': self.product_filter,
            'product_id': self.product_id.id if self.product_id else False,
            'product_name': self.product_id.display_name if self.product_id else False,
            'date_from': str(self.date_from),
            'date_to': str(self.date_to),
        }

        # Look up the ir.actions.report record by its report_name field
        # (the 'name' attribute in the <report> tag in XML).
        # This avoids relying on env.ref() which requires the XML id to be
        # registered as an ir.model.data entry — which Odoo 19 may skip for
        # <report> shorthand tags.
        report_action = self.env['ir.actions.report'].search([
            ('report_name', '=',
             'purchase_sales_comparison_report.report_psc_pur_sal_comparison'),
        ], limit=1)

        if not report_action:
            raise UserError(
                'Report action not found. Please upgrade the module and try again.'
            )

        return report_action.report_action(self, data=data)