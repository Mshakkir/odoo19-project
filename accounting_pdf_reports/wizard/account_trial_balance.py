# from odoo import fields, models, api
#
#
# class AccountBalanceReport(models.TransientModel):
#     _name = 'account.balance.report'
#     _inherit = "account.common.account.report"
#     _description = 'Trial Balance Report'
#
#     journal_ids = fields.Many2many(
#         'account.journal', 'account_balance_report_journal_rel',
#         'account_id', 'journal_id',
#         string='Journals', required=True, default=[]
#     )
#     analytic_account_ids = fields.Many2many(
#         'account.analytic.account',
#         'account_trial_balance_analytic_rel', string='Analytic Accounts'
#     )
#
#     def _get_report_data(self, data):
#         data = self.pre_print_report(data)
#         records = self.env[data['model']].browse(data.get('ids', []))
#         return records, data
#
#     def _print_report(self, data):
#         records, data = self._get_report_data(data)
#         return self.env.ref('accounting_pdf_reports.action_report_trial_balance').report_action(records, data=data)
from lxml import etree
from odoo import api, fields, models


class AccountBalanceReport(models.TransientModel):
    _name = 'account.balance.report'
    _inherit = "account.common.account.report"
    _description = 'Trial Balance Report'

    journal_ids = fields.Many2many(
        'account.journal', 'account_balance_report_journal_rel',
        'account_id', 'journal_id',
        string='Journals', required=True, default=[]
    )
    analytic_account_ids = fields.Many2many(
        'account.analytic.account',
        'account_trial_balance_analytic_rel', string='Analytic Accounts'
    )

    # ---------- NEW PART ----------
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """Dynamically modify the wizard view so the Journals field
        shows journals from *all* companies the user is allowed to access."""
        res = super().fields_view_get(view_id=view_id, view_type=view_type,
                                      toolbar=toolbar, submenu=submenu)
        if view_type == 'form' and res.get('arch'):
            doc = etree.XML(res['arch'])
            # Collect allowed company IDs for the current user
            allowed_company_ids = self.env.companies.ids or \
                self.env['res.company'].search([]).ids
            # Build a safe domain string
            domain = "[('company_id', 'in', %s)]" % (allowed_company_ids,)
            for node in doc.xpath("//field[@name='journal_ids']"):
                node.set('domain', domain)
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res
    # ---------- END NEW PART ----------

    def _get_report_data(self, data):
        data = self.pre_print_report(data)
        records = self.env[data['model']].browse(data.get('ids', []))
        return records, data

    def _print_report(self, data):
        records, data = self._get_report_data(data)
        return self.env.ref('accounting_pdf_reports.action_report_trial_balance').report_action(records, data=data)
