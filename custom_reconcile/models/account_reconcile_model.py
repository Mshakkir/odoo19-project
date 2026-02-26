# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountReconcileModel(models.Model):
    """
    Custom Reconciliation Rules/Models.
    Defines automatic matching rules for bank transactions.
    """
    _name = 'custom.reconcile.model'
    _description = 'Custom Reconciliation Model'
    _order = 'sequence, id'

    # ─── Basic Info ───────────────────────────────────────────────────────────
    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one(
        'res.company', string='Company',
        required=True, default=lambda self: self.env.company
    )

    # ─── Rule Type ────────────────────────────────────────────────────────────
    rule_type = fields.Selection([
        ('writeoff_button', 'Write-off Button'),
        ('writeoff_suggestion', 'Suggest Counterpart Values'),
        ('invoice_matching', 'Match Existing Invoices/Bills'),
    ], string='Type', required=True, default='invoice_matching')

    # ─── Matching Criteria ───────────────────────────────────────────────────
    match_journal_ids = fields.Many2many(
        'account.journal',
        string='Journals Availability',
        help='Restrict this rule to specific bank journals. Leave empty for all.'
    )
    match_nature = fields.Selection([
        ('amount_received', 'Amount Received'),
        ('amount_paid', 'Amount Paid'),
        ('both', 'Amount Paid/Received'),
    ], string='Amount Type', default='both')

    match_amount = fields.Selection([
        ('lower', 'Is Lower Than'),
        ('greater', 'Is Greater Than'),
        ('between', 'Is Between'),
    ], string='Amount Condition')
    match_amount_min = fields.Float(string='Amount Min')
    match_amount_max = fields.Float(string='Amount Max')

    match_label = fields.Selection([
        ('contains', 'Contains'),
        ('not_contains', 'Not Contains'),
        ('match_regex', 'Match Regex'),
    ], string='Label')
    match_label_param = fields.Char(string='Label Parameter')

    match_partner = fields.Boolean(string='Partner Is Set')
    match_partner_ids = fields.Many2many(
        'res.partner', string='Specific Partners',
        help='Match only with these partners'
    )
    match_partner_category_ids = fields.Many2many(
        'res.partner.category', string='Partner Categories'
    )

    # ─── Write-off / Suggestion Fields ───────────────────────────────────────
    line_ids = fields.One2many(
        'custom.reconcile.model.line', 'model_id',
        string='Write-off Lines'
    )

    # ─── Invoice Matching Options ─────────────────────────────────────────────
    allow_payment_tolerance = fields.Boolean(
        string='Payment Tolerance', default=True,
        help='Allow small differences to be written off automatically'
    )
    payment_tolerance_param = fields.Float(
        string='Tolerance (%)', default=0.0,
        help='Maximum percentage difference allowed for auto write-off'
    )
    past_months_limit = fields.Integer(
        string='Months Limit', default=0,
        help='Only match invoices within this many months. 0 = no limit.'
    )
    matching_order = fields.Selection([
        ('old_first', 'Oldest First'),
        ('new_first', 'Newest First'),
    ], string='Matching Order', default='old_first')

    # ─── Auto Reconcile ──────────────────────────────────────────────────────
    auto_reconcile = fields.Boolean(
        string='Auto Validate', default=False,
        help='Automatically reconcile if this rule matches perfectly'
    )

    # ─── Computed ────────────────────────────────────────────────────────────
    number_entries = fields.Integer(
        string='Entries Matched',
        compute='_compute_number_entries'
    )

    @api.depends('name')
    def _compute_number_entries(self):
        for rec in self:
            rec.number_entries = self.env['custom.reconcile.history'].search_count([
                ('model_id', '=', rec.id)
            ])

    def action_reconcile_history(self):
        """Open reconciliation history for this model."""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reconciliation History'),
            'res_model': 'custom.reconcile.history',
            'view_mode': 'list,form',
            'domain': [('model_id', '=', self.id)],
        }

    @api.constrains('payment_tolerance_param')
    def _check_tolerance(self):
        for rec in self:
            if rec.payment_tolerance_param < 0 or rec.payment_tolerance_param > 100:
                raise ValidationError(_('Tolerance must be between 0 and 100.'))


class AccountReconcileModelLine(models.Model):
    """Write-off lines for reconciliation models."""
    _name = 'custom.reconcile.model.line'
    _description = 'Reconcile Model Write-off Line'

    model_id = fields.Many2one(
        'custom.reconcile.model', string='Model',
        required=True, ondelete='cascade'
    )
    sequence = fields.Integer(string='Sequence', default=10)

    account_id = fields.Many2one(
        'account.account', string='Account',
        required=True,
        domain=[('deprecated', '=', False)]
    )
    journal_id = fields.Many2one(
        'account.journal', string='Journal'
    )
    label = fields.Char(string='Journal Item Label')
    amount_type = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage of Balance'),
        ('percentage_st_line', 'Percentage of Statement Line'),
        ('regex', 'From Label (regex)'),
    ], string='Amount Type', default='percentage', required=True)
    amount = fields.Float(string='Amount', default=100.0)
    amount_string = fields.Char(string='Amount from Regex')
    force_tax_included = fields.Boolean(string='Tax Included in Price')
    tax_ids = fields.Many2many('account.tax', string='Taxes')
    analytic_distribution = fields.Json(string='Analytic')
    company_id = fields.Many2one(
        related='model_id.company_id', store=True
    )


class AccountReconcileHistory(models.Model):
    """Tracks which model was used for each reconciliation."""
    _name = 'custom.reconcile.history'
    _description = 'Reconcile History'
    _order = 'date desc'

    model_id = fields.Many2one(
        'custom.reconcile.model', string='Rule Used',
        ondelete='set null'
    )
    date = fields.Date(string='Date', default=fields.Date.today)
    company_id = fields.Many2one('res.company', string='Company')
    statement_line_id = fields.Many2one(
        'account.bank.statement.line', string='Bank Statement Line'
    )
    reconciled_amount = fields.Monetary(
        string='Reconciled Amount', currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id
    )
    state = fields.Selection([
        ('reconciled', 'Reconciled'),
        ('unreconciled', 'Unreconciled'),
    ], string='Status', default='reconciled')