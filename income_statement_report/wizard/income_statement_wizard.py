# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class IncomeStatementWizard(models.TransientModel):
    _name = 'income.statement.wizard'
    _description = 'Income Statement Report Wizard'

    company_id = fields.Many2one(
        'res.company',
        string='Company / Branch',
        default=lambda self: self.env.company,
    )
    all_companies = fields.Boolean(string='All Companies', default=False)
    date_from = fields.Date(
        string='From',
        required=True,
        default=lambda self: fields.Date.today().replace(month=1, day=1),
    )
    date_to = fields.Date(
        string='To',
        required=True,
        default=fields.Date.today,
    )

    @api.onchange('all_companies')
    def _onchange_all_companies(self):
        if self.all_companies:
            self.company_id = False

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise ValidationError("'From' date must be earlier than 'To' date.")

    def _fmt(self, val):
        """Format number with thousands separator and 2 decimals. Negatives show as -X.XX"""
        return '{:,.2f}'.format(val or 0.0)

    def _get_lines(self, account_types, company_ids):
        """Return grouped account.move.line data for the given account_types."""
        if not account_types:
            return []
        domain = [
            ('move_id.state', '=', 'posted'),
            ('move_id.date', '>=', self.date_from),
            ('move_id.date', '<=', self.date_to),
            ('account_id.account_type', 'in', account_types),
        ]
        if company_ids:
            domain.append(('company_id', 'in', company_ids))

        groups = self.env['account.move.line'].read_group(
            domain,
            fields=['account_id', 'balance'],
            groupby=['account_id'],
        )
        result = []
        for g in groups:
            account = self.env['account.account'].browse(g['account_id'][0])
            result.append({
                'name': account.name,
                'code': account.code,
                'balance': g['balance'],
            })
        return result

    def _build_data(self):
        if self.all_companies:
            company_ids = self.env['res.company'].search([]).ids
            company = self.env.company
        else:
            company_ids = [self.company_id.id] if self.company_id else []
            company = self.company_id or self.env.company

        # ── REVENUE ───────────────────────────────────────────────────────────
        # account_type='income': credit-normal → negate balance to get positive revenue
        sales_lines_raw = self._get_lines(['income'], company_ids)
        sales_total = sum(-l['balance'] for l in sales_lines_raw)

        # Sales Return lines: these are accounts where customers return goods.
        # In Odoo they are typically posted as debit on income accounts (credit notes).
        # We look for any income account lines with net positive (debit) balance = returns.
        # OR dedicated return accounts under income_other with positive balance.
        # Strategy: use income_other account_type for dedicated Sales Return accounts.
        sales_return_lines_raw = self._get_lines(['income_other'], company_ids)

        # Split income_other into:
        #   - Sales Returns: net debit balance (positive) → deduction from revenue
        #   - Other Income:  net credit balance (negative) → non-operating income
        actual_return_lines = [l for l in sales_return_lines_raw if l['balance'] >= 0]
        other_income_lines_raw = [l for l in sales_return_lines_raw if l['balance'] < 0]

        # Sales return total = sum of debit balances (already positive)
        sales_return_total = sum(l['balance'] for l in actual_return_lines)
        total_revenue = sales_total - sales_return_total

        # ── COST OF SALES ─────────────────────────────────────────────────────
        # account_type='expense_direct_cost': debit-normal → balance is already positive
        cogs_lines_raw = self._get_lines(['expense_direct_cost'], company_ids)
        cogs_total = sum(l['balance'] for l in cogs_lines_raw)
        gross_profit = total_revenue - cogs_total

        # ── OTHER INCOME & EXPENSES ───────────────────────────────────────────
        # Other Income: credit-normal → balance is negative in DB.
        # Display value = balance as-is (negative), matching target image showing -15.39
        other_income_display_total = sum(l['balance'] for l in other_income_lines_raw)

        # Other Expenses: debit-normal → balance is positive
        other_expense_lines_raw = self._get_lines(
            ['expense', 'expense_depreciation'], company_ids
        )
        other_expense_total = sum(l['balance'] for l in other_expense_lines_raw)

        # Net deduction from gross profit:
        # expenses are positive (increase cost), other_income is negative (reduces cost)
        total_other_net = other_expense_total + other_income_display_total  # income is negative so this subtracts
        # Displayed total: negate so it shows as negative (e.g. -13,274.60)
        total_other_display = -(total_other_net)

        net_profit = gross_profit - total_other_net

        # ── FORMAT LINES FOR TEMPLATE ─────────────────────────────────────────

        # Sales: credit-normal → negate for positive display
        sales_display = [
            {'name': l['name'], 'code': l['code'], 'balance': self._fmt(-l['balance'])}
            for l in sales_lines_raw
        ]

        # Sales Returns: already positive debit balance → display as-is
        sales_return_display = [
            {'name': l['name'], 'code': l['code'], 'balance': self._fmt(l['balance'])}
            for l in actual_return_lines
        ]

        # COGS: already positive → display as-is
        cogs_display = [
            {'name': l['name'], 'code': l['code'], 'balance': self._fmt(l['balance'])}
            for l in cogs_lines_raw
        ]

        # Other Income: credit-normal → balance is negative in DB → display as-is (shows -15.39)
        other_income_display = [
            {'name': l['name'], 'code': l['code'], 'balance': self._fmt(l['balance'])}
            for l in other_income_lines_raw
        ]

        # Other Expenses: positive → display as-is
        other_expense_display = [
            {'name': l['name'], 'code': l['code'], 'balance': self._fmt(l['balance'])}
            for l in other_expense_lines_raw
        ]

        return {
            # Company info
            'company_name': company.name or '',
            'company_name_ar': company.partner_id.name or '',
            'vat': company.vat or '',
            'street': company.street or '',
            'city': company.city or '',
            'zip': company.zip or '',
            'date_from': str(self.date_from),
            'date_to': str(self.date_to),

            # Revenue
            'sales_lines': sales_display,
            'sales_total': self._fmt(sales_total),
            'sales_return_lines': sales_return_display,
            'sales_return_total': self._fmt(sales_return_total),
            'total_revenue': self._fmt(total_revenue),

            # Cost of Sales (line values positive, total negative)
            'cogs_lines': cogs_display,
            'cogs_total': self._fmt(cogs_total),
            'total_cost_of_sales': self._fmt(-cogs_total),

            # Gross Profit
            'gross_profit': self._fmt(gross_profit),

            # Other Income & Expenses
            'other_income_lines': other_income_display,       # negative values e.g. -15.39
            'other_expense_lines': other_expense_display,     # positive values e.g. 6,682.99
            'total_other': self._fmt(total_other_display),    # negative total e.g. -13,274.60

            # Net Profit
            'net_profit': self._fmt(net_profit),
        }

    def action_show_report(self):
        data = self._build_data()
        return self.env.ref(
            'income_statement_report.action_income_statement_report'
        ).report_action(self, data={'form': data})

    def action_clear(self):
        self.write({
            'date_from': fields.Date.today().replace(month=1, day=1),
            'date_to': fields.Date.today(),
            'all_companies': False,
            'company_id': self.env.company.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'income.statement.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }


class IncomeStatementReport(models.AbstractModel):
    _name = 'report.income_statement_report.report_income_statement_template'
    _description = 'Income Statement Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        form = data.get('form', {}) if data else {}
        docs = self.env['income.statement.wizard'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'income.statement.wizard',
            'docs': docs,
            'form': form,
        }