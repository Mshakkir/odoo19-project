from odoo import models

class AssetDepreciationLine(models.Model):
    _inherit = "account.asset.depreciation.line"

    def action_post_depreciation(self):
        """
        Post single depreciation entry
        """
        for line in self:
            if not line.move_id:
                line.create_move()
        return True
