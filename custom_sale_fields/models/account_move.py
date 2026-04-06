from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    invoice_incoterm_id = fields.Many2one(
        'account.incoterms',
        string='Incoterm'
    )

    delivery_note_number = fields.Char(
        string='Delivery Note Number',
        help='Delivery note or dispatch number',
        copy=False
    )

    awb_number = fields.Char(
        string='Shipping Ref #',
        help='Air Waybill Number',
        copy=False
    )

    client_order_ref = fields.Char(
        string='PO/Reference #',
        help='PO/Reference...',
        copy=False
    )

    # ── Manual Currency Rate (transferred from Sale Order) ───────────────────
    manual_currency_rate = fields.Float(
        string='Currency Rate',
        digits=(12, 6),
        store=True,
        copy=False,
        help='Exchange rate: how many company currency = 1 invoice currency.',
    )

    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Company Currency',
        store=False,
        readonly=True,
    )

    amount_total_company_currency = fields.Monetary(
        string='Total in Company Currency',
        compute='_compute_amount_total_company_currency',
        store=True,
        currency_field='company_currency_id',
    )

    currency_rate_prefix = fields.Char(
        compute='_compute_currency_rate_affixes',
        store=False,
    )
    currency_rate_suffix = fields.Char(
        compute='_compute_currency_rate_affixes',
        store=False,
    )

    # ── Compute Prefix/Suffix Labels ─────────────────────────────────────────
    @api.depends('currency_id', 'company_id')
    def _compute_currency_rate_affixes(self):
        for move in self:
            company_currency = move.company_id.currency_id
            inv_currency = move.currency_id
            if inv_currency and company_currency and inv_currency != company_currency:
                move.currency_rate_prefix = "1 %s =" % inv_currency.name
                move.currency_rate_suffix = company_currency.name
            else:
                move.currency_rate_prefix = ""
                move.currency_rate_suffix = ""

    # ── Compute Total in Company Currency ────────────────────────────────────
    @api.depends('amount_total', 'manual_currency_rate', 'currency_id', 'company_id')
    def _compute_amount_total_company_currency(self):
        for move in self:
            company_currency = move.company_id.currency_id
            inv_currency = move.currency_id
            if inv_currency and company_currency and inv_currency != company_currency:
                rate = move.manual_currency_rate
                if not rate:
                    # fallback to system rate
                    rate_date = move.invoice_date or fields.Date.today()
                    rate_record = move.env['res.currency.rate'].search([
                        ('currency_id', '=', inv_currency.id),
                        ('company_id', '=', move.company_id.id),
                        ('name', '<=', str(rate_date)),
                    ], order='name desc', limit=1)
                    if rate_record and rate_record.inverse_company_rate:
                        rate = rate_record.inverse_company_rate
                    else:
                        rate = 1.0
                move.amount_total_company_currency = move.amount_total * rate
            else:
                move.amount_total_company_currency = move.amount_total

    # ── Auto-fill rate label when currency changes ───────────────────────────
    @api.onchange('currency_id', 'invoice_date')
    def _onchange_invoice_currency_rate(self):
        for move in self:
            company_currency = move.company_id.currency_id
            inv_currency = move.currency_id
            # Only auto-fill if no manual rate already set
            if inv_currency and company_currency and inv_currency != company_currency:
                if not move.manual_currency_rate:
                    rate_date = move.invoice_date or fields.Date.today()
                    rate_record = move.env['res.currency.rate'].search([
                        ('currency_id', '=', inv_currency.id),
                        ('company_id', '=', move.company_id.id),
                        ('name', '<=', str(rate_date)),
                    ], order='name desc', limit=1)
                    if rate_record and rate_record.inverse_company_rate:
                        move.manual_currency_rate = rate_record.inverse_company_rate

    @api.onchange('invoice_origin')
    def _onchange_invoice_origin_client_order_ref(self):
        """Auto-populate client_order_ref from the related sale order"""
        if not self.invoice_origin:
            return
        sale_order = self.env['sale.order'].search(
            [('name', '=', self.invoice_origin)],
            limit=1
        )
        if sale_order and sale_order.client_order_ref:
            self.client_order_ref = sale_order.client_order_ref

    def _reverse_moves(self, default_values_list=None, cancel=False):
        """Override to copy custom fields to credit notes"""
        reverse_moves = super(AccountMove, self)._reverse_moves(
            default_values_list=default_values_list,
            cancel=cancel
        )
        for move, reverse_move in zip(self, reverse_moves):
            if move.delivery_note_number:
                reverse_move.delivery_note_number = move.delivery_note_number
            if move.awb_number:
                reverse_move.awb_number = move.awb_number
            if move.client_order_ref:
                reverse_move.client_order_ref = move.client_order_ref
            if move.manual_currency_rate:
                reverse_move.manual_currency_rate = move.manual_currency_rate
        return reverse_moves
