from odoo import http
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request


class WebsiteProducts(WebsiteSale):

    @http.route(['/shop', '/shop/page/<int:page>'], type='http', auth="public", website=True, sitemap=True)
    def shop(self, page=0, category=None, search='', min_price=0.0, max_price=None, ppg=False, **post):
        """Override shop method to add custom logic"""
        # Get parent implementation
        response = super().shop(
            page=page,
            category=category,
            search=search,
            min_price=min_price,
            max_price=max_price,
            ppg=ppg,
            **post
        )

        # Add custom data to context
        if hasattr(response, 'qcontext'):
            products = response.qcontext.get('products', [])

            # Add inventory status to each product
            for product in products:
                product.inventory_status = product.get_inventory_status()

            response.qcontext['custom_products'] = True

        return response

    @http.route(['/product/<model("product.template"):product>'], type='http', auth="public", website=True,
                sitemap=True)
    def product(self, product, category='', search='', **kwargs):
        """Override product detail page"""
        response = super().product(product, category=category, search=search, **kwargs)

        if hasattr(response, 'qcontext'):
            # Add inventory info
            response.qcontext['product_qty'] = product.qty_available
            response.qcontext['product_status'] = product.get_inventory_status()
            response.qcontext['warehouse_stock'] = self._get_warehouse_stock(product)

        return response

    def _get_warehouse_stock(self, product):
        """Get stock by warehouse"""
        warehouses = request.env['stock.warehouse'].search([])
        stock_by_warehouse = {}

        for warehouse in warehouses:
            stock_qty = product.with_context(warehouse=warehouse.id).qty_available
            stock_by_warehouse[warehouse.name] = stock_qty

        return stock_by_warehouse