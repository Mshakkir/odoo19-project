{
    'name': 'Direct Purchase with Stock Move',
    'version': '19.0.1.0.0',
    'category': 'Purchases/Accounting',
    'summary': 'Create automatic receipts from vendor bills for direct purchases',
    'description': """
        Direct Purchase with Stock Move
        =================================
        Create vendor bills directly and automatically update inventory 
        by creating and validating stock receipts.

        Features:
        ---------
        ✅ Create vendor bills directly without purchase orders
        ✅ Automatic receipt creation on bill validation
        ✅ Automatic stock receipt and inventory update
        ✅ Refund support with automatic returns to vendor
        ✅ Stock validation and overstocking warnings
        ✅ Prevents bill cancellation when stock already received
        ✅ Manager override for stock issues
        ✅ Proper traceability between bill and receipt
        ✅ Works with stockable products only
        ✅ Warehouse auto-detection from analytic accounts

        Safety Features:
        ----------------
        🔒 Bill Cancellation Protection
           - Prevents cancellation if stock already received
           - Auto-removes unvalidated receipts on cancel
           - Guides users to proper refund process

        🔄 Refund Handling
           - Automatically creates returns to vendor
           - Removes products from warehouse
           - Maintains inventory accuracy

        ⚠️ Stock Validation
           - Real-time validation
           - Manager notifications for issues
           - Maintains data integrity

        Use Cases:
        ----------
        - Walk-in vendor purchases
        - Cash purchases without formal POs
        - Emergency purchases
        - Small vendor transactions
        - Counter purchases

        Requirements:
        ------------
        - Odoo 19 Community Edition
        - Stock/Inventory module
        - Account/Invoicing module
        - Purchase module (for purchase-related dependencies)

        Compatibility:
        -------------
        Works alongside:
        - Standard Odoo Purchase module
        - Direct Invoice with Stock Move module
        - Third-party accounting modules (like Odoo Mates)

        Support:
        -------
        For issues or questions, contact your system administrator.
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'account',
        'stock',
        'purchase',  # For purchase-related fields/context
    ],
    'data': [
        'views/account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}