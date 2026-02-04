{
    'name': 'Sale AWB Field',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Add AWB Number field to Sales and Invoices',
    'description': """
        Add Air Waybill (AWB) Number Field
        ===================================

        * Adds AWB Number field to Sale Orders
        * Adds AWB Number field to Invoices
        * Adds AWB Number field to Delivery Orders
        * Auto-transfers AWB from Sale Order to Invoice/Delivery
    """,
    'author': 'Your Name',
    'depends': [
        'sale_management',
        'account',       # ← added, required for stock.picking
    ],
    'data': [
        'security/ir.model.access.csv',
        # 'views/sale_order_views.xml',      # ← was missing entirely
        # 'views/account_move_views.xml',    # ← was commented out
        'views/stock_picking_view.xml',
    ],                                     # ← 'views/templates.xml' removed
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}