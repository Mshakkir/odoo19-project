from odoo import models, api


class BalanceSheetReport(models.AbstractModel):
    _name = "report.custom_balance_sheet.balance_sheet_template"
    _description = "Balance Sheet Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        # Fetch accounts
        accounts = self.env['account.account'].search([])

        # Separate by type
        assets = []
        liabilities = []
        equity = []

        for account in accounts:
            balance = sum(line.balance for line in account.line_ids
                          if (line.date >= date_from and line.date <= date_to))

            # Construct ledger URL
            ledger_action = {
                'type': 'ir.actions.act_window',
                'name': 'Ledger',
                'res_model': 'account.move.line',
                'view_mode': 'tree,form',
                'domain': [('account_id', '=', account.id),
                           ('date', '>=', date_from),
                           ('date', '<=', date_to)],
                'target': 'current'
            }

            record = {
                'code': account.code,
                'name': account.name,
                'balance': balance,
                'ledger_action': ledger_action,
            }

            if account.user_type_id.type == 'asset':
                assets.append(record)
            elif account.user_type_id.type == 'liability':
                liabilities.append(record)
            elif account.user_type_id.type == 'equity':
                equity.append(record)

        return {
            'doc_ids': docids,
            'doc_model': 'balance.sheet.wizard',
            'date_from': date_from,
            'date_to': date_to,
            'assets': assets,
            'liabilities': liabilities,
            'equity': equity,
        }
