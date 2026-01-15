# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountAssetDepreciationLine(models.Model):
    _inherit = 'account.asset.depreciation.line'

    move_posted_check = fields.Boolean(
        string='Posted',
        compute='_compute_move_posted_check',
        store=True,
        help="Indicates if the depreciation entry has been posted"
    )

    @api.depends('move_id', 'move_id.state')
    def _compute_move_posted_check(self):
        """Check if the journal entry is posted"""
        for line in self:
            line.move_posted_check = bool(line.move_id and line.move_id.state == 'posted')

    def create_move(self):
        """Create and post the depreciation journal entry"""
        for line in self:
            # Check if already posted
            if line.move_posted_check:
                raise UserError(_('This depreciation entry has already been posted.'))

            # Check if there's already a move
            if line.move_id:
                raise UserError(_('A journal entry already exists for this depreciation line.'))

            # Get the asset
            asset = line.asset_id

            if not asset:
                raise UserError(_('No asset linked to this depreciation line.'))

            # Get category
            category = asset.category_id

            if not category:
                raise UserError(_('Asset category is not defined.'))

            # Check required accounts
            if not category.account_depreciation_expense_id:
                raise UserError(_('Depreciation Expense Account is not configured in asset category.'))

            if not category.account_depreciation_id:
                raise UserError(_('Accumulated Depreciation Account is not configured in asset category.'))

            if not category.journal_id:
                raise UserError(_('Journal is not configured in asset category.'))

            # Prepare account.move.line values
            debit_vals = {
                'name': asset.name,
                'account_id': category.account_depreciation_expense_id.id,
                'debit': line.amount,
                'credit': 0.0,
                'partner_id': asset.partner_id.id if asset.partner_id else False,
            }

            credit_vals = {
                'name': asset.name,
                'account_id': category.account_depreciation_id.id,
                'debit': 0.0,
                'credit': line.amount,
                'partner_id': asset.partner_id.id if asset.partner_id else False,
            }

            # Add analytic distribution if exists
            if hasattr(asset, 'analytic_distribution') and asset.analytic_distribution:
                debit_vals['analytic_distribution'] = asset.analytic_distribution
                credit_vals['analytic_distribution'] = asset.analytic_distribution

            # Prepare journal entry values
            move_vals = {
                'ref': asset.name,
                'date': line.depreciation_date,
                'journal_id': category.journal_id.id,
                'line_ids': [
                    (0, 0, debit_vals),
                    (0, 0, credit_vals),
                ],
            }

            # Create the journal entry
            move = self.env['account.move'].sudo().create(move_vals)

            # Link the move to this depreciation line
            line.write({'move_id': move.id})

            # Post the journal entry
            if move.state == 'draft':
                move.action_post()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Depreciation entry posted successfully!'),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def view_move(self):
        """View the related journal entry"""
        self.ensure_one()
        if not self.move_id:
            raise UserError(_('No journal entry exists for this depreciation line.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Entry'),
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def unlink(self):
        """Prevent deletion of posted entries"""
        for line in self:
            if line.move_posted_check:
                raise UserError(
                    _('You cannot delete a posted depreciation entry. Reset the journal entry to draft first.'))
        return super(AccountAssetDepreciationLine, self).unlink()


class AccountAsset(models.Model):
    _inherit = 'account.asset.asset'

    def action_post_all_due_depreciation(self):
        """Post all due depreciation entries for this asset"""
        today = fields.Date.today()

        lines_to_post = self.depreciation_line_ids.filtered(
            lambda x: x.depreciation_date <= today and not x.move_posted_check and not x.move_id
        )

        if not lines_to_post:
            raise UserError(_('No depreciation entries are due for posting.'))

        posted_count = 0
        for line in lines_to_post:
            try:
                line.create_move()
                posted_count += 1
            except Exception as e:
                raise UserError(_('Error posting depreciation line dated %s:\n%s') % (line.depreciation_date, str(e)))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('%s depreciation entries posted successfully!') % posted_count,
                'type': 'success',
                'sticky': False,
            }
        }