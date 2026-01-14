from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class AssetDepreciationLine(models.Model):
    _inherit = 'account.asset.depreciation.line'  # OdooMates model name

    def action_post_depreciation(self):
        """
        Post the depreciation journal entry for this line.
        This method is called when the Post button is clicked.
        """
        for line in self:
            # Check if already posted
            if line.move_id and line.move_id.state == 'posted':
                raise UserError(
                    f"Depreciation line dated {line.depreciation_date} "
                    f"is already posted."
                )

            # Check if move exists
            if not line.move_id:
                raise UserError(
                    f"No journal entry found for depreciation line dated "
                    f"{line.depreciation_date}. Please compute depreciation first."
                )

            # Post the journal entry
            if line.move_id.state == 'draft':
                line.move_id.action_post()

            # Refresh the parent asset's residual value
            if line.asset_id:
                line.asset_id._compute_depreciation()

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_unpost_depreciation(self):
        """
        Unpost the depreciation journal entry for this line.
        """
        for line in self:
            if not line.move_id or line.move_id.state != 'posted':
                raise UserError(
                    f"Depreciation line dated {line.depreciation_date} "
                    f"is not posted or has no entry."
                )

            if line.move_id:
                try:
                    line.move_id.button_draft()
                except Exception as e:
                    raise UserError(
                        f"Cannot unpost entry: {str(e)}"
                    )

            # Refresh the parent asset's residual value
            if line.asset_id:
                line.asset_id._compute_depreciation()

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }