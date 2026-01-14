# from odoo import models, fields, api
# from odoo.exceptions import UserError
#
# class AccountAssetDepreciationLine(models.Model):
#     _inherit = "account.asset.depreciation.line"
#
#     def action_post_depreciation(self):
#         for line in self:
#             if line.move_id:
#                 raise UserError("This depreciation is already posted.")
#
#             asset = line.asset_id
#             if not asset:
#                 raise UserError("Asset not found.")
#
#             move = self.env["account.move"].create({
#                 "date": line.depreciation_date,
#                 "journal_id": asset.journal_id.id,
#                 "line_ids": [
#                     (0, 0, {
#                         "name": asset.name,
#                         "account_id": asset.account_depreciation_expense_id.id,
#                         "debit": line.amount,
#                         "credit": 0.0,
#                     }),
#                     (0, 0, {
#                         "name": asset.name,
#                         "account_id": asset.account_depreciation_id.id,
#                         "debit": 0.0,
#                         "credit": line.amount,
#                     }),
#                 ],
#             })
#
#             move.action_post()
#             line.move_id = move.id
