from odoo import api, models
import logging

_logger = logging.getLogger(__name__)


class ReportFinancialInherit(models.AbstractModel):
    _inherit = 'report.accounting_pdf_reports.report_financial'

    def _compute_account_balance(self, accounts):
        """Override to add analytic account filtering"""
        analytic_account_ids = self.env.context.get('analytic_account_ids', [])

        _logger.info("=" * 80)
        _logger.info(f"_compute_account_balance called")
        _logger.info(f"Accounts to compute: {accounts.mapped('code')}")
        _logger.info(f"Analytic IDs from context: {analytic_account_ids}")
        _logger.info(f"Full context: {self.env.context}")

        # If no analytic filter, use original method
        if not analytic_account_ids:
            _logger.info("No analytic filter - using super()")
            result = super(ReportFinancialInherit, self)._compute_account_balance(accounts)
            _logger.info(f"Super returned {len(result)} accounts")
            return result

        _logger.info(f"Using analytic filter for IDs: {analytic_account_ids}")

        mapping = {
            'balance': "COALESCE(SUM(debit),0) - COALESCE(SUM(credit), 0) as balance",
            'debit': "COALESCE(SUM(debit), 0) as debit",
            'credit': "COALESCE(SUM(credit), 0) as credit",
        }

        res = {}
        for account in accounts:
            res[account.id] = dict.fromkeys(mapping, 0.0)

        if not accounts:
            return res

        # Get move lines with analytic filter using domain
        domain = [('account_id', 'in', accounts.ids)]

        # Add date filters from context
        context = self.env.context
        if context.get('date_from'):
            domain.append(('date', '>=', context['date_from']))
            _logger.info(f"Date from filter: {context['date_from']}")
        if context.get('date_to'):
            domain.append(('date', '<=', context['date_to']))
            _logger.info(f"Date to filter: {context['date_to']}")
        if context.get('state') == 'posted':
            domain.append(('move_id.state', '=', 'posted'))
            _logger.info("State filter: posted only")

        _logger.info(f"Base domain (before analytic): {domain}")

        # Get all move lines first
        all_move_lines = self.env['account.move.line'].search(domain)
        _logger.info(f"Total move lines before analytic filter: {len(all_move_lines)}")

        # Filter by analytic account
        filtered_lines = all_move_lines.filtered(
            lambda l: any(
                anal_line.account_id.id in analytic_account_ids
                for anal_line in l.analytic_line_ids
            )
        )

        _logger.info(f"Move lines after analytic filter: {len(filtered_lines)}")

        if filtered_lines:
            _logger.info(f"Sample filtered line: Account={filtered_lines[0].account_id.code}, "
                         f"Debit={filtered_lines[0].debit}, Credit={filtered_lines[0].credit}")

        # Group by account and sum
        for line in filtered_lines:
            if line.account_id.id not in res:
                res[line.account_id.id] = {'debit': 0.0, 'credit': 0.0, 'balance': 0.0}
            res[line.account_id.id]['debit'] += line.debit
            res[line.account_id.id]['credit'] += line.credit
            res[line.account_id.id]['balance'] += (line.debit - line.credit)

        _logger.info(
            f"Final balance result: {len([v for v in res.values() if v['balance'] != 0])} accounts with non-zero balance")
        for acc_id, values in res.items():
            if values['balance'] != 0:
                account = self.env['account.account'].browse(acc_id)
                _logger.info(f"  {account.code}: Balance={values['balance']}")

        return res

    @api.model
    def _get_report_values(self, docids, data=None):
        """Override to handle separate reports per analytic account"""

        _logger.info("=" * 80)
        _logger.info("_get_report_values called")
        _logger.info(f"docids: {docids}")
        _logger.info(f"data: {data}")

        if not data or not data.get('form'):
            _logger.info("No data form - using super()")
            return super(ReportFinancialInherit, self)._get_report_values(docids, data)

        analytic_account_ids = data['form'].get('analytic_account_ids', [])
        analytic_filter_mode = data['form'].get('analytic_filter_mode', 'combined')

        _logger.info(f"Analytic IDs: {analytic_account_ids}")
        _logger.info(f"Filter Mode: {analytic_filter_mode}")
        _logger.info(f"Used context from data: {data['form'].get('used_context')}")

        # If separate mode and analytic accounts selected
        if analytic_account_ids and analytic_filter_mode == 'separate':
            _logger.info("SEPARATE MODE activated")
            all_reports = []

            for analytic_id in analytic_account_ids:
                analytic_account = self.env['account.analytic.account'].browse(analytic_id)
                _logger.info(f"Processing analytic account: {analytic_account.name} (ID: {analytic_id})")

                # Create context with single analytic account
                report_context = dict(data['form'].get('used_context', {}))
                report_context['analytic_account_ids'] = [analytic_id]

                _logger.info(f"Report context for {analytic_account.name}: {report_context}")

                # Get report lines
                report_lines = self.with_context(**report_context).get_account_lines(data['form'])

                _logger.info(f"Got {len(report_lines)} report lines for {analytic_account.name}")

                all_reports.append({
                    'analytic_account': analytic_account,
                    'report_lines': report_lines,
                    'data': data['form'],
                })

            model = self.env.context.get('active_model')
            docs = self.env[model].browse(self.env.context.get('active_id'))

            result = {
                'doc_ids': self.ids,
                'doc_model': model,
                'data': data['form'],
                'docs': docs,
                'time': __import__('time'),
                'all_reports': all_reports,
                'analytic_filter_mode': 'separate',
            }

            _logger.info(f"Returning separate mode with {len(all_reports)} reports")
            return result

        # Combined mode - add context
        if analytic_account_ids:
            _logger.info("COMBINED MODE activated")
            context = dict(self.env.context)
            context['analytic_account_ids'] = analytic_account_ids
            _logger.info(f"Combined context: {context}")
            return super(ReportFinancialInherit, self.with_context(**context))._get_report_values(docids, data)

        # No analytics
        _logger.info("NO ANALYTICS - using super()")
        return super(ReportFinancialInherit, self)._get_report_values(docids, data)