# custom_balance_sheet/models/balance_sheet_report.py
from odoo import api, models, _
from odoo.exceptions import UserError

class BalanceSheetReport(models.AbstractModel):
    _name = 'report.custom_balance_sheet.balance_sheet_template'
    _description = 'Balance Sheet QWeb Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        # data contains wizard_uuid, move_scope, date_from, date_to
        if not data:
            raise UserError(_('No data for report'))
        wizard_uuid = data.get('wizard_uuid')
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        move_scope = data.get('move_scope')

        # get aggregated lines from account.move.line
        domain = [('date', '>=', date_from), ('date', '<=', date_to)]
        if move_scope == 'posted':
            domain += [('move_id.state', '=', 'posted')]
        aml_model = self.env['account.move.line']
        grouped = aml_model.read_group(domain + [('account_id', '!=', False)],
                                       ['account_id', 'debit', 'credit', 'balance'],
                                       ['account_id'], orderby='account_id')
        # Transform grouped into structured rows with account record
        rows = []
        total_debit = total_credit = total_balance = 0.0
        for g in grouped:
            if not g.get('account_id'):
                continue
            acc_id = g['account_id'][0]
            acc = self.env['account.account'].browse(acc_id)
            debit = g.get('debit') or 0.0
            credit = g.get('credit') or 0.0
            balance = g.get('balance') or 0.0
            rows.append({
                'account': acc,
                'debit': debit,
                'credit': credit,
                'balance': balance,
            })
            total_debit += debit
            total_credit += credit
            total_balance += balance

        # We can optionally compute top-level categories if needed (Assets/Liability). For simplicity we show account lines.
        return {
            'doc_ids': docids,
            'doc_model': 'balance.sheet.wizard',
            'date_from': date_from,
            'date_to': date_to,
            'move_scope': move_scope,
            'rows': rows,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'total_balance': total_balance,
            'company': self.env.company,
            'time': __import__('datetime').datetime.now(),
        }
