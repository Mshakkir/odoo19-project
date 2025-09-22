from odoo import models, fields
import base64
import qrcode
from io import BytesIO
import struct  # Required for TLV

class AccountMove(models.Model):
    _inherit = 'account.move'

    qr_code_image = fields.Binary(
        string="ZATCA QR Code",
        compute="_compute_qr_code_image",
        store=False
    )

    def _compute_qr_code_image(self):
        for rec in self:
            def _encode_tlv(tag, value):
                value_bytes = value.encode('utf-8')
                return struct.pack('B', tag) + struct.pack('B', len(value_bytes)) + value_bytes

            seller_name = rec.company_id.name or ''
            vat_number = rec.company_id.vat or ''
            invoice_date = rec.invoice_date.isoformat() if rec.invoice_date else ''
            total_amount = "{:.2f}".format(rec.amount_total or 0)
            vat_amount = "{:.2f}".format(rec.amount_tax or 0)

            tlv = b''.join([
                _encode_tlv(1, seller_name),
                _encode_tlv(2, vat_number),
                _encode_tlv(3, invoice_date),
                _encode_tlv(4, total_amount),
                _encode_tlv(5, vat_amount),
            ])

            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(base64.b64encode(tlv).decode())
            qr.make(fit=True)

            img = qr.make_image(fill_color='black', back_color='white')
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            rec.qr_code_image = base64.b64encode(buffer.getvalue())
