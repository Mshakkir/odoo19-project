from odoo import models, fields, api


class RackList(models.Model):
    _name = 'rack.list'
    _description = 'Rack List - Products with Locations'
    _auto = False
    _order = 'location_complete_name, product_name'

    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_name = fields.Char(string='Product Name', readonly=True)
    product_code = fields.Char(string='Internal Reference', readonly=True)
    product_categ_id = fields.Many2one('product.category', string='Category', readonly=True)
    location_id = fields.Many2one('stock.location', string='Location', readonly=True)
    location_complete_name = fields.Char(string='Full Location Path', readonly=True)
    quantity = fields.Float(string='Quantity On Hand', readonly=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', readonly=True)

    def init(self):
        self.env.cr.execute("DROP VIEW IF EXISTS rack_list")
        self.env.cr.execute("""
            CREATE VIEW rack_list AS
            SELECT
                ROW_NUMBER() OVER ()        AS id,
                sq.product_id               AS product_id,
                pt.name                     AS product_name,
                pp.default_code             AS product_code,
                pt.categ_id                 AS product_categ_id,
                sq.location_id              AS location_id,
                sl.complete_name            AS location_complete_name,
                SUM(sq.quantity)            AS quantity,
                pt.uom_id                   AS uom_id
            FROM stock_quant sq
            JOIN product_product pp      ON pp.id = sq.product_id
            JOIN product_template pt     ON pt.id = pp.product_tmpl_id
            JOIN stock_location sl       ON sl.id = sq.location_id
            WHERE
                sl.usage = 'internal'
                AND sq.quantity > 0
            GROUP BY
                sq.product_id,
                pt.name,
                pp.default_code,
                pt.categ_id,
                sq.location_id,
                sl.complete_name,
                pt.uom_id
        """)

    @api.model
    def get_locations(self):
        """Return ALL active internal locations."""
        self.env.cr.execute("""
            SELECT id, complete_name as name
            FROM stock_location
            WHERE usage = 'internal'
              AND active = true
            ORDER BY complete_name
        """)
        rows = self.env.cr.fetchall()
        return [{'id': r[0], 'name': r[1]} for r in rows]

    @api.model
    def search_products(self, query, limit=10):
        """
        Return products that are currently in stock and match the query
        by name or internal reference. Used for the autocomplete dropdown.
        """
        lang = self.env.lang or 'en_US'
        self.env.cr.execute("""
            SELECT DISTINCT
                pp.id,
                pp.default_code,
                pt.name
            FROM stock_quant sq
            JOIN product_product pp  ON pp.id = sq.product_id
            JOIN product_template pt ON pt.id = pp.product_tmpl_id
            JOIN stock_location sl   ON sl.id = sq.location_id
            WHERE sl.usage = 'internal'
              AND sq.quantity > 0
              AND (
                  pp.default_code ILIKE %(query)s
                  OR (pt.name->>%(lang)s) ILIKE %(query)s
                  OR (pt.name->>'en_US') ILIKE %(query)s
              )
            ORDER BY pp.default_code, pt.name->>%(lang)s
            LIMIT %(limit)s
        """, {
            'query': f'%{query}%',
            'lang': lang,
            'limit': limit,
        })
        rows = self.env.cr.fetchall()
        results = []
        for r in rows:
            prod_id, code, name_jsonb = r
            # name_jsonb is a dict from psycopg2 for jsonb columns
            if isinstance(name_jsonb, dict):
                name = name_jsonb.get(lang) or name_jsonb.get('en_US') or next(iter(name_jsonb.values()), '')
            else:
                name = name_jsonb or ''
            label = f'[{code}] {name}' if code else name
            results.append({
                'id': prod_id,
                'code': code or '',
                'name': name,
                'label': label,
            })
        return results