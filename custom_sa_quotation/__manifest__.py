{
    'name': 'Custom Saudi Quotation',
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Custom Quotation Template for Saudi Format',
    'depends': ['sale'],
    'data': [
        'report/report.xml',
        'report/custom_quotation_template.xml',
        "report/report_footer.xml",

    ],
    'assets': {
        'web.report_assets_common': [
            '/custom_sa_quotation/static/src/fonts/NotoNaskhArabic-VariableFont_wght.ttf',
        ],
    },
    'installable': True,
    'application': False,
}
