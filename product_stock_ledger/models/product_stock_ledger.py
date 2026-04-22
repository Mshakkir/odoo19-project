from odoo import models, fields, tools, _
from odoo.exceptions import UserError, AccessError


class ProductStockLedger(models.Model):
    """
    SQL-backed read-only model (PostgreSQL VIEW).
    Compatible with Odoo 19 CE. Handles jsonb translated fields (name, complete_name).

    Rate source (CE-safe priority):
      1. account_move_line.price_unit  — from linked vendor bill / customer invoice line
      2. stock_valuation_layer         — if available (Enterprise / enabled CE valuation)
      3. purchase_order_line.price_unit — fallback for receipts
      4. sale_order_line.price_unit     — fallback for deliveries
      5. 0                              — if nothing found
    """
    _name = 'product.stock.ledger'
    _description = 'Product Stock Ledger'
    _auto = False
    _order = 'date desc, id desc'

    product_id      = fields.Many2one('product.product', string='Product',         readonly=True)
    warehouse_id    = fields.Many2one('stock.warehouse',  string='Warehouse',       readonly=True)
    date            = fields.Datetime(string='_Date_Raw',  readonly=True)
    date_str        = fields.Char(string='Date',           readonly=True)
    voucher         = fields.Char(string='Voucher',       readonly=True)
    particulars     = fields.Char(string='Particulars',   readonly=True)
    move_type       = fields.Char(string='Type',          readonly=True)
    rec_qty         = fields.Float(string='Rec. Qty',     readonly=True, digits=(16, 4))
    rec_rate        = fields.Float(string='Rec. Rate',    readonly=True, digits=(16, 4))
    issue_qty       = fields.Float(string='Issue Qty',    readonly=True, digits=(16, 4))
    issue_rate      = fields.Float(string='Issue Rate',   readonly=True, digits=(16, 4))
    balance         = fields.Float(string='Balance',      readonly=True, digits=(16, 4))
    uom             = fields.Char(string='Unit',          readonly=True)
    invoice_status  = fields.Char(string='Invoice Status', readonly=True)
    move_id         = fields.Many2one('stock.move',       string='Stock Move',      readonly=True)
    company_id      = fields.Many2one('res.company',      string='Company',         readonly=True)

    # ------------------------------------------------------------------
    def _table_exists(self, table_name):
        self.env.cr.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = %s
            )
        """, (table_name,))
        return self.env.cr.fetchone()[0]

    def _col_exists(self, table_name, col_name):
        self.env.cr.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name   = %s
                  AND column_name  = %s
            )
        """, (table_name, col_name))
        return self.env.cr.fetchone()[0]

    def _col_type(self, table_name, col_name):
        self.env.cr.execute("""
            SELECT data_type FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name   = %s
              AND column_name  = %s
        """, (table_name, col_name))
        row = self.env.cr.fetchone()
        return row[0] if row else None

    def _jsonb_to_text(self, col_expr):
        return (
            "COALESCE("
            f"  ({col_expr})->>'en_US',"
            f"  (SELECT v FROM jsonb_each_text({col_expr}) AS t(k,v) LIMIT 1),"
            "  ''"
            ")"
        )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        has_svl = self._table_exists('stock_valuation_layer')
        has_so  = self._table_exists('sale_order')
        has_po  = self._table_exists('purchase_order')
        has_pol = self._table_exists('purchase_order_line')
        has_sol = self._table_exists('sale_order_line')

        uom_name_type = self._col_type('uom_uom', 'name')
        if uom_name_type and 'json' in uom_name_type.lower():
            uom_name_sql = self._jsonb_to_text('uom_u.name')
        else:
            uom_name_sql = "COALESCE(uom_u.name::text, '')"

        loc_cn_type = self._col_type('stock_location', 'complete_name')
        if loc_cn_type and 'json' in loc_cn_type.lower():
            sl_cn   = "(sl.complete_name->>'en_US')"
            root_cn = "(root.complete_name->>'en_US')"
        else:
            sl_cn   = "sl.complete_name"
            root_cn = "root.complete_name"

        sm_ref = 'sm.reference' if self._col_exists('stock_move', 'reference') else 'sm.origin'

        # ── Rate source (CE-safe) ──────────────────────────────────────────
        # Priority:
        #   1. Vendor bill line (in_invoice)  → best for purchases
        #   2. Customer invoice line (out_invoice) → best for sales
        #   3. stock_valuation_layer if available
        #   4. purchase_order_line.price_unit fallback
        #   5. sale_order_line.price_unit fallback
        #   6. 0

        # CTE: unit cost from account_move_line (linked via stock_move)
        # purchase bill lines are linked via purchase_line_id → purchase_order_line → stock_move
        # sale invoice lines are linked via sale_line_ids (many2many rel table)

        # Check for the purchase line link on account_move_line
        has_aml_purchase_link = self._col_exists('account_move_line', 'purchase_line_id')

        # Check sale_order_line_invoice_rel table (links sale lines to invoice lines)
        has_sol_inv_rel = self._table_exists('sale_order_line_invoice_rel')

        # ── SVL cost CTE ──────────────────────────────────────────────────
        if has_svl:
            svl_cte = """
svl_cost AS (
    SELECT
        stock_move_id,
        CASE WHEN SUM(ABS(quantity)) > 0
             THEN SUM(ABS(value)) / SUM(ABS(quantity))
             ELSE 0
        END AS unit_cost
    FROM stock_valuation_layer
    WHERE stock_move_id IS NOT NULL
    GROUP BY stock_move_id
),"""
            svl_join  = "LEFT JOIN svl_cost svl ON svl.stock_move_id = sm.id"
            svl_field = "svl.unit_cost"
        else:
            svl_cte   = ""
            svl_join  = ""
            svl_field = "NULL::numeric"

        # ── Account Move Line cost CTE (purchase bills) ───────────────────
        # Link: stock_move.purchase_line_id → purchase_order_line.id
        #       account_move_line.purchase_line_id → purchase_order_line.id
        has_sm_pol = self._col_exists('stock_move', 'purchase_line_id')

        if has_aml_purchase_link and has_sm_pol:
            aml_purchase_cte = """
aml_purchase_cost AS (
    SELECT
        sm_inner.id AS stock_move_id,
        aml.price_unit AS unit_cost
    FROM stock_move sm_inner
    JOIN account_move_line aml
        ON aml.purchase_line_id = sm_inner.purchase_line_id
       AND aml.purchase_line_id IS NOT NULL
    JOIN account_move am
        ON am.id = aml.move_id
       AND am.move_type = 'in_invoice'
       AND am.state = 'posted'
    WHERE sm_inner.purchase_line_id IS NOT NULL
),"""
            aml_pur_join  = "LEFT JOIN aml_purchase_cost apc ON apc.stock_move_id = sm.id"
            aml_pur_field = "apc.unit_cost"
        else:
            aml_purchase_cte = ""
            aml_pur_join     = ""
            aml_pur_field    = "NULL::numeric"

        # ── Account Move Line cost CTE (customer invoices / sale) ─────────
        has_sm_sol = self._col_exists('stock_move', 'sale_line_id')

        if has_sol_inv_rel and has_sm_sol:
            aml_sale_cte = """
aml_sale_cost AS (
    SELECT
        sm_inner.id  AS stock_move_id,
        aml.price_unit AS unit_cost
    FROM stock_move sm_inner
    JOIN sale_order_line_invoice_rel rel
        ON rel.order_line_id = sm_inner.sale_line_id
    JOIN account_move_line aml
        ON aml.id = rel.invoice_line_id
    JOIN account_move am
        ON am.id = aml.move_id
       AND am.move_type = 'out_invoice'
       AND am.state = 'posted'
    WHERE sm_inner.sale_line_id IS NOT NULL
),"""
            aml_sale_join  = "LEFT JOIN aml_sale_cost asc2 ON asc2.stock_move_id = sm.id"
            aml_sale_field = "asc2.unit_cost"
        else:
            aml_sale_cte  = ""
            aml_sale_join = ""
            aml_sale_field = "NULL::numeric"

        # ── Purchase Order Line price fallback ────────────────────────────
        if has_pol and has_sm_pol:
            pol_cte = """
pol_cost AS (
    SELECT sm_inner.id AS stock_move_id, pol.price_unit AS unit_cost
    FROM stock_move sm_inner
    JOIN purchase_order_line pol ON pol.id = sm_inner.purchase_line_id
    WHERE sm_inner.purchase_line_id IS NOT NULL
),"""
            pol_join  = "LEFT JOIN pol_cost polc ON polc.stock_move_id = sm.id"
            pol_field = "polc.unit_cost"
        else:
            pol_cte   = ""
            pol_join  = ""
            pol_field = "NULL::numeric"

        # ── Sale Order Line price fallback ────────────────────────────────
        if has_sol and has_sm_sol:
            sol_cte = """
sol_cost AS (
    SELECT sm_inner.id AS stock_move_id, sol.price_unit AS unit_cost
    FROM stock_move sm_inner
    JOIN sale_order_line sol ON sol.id = sm_inner.sale_line_id
    WHERE sm_inner.sale_line_id IS NOT NULL
),"""
            sol_join  = "LEFT JOIN sol_cost solc ON solc.stock_move_id = sm.id"
            sol_field = "solc.unit_cost"
        else:
            sol_cte   = ""
            sol_join  = ""
            sol_field = "NULL::numeric"

        # ── Final COALESCE for unit cost ──────────────────────────────────
        # For IN moves (receipts): prefer purchase bill rate, then SVL, then POL
        # For OUT moves (issues):  prefer sale invoice rate, then SVL, then SOL
        cost_field = f"""COALESCE(
                CASE
                    WHEN dest_loc.usage = 'internal' AND src_loc.usage != 'internal'
                        THEN COALESCE({aml_pur_field}, {svl_field}, {pol_field})
                    WHEN src_loc.usage = 'customer'
                        THEN COALESCE({aml_pur_field}, {svl_field}, {pol_field})
                    WHEN src_loc.usage = 'internal' AND dest_loc.usage != 'internal'
                        THEN COALESCE({aml_sale_field}, {svl_field}, {sol_field})
                    ELSE COALESCE({svl_field}, {aml_pur_field}, {aml_sale_field}, {pol_field}, {sol_field})
                END,
                0
            )"""

        # ── SO / PO joins ─────────────────────────────────────────────────
        # Use direct FK links instead of origin string matching (much more reliable)
        if has_so and has_sm_sol:
            so_join   = "LEFT JOIN sale_order so ON so.id = sm.sale_id" if self._col_exists('stock_move', 'sale_id') else \
                        "LEFT JOIN sale_order_line sol_ref ON sol_ref.id = sm.sale_line_id LEFT JOIN sale_order so ON so.id = sol_ref.order_id"
            so_name   = "so.name"
            so_cond   = "so.id IS NOT NULL"
            so_inv    = "so.invoice_status" if self._col_exists('sale_order', 'invoice_status') else "NULL::varchar"
        else:
            so_join   = ""
            so_name   = "NULL::varchar"
            so_cond   = "FALSE"
            so_inv    = "NULL::varchar"

        if has_po and has_sm_pol:
            po_join   = "LEFT JOIN purchase_order po ON po.id = sm.purchase_id" if self._col_exists('stock_move', 'purchase_id') else \
                        "LEFT JOIN purchase_order_line pol_ref ON pol_ref.id = sm.purchase_line_id LEFT JOIN purchase_order po ON po.id = pol_ref.order_id"
            po_name   = "po.name"
            po_cond   = "po.id IS NOT NULL"
            po_inv    = "po.invoice_status" if self._col_exists('purchase_order', 'invoice_status') else "NULL::varchar"
        else:
            po_join   = ""
            po_name   = "NULL::varchar"
            po_cond   = "FALSE"
            po_inv    = "NULL::varchar"

        # ── Assemble all CTEs ─────────────────────────────────────────────
        # Remove trailing commas from the last CTE before ledger CTE
        all_ctes = "".join(filter(None, [
            svl_cte,
            aml_purchase_cte,
            aml_sale_cte,
            pol_cte,
            sol_cte,
        ]))
        # Strip trailing comma+whitespace before "ledger AS"
        if all_ctes.strip().endswith(','):
            all_ctes = all_ctes.rstrip().rstrip(',')

        sql = f"""
CREATE OR REPLACE VIEW product_stock_ledger AS

WITH
loc_warehouse AS (
    SELECT DISTINCT ON (sl.id)
        sl.id AS location_id,
        sw.id AS warehouse_id
    FROM stock_location sl
    JOIN stock_warehouse sw
        ON sl.id = sw.lot_stock_id
        OR {sl_cn} LIKE (
            SELECT {root_cn} || '/%'
            FROM stock_location root
            WHERE root.id = sw.lot_stock_id
        )
    WHERE sl.usage = 'internal'
    ORDER BY sl.id, sw.id
),
{all_ctes}

ledger AS (
    SELECT
        sml.id                                               AS id,
        sml.product_id                                       AS product_id,
        COALESCE(wh_src.warehouse_id, wh_dest.warehouse_id) AS warehouse_id,
        sm.date                                              AS date,
        TO_CHAR(sm.date AT TIME ZONE 'UTC', 'DD/MM/YY')     AS date_str,

        COALESCE({so_name}, {po_name}, sp.name, sm.origin, {sm_ref}, '')
                                                             AS voucher,

        COALESCE(sm.origin, {sm_ref}, sp.name, '')           AS particulars,

        CASE
            WHEN src_loc.usage = 'supplier'                          THEN 'IN'
            WHEN dest_loc.usage = 'customer'                         THEN 'OUT'
            WHEN src_loc.usage = 'customer'                          THEN 'IN'
            WHEN dest_loc.usage = 'supplier'                         THEN 'OUT'
            WHEN src_loc.usage  IN ('internal','transit')
             AND dest_loc.usage IN ('internal','transit')            THEN 'INT'
            WHEN dest_loc.usage = 'internal'                         THEN 'IN'
            WHEN src_loc.usage  = 'internal'                         THEN 'OUT'
            ELSE 'INT'
        END                                                  AS move_type,

        CASE
            WHEN dest_loc.usage = 'internal' AND src_loc.usage != 'internal'
                THEN sml.quantity
            WHEN src_loc.usage = 'customer'
                THEN sml.quantity
            ELSE 0
        END                                                  AS rec_qty,

        CASE
            WHEN dest_loc.usage = 'internal' AND src_loc.usage != 'internal'
                THEN {cost_field}
            WHEN src_loc.usage = 'customer'
                THEN {cost_field}
            ELSE 0
        END                                                  AS rec_rate,

        CASE
            WHEN src_loc.usage = 'internal' AND dest_loc.usage != 'internal'
                THEN sml.quantity
            ELSE 0
        END                                                  AS issue_qty,

        CASE
            WHEN src_loc.usage = 'internal' AND dest_loc.usage != 'internal'
                THEN {cost_field}
            ELSE 0
        END                                                  AS issue_rate,

        SUM(
            CASE
                WHEN dest_loc.usage = 'internal' AND src_loc.usage != 'internal'
                    THEN  sml.quantity
                WHEN src_loc.usage = 'customer'
                    THEN  sml.quantity
                WHEN src_loc.usage = 'internal' AND dest_loc.usage != 'internal'
                    THEN -sml.quantity
                ELSE 0
            END
        ) OVER (
            PARTITION BY sml.product_id,
                         COALESCE(wh_src.warehouse_id, wh_dest.warehouse_id)
            ORDER BY sm.date, sml.id
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        )                                                    AS balance,

        {uom_name_sql}                                       AS uom,

        -- invoice_status: use direct FK join (reliable) with human-readable label
        COALESCE(
            CASE
                WHEN {so_cond} THEN
                    CASE {so_inv}
                        WHEN 'invoiced'    THEN 'Invoiced'
                        WHEN 'to invoice'  THEN 'To Invoice'
                        WHEN 'upselling'   THEN 'Upselling'
                        WHEN 'nothing'     THEN 'Nothing'
                        ELSE {so_inv}
                    END
                WHEN {po_cond} THEN
                    CASE {po_inv}
                        WHEN 'invoiced'    THEN 'Invoiced'
                        WHEN 'to invoice'  THEN 'To Invoice'
                        WHEN 'nothing'     THEN 'Nothing'
                        ELSE {po_inv}
                    END
                ELSE NULL
            END,
            ''
        )                                                    AS invoice_status,

        sm.id         AS move_id,
        sm.company_id AS company_id

    FROM stock_move_line sml

    JOIN stock_move sm
        ON sm.id    = sml.move_id
       AND sm.state = 'done'

    JOIN stock_location src_loc  ON src_loc.id  = sml.location_id
    JOIN stock_location dest_loc ON dest_loc.id = sml.location_dest_id

    LEFT JOIN loc_warehouse wh_src
        ON wh_src.location_id = sml.location_id
       AND src_loc.usage = 'internal'

    LEFT JOIN loc_warehouse wh_dest
        ON wh_dest.location_id = sml.location_dest_id
       AND dest_loc.usage = 'internal'

    LEFT JOIN uom_uom    uom_u ON uom_u.id = sml.product_uom_id
    LEFT JOIN stock_picking sp ON sp.id    = sml.picking_id

    {svl_join}
    {aml_pur_join}
    {aml_sale_join}
    {pol_join}
    {sol_join}
    {so_join}
    {po_join}

    WHERE sm.state = 'done'
)

SELECT * FROM ledger
;
        """

        self.env.cr.execute(sql)

    # ------------------------------------------------------------------
    def action_open_delete_wizard(self):
        """Open confirmation wizard to delete selected ledger entries."""
        if not self:
            raise UserError(_('Please select at least one record to delete.'))

        move_ids = self.mapped('move_id').ids
        if not move_ids:
            raise UserError(_('No stock moves linked to the selected records.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Delete Ledger Entries'),
            'res_model': 'product.stock.ledger.delete.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_move_ids': move_ids,
                'default_ledger_count': len(self),
            },
        }

    # ------------------------------------------------------------------
    def write(self, vals):
        raise UserError(_('Stock Ledger records are read-only.'))

    def create(self, vals):
        raise UserError(_('Stock Ledger records are read-only.'))

    def unlink(self):
        raise UserError(_('Stock Ledger records are read-only.'))


