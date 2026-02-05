# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools
from odoo.exceptions import UserError


class PurchaseReport(models.Model):
    _name = 'purchase.report.view'
    _description = 'Purchase Report'
    _auto = False
    _order = 'order_date desc'

    # Purchase Order Fields
    order_id = fields.Many2one('purchase.order', string='Order Reference', readonly=True)
    order_name = fields.Char(string='Order Number', readonly=True)
    order_date = fields.Datetime(string='Order Date', readonly=True)
    state = fields.Selection([
        ('draft', 'RFQ'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True)

    # Partner/Vendor Fields
    partner_id = fields.Many2one('res.partner', string='Vendor', readonly=True)
    partner_name = fields.Char(string='Vendor Name', readonly=True)

    # Product Fields
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_name = fields.Char(string='Product Name', readonly=True)
    product_code = fields.Char(string='Product Code', readonly=True)
    categ_id = fields.Many2one('product.category', string='Product Category', readonly=True)
    category_name = fields.Char(string='Category Name', readonly=True)

    # Warehouse Fields
    picking_type_id = fields.Many2one('stock.picking.type', string='Deliver To', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', readonly=True)
    warehouse_name = fields.Char(string='Warehouse Name', readonly=True)

    # User Fields
    user_id = fields.Many2one('res.users', string='Purchase Representative', readonly=True)
    user_name = fields.Char(string='Salesman', readonly=True)

    # Quantities and Amounts
    product_qty = fields.Float(string='Quantity', readonly=True)
    qty_received = fields.Float(string='Received Qty', readonly=True)
    qty_invoiced = fields.Float(string='Billed Qty', readonly=True)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure', readonly=True)

    price_unit = fields.Float(string='Unit Price', readonly=True)
    price_subtotal = fields.Float(string='Untaxed Total', readonly=True)
    price_total = fields.Float(string='Total', readonly=True)

    # Company
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT 
                    pol.id as id,
                    po.id as order_id,
                    po.name as order_name,
                    po.date_order as order_date,
                    po.state as state,
                    po.partner_id as partner_id,
                    rp.name as partner_name,
                    pol.product_id as product_id,
                    pp.default_code as product_code,
                    pt.name as product_name,
                    pt.categ_id as categ_id,
                    pc.complete_name as category_name,
                    po.picking_type_id as picking_type_id,
                    spt.warehouse_id as warehouse_id,
                    sw.name as warehouse_name,
                    po.user_id as user_id,
                    rpu.name as user_name,
                    pol.product_qty as product_qty,
                    pol.qty_received as qty_received,
                    pol.qty_invoiced as qty_invoiced,
                    pol.product_uom_id as product_uom,
                    pol.price_unit as price_unit,
                    pol.price_subtotal as price_subtotal,
                    pol.price_total as price_total,
                    po.company_id as company_id,
                    po.currency_id as currency_id
                FROM 
                    purchase_order_line pol
                    INNER JOIN purchase_order po ON pol.order_id = po.id
                    LEFT JOIN res_partner rp ON po.partner_id = rp.id
                    LEFT JOIN product_product pp ON pol.product_id = pp.id
                    LEFT JOIN product_template pt ON pp.product_tmpl_id = pt.id
                    LEFT JOIN product_category pc ON pt.categ_id = pc.id
                    LEFT JOIN stock_picking_type spt ON po.picking_type_id = spt.id
                    LEFT JOIN stock_warehouse sw ON spt.warehouse_id = sw.id
                    LEFT JOIN res_users ru ON po.user_id = ru.id
                    LEFT JOIN res_partner rpu ON ru.partner_id = rpu.id
            )
        """ % self._table)

    @api.model
    def _read_group_raw(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """Override to add custom aggregations"""
        return super(PurchaseReport, self)._read_group_raw(
            domain, fields, groupby, offset=offset, limit=limit,
            orderby=orderby, lazy=lazy
        )

    def action_export_excel(self):
        """Export report data to Excel"""
        import base64
        from io import BytesIO
        try:
            import xlsxwriter
        except ImportError:
            raise UserError('Please install xlsxwriter: pip install xlsxwriter')

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Purchase Report')

        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D3D3D3',
            'border': 1
        })

        number_format = workbook.add_format({'num_format': '#,##0.00'})
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})

        # Write headers
        headers = [
            'Order Date', 'Order Number', 'Vendor', 'Product Code',
            'Product Name', 'Category', 'Warehouse', 'Purchase Rep',
            'Quantity', 'Received', 'Invoiced', 'UoM',
            'Unit Price', 'Untaxed Total', 'Total', 'Status'
        ]

        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # Write data
        row = 1
        for record in self:
            worksheet.write(row, 0, record.order_date.strftime('%Y-%m-%d') if record.order_date else '', date_format)
            worksheet.write(row, 1, record.order_name or '')
            worksheet.write(row, 2, record.partner_name or '')
            worksheet.write(row, 3, record.product_code or '')
            worksheet.write(row, 4, record.product_name or '')
            worksheet.write(row, 5, record.category_name or '')
            worksheet.write(row, 6, record.warehouse_name or '')
            worksheet.write(row, 7, record.user_name or '')
            worksheet.write(row, 8, record.product_qty, number_format)
            worksheet.write(row, 9, record.qty_received, number_format)
            worksheet.write(row, 10, record.qty_invoiced, number_format)
            worksheet.write(row, 11, record.product_uom.name if record.product_uom else '')
            worksheet.write(row, 12, record.price_unit, number_format)
            worksheet.write(row, 13, record.price_subtotal, number_format)
            worksheet.write(row, 14, record.price_total, number_format)
            worksheet.write(row, 15, dict(self._fields['state'].selection).get(record.state, ''))
            row += 1

        # Auto-fit columns
        worksheet.set_column('A:P', 15)

        workbook.close()
        output.seek(0)

        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': 'Purchase_Report.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(output.read()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }