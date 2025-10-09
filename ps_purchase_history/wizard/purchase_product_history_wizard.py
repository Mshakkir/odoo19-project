# -*- coding: utf-8 -*-


from odoo import api,fields, models
import xlwt
import base64
from io import BytesIO
from xlwt import easyxf
from xlwt import Workbook, XFStyle, easyxf
import pytz


class ProductHistory(models.TransientModel):
    _name = 'product.purchase.history'

    product_id = fields.Many2one('product.template', string="Product")
    line_ids = fields.One2many('product.purchase.history.line', 'history_id', string="History Lines")


    def action_download_excel(self):

        fl = BytesIO()
        workbook = Workbook(encoding='utf-8')
        sheet = workbook.add_sheet('Product History')

        # Styles
        bold_style = easyxf('font: bold 1; align: horiz left')
        yellow_style = easyxf(
            'pattern: pattern solid, fore_colour yellow; font: bold on; align: horiz center'
        )

        headings = ['Vendor', 'PO Number', 'Date', 'Quantity', 'Price']
        column_widths = [5000, 4000, 6000, 4000, 4000]

        sheet.write_merge(0, 0, 0, len(headings) - 1, f"Product: {self.product_id.name}", yellow_style)

        for col_num, (heading, width) in enumerate(zip(headings, column_widths)):
            sheet.write(1, col_num, heading, bold_style)
            sheet.col(col_num).width = width

        row = 2
        for line in self.line_ids:
            sheet.write(row, 0, line.vendor if line.vendor else '')
            sheet.write(row, 1, line.po_number)
            sheet.write(row, 2, line.po_date.strftime('%Y-%m-%d %H:%M:%S') if line.po_date else '')
            sheet.write(row, 3, line.quantity)
            sheet.write(row, 4, line.unit_price)
            row += 1

        filename = "Product History"
        workbook.save(fl)
        fl.seek(0)

        file_data = base64.encodebytes(fl.read())
        attachment = self.env['ir.attachment'].create({
            'name': f'{filename}.xls',
            'datas': file_data,
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }



class ProductPurchaseHistoryLine(models.TransientModel):
    _name = 'product.purchase.history.line'
    _description = 'Purchase History Line'

    history_id = fields.Many2one('product.purchase.history', string="History")
    po_number = fields.Char(string="PO Number")
    vendor = fields.Char(string="Vendor")
    po_date = fields.Datetime(string="PO Date")
    quantity = fields.Float(string="Quantity")
    unit_price = fields.Float(string="Unit Price")




