# Copyright 2019 Tecnativa - David Vidal
# Copyright 2020 Tecnativa - Pedro M. Baeza
# Copyright 2021 Tecnativa - Víctor Martínez
# Copyright 2025 - Odoo 19 CE Conversion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import exceptions
from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestGlobalDiscount(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(cls.env.context, test_account_global_discount=True)
        )
        cls.env.ref("base_global_discount.group_global_discount").write(
            {"users": [(4, cls.env.user.id)]}
        )
        cls.account = cls.company_data["default_account_revenue"]
        cls.global_discount_obj = cls.env["global.discount"]

        cls.global_discount_1 = cls.global_discount_obj.create(
            {
                "name": "Test Discount 1",
                "discount_scope": "sale",
                "discount": 20,
                "account_id": cls.account.id,
                "sequence": 3,
            }
        )
        cls.global_discount_2 = cls.global_discount_obj.create(
            {
                "name": "Test Discount 2",
                "discount_scope": "purchase",
                "discount": 30,
                "account_id": cls.account.id,
                "sequence": 2,
            }
        )
        cls.global_discount_3 = cls.global_discount_obj.create(
            {
                "name": "Test Discount 3",
                "discount_scope": "purchase",
                "discount": 50,
                "account_id": cls.account.id,
                "sequence": 1,
            }
        )

        cls.partner_1 = cls.env["res.partner"].create({"name": "Mr. Odoo"})
        cls.partner_2 = cls.env["res.partner"].create({"name": "Mrs. Odoo"})
        cls.partner_2.supplier_global_discount_ids = cls.global_discount_2

        cls.tax = cls.tax_purchase_a
        cls.tax.amount = 15
        cls.tax_0 = cls.tax_purchase_b
        cls.tax_0.amount = 0

        cls.product_3 = cls.env["product.product"].create(
            {
                "name": "Test Product 3",
                "type": "service",
                "bypass_global_discount": True,
            }
        )

        cls.invoice = (
            cls.env["account.move"]
            .with_context(default_move_type="in_invoice")
            .create(
                {
                    "partner_id": cls.partner_1.id,
                    "ref": "Test global discount",
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "name": "Line 1",
                                "price_unit": 200.0,
                                "quantity": 1,
                                "tax_ids": [(6, 0, [cls.tax.id])],
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "name": "Line 2",
                                "product_id": cls.product_3.id,
                                "price_unit": 200.0,
                                "quantity": 1,
                                "tax_ids": [(6, 0, [cls.tax_0.id])],
                            },
                        ),
                    ],
                }
            )
        )

    def test_01_global_invoice_successive_discounts(self):
        """Add global discounts to the invoice"""
        invoice_tax_line = self.invoice.line_ids.filtered("tax_line_id")
        self.assertAlmostEqual(self.invoice.amount_total, 430)
        self.assertAlmostEqual(invoice_tax_line.tax_base_amount, 200.0)
        self.assertAlmostEqual(invoice_tax_line.balance, 30.0)

        # Apply 50% discount
        with Form(self.invoice) as invoice_form:
            invoice_form.global_discount_ids.clear()
            invoice_form.global_discount_ids.add(self.global_discount_3)

        self.assertEqual(len(self.invoice.invoice_global_discount_ids), 1)
        precision = self.env["decimal.precision"].precision_get("Discount")
        self.assertEqual(
            self.invoice.invoice_global_discount_ids.discount_display,
            "-50.{}%".format("0" * precision),
        )

        invoice_tax_line = self.invoice.line_ids.filtered("tax_line_id")
        self.assertAlmostEqual(invoice_tax_line.tax_base_amount, 100.0)
        self.assertAlmostEqual(invoice_tax_line.balance, 15.0)
        self.assertAlmostEqual(self.invoice.amount_untaxed, 300.0)
        self.assertAlmostEqual(self.invoice.amount_total, 315.0)
        self.assertAlmostEqual(self.invoice.amount_global_discount, -100.0)

        # Apply successive discounts: 50% then 30%
        with Form(self.invoice) as invoice_form:
            invoice_form.global_discount_ids.add(self.global_discount_2)

        self.assertEqual(len(self.invoice.invoice_global_discount_ids), 2)
        invoice_tax_line = self.invoice.line_ids.filtered("tax_line_id")
        self.assertAlmostEqual(invoice_tax_line.tax_base_amount, 70.0)
        self.assertAlmostEqual(invoice_tax_line.balance, 10.5)
        self.assertAlmostEqual(self.invoice.amount_untaxed, 270.0)
        self.assertAlmostEqual(self.invoice.amount_total, 280.5)
        self.assertAlmostEqual(self.invoice.amount_global_discount, -130.0)

    def test_02_global_invoice_discounts_from_partner(self):
        """Change the partner and his global discounts go to the invoice"""
        invoice_tax_line = self.invoice.line_ids.filtered("tax_line_id")
        self.assertAlmostEqual(self.invoice.amount_total, 430)
        self.assertAlmostEqual(invoice_tax_line.tax_base_amount, 200.0)
        self.assertAlmostEqual(invoice_tax_line.balance, 30.0)

        with Form(self.invoice) as invoice_form:
            invoice_form.partner_id = self.partner_2

        self.assertAlmostEqual(invoice_tax_line.tax_base_amount, 140.0)
        self.assertAlmostEqual(invoice_tax_line.balance, 21.0)
        self.assertAlmostEqual(self.invoice.amount_untaxed, 340.0)
        self.assertAlmostEqual(self.invoice.amount_total, 361.0)
        self.assertAlmostEqual(self.invoice.amount_global_discount, -60.0)

    def test_03_multiple_taxes_multi_line(self):
        """Test multiple taxes on multiple lines"""
        tax2 = self.tax.copy(default={"amount": 20.0, "name": "Tax 2"})

        with Form(self.invoice) as invoice_form:
            invoice_form.global_discount_ids.add(self.global_discount_1)
            with invoice_form.invoice_line_ids.new() as line_form:
                line_form.name = "Line 3"
                line_form.price_unit = 100.0
                line_form.quantity = 1
                line_form.tax_ids.clear()
                line_form.tax_ids.add(tax2)

        self.assertEqual(len(self.invoice.invoice_global_discount_ids), 2)
        discount_tax_15 = self.invoice.invoice_global_discount_ids.filtered(
            lambda x: self.tax in x.tax_ids
        )
        discount_tax_20 = self.invoice.invoice_global_discount_ids.filtered(
            lambda x: tax2 in x.tax_ids
        )

        self.assertAlmostEqual(discount_tax_15.discount_amount, 40)
        self.assertAlmostEqual(discount_tax_20.discount_amount, 20)

    def test_04_customer_invoice(self):
        """Test customer invoice with global discounts"""
        global_discount = self.global_discount_obj.create(
            {
                "name": "Test Discount Sales",
                "discount_scope": "sale",
                "discount": 50,
                "account_id": self.account.id,
                "sequence": 1,
            }
        )
        tax = self.tax_sale_a.copy(default={"amount": 15.0, "name": "Tax Sales"})

        invoice = (
            self.env["account.move"]
            .with_context(test_account_global_discount=True)
            .create(
                {
                    "move_type": "out_invoice",
                    "partner_id": self.partner_1.id,
                    "global_discount_ids": [(6, 0, global_discount.ids)],
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "name": "Line 1",
                                "price_unit": 200.0,
                                "quantity": 1,
                                "tax_ids": [(6, 0, tax.ids)],
                            },
                        )
                    ],
                }
            )
        )

        self.assertEqual(len(invoice.invoice_global_discount_ids), 1)
        invoice_tax_line = invoice.line_ids.filtered("tax_line_id")
        self.assertAlmostEqual(invoice_tax_line.tax_base_amount, 100.0)
        self.assertAlmostEqual(invoice_tax_line.balance, -15.0)
        self.assertAlmostEqual(invoice.amount_untaxed, 100.0)
        self.assertAlmostEqual(invoice.amount_total, 115.0)
        self.assertAlmostEqual(invoice.amount_global_discount, -100.0)

    def test_05_incompatible_taxes(self):
        """Test that incompatible tax combinations raise an error"""
        tax2 = self.tax.copy(default={"amount": -20.0, "name": "Tax 2"})

        with self.assertRaises(exceptions.UserError):
            with Form(self.invoice) as invoice_form:
                invoice_form.global_discount_ids.add(self.global_discount_1)
                with invoice_form.invoice_line_ids.new() as line_form:
                    line_form.name = "Line 3"
                    line_form.price_unit = 100.0
                    line_form.quantity = 1
                    line_form.tax_ids.clear()
                    line_form.tax_ids.add(self.tax)
                    line_form.tax_ids.add(tax2)

    def test_06_no_taxes(self):
        """Test that lines without taxes raise an error with global discounts"""
        with self.assertRaises(exceptions.UserError):
            with Form(self.invoice) as invoice_form:
                invoice_form.global_discount_ids.add(self.global_discount_1)
                with invoice_form.invoice_line_ids.edit(0) as line_form:
                    line_form.tax_ids.clear()