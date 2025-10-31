from odoo import fields, models, api, _

class AccountReportGeneralLedgerAnalytic(models.TransientModel):
    _inherit = "account.report.general.ledger"

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        string='Analytic Accounts',
        help='Filter General Ledger entries by analytic accounts.'
    )

    detail_line_ids = fields.One2many(
        'general.ledger.detail.line', 'wizard_id', string="Detail Lines"
    )

    def compute_detail_lines(self):
        """Populate detail lines for each account in the selected analytic accounts"""
        self.ensure_one()
        Detail = self.env['general.ledger.detail.line']
        Detail.search([('wizard_id', '=', self.id)]).unlink()

        # Query account move lines (reuse from your report_general_ledger_analytic.py)
        analytic_ids = self.analytic_account_ids.ids or []
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
            ('parent_state', '=', 'posted'),
        ]
        if analytic_ids:
            domain.append(('analytic_account_id', 'in', analytic_ids))

        lines = self.env['account.move.line'].search(domain)

        # Group by account
        grouped = {}
        for line in lines:
            grouped.setdefault(line.account_id, []).append(line)

        for account, acc_lines in grouped.items():
            debit = sum(l.debit for l in acc_lines)
            credit = sum(l.credit for l in acc_lines)
            balance = debit - credit

            Detail.create({
                'wizard_id': self.id,
                'account_id': account.id,
                'analytic_account_id': acc_lines[0].analytic_account_id.id if acc_lines[0].analytic_account_id else False,
                'partner_name': ', '.join(set(l.partner_id.name for l in acc_lines if l.partner_id)),
                'date': acc_lines[0].date,
                'move_name': acc_lines[0].move_id.name,
                'label': acc_lines[0].name,
                'debit': debit,
                'credit': credit,
                'balance': balance,
                'move_line_ids': [(6, 0, [l.id for l in acc_lines])],
            })

    def open_general_ledger_details(self):
        """Action to show computed detail lines"""
        self.compute_detail_lines()
        return {
            'name': 'General Ledger Details',
            'type': 'ir.actions.act_window',
            'res_model': 'general.ledger.detail.line',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('wizard_id', '=', self.id)],
            'context': {'default_wizard_id': self.id},
        }
