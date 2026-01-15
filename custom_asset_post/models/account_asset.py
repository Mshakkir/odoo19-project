# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountAssetDepreciationLine(models.Model):
    _inherit = 'account.asset.depreciation.line'

    move_posted_check = fields.Boolean(
        string='Posted',
        compute='_compute_move_posted_check',
        store=True
    )

    @api.depends('move_id', 'move_id.state')
    def _compute_move_posted_check(self):
        """Check if the journal entry is posted"""
        for line in self:
            line.move_posted_check = bool(line.move_id and line.move_id.state == 'posted')

    def create_move(self):
        """Create and post the depreciation journal entry"""
        self.ensure_one()

        # Check if already posted
        if self.move_posted_check:
            raise UserError(_('This depreciation entry has already been posted.'))

        # Check if there's already a move
        if self.move_id:
            raise UserError(_('A journal entry already exists for this depreciation line.'))

        # Get the asset
        asset = self.asset_id

        # Prepare journal entry values
        move_vals = {
            'date': self.depreciation_date,
            'ref': asset.name + ' - ' + _('Depreciation'),
            'journal_id': asset.category_id.journal_id.id,
            'asset_id': asset.id,
            'line_ids': [],
        }

        # Depreciation expense line (Debit)
        expense_line = {
            'name': asset.name + ' - ' + _('Depreciation'),
            'account_id': asset.category_id.account_depreciation_expense_id.id,
            'debit': self.amount,
            'credit': 0.0,
            'asset_id': asset.id,
        }

        # Accumulated depreciation line (Credit)
        accumulated_line = {
            'name': asset.name + ' - ' + _('Depreciation'),
            'account_id': asset.category_id.account_depreciation_id.id,
            'debit': 0.0,
            'credit': self.amount,
            'asset_id': asset.id,
        }

        move_vals['line_ids'] = [(0, 0, expense_line), (0, 0, accumulated_line)]

        # Create the journal entry
        move = self.env['account.move'].create(move_vals)

        # Link the move to this depreciation line
        self.write({'move_id': move.id})

        # Post the journal entry
        move.action_post()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Entry'),
            'res_model': 'account.move',
            'res_id': move.id,
            'view_mode': 'form',
            'target': 'current',
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
                raise UserError(_('You cannot delete a posted depreciation entry. Cancel the journal entry first.'))
        return super(AccountAssetDepreciationLine, self).unlink()


class AccountAsset(models.Model):
    _inherit = 'account.asset.asset'

    def action_post_all_due_depreciation(self):
        """Post all due depreciation entries"""
        today = fields.Date.today()

        for asset in self:
            lines_to_post = asset.depreciation_line_ids.filtered(
                lambda x: x.depreciation_date <= today and not x.move_posted_check
            )

            for line in lines_to_post:
                line.create_move()

        return True