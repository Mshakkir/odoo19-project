{
    'name': 'Product Image Zoom',
    'version': '19.0.1.0.0',
    'summary': 'Click product image to open full-size zoomable lightbox',
    'category': 'Inventory',
    'author': 'Custom',
    'depends': ['product', 'stock'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'product_image_zoom/static/src/css/image_zoom.css',
            'product_image_zoom/static/src/js/image_zoom.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
