from odoo import http
from odoo.addons.website.controllers.website import Website
from odoo.http import request


class WebsiteProducts(Website):
    """Extended Website controller for Products page"""

    @http.route('/website/products', type='http', auth='public', website=True)
    def products_page(self, **kwargs):
        """Display products with inventory details"""

        # Get all published products from product.product model
        Product = request.env['product.product'].sudo()
        products = Product.search([
            ('website_published', '=', True),
            ('sale_ok', '=', True)
        ], order='name ASC')

        # Enrich products with inventory data
        products_data = []
        for product in products:
            # Get stock data from stock.quant
            quants = request.env['stock.quant'].sudo().search([
                ('product_id', '=', product.id),
                ('location_id.usage', '=', 'internal')
            ])

            # Calculate inventory metrics
            qty_available = sum(quants.mapped('quantity'))
            reserved_qty = sum(quants.mapped('reserved_quantity'))

            # Get incoming and outgoing quantities from stock moves
            incoming_moves = request.env['stock.move'].sudo().search([
                ('product_id', '=', product.id),
                ('location_dest_id.usage', '=', 'internal'),
                ('state', 'in', ['confirmed', 'partially_available', 'assigned'])
            ])
            incoming_qty = sum(incoming_moves.mapped('product_qty'))

            outgoing_moves = request.env['stock.move'].sudo().search([
                ('product_id', '=', product.id),
                ('location_id.usage', '=', 'internal'),
                ('location_dest_id.usage', '!=', 'internal'),
                ('state', 'in', ['confirmed', 'partially_available', 'assigned'])
            ])
            outgoing_qty = sum(outgoing_moves.mapped('product_qty'))

            products_data.append({
                'id': product.id,
                'name': product.name,
                'description': product.description_sale or product.description,
                'list_price': product.list_price,
                'image_1920': product.image_1920,
                'qty_available': qty_available,
                'reserved_quantity': reserved_qty,
                'incoming_qty': incoming_qty,
                'outgoing_qty': outgoing_qty,
                'product_obj': product
            })

        # Prepare values for template
        values = {
            'products': products_data,
            'products_count': len(products_data)
        }

        return request.render('website.website_products', values)

    @http.route('/website/product/<int:product_id>', type='http', auth='public', website=True)
    def product_detail(self, product_id, **kwargs):
        """Display detailed view of a single product with inventory info"""

        Product = request.env['product.product'].sudo()
        product = Product.browse(product_id)

        if not product.exists() or not product.website_published:
            return request.render('website.404')

        # Get detailed stock information
        quants = request.env['stock.quant'].sudo().search([
            ('product_id', '=', product.id),
            ('location_id.usage', '=', 'internal')
        ])

        qty_available = sum(quants.mapped('quantity'))
        reserved_qty = sum(quants.mapped('reserved_quantity'))

        # Stock moves
        incoming_moves = request.env['stock.move'].sudo().search([
            ('product_id', '=', product.id),
            ('location_dest_id.usage', '=', 'internal'),
            ('state', 'in', ['confirmed', 'partially_available', 'assigned'])
        ])
        incoming_qty = sum(incoming_moves.mapped('product_qty'))

        outgoing_moves = request.env['stock.move'].sudo().search([
            ('product_id', '=', product.id),
            ('location_id.usage', '=', 'internal'),
            ('location_dest_id.usage', '!=', 'internal'),
            ('state', 'in', ['confirmed', 'partially_available', 'assigned'])
        ])
        outgoing_qty = sum(outgoing_moves.mapped('product_qty'))

        # Get variants if any
        variants = product.product_template_id.product_variant_ids

        values = {
            'product': product,
            'qty_available': qty_available,
            'reserved_quantity': reserved_qty,
            'incoming_qty': incoming_qty,
            'outgoing_qty': outgoing_qty,
            'variants': variants,
            'quants': quants
        }

        return request.render('website.product_detail', values)