# ======================================================================

class ProductStockLedgerDeleteWizard(models.TransientModel):
    """Confirmation wizard — deletes underlying stock.move records."""
    _name = 'product.stock.ledger.delete.wizard'
    _description = 'Delete Stock Ledger Entries'

    move_ids = fields.Many2many(
        'stock.move',
        string='Stock Moves to Delete',
        readonly=True,
    )
    ledger_count = fields.Integer(
        string='Selected Rows',
        readonly=True,
    )
    summary = fields.Html(
        string='Summary',
        compute='_compute_summary',
    )

    def _compute_summary(self):
        for rec in self:
            rows = []
            for move in rec.move_ids:
                rows.append(
                    f"<tr>"
                    f"<td style='padding:4px 10px'>{move.reference or ''}</td>"
                    f"<td style='padding:4px 10px'>{move.date.strftime('%d/%m/%Y') if move.date else ''}</td>"
                    f"<td style='padding:4px 10px'>{move.product_id.display_name or ''}</td>"
                    f"<td style='padding:4px 10px; text-align:right'>{move.quantity:.4f}</td>"
                    f"</tr>"
                )
            table = (
                "<table style='width:100%;border-collapse:collapse;font-size:13px'>"
                "<thead><tr style='background:#f5f5f5'>"
                "<th style='padding:6px 10px;text-align:left'>Reference</th>"
                "<th style='padding:6px 10px;text-align:left'>Date</th>"
                "<th style='padding:6px 10px;text-align:left'>Product</th>"
                "<th style='padding:6px 10px;text-align:right'>Quantity</th>"
                "</tr></thead><tbody>"
                + "".join(rows)
                + "</tbody></table>"
            )
            rec.summary = table

    def _table_exists(self, table_name):
        self.env.cr.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = %s
            )
        """, (table_name,))
        return self.env.cr.fetchone()[0]

    def action_confirm_delete(self):
        """Delete stock moves and all related records."""
        self.ensure_one()

        if not self.env.user.has_group('stock.group_stock_manager'):
            raise AccessError(_('Only Inventory Managers can delete stock ledger entries.'))

        move_ids = self.move_ids.ids
        if not move_ids:
            raise UserError(_('No stock moves to delete.'))

        cr = self.env.cr

        if self._table_exists('stock_valuation_layer'):
            cr.execute(
                "DELETE FROM stock_valuation_layer WHERE stock_move_id = ANY(%s)",
                (move_ids,)
            )

        if self._table_exists('stock_move_account_move_line_rel'):
            cr.execute(
                "DELETE FROM stock_move_account_move_line_rel WHERE stock_move_id = ANY(%s)",
                (move_ids,)
            )

        cr.execute(
            "DELETE FROM stock_move_line WHERE move_id = ANY(%s)",
            (move_ids,)
        )

        cr.execute(
            "DELETE FROM stock_move WHERE id = ANY(%s)",
            (move_ids,)
        )

        cr.execute("""
            DELETE FROM stock_quant
            WHERE quantity = 0
              AND reserved_quantity = 0
        """)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Deleted Successfully'),
                'message': _(
                    '%d stock move(s) removed from the ledger.'
                ) % len(move_ids),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}















# from odoo import models, fields, tools, _
# from odoo.exceptions import UserError, AccessError
#
#
# class ProductStockLedger(models.Model):
#     """
#     SQL-backed read-only model (PostgreSQL VIEW).
#     Compatible with Odoo 19 CE. Handles jsonb translated fields (name, complete_name).
#     """
#     _name = 'product.stock.ledger'
#     _description = 'Product Stock Ledger'
#     _auto = False
#     _order = 'date desc, id desc'
#
#     product_id      = fields.Many2one('product.product', string='Product',         readonly=True)
#     warehouse_id    = fields.Many2one('stock.warehouse',  string='Warehouse',       readonly=True)
#     date            = fields.Datetime(string='_Date_Raw',  readonly=True)
#     date_str        = fields.Char(string='Date',           readonly=True)
#     voucher         = fields.Char(string='Voucher',       readonly=True)
#     particulars     = fields.Char(string='Particulars',   readonly=True)
#     move_type       = fields.Char(string='Type',          readonly=True)
#     rec_qty         = fields.Float(string='Rec. Qty',     readonly=True, digits=(16, 4))
#     rec_rate        = fields.Float(string='Rec. Rate',    readonly=True, digits=(16, 4))
#     issue_qty       = fields.Float(string='Issue Qty',    readonly=True, digits=(16, 4))
#     issue_rate      = fields.Float(string='Issue Rate',   readonly=True, digits=(16, 4))
#     balance         = fields.Float(string='Balance',      readonly=True, digits=(16, 4))
#     uom             = fields.Char(string='Unit',          readonly=True)
#     invoice_status  = fields.Char(string='Invoice Status', readonly=True)
#     move_id         = fields.Many2one('stock.move',       string='Stock Move',      readonly=True)
#     company_id      = fields.Many2one('res.company',      string='Company',         readonly=True)
#
#     # ------------------------------------------------------------------
#     def _table_exists(self, table_name):
#         self.env.cr.execute("""
#             SELECT EXISTS (
#                 SELECT 1 FROM information_schema.tables
#                 WHERE table_schema = 'public' AND table_name = %s
#             )
#         """, (table_name,))
#         return self.env.cr.fetchone()[0]
#
#     def _col_exists(self, table_name, col_name):
#         self.env.cr.execute("""
#             SELECT EXISTS (
#                 SELECT 1 FROM information_schema.columns
#                 WHERE table_schema = 'public'
#                   AND table_name   = %s
#                   AND column_name  = %s
#             )
#         """, (table_name, col_name))
#         return self.env.cr.fetchone()[0]
#
#     def _col_type(self, table_name, col_name):
#         self.env.cr.execute("""
#             SELECT data_type FROM information_schema.columns
#             WHERE table_schema = 'public'
#               AND table_name   = %s
#               AND column_name  = %s
#         """, (table_name, col_name))
#         row = self.env.cr.fetchone()
#         return row[0] if row else None
#
#     def _jsonb_to_text(self, col_expr):
#         return (
#             "COALESCE("
#             f"  ({col_expr})->>'en_US',"
#             f"  (SELECT v FROM jsonb_each_text({col_expr}) AS t(k,v) LIMIT 1),"
#             "  ''"
#             ")"
#         )
#
#     def init(self):
#         tools.drop_view_if_exists(self.env.cr, self._table)
#
#         has_svl = self._table_exists('stock_valuation_layer')
#         has_so  = self._table_exists('sale_order')
#         has_po  = self._table_exists('purchase_order')
#
#         uom_name_type = self._col_type('uom_uom', 'name')
#         if uom_name_type and 'json' in uom_name_type.lower():
#             uom_name_sql = self._jsonb_to_text('uom_u.name')
#         else:
#             uom_name_sql = "COALESCE(uom_u.name::text, '')"
#
#         loc_cn_type = self._col_type('stock_location', 'complete_name')
#         if loc_cn_type and 'json' in loc_cn_type.lower():
#             sl_cn  = "(sl.complete_name->>'en_US')"
#             root_cn = "(root.complete_name->>'en_US')"
#         else:
#             sl_cn   = "sl.complete_name"
#             root_cn = "root.complete_name"
#
#         sm_ref = 'sm.reference' if self._col_exists('stock_move', 'reference') else 'sm.origin'
#
#         so_inv = 'so.invoice_status' if has_so and self._col_exists('sale_order', 'invoice_status') else "NULL::varchar"
#         po_inv = 'po.invoice_status' if has_po and self._col_exists('purchase_order', 'invoice_status') else "NULL::varchar"
#
#         if has_svl:
#             cost_cte = """
# move_cost AS (
#     SELECT
#         stock_move_id,
#         CASE WHEN SUM(ABS(quantity)) > 0
#              THEN SUM(ABS(value)) / SUM(ABS(quantity))
#              ELSE 0
#         END AS unit_cost
#     FROM stock_valuation_layer
#     WHERE stock_move_id IS NOT NULL
#     GROUP BY stock_move_id
# ),"""
#             cost_join  = "LEFT JOIN move_cost mc ON mc.stock_move_id = sm.id"
#             cost_field = "COALESCE(mc.unit_cost, 0)"
#         else:
#             cost_cte   = ""
#             cost_join  = ""
#             cost_field = "0::numeric"
#
#         if has_so:
#             so_join = "LEFT JOIN sale_order so ON so.name = sm.origin"
#             so_name = "so.name"
#             so_cond = "so.id IS NOT NULL"
#         else:
#             so_join = ""
#             so_name = "NULL::varchar"
#             so_cond = "FALSE"
#
#         if has_po:
#             po_join = "LEFT JOIN purchase_order po ON po.name = sm.origin"
#             po_name = "po.name"
#             po_cond = "po.id IS NOT NULL"
#         else:
#             po_join = ""
#             po_name = "NULL::varchar"
#             po_cond = "FALSE"
#
#         sql = f"""
# CREATE OR REPLACE VIEW product_stock_ledger AS
#
# WITH
# loc_warehouse AS (
#     SELECT DISTINCT ON (sl.id)
#         sl.id AS location_id,
#         sw.id AS warehouse_id
#     FROM stock_location sl
#     JOIN stock_warehouse sw
#         ON sl.id = sw.lot_stock_id
#         OR {sl_cn} LIKE (
#             SELECT {root_cn} || '/%'
#             FROM stock_location root
#             WHERE root.id = sw.lot_stock_id
#         )
#     WHERE sl.usage = 'internal'
#     ORDER BY sl.id, sw.id
# ),
# {cost_cte}
#
# ledger AS (
#     SELECT
#         sml.id                                               AS id,
#         sml.product_id                                       AS product_id,
#         COALESCE(wh_src.warehouse_id, wh_dest.warehouse_id) AS warehouse_id,
#         sm.date                                              AS date,
#         TO_CHAR(sm.date AT TIME ZONE 'UTC', 'DD/MM/YY')     AS date_str,
#
#         COALESCE({so_name}, {po_name}, sp.name, sm.origin, {sm_ref}, '')
#                                                              AS voucher,
#
#         COALESCE(sm.origin, {sm_ref}, sp.name, '')           AS particulars,
#
#         CASE
#             WHEN src_loc.usage = 'supplier'                          THEN 'IN'
#             WHEN dest_loc.usage = 'customer'                         THEN 'OUT'
#             WHEN src_loc.usage = 'customer'                          THEN 'IN'
#             WHEN dest_loc.usage = 'supplier'                         THEN 'OUT'
#             WHEN src_loc.usage  IN ('internal','transit')
#              AND dest_loc.usage IN ('internal','transit')            THEN 'INT'
#             WHEN dest_loc.usage = 'internal'                         THEN 'IN'
#             WHEN src_loc.usage  = 'internal'                         THEN 'OUT'
#             ELSE 'INT'
#         END                                                  AS move_type,
#
#         CASE
#             WHEN dest_loc.usage = 'internal' AND src_loc.usage != 'internal'
#                 THEN sml.quantity
#             WHEN src_loc.usage = 'customer'
#                 THEN sml.quantity
#             ELSE 0
#         END                                                  AS rec_qty,
#
#         CASE
#             WHEN dest_loc.usage = 'internal' AND src_loc.usage != 'internal'
#                 THEN {cost_field}
#             WHEN src_loc.usage = 'customer'
#                 THEN {cost_field}
#             ELSE 0
#         END                                                  AS rec_rate,
#
#         CASE
#             WHEN src_loc.usage = 'internal' AND dest_loc.usage != 'internal'
#                 THEN sml.quantity
#             ELSE 0
#         END                                                  AS issue_qty,
#
#         CASE
#             WHEN src_loc.usage = 'internal' AND dest_loc.usage != 'internal'
#                 THEN {cost_field}
#             ELSE 0
#         END                                                  AS issue_rate,
#
#         SUM(
#             CASE
#                 WHEN dest_loc.usage = 'internal' AND src_loc.usage != 'internal'
#                     THEN  sml.quantity
#                 WHEN src_loc.usage = 'customer'
#                     THEN  sml.quantity
#                 WHEN src_loc.usage = 'internal' AND dest_loc.usage != 'internal'
#                     THEN -sml.quantity
#                 ELSE 0
#             END
#         ) OVER (
#             PARTITION BY sml.product_id,
#                          COALESCE(wh_src.warehouse_id, wh_dest.warehouse_id)
#             ORDER BY sm.date, sml.id
#             ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
#         )                                                    AS balance,
#
#         {uom_name_sql}                                       AS uom,
#
#         COALESCE(CASE
#             WHEN {so_cond} THEN {so_inv}
#             WHEN {po_cond} THEN {po_inv}
#             ELSE NULL
#         END, '')                                             AS invoice_status,
#
#         sm.id         AS move_id,
#         sm.company_id AS company_id
#
#     FROM stock_move_line sml
#
#     JOIN stock_move sm
#         ON sm.id    = sml.move_id
#        AND sm.state = 'done'
#
#     JOIN stock_location src_loc  ON src_loc.id  = sml.location_id
#     JOIN stock_location dest_loc ON dest_loc.id = sml.location_dest_id
#
#     LEFT JOIN loc_warehouse wh_src
#         ON wh_src.location_id = sml.location_id
#        AND src_loc.usage = 'internal'
#
#     LEFT JOIN loc_warehouse wh_dest
#         ON wh_dest.location_id = sml.location_dest_id
#        AND dest_loc.usage = 'internal'
#
#     LEFT JOIN uom_uom    uom_u ON uom_u.id = sml.product_uom_id
#     LEFT JOIN stock_picking sp ON sp.id    = sml.picking_id
#
#     {cost_join}
#     {so_join}
#     {po_join}
#
#     WHERE sm.state = 'done'
# )
#
# SELECT * FROM ledger
# ;
#         """
#
#         self.env.cr.execute(sql)
#
#     # ------------------------------------------------------------------
#     def action_open_delete_wizard(self):
#         """Open confirmation wizard to delete selected ledger entries."""
#         if not self:
#             raise UserError(_('Please select at least one record to delete.'))
#
#         # Collect stock move IDs from selected ledger rows
#         move_ids = self.mapped('move_id').ids
#         if not move_ids:
#             raise UserError(_('No stock moves linked to the selected records.'))
#
#         return {
#             'type': 'ir.actions.act_window',
#             'name': _('Delete Ledger Entries'),
#             'res_model': 'product.stock.ledger.delete.wizard',
#             'view_mode': 'form',
#             'target': 'new',
#             'context': {
#                 'default_move_ids': move_ids,
#                 'default_ledger_count': len(self),
#             },
#         }
#
#     # ------------------------------------------------------------------
#     def write(self, vals):
#         raise UserError(_('Stock Ledger records are read-only.'))
#
#     def create(self, vals):
#         raise UserError(_('Stock Ledger records are read-only.'))
#
#     def unlink(self):
#         raise UserError(_('Stock Ledger records are read-only.'))
#
#
# # ======================================================================
#
# class ProductStockLedgerDeleteWizard(models.TransientModel):
#     """Confirmation wizard — deletes underlying stock.move records."""
#     _name = 'product.stock.ledger.delete.wizard'
#     _description = 'Delete Stock Ledger Entries'
#
#     move_ids = fields.Many2many(
#         'stock.move',
#         string='Stock Moves to Delete',
#         readonly=True,
#     )
#     ledger_count = fields.Integer(
#         string='Selected Rows',
#         readonly=True,
#     )
#     summary = fields.Html(
#         string='Summary',
#         compute='_compute_summary',
#     )
#
#     def _compute_summary(self):
#         for rec in self:
#             rows = []
#             for move in rec.move_ids:
#                 rows.append(
#                     f"<tr>"
#                     f"<td style='padding:4px 10px'>{move.reference or ''}</td>"
#                     f"<td style='padding:4px 10px'>{move.date.strftime('%d/%m/%Y') if move.date else ''}</td>"
#                     f"<td style='padding:4px 10px'>{move.product_id.display_name or ''}</td>"
#                     f"<td style='padding:4px 10px; text-align:right'>{move.quantity:.4f}</td>"
#                     f"</tr>"
#                 )
#             table = (
#                 "<table style='width:100%;border-collapse:collapse;font-size:13px'>"
#                 "<thead><tr style='background:#f5f5f5'>"
#                 "<th style='padding:6px 10px;text-align:left'>Reference</th>"
#                 "<th style='padding:6px 10px;text-align:left'>Date</th>"
#                 "<th style='padding:6px 10px;text-align:left'>Product</th>"
#                 "<th style='padding:6px 10px;text-align:right'>Quantity</th>"
#                 "</tr></thead><tbody>"
#                 + "".join(rows)
#                 + "</tbody></table>"
#             )
#             rec.summary = table
#
#     def _table_exists(self, table_name):
#         """Check if a PostgreSQL table exists in the public schema."""
#         self.env.cr.execute("""
#             SELECT EXISTS (
#                 SELECT 1 FROM information_schema.tables
#                 WHERE table_schema = 'public'
#                   AND table_name = %s
#             )
#         """, (table_name,))
#         return self.env.cr.fetchone()[0]
#
#     def action_confirm_delete(self):
#         """Delete stock moves and all related records."""
#         self.ensure_one()
#
#         # Only inventory managers can delete
#         if not self.env.user.has_group('stock.group_stock_manager'):
#             raise AccessError(_('Only Inventory Managers can delete stock ledger entries.'))
#
#         move_ids = self.move_ids.ids
#         if not move_ids:
#             raise UserError(_('No stock moves to delete.'))
#
#         cr = self.env.cr
#
#         # 1. Delete stock valuation layers (only if table exists — CE may not have it)
#         if self._table_exists('stock_valuation_layer'):
#             cr.execute(
#                 "DELETE FROM stock_valuation_layer WHERE stock_move_id = ANY(%s)",
#                 (move_ids,)
#             )
#
#         # 2. Delete stock account move line links (if table exists)
#         if self._table_exists('stock_move_account_move_line_rel'):
#             cr.execute(
#                 "DELETE FROM stock_move_account_move_line_rel WHERE stock_move_id = ANY(%s)",
#                 (move_ids,)
#             )
#
#         # 3. Delete stock move lines
#         cr.execute(
#             "DELETE FROM stock_move_line WHERE move_id = ANY(%s)",
#             (move_ids,)
#         )
#
#         # 4. Delete stock moves
#         cr.execute(
#             "DELETE FROM stock_move WHERE id = ANY(%s)",
#             (move_ids,)
#         )
#
#         # 4. Clean up orphan zero quants
#         cr.execute("""
#             DELETE FROM stock_quant
#             WHERE quantity = 0
#               AND reserved_quantity = 0
#         """)
#
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'title': _('Deleted Successfully'),
#                 'message': _(
#                     '%d stock move(s) removed from the ledger.'
#                 ) % len(move_ids),
#                 'type': 'success',
#                 'sticky': False,
#                 'next': {'type': 'ir.actions.act_window_close'},
#             },
#         }
#
#     def action_cancel(self):
#         return {'type': 'ir.actions.act_window_close'}
#
