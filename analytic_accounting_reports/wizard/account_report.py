# -*- coding: utf-8 -*-
from odoo import api, fields, models


def _normalize_m2m_field(value):
    """Return list of ids from possible many2many form formats:
       - [(6, 0, [id1, id2])]
       - [id1, id2]
    """
    if not value:
        return []
    if isinstance(value, (list, tuple)) and value and isinstance(value[0], (list, tuple)):
        return value[0][2] if len(value[0]) > 2 else []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


class AccountingReport(models.TransientModel):
    _inherit = "accounting.report"

    # ------------------------------------------------------------------
    #  ANALYTIC FILTER FIELDS
    # ------------------------------------------------------------------
    analytic_filter = fields.Selection(
        [
            ('all', 'All Analytic Accounts'),
            ('selected', 'Selected Analytic Accounts'),
        ],
        string="Analytic Filter",
        default='all'
    )

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        string="Analytic Accounts"
    )

    show_analytic_breakdown = fields.Boolean(
        string="Show Breakdown by Analytic",
        help="If enabled, the report will split balances by analytic accounts."
    )

    include_combined = fields.Boolean(
        string='Show Combined Column',
        default=False,
        help='Show total column when multiple analytic accounts are selected.'
    )

    # ------------------------------------------------------------------
    #  ONCHANGE
    # ------------------------------------------------------------------
    @api.onchange('analytic_account_ids')
    def _onchange_analytic_account_ids(self):
        """Disable combined column when only one analytic is selected."""
        if len(self.analytic_account_ids) <= 1:
            self.include_combined = False

    # ------------------------------------------------------------------
    #  CONTEXT BUILDERS
    # ------------------------------------------------------------------
    def _build_contexts(self, data):
        result = super()._build_contexts(data)
        analytic_field = data.get('form', {}).get('analytic_account_ids', [])
        result['analytic_account_ids'] = _normalize_m2m_field(analytic_field)
        result['include_combined'] = data['form'].get('include_combined', False)
        return result

    def _build_comparison_context(self, data):
        result = super()._build_comparison_context(data)
        analytic_field = data.get('form', {}).get('analytic_account_ids', [])
        result['analytic_account_ids'] = _normalize_m2m_field(analytic_field)
        result['include_combined'] = data['form'].get('include_combined', False)
        return result

    # ------------------------------------------------------------------
    #  REPORT ACTION
    # ------------------------------------------------------------------
    def _print_report(self, data):
        """Inject analytic fields into report action."""
        try:
            vals = self.read([
                'date_from_cmp', 'debit_credit', 'date_to_cmp', 'filter_cmp',
                'account_report_id', 'enable_filter', 'label_filter', 'target_move',
            ])[0]
            data['form'].update(vals)
        except Exception:
            pass

        data['form'].update({
            'analytic_account_ids': [(6, 0, self.analytic_account_ids.ids)],
            'include_combined': bool(self.include_combined),
        })

        return self.env.ref(
            'accounting_pdf_reports.action_report_financial'
        ).report_action(self, data=data, config=False)
