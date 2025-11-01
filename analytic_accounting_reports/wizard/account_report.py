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
        # command format
        return value[0][2] if len(value[0]) > 2 else []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


class AccountingReport(models.TransientModel):
    _inherit = "accounting.report"

    # ------------------------------------------------------------------
    #  CUSTOM ANALYTIC FILTER FIELDS
    # ------------------------------------------------------------------
    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        'accounting_report_analytic_rel',
        'report_id',
        'analytic_id',
        string='Warehouses / Analytic Accounts',
        help='Select one or more warehouses/analytic accounts. '
             'Leave empty to include all.'
    )

    include_combined = fields.Boolean(
        string='Show Combined Column',
        default=False,
        help='When multiple analytic accounts are selected, show a total column.'
    )

    # ------------------------------------------------------------------
    #  REQUIRED STUB FIELD (fixes view error "Field analytic_filter does not exist")
    #  You can later convert it into a real field if needed.
    # ------------------------------------------------------------------
    analytic_filter = fields.Boolean(
        string='Analytic Filter',
        default=False,
        help="(Technical field) Added to avoid view error in inherited wizard."
    )
    show_analytic_breakdown = fields.Boolean(
        string='Show Analytic Breakdown',
        default=False,
        help="(Technical placeholder) Added because the XML view expects this field."
    )

    # ------------------------------------------------------------------
    #  ONCHANGE BEHAVIOUR
    # ------------------------------------------------------------------
    @api.onchange('analytic_account_ids')
    def _onchange_analytic_account_ids(self):
        if len(self.analytic_account_ids) <= 1:
            self.include_combined = False

    # ------------------------------------------------------------------
    #  BUILD CONTEXTS
    # ------------------------------------------------------------------
    def _build_contexts(self, data):
        result = super()._build_contexts(data)
        analytic_field = data.get('form', {}).get('analytic_account_ids', [])
        analytic_ids = _normalize_m2m_field(analytic_field)
        result['analytic_account_ids'] = analytic_ids or []
        result['include_combined'] = data.get('form', {}).get('include_combined', False)
        return result

    def _build_comparison_context(self, data):
        result = super()._build_comparison_context(data)
        analytic_field = data.get('form', {}).get('analytic_account_ids', [])
        analytic_ids = _normalize_m2m_field(analytic_field)
        result['analytic_account_ids'] = analytic_ids or []
        result['include_combined'] = data.get('form', {}).get('include_combined', False)
        return result

    # ------------------------------------------------------------------
    #  PRINT REPORT
    # ------------------------------------------------------------------
    def _print_report(self, data):
        """Inject analytic selections into the report call."""
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
