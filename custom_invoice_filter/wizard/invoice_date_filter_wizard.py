from odoo import models, fields, api
from odoo.exceptions import UserError


class InvoiceDateFilterWizard(models.TransientModel):
    _name = 'invoice.date.filter.wizard'
    _description = 'Invoice Date Filter Wizard'

    from_date = fields.Date(
        string='From Date',
        required=True,
        default=fields.Date.context_today
    )
    to_date = fields.Date(
        string='To Date',
        required=True,
        default=fields.Date.context_today
    )

    @api.constrains('from_date', 'to_date')
    def _check_dates(self):
        for record in self:
            if record.from_date > record.to_date:
                raise UserError('From Date cannot be later than To Date!')

    def action_apply_filter(self):
        self.ensure_one()

        # Build domain to filter invoices
        domain = [
            ('move_type', 'in', ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']),
            ('invoice_date', '>=', self.from_date),
            ('invoice_date', '<=', self.to_date),
        ]

        # Return action to show filtered invoices
        return {
            'name': f'Invoices from {self.from_date} to {self.to_date}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {
                'create': False,
                'search_default_filter_date': 1,
            },
            'target': 'current',
        }