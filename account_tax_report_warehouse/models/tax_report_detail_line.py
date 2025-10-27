from odoo import models, fields, api


class TaxReportDetailLine(models.TransientModel):
    _name = 'tax.report.detail.line'
    _description = 'Tax Report Detail Line'

    wizard_id = fields.Many2one('account.tax.report.wizard', string="Wizard", ondelete='cascade')

    tax_name = fields.Char(string="Tax Name")
    tax_id = fields.Many2one('account.tax', string="Tax")
    type = fields.Selection([
        ('sale', 'Sales'),
        ('purchase', 'Purchase'),
    ], string="Type")

    base_amount = fields.Monetary(string="Base Amount", currency_field='currency_id')
    tax_amount = fields.Monetary(string="Tax Amount", currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  default=lambda self: self.env.company.currency_id.id)

    move_ids = fields.Many2many('account.move', string='Invoices')

    # New field to identify summary rows
    is_summary_row = fields.Boolean(string="Is Summary Row", default=False)
    sequence = fields.Integer(string="Sequence", default=10)  # For ordering

    def open_moves(self):
        """Open invoices related to this tax line"""
        self.ensure_one()
        return {
            'name': 'Invoices for Tax',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.move_ids.ids)],
            'target': 'current',
        }