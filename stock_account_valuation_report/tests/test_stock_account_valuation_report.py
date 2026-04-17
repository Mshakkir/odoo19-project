# 2020 Copyright ForgeFlow, S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests.common import TransactionCase


class TestStockAccountValuationReport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Get required Models
        cls.product_model = cls.env["product.product"]
        cls.template_model = cls.env["product.template"]
        cls.product_ctg_model = cls.env["product.category"]
        cls.account_model = cls.env["account.account"]
        cls.quant_model = cls.env["stock.quant"]
        cls.layer_model = cls.env["stock.valuation.layer"]
        cls.stock_location_model = cls.env["stock.location"]
        cls.res_users_model = cls.env["res.users"]
        cls.account_move_model = cls.env["account.move"]
        cls.aml_model = cls.env["account.move.line"]
        cls.journal_model = cls.env["account.journal"]
        # Get required Model data
        cls.product_uom = cls.env.ref("uom.product_uom_unit")
        cls.company = cls.env.ref("base.main_company")
        cls.stock_picking_type_out = cls.env.ref("stock.picking_type_out")
        cls.stock_picking_type_in = cls.env.ref("stock.picking_type_in")
        cls.stock_location_id = cls.env.ref("stock.stock_location_stock").id
        cls.stock_location_customer_id = cls.env.ref(
            "stock.stock_location_customers"
        ).id
        cls.stock_location_supplier_id = cls.env.ref(
            "stock.stock_location_suppliers"
        ).id
        # Account types
        expense_type = "expense"
        equity_type = "equity"
        asset_type = "asset_current"
        # Create account for Goods Received Not Invoiced
        cls.account_grni = cls._create_account(
            equity_type, "Goods Received Not Invoiced", "grni", cls.company
        )
        # Create account for Cost of Goods Sold
        cls.account_cogs = cls._create_account(
            expense_type, "Cost of Goods Sold", "cogs", cls.company
        )
        # Create account for Goods Delivered Not Invoiced
        cls.account_gdni = cls._create_account(
            expense_type, "Goods Delivered Not Invoiced", "gdni", cls.company
        )
        # Create account for Inventory
        cls.account_inventory = cls._create_account(
            asset_type, "Inventory", "inventory", cls.company
        )
        cls.stock_journal = cls.env["account.journal"].create(
            {"name": "Stock journal", "type": "general", "code": "STK00"}
        )
        # Create product category
        cls.product_ctg = cls._create_product_category()
        # Create partners
        cls.supplier = cls.env["res.partner"].create({"name": "Test supplier"})
        cls.customer = cls.env["res.partner"].create({"name": "Test customer"})
        cls.vendor_partner = cls.env["res.partner"].create(
            {"name": "dropship vendor"}
        )
        # Create a Product with real cost
        cls.product = cls._create_product(10.0, False, 20.0)

    @classmethod
    def _create_account(cls, account_type, name, code, company):
        """Create an account."""
        return cls.account_model.create(
            {
                "name": name,
                "code": code,
                "account_type": account_type,
                "company_id": company.id,
            }
        )

    @classmethod
    def _create_product_category(cls):
        return cls.product_ctg_model.create(
            {
                "name": "test_product_ctg",
                "property_stock_valuation_account_id": cls.account_inventory.id,
                "property_stock_account_input_categ_id": cls.account_grni.id,
                "property_account_expense_categ_id": cls.account_cogs.id,
                "property_stock_account_output_categ_id": cls.account_gdni.id,
                "property_valuation": "real_time",
                "property_cost_method": "fifo",
                "property_stock_journal": cls.stock_journal.id,
            }
        )

    @classmethod
    def _create_product(cls, standard_price, template, list_price):
        """Create a Product variant."""
        if not template:
            template = cls.template_model.create(
                {
                    "name": "test_product",
                    "categ_id": cls.product_ctg.id,
                    # Odoo 17+: storable products use 'consu' with
                    # can_be_expensed/tracking; 'product' type is removed.
                    "type": "consu",
                    "standard_price": standard_price,
                    "valuation": "real_time",
                }
            )
            return template.product_variant_ids[0]
        return cls.product_model.create(
            {"product_tmpl_id": template.id, "list_price": list_price}
        )

    def _create_delivery(self, product, qty, price_unit=10.0):
        return self.env["stock.picking"].create(
            {
                "name": self.stock_picking_type_out.sequence_id._next(),
                "partner_id": self.customer.id,
                "picking_type_id": self.stock_picking_type_out.id,
                "location_id": self.stock_location_id,
                "location_dest_id": self.stock_location_customer_id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "name": product.name,
                            "product_id": product.id,
                            "product_uom": product.uom_id.id,
                            "product_uom_qty": qty,
                            "price_unit": price_unit,
                            "location_id": self.stock_location_id,
                            "location_dest_id": self.stock_location_customer_id,
                            "procure_method": "make_to_stock",
                        },
                    )
                ],
            }
        )

    def _create_dropship_picking(self, product, qty, price_unit=10.0):
        return self.env["stock.picking"].create(
            {
                "name": self.stock_picking_type_out.sequence_id._next(),
                "partner_id": self.customer.id,
                "picking_type_id": self.stock_picking_type_out.id,
                "location_id": self.stock_location_supplier_id,
                "location_dest_id": self.stock_location_customer_id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "name": product.name,
                            "product_id": product.id,
                            "product_uom": product.uom_id.id,
                            "product_uom_qty": qty,
                            "price_unit": price_unit,
                            "location_id": self.stock_location_supplier_id,
                            "location_dest_id": self.stock_location_customer_id,
                        },
                    )
                ],
            }
        )

    def _create_receipt(self, product, qty, move_dest_id=False, price_unit=10.0):
        move_dest_id = [(4, move_dest_id)] if move_dest_id else False
        return self.env["stock.picking"].create(
            {
                "name": self.stock_picking_type_in.sequence_id._next(),
                "partner_id": self.vendor_partner.id,
                "picking_type_id": self.stock_picking_type_in.id,
                "location_id": self.stock_location_supplier_id,
                "location_dest_id": self.stock_location_id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "name": product.name,
                            "product_id": product.id,
                            "product_uom": product.uom_id.id,
                            "product_uom_qty": qty,
                            "price_unit": price_unit,
                            "move_dest_ids": move_dest_id,
                            "location_id": self.stock_location_supplier_id,
                            "location_dest_id": self.stock_location_id,
                            "procure_method": "make_to_stock",
                        },
                    )
                ],
            }
        )

    def _do_picking(self, picking, date, qty):
        """Confirm and validate a picking on the given date."""
        picking.write({"date": date})
        picking.move_ids.write({"date": date})
        picking.action_confirm()
        picking.action_assign()
        # Odoo 17+: use move_line_ids.qty_done instead of move_ids.quantity_done
        for move_line in picking.move_line_ids:
            move_line.qty_done = qty
        picking.button_validate()
        # Hack create_date of the SVL to test date-based filtering
        self.env.cr.execute(
            "UPDATE stock_valuation_layer SET create_date = %s WHERE id IN %s",
            (date, tuple(picking.move_ids.stock_valuation_layer_ids.ids)),
        )
        return True

    def test_01_stock_receipt(self):
        """Receive into stock and ship to the customer."""
        in_picking = self._create_receipt(self.product, 1.0)
        self._do_picking(in_picking, fields.Datetime.now(), 1.0)

        aml = self.aml_model.search([("product_id", "=", self.product.id)])
        inv_aml = aml.filtered(
            lambda l: l.account_id == self.account_inventory
        )
        self.assertEqual(sum(inv_aml.mapped("balance")), 10.0)

        move = in_picking.move_ids
        layer = self.layer_model.search([("stock_move_id", "=", move.id)])
        self.assertEqual(layer.remaining_value, 10.0)

        self.assertEqual(self.product.stock_value, 10.0)
        self.assertEqual(self.product.account_value, 10.0)
        self.assertEqual(self.product.qty_at_date, 1.0)
        self.assertEqual(self.product.account_qty_at_date, 1.0)

        out_picking = self._create_delivery(self.product, 1)
        self._do_picking(out_picking, fields.Datetime.now(), 1.0)

        self.assertEqual(layer.remaining_qty, 0.0)
        self.assertEqual(layer.remaining_value, 0.0)

        move = out_picking.move_ids
        layer = self.layer_model.search([("stock_move_id", "=", move.id)])
        self.assertEqual(layer.value, -10.0)

        self.product._compute_inventory_value()
        self.assertEqual(self.product.stock_value, 0.0)
        self.assertEqual(self.product.account_value, 0.0)
        self.assertEqual(self.product.qty_at_date, 0.0)
        self.assertEqual(self.product.account_qty_at_date, 0.0)

    def test_02_drop_ship(self):
        """Drop shipment from vendor to customer."""
        dropship_picking = self._create_dropship_picking(self.product, 1.0)
        self._do_picking(dropship_picking, fields.Datetime.now(), 1.0)

        aml = self.aml_model.search([("product_id", "=", self.product.id)])
        inv_aml = aml.filtered(
            lambda l: l.account_id == self.account_inventory
        )
        self.assertEqual(sum(inv_aml.mapped("balance")), 0.0)

        move = dropship_picking.move_ids
        layers = self.layer_model.search([("stock_move_id", "=", move.id)])
        self.assertEqual(len(layers), 2)
        in_layer = layers.filtered(lambda l: l.quantity > 0)
        self.assertEqual(in_layer.remaining_qty, 0.0)
        self.assertEqual(in_layer.remaining_value, 0.0)

        self.assertEqual(self.product.stock_value, 0.0)
        self.assertEqual(self.product.account_value, 0.0)
        self.assertEqual(self.product.qty_at_date, 0.0)
        self.assertEqual(self.product.account_qty_at_date, 0.0)

    def test_03_stock_receipt_several_costs_several_dates(self):
        """Receive into stock at different costs on different dates."""
        in_picking = self._create_receipt(self.product, 1.0)
        self._do_picking(in_picking, fields.Datetime.now(), 1.0)

        aml = self.aml_model.search([("product_id", "=", self.product.id)])
        inv_aml = aml.filtered(
            lambda l: l.account_id == self.account_inventory
        )
        self.assertEqual(sum(inv_aml.mapped("balance")), 10.0)

        move = in_picking.move_ids
        layer = self.layer_model.search([("stock_move_id", "=", move.id)])
        self.assertEqual(layer.remaining_value, 10.0)

        in_picking2 = self._create_receipt(self.product, 2.0, False, 20.0)
        self._do_picking(
            in_picking2,
            fields.Datetime.now() + relativedelta(days=3),
            2.0,
        )

        aml = self.aml_model.search([("product_id", "=", self.product.id)])
        inv_aml = aml.filtered(
            lambda l: l.account_id == self.account_inventory
        )
        self.assertEqual(sum(inv_aml.mapped("balance")), 50.0)

        move2 = in_picking2.move_ids
        layer2 = self.layer_model.search([("stock_move_id", "=", move2.id)])
        self.assertEqual(layer2.remaining_value, 40.0)

        self.assertEqual(self.product.stock_value, 50.0)
        self.assertEqual(self.product.account_value, 50.0)
        self.assertEqual(self.product.qty_at_date, 3.0)
        self.assertEqual(self.product.account_qty_at_date, 3.0)

        aml_layer = layer2.account_move_id.line_ids
        self.env.cr.execute(
            "UPDATE account_move_line SET date = %s WHERE id IN %s",
            (
                fields.Datetime.now() + relativedelta(days=3),
                tuple(aml_layer.ids),
            ),
        )
        self.product.with_context(
            at_date=fields.Datetime.now() + relativedelta(days=1)
        )._compute_inventory_value()
        self.assertEqual(self.product.stock_value, 10.0)
        self.assertEqual(self.product.account_value, 10.0)
        self.assertEqual(self.product.qty_at_date, 1.0)
        self.assertEqual(self.product.account_qty_at_date, 1.0)
