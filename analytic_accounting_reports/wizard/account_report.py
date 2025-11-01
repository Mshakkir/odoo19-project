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

    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        'accounting_report_analytic_rel',
        'report_id',
        'analytic_id',
        string='Warehouses',
        help='Select one or more warehouses. Leave empty to include all warehouses.'
    )

    include_combined = fields.Boolean(
        string='Show Combined Column',
        default=False,
        help='When multiple warehouses are selected, show a combined total column'
    )

    @api.onchange('analytic_account_ids')
    def _onchange_analytic_account_ids(self):
        if len(self.analytic_account_ids) <= 1:
            self.include_combined = False

    def _build_contexts(self, data):
        result = super(AccountingReport, self)._build_contexts(data)
        analytic_field = data.get('form', {}).get('analytic_account_ids', [])
        analytic_ids = _normalize_m2m_field(analytic_field)
        result['analytic_account_ids'] = analytic_ids or []
        result['include_combined'] = data.get('form', {}).get('include_combined', False)
        return result

    def _build_comparison_context(self, data):
        result = super(AccountingReport, self)._build_comparison_context(data)
        analytic_field = data.get('form', {}).get('analytic_account_ids', [])
        analytic_ids = _normalize_m2m_field(analytic_field)
        result['analytic_account_ids'] = analytic_ids or []
        result['include_combined'] = data.get('form', {}).get('include_combined', False)
        return result

    def _print_report(self, data):
        """Pass analytic selections safely into the report action.

        Some parent wizards may not have the same fields available via .read([...]).
        So we try to read the parent fields but always update analytic keys explicitly.
        """
        # try to read parent fields (best-effort)
        try:
            vals = self.read([
                'date_from_cmp', 'debit_credit', 'date_to_cmp', 'filter_cmp',
                'account_report_id', 'enable_filter', 'label_filter', 'target_move',
            ])[0]
            data['form'].update(vals)
        except Exception:
            # ignore — we'll pass analytic fields explicitly below
            pass

        # ensure analytic fields are in the form in canonical many2many command form
        data['form'].update({
            'analytic_account_ids': [(6, 0, self.analytic_account_ids.ids)],
            'include_combined': bool(self.include_combined),
        })
        return self.env.ref('accounting_pdf_reports.action_report_financial').report_action(
            self, data=data, config=False)
