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
        """Open invoices related to this tax line filtered by analytic account"""
        self.ensure_one()

        # Get the wizard's analytic account filter
        analytic_account_ids = self.wizard_id.analytic_account_ids.ids if self.wizard_id.analytic_account_ids else []

        # Base domain with move_ids from this line
        domain = [('id', 'in', self.move_ids.ids)]

        # If analytic accounts are selected in wizard, filter invoices by those accounts
        if analytic_account_ids:
            domain.append(('line_ids.analytic_distribution', '!=', False))

            # Filter moves that have invoice lines with the selected analytic accounts
            filtered_move_ids = []
            for move in self.move_ids:
                for line in move.line_ids:
                    if line.analytic_distribution:
                        # Check if any of the selected analytic accounts are in the distribution
                        analytic_ids_in_line = [int(k) for k in line.analytic_distribution.keys()]
                        if any(acc_id in analytic_ids_in_line for acc_id in analytic_account_ids):
                            filtered_move_ids.append(move.id)
                            break

            domain = [('id', 'in', filtered_move_ids)]

        return {
            'name': f'Invoices for {self.tax_name or self.tax_id.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': domain,
            'target': 'current',
            'context': {'create': False},
        }