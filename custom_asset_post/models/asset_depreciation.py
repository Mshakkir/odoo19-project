from odoo import models, fields, api
from odoo.exceptions import UserError


class AssetDepreciationLine(models.Model):
    _inherit = 'account.asset.depreciation.line'

    def action_post_depreciation(self):
        """
        Post the depreciation journal entry for this line instantly.
        """
        for line in self:
            # Check if already posted
            if line.move_check:
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
                line.move_check = True

        return True

    def action_unpost_depreciation(self):
        """
        Unpost the depreciation journal entry for this line.
        """
        for line in self:
            if not line.move_check:
                raise UserError(
                    f"Depreciation line dated {line.depreciation_date} "
                    f"is not posted."
                )

            if line.move_id and line.move_id.state == 'posted':
                try:
                    line.move_id.button_draft()
                    line.move_check = False
                except Exception as e:
                    raise UserError(
                        f"Cannot unpost entry: {str(e)}"
                    )

        return True