{
    'name': 'Product Image Zoom',
    'version': '19.0.1.0.0',
    'summary': 'Adds zoom popup functionality to product images in inventory',
    'description': """
        Clicking the product image on the product form opens a full-size
        lightbox popup with pinch/scroll zoom and pan support.
    """,
    'category': 'Inventory',
    'author': 'Custom',
    'depends': ['product', 'stock'],
    'data': [
        'views/product_template_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'product_image_zoom/static/src/css/image_zoom.css',
            'product_image_zoom/static/src/js/image_zoom_widget.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
