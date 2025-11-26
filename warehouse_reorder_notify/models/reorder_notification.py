from odoo import models, fields

class ReorderNotification(models.Model):
    _name = "reorder.notification"
    _description = "Reorder Notification"
    _order = "id desc"

    product_id = fields.Many2one('product.product', string="Product", required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse", required=True)
    qty_available = fields.Float(string="Quantity On Hand")
    min_qty = fields.Float(string="Minimum Quantity")
    date_notified = fields.Datetime(string="Notified On", default=fields.Datetime.now)
    processed = fields.Boolean(string="Processed", default=False)









# from odoo import models, fields, api
#
# class ReorderNotification(models.Model):
#     _name = 'reorder.notification'
#     _description = 'Reorder Notification'
#     _order = 'create_date desc'
#
#     product_id = fields.Many2one('product.product', string='Product')
#     warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
#     qty_on_hand = fields.Float('On Hand Qty')
#     min_qty = fields.Float('Minimum Qty')
#     state = fields.Selection([
#         ('new', 'New'),
#         ('read', 'Read'),
#     ], default='new')
#
#     user_id = fields.Many2one('res.users', string='Assigned To')
