# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class PurchaseReportByProductGroupWizard(models.TransientModel):
    _name = 'purchase.report.by.product.group.wizard'
    _description = 'Purchase Report By Product Group Wizard'

    date_from = fields.Date(string='Date From', required=True, default=fields.Date.context_today)
    date_to = fields.Date(string='Date To', required=True, default=fields.Date.context_today)
    categ_ids = fields.Many2many('product.category', string='Product Groups')
    partner_ids = fields.Many2many('res.partner', string='Vendors', domain=[('supplier_rank', '>', 0)])
    warehouse_ids = fields.Many2many('stock.warehouse', string='Warehouses')
    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ], string='Status', default='purchase')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from > record.date_to:
                raise UserError('Date From must be before Date To.')

    def action_generate_report(self):
        self.ensure_one()

        domain = [
            ('order_date', '>=', self.date_from),
            ('order_date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id)
        ]

        if self.categ_ids:
            domain.append(('categ_id', 'in', self.categ_ids.ids))

        if self.partner_ids:
            domain.append(('partner_id', 'in', self.partner_ids.ids))

        if self.warehouse_ids:
            domain.append(('warehouse_id', 'in', self.warehouse_ids.ids))

        if self.state:
            domain.append(('state', '=', self.state))

        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Report - By Product Group',
            'res_model': 'purchase.report.view',
            'view_mode': 'tree,pivot,graph',
            'domain': domain,
            'target': 'current',
            'context': {
                'search_default_group_by_category': 1,
                'report_type': 'by_product_group',
            }
        }