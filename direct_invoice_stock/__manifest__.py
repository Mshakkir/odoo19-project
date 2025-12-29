# {
#     'name': 'Direct Invoice with Stock Move',
#     'version': '19.0.1.0.0',
#     'category': 'Sales/Accounting',
#     'summary': 'Create automatic delivery orders from invoices for counter sales',
#     'description': """
#         Direct Invoice with Stock Move
#         ================================
#         This module allows you to create invoices directly for walk-in customers
#         and automatically updates inventory by creating and validating delivery orders.
#
#         Features:
#         ---------
#         * Create invoice directly without sales order
#         * Automatic delivery order creation on invoice validation
#         * Automatic stock move and inventory update
#         * Proper traceability between invoice and delivery
#         * Works with stockable products only
#     """,
#     'author': 'Your Company',
#     'website': 'https://www.yourcompany.com',
#     'depends': ['account', 'stock', 'sale'],
#     'data': [
#         'views/account_move_views.xml',
#     ],
#     'installable': True,
#     'application': False,
#     'auto_install': False,
#     'license': 'LGPL-3',
# }
{
    'name': 'Direct Invoice with Stock Move',
    'version': '19.0.2.0.0',  # Updated version
    'category': 'Sales/Accounting',
    'summary': 'Create automatic delivery orders from invoices with stock protection',
    'description': """
        Direct Invoice with Stock Move - Enhanced Edition
        ===================================================
        Create invoices directly for walk-in customers and automatically 
        update inventory by creating and validating delivery orders.

        Features:
        ---------
        ✓ Create invoice directly without sales order
        ✓ Automatic delivery order creation on invoice validation
        ✓ Automatic stock move and inventory update
        ✓ Credit note support with automatic stock returns
        ✓ Stock availability checking with warnings
        ✓ Prevents invoice cancellation when stock already moved
        ✓ Manager override for negative stock situations
        ✓ Proper traceability between invoice and delivery
        ✓ Works with stockable products only
        ✓ Warehouse auto-detection from analytic accounts

        Safety Features:
        ----------------
        🔒 Invoice Cancellation Protection
           - Prevents cancellation if stock already moved
           - Auto-removes unvalidated deliveries on cancel
           - Guides users to proper refund process

        🔄 Credit Note Handling
           - Automatically creates stock returns
           - Returns products back to warehouse
           - Maintains inventory accuracy

        ⚠️ Stock Availability Checking
           - Warns about insufficient stock
           - Blocks regular users from negative stock
           - Allows managers to override with warnings
           - Real-time stock validation

        Version History:
        ---------------
        v19.0.2.0.0 - Added all safety features (cancellation, returns, stock warnings)
        v19.0.1.0.0 - Initial release with basic delivery creation

        Requirements:
        ------------
        - Odoo 19 Community Edition
        - Stock/Inventory module
        - Account/Invoicing module

        Support:
        -------
        For issues or questions, contact your system administrator.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'account',
        'stock',
        'sale',
    ],
    'data': [
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}