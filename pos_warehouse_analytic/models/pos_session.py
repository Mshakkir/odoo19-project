# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PosSession(models.Model):
    _inherit = 'pos.session'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        required=True,
        readonly=True,
        states={'opening_control': [('readonly', False)]},
        help='Warehouse for this POS session. All transactions will be linked to this warehouse.'
    )

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        readonly=True,
        states={'opening_control': [('readonly', False)]},
        help='Analytic account for tracking transactions from this session.'
    )

    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        """Auto-populate analytic account based on warehouse name"""
        if self.warehouse_id:
            # Search for analytic account with same name as warehouse
            analytic = self.env['account.analytic.account'].search([
                ('name', '=', self.warehouse_id.name)
            ], limit=1)

            if analytic:
                self.analytic_account_id = analytic.id
            else:
                # If no matching analytic account, clear the field
                self.analytic_account_id = False
                return {
                    'warning': {
                        'title': _('No Analytic Account Found'),
                        'message': _(
                            'No analytic account found with name "%s". '
                            'Please create one or select manually.'
                        ) % self.warehouse_id.name
                    }
                }

    @api.model
    def create(self, vals):
        """Set default warehouse from POS config if not provided"""
        if 'warehouse_id' not in vals or not vals.get('warehouse_id'):
            config_id = vals.get('config_id')
            if config_id:
                config = self.env['pos.config'].browse(config_id)
                if config.warehouse_id:
                    vals['warehouse_id'] = config.warehouse_id.id
                    # Auto-set analytic account
                    analytic = self.env['account.analytic.account'].search([
                        ('name', '=', config.warehouse_id.name)
                    ], limit=1)
                    if analytic:
                        vals['analytic_account_id'] = analytic.id

        return super(PosSession, self).create(vals)

    @api.constrains('warehouse_id')
    def _check_warehouse_id(self):
        """Ensure warehouse is selected before opening session"""
        for session in self:
            if session.state != 'opening_control' and not session.warehouse_id:
                raise ValidationError(_('Please select a warehouse before opening the session.'))