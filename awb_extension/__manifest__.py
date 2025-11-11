{
    'name': 'AWB Extension',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Add Air Waybill Number in Delivery and Invoice',
    'depends': ['stock', 'account', 'sale'],
    'data': [
        'views/stock_picking_view.xml',
        'views/account_move_view.xml',
        'report/report_invoice_awb.xml',
    ],
    'installable': True,
    'application': False,
}
