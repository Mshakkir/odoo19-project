{
    'name': 'Stock Final Location Fix',
    'version': '19.0.1.0.0',
    'summary': 'Forces stock moves to respect the Final Location (location_final_id) field on validation',
    'description': """
        When validating a receipt/transfer, this module overrides the 
        destination location (location_dest_id) with the Final Location 
        (location_final_id) if it is set on the stock move.
    """,
    'author': 'Custom',
    'category': 'Inventory',
    'depends': ['stock'],
    'data': [],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}