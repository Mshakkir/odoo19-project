from odoo import models, fields, api


class RackList(models.Model):
    _name = 'rack.list'
    _description = 'Rack List - Products with Locations'
    _auto = False  # This is a SQL view, not a real table
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
        """Create SQL view for rack list"""
        self.env.cr.execute("DROP VIEW IF EXISTS rack_list")
        self.env.cr.execute("""
            CREATE VIEW rack_list AS
            SELECT
                sq.id                           AS id,
                sq.product_id                   AS product_id,
                pt.name                         AS product_name,
                pp.default_code                 AS product_code,
                pt.categ_id                     AS product_categ_id,
                sq.location_id                  AS location_id,
                sl.complete_name                AS location_complete_name,
                SUM(sq.quantity)                AS quantity,
                pt.uom_id                       AS uom_id
            FROM stock_quant sq
            JOIN product_product pp      ON pp.id = sq.product_id
            JOIN product_template pt     ON pt.id = pp.product_tmpl_id
            JOIN stock_location sl       ON sl.id = sq.location_id
            WHERE
                sl.usage = 'internal'
                AND sq.quantity > 0
            GROUP BY
                sq.id,
                sq.product_id,
                pt.name,
                pp.default_code,
                pt.categ_id,
                sq.location_id,
                sl.complete_name,
                pt.uom_id
        """)