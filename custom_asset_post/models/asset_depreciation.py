from odoo import models

class AccountAssetDepreciationLine(models.Model):
    _inherit = "account.asset.depreciation.line"

    def action_post_depreciation(self):
        for line in self:
            if line.move_id:
                continue
            line._create_move()
            line.move_id.action_post()
