# product_stock_ledger/controllers/main.py
from odoo import http, fields
from odoo.http import request
import urllib.parse

class ProductStockLedgerController(http.Controller):

    @http.route('/product_stock_ledger/ledger', type='http', auth='user', website=False)
    def ledger_view(self, **kwargs):
        """
        URL params expected: product_id, warehouse_id (optional), date_from, date_to
        Example: /product_stock_ledger/ledger?product_id=1&date_from=2025-01-01%2010:00:00&date_to=2025-01-31%2018:00:00
        """
        # Parse params
        product_id = int(kwargs.get('product_id') or 0)
        warehouse_id = int(kwargs.get('warehouse_id') or 0) if kwargs.get('warehouse_id') else False
        date_from = kwargs.get('date_from') or False
        date_to = kwargs.get('date_to') or False

        # Prepare data dict like wizard would
        data = {
            'product_id': product_id,
            'warehouse_id': warehouse_id,
            'date_from': date_from,
            'date_to': date_to,
        }

        # Use report model to prepare values (sudo to avoid access limitations)
        report_model = request.env['report.product_stock_ledger.product_stock_ledger_report'].sudo()
        try:
            rpt_vals = report_model._get_report_values(docids=[], data=data)
        except Exception:
            # Fallback: build minimal context to avoid server error
            rpt_vals = {
                'product': request.env['product.product'].sudo().browse(product_id),
                'lines': [],
                'total_rec': 0.0,
                'total_issue': 0.0,
                'data': data,
                'company': request.env.company.sudo(),
            }

        # You can add extra variables to context if needed
        context = {
            'product': rpt_vals.get('product'),
            'lines': rpt_vals.get('lines', []),
            'total_rec': rpt_vals.get('total_rec', 0.0),
            'total_issue': rpt_vals.get('total_issue', 0.0),
            'data': rpt_vals.get('data', data),
            'company': rpt_vals.get('company') or request.env.company.sudo(),
        }

        # Render QWeb template (template t-name should be product_stock_ledger.ledger_html_template)
        # Use request.render to honor QWeb and r/o environment
        return request.render('product_stock_ledger.ledger_html_template', context)
