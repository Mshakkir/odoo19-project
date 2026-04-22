from odoo import models, fields, tools, _
from odoo.exceptions import UserError, AccessError


class ProductStockLedger(models.Model):
    """
    SQL-backed read-only model (PostgreSQL VIEW).
    Compatible with Odoo 19 CE. Handles jsonb translated fields.

    Rate source priority (CE-safe):
      1. account_move_line.price_unit  (posted vendor bill / customer invoice)
      2. stock_valuation_layer         (if available)
      3. purchase_order_line / sale_order_line price_unit fallback
      4. 0
    """
    _name = 'product.stock.ledger'
    _description = 'Product Stock Ledger'
    _auto = False
    _order = 'date desc, id desc'

    product_id      = fields.Many2one('product.product', string='Product',          readonly=True)
    warehouse_id    = fields.Many2one('stock.warehouse',  string='Warehouse',        readonly=True)
    date            = fields.Datetime(string='_Date_Raw',  readonly=True)
    date_str        = fields.Char(string='Date',           readonly=True)
    voucher         = fields.Char(string='Voucher',        readonly=True)
    particulars     = fields.Char(string='Particulars',    readonly=True)
    move_type       = fields.Char(string='Type',           readonly=True)
    rec_qty         = fields.Float(string='Rec. Qty',      readonly=True, digits=(16, 4))
    rec_rate        = fields.Float(string='Rec. Rate',     readonly=True, digits=(16, 4))
    issue_qty       = fields.Float(string='Issue Qty',     readonly=True, digits=(16, 4))
    issue_rate      = fields.Float(string='Issue Rate',    readonly=True, digits=(16, 4))
    balance         = fields.Float(string='Balance',       readonly=True, digits=(16, 4))
    uom             = fields.Char(string='Unit',           readonly=True)
    invoice_status  = fields.Char(string='Invoice Status', readonly=True)
    move_id         = fields.Many2one('stock.move',        string='Stock Move',      readonly=True)
    company_id      = fields.Many2one('res.company',       string='Company',         readonly=True)

    # ── Schema helpers ─────────────────────────────────────────────────────────

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
                  AND table_name  = %s
                  AND column_name = %s
            )
        """, (table_name, col_name))
        return self.env.cr.fetchone()[0]

    def _col_type(self, table_name, col_name):
        self.env.cr.execute("""
            SELECT data_type FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name  = %s
              AND column_name = %s
        """, (table_name, col_name))
        row = self.env.cr.fetchone()
        return row[0] if row else None

    def _jsonb_text(self, expr):
        return (
            f"COALESCE(({expr})->>'en_US',"
            f" (SELECT v FROM jsonb_each_text({expr}) AS j(k,v) LIMIT 1),"
            f" '')"
        )

    # ── View init ──────────────────────────────────────────────────────────────

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        # ── Feature detection ──────────────────────────────────────────────
        has_svl     = self._table_exists('stock_valuation_layer')
        has_so      = self._table_exists('sale_order')
        has_po      = self._table_exists('purchase_order')
        has_pol_tbl = self._table_exists('purchase_order_line')
        has_sol_tbl = self._table_exists('sale_order_line')
        has_sol_rel = self._table_exists('sale_order_line_invoice_rel')

        has_sm_pol  = self._col_exists('stock_move', 'purchase_line_id')
        has_sm_sol  = self._col_exists('stock_move', 'sale_line_id')
        has_sm_said = self._col_exists('stock_move', 'sale_id')
        has_sm_poid = self._col_exists('stock_move', 'purchase_id')
        has_aml_pol = self._col_exists('account_move_line', 'purchase_line_id')

        # ── Translated field handling ──────────────────────────────────────
        uom_type = self._col_type('uom_uom', 'name')
        uom_sql  = self._jsonb_text('uom_u.name') if uom_type and 'json' in uom_type else "COALESCE(uom_u.name::text,'')"

        loc_type = self._col_type('stock_location', 'complete_name')
        if loc_type and 'json' in loc_type:
            sl_cn   = "(sl.complete_name->>'en_US')"
            root_cn = "(root.complete_name->>'en_US')"
        else:
            sl_cn   = "sl.complete_name"
            root_cn = "root.complete_name"

        sm_ref = 'sm.reference' if self._col_exists('stock_move', 'reference') else 'sm.origin'

        # ── Build optional CTE list ────────────────────────────────────────
        # Each entry is a (name, body_sql) tuple.
        # We assemble them at the end — this avoids any trailing-comma issues.
        cte_list = []   # list of "name AS ( ... )" strings, NO trailing commas

        # loc_warehouse — always present
        cte_list.append(f"""loc_warehouse AS (
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
)""")

        # svl_cost — stock valuation layer (Enterprise / CE with costing)
        if has_svl:
            cte_list.append("""svl_cost AS (
    SELECT
        stock_move_id,
        CASE WHEN SUM(ABS(quantity)) > 0
             THEN SUM(ABS(value)) / SUM(ABS(quantity))
             ELSE 0
        END AS unit_cost
    FROM stock_valuation_layer
    WHERE stock_move_id IS NOT NULL
    GROUP BY stock_move_id
)""")

        # aml_purchase_cost — unit price from posted vendor bills
        if has_aml_pol and has_sm_pol:
            cte_list.append("""aml_purchase_cost AS (
    SELECT DISTINCT ON (sm2.id)
        sm2.id          AS stock_move_id,
        aml.price_unit  AS unit_cost
    FROM stock_move sm2
    JOIN account_move_line aml
        ON aml.purchase_line_id = sm2.purchase_line_id
       AND aml.purchase_line_id IS NOT NULL
    JOIN account_move am
        ON am.id        = aml.move_id
       AND am.move_type = 'in_invoice'
       AND am.state     = 'posted'
    WHERE sm2.purchase_line_id IS NOT NULL
    ORDER BY sm2.id, am.invoice_date DESC
)""")

        # aml_sale_cost — unit price from posted customer invoices (via SO link)
        if has_sol_rel and has_sm_sol:
            cte_list.append("""aml_sale_cost AS (
    SELECT DISTINCT ON (sm2.id)
        sm2.id          AS stock_move_id,
        aml.price_unit  AS unit_cost
    FROM stock_move sm2
    JOIN sale_order_line_invoice_rel rel
        ON rel.order_line_id = sm2.sale_line_id
    JOIN account_move_line aml
        ON aml.id = rel.invoice_line_id
    JOIN account_move am
        ON am.id        = aml.move_id
       AND am.move_type = 'out_invoice'
       AND am.state     = 'posted'
    WHERE sm2.sale_line_id IS NOT NULL
    ORDER BY sm2.id, am.invoice_date DESC
)""")

        # direct_purchase_cost — for vendor bills created WITHOUT a purchase order
        # Match by: same product + same partner (vendor) + invoice date within ±7 days of picking date
        # Only used when no PO link exists on the stock move
        cte_list.append("""direct_purchase_cost AS (
    SELECT DISTINCT ON (sm2.id)
        sm2.id         AS stock_move_id,
        aml.price_unit AS unit_cost,
        am.name        AS invoice_name,
        CASE am.state
            WHEN 'posted' THEN 'Invoiced'
            WHEN 'draft'  THEN 'Draft'
            ELSE am.state
        END            AS invoice_status
    FROM stock_move sm2
    JOIN stock_picking sp2
        ON sp2.id = sm2.picking_id
    JOIN stock_location src2  ON src2.id  = sm2.location_id
    JOIN stock_location dest2 ON dest2.id = sm2.location_dest_id
    JOIN account_move am
        ON am.partner_id  = sp2.partner_id
       AND am.move_type   = 'in_invoice'
       AND am.state       = 'posted'
       AND am.invoice_date BETWEEN (sm2.date::date - INTERVAL '7 days')
                                AND (sm2.date::date + INTERVAL '7 days')
    JOIN account_move_line aml
        ON aml.move_id    = am.id
       AND aml.product_id = sm2.product_id
       AND aml.price_unit > 0
    WHERE sm2.state = 'done'
      AND dest2.usage = 'internal'
      AND src2.usage  != 'internal'
      AND sm2.purchase_line_id IS NULL
    ORDER BY sm2.id, ABS((am.invoice_date - sm2.date::date)::integer)
)""")

        # direct_sale_cost — for customer invoices created WITHOUT a sale order
        # Match by: same product + same partner (customer) + invoice date within ±7 days of picking date
        # Only used when no SO link exists on the stock move
        cte_list.append("""direct_sale_cost AS (
    SELECT DISTINCT ON (sm2.id)
        sm2.id         AS stock_move_id,
        aml.price_unit AS unit_cost,
        am.name        AS invoice_name,
        CASE am.state
            WHEN 'posted' THEN 'Invoiced'
            WHEN 'draft'  THEN 'Draft'
            ELSE am.state
        END            AS invoice_status
    FROM stock_move sm2
    JOIN stock_picking sp2
        ON sp2.id = sm2.picking_id
    JOIN stock_location src2  ON src2.id  = sm2.location_id
    JOIN stock_location dest2 ON dest2.id = sm2.location_dest_id
    JOIN account_move am
        ON am.partner_id  = sp2.partner_id
       AND am.move_type   = 'out_invoice'
       AND am.state       = 'posted'
       AND am.invoice_date BETWEEN (sm2.date::date - INTERVAL '7 days')
                                AND (sm2.date::date + INTERVAL '7 days')
    JOIN account_move_line aml
        ON aml.move_id    = am.id
       AND aml.product_id = sm2.product_id
       AND aml.price_unit > 0
    WHERE sm2.state = 'done'
      AND src2.usage  = 'internal'
      AND dest2.usage != 'internal'
      AND sm2.sale_line_id IS NULL
    ORDER BY sm2.id, ABS((am.invoice_date - sm2.date::date)::integer)
)""")

        # so_invoice_ref — get the invoice number for SO-linked stock moves
        # Links: stock_move.sale_line_id → sale_order_line_invoice_rel → account_move_line → account_move
        if has_sol_rel and has_sm_sol:
            cte_list.append("""so_invoice_ref AS (
    SELECT DISTINCT ON (sm2.id)
        sm2.id   AS stock_move_id,
        am.name  AS invoice_name,
        CASE {so_inv_status}
            WHEN 'invoiced'   THEN 'Invoiced'
            WHEN 'to invoice' THEN 'To Invoice'
            WHEN 'upselling'  THEN 'Upselling'
            WHEN 'nothing'    THEN 'Nothing'
            ELSE COALESCE({so_inv_status}, '')
        END      AS invoice_status
    FROM stock_move sm2
    JOIN sale_order_line_invoice_rel rel
        ON rel.order_line_id = sm2.sale_line_id
    JOIN account_move_line aml
        ON aml.id = rel.invoice_line_id
    JOIN account_move am
        ON am.id        = aml.move_id
       AND am.move_type = 'out_invoice'
       AND am.state     = 'posted'
    WHERE sm2.sale_line_id IS NOT NULL
    ORDER BY sm2.id, am.invoice_date DESC
)""".format(
    so_inv_status="so2.invoice_status" if has_so and self._col_exists('sale_order', 'invoice_status') else "am.state"
))

        # po_invoice_ref — get the invoice number for PO-linked stock moves
        # Links: stock_move.purchase_line_id → account_move_line.purchase_line_id → account_move
        if has_aml_pol and has_sm_pol:
            cte_list.append("""po_invoice_ref AS (
    SELECT DISTINCT ON (sm2.id)
        sm2.id   AS stock_move_id,
        am.name  AS invoice_name,
        CASE {po_inv_status}
            WHEN 'invoiced'   THEN 'Invoiced'
            WHEN 'to invoice' THEN 'To Invoice'
            WHEN 'nothing'    THEN 'Nothing'
            ELSE COALESCE({po_inv_status}, '')
        END      AS invoice_status
    FROM stock_move sm2
    JOIN account_move_line aml
        ON aml.purchase_line_id = sm2.purchase_line_id
       AND aml.purchase_line_id IS NOT NULL
    JOIN account_move am
        ON am.id        = aml.move_id
       AND am.move_type = 'in_invoice'
       AND am.state     = 'posted'
    WHERE sm2.purchase_line_id IS NOT NULL
    ORDER BY sm2.id, am.invoice_date DESC
)""".format(
    po_inv_status="po2.invoice_status" if has_po and self._col_exists('purchase_order', 'invoice_status') else "am.state"
))

        # pol_cost — purchase order line price fallback
        if has_pol_tbl and has_sm_pol:
            cte_list.append("""pol_cost AS (
    SELECT sm2.id AS stock_move_id, pol.price_unit AS unit_cost
    FROM stock_move sm2
    JOIN purchase_order_line pol ON pol.id = sm2.purchase_line_id
    WHERE sm2.purchase_line_id IS NOT NULL
)""")

        # sol_cost — sale order line price fallback
        if has_sol_tbl and has_sm_sol:
            cte_list.append("""sol_cost AS (
    SELECT sm2.id AS stock_move_id, sol.price_unit AS unit_cost
    FROM stock_move sm2
    JOIN sale_order_line sol ON sol.id = sm2.sale_line_id
    WHERE sm2.sale_line_id IS NOT NULL
)""")

        # ── CTE body: join each CTE with ",\n" separator ───────────────────
        # No trailing comma ever — each item has NO trailing comma.
        ctes_sql = ",\n".join(cte_list)

        # ── Rate field expressions ─────────────────────────────────────────
        svl_f    = "svl.unit_cost"   if has_svl                    else "NULL::numeric"
        apc_f    = "apc.unit_cost"   if has_aml_pol and has_sm_pol else "NULL::numeric"
        asc_f    = "asc2.unit_cost"  if has_sol_rel and has_sm_sol else "NULL::numeric"
        polc_f   = "polc.unit_cost"  if has_pol_tbl and has_sm_pol else "NULL::numeric"
        solc_f   = "solc.unit_cost"  if has_sol_tbl and has_sm_sol else "NULL::numeric"
        # direct invoice rates — always present (CTEs are always added)
        dpc_f    = "dpc.unit_cost"   # direct_purchase_cost
        dsc_f    = "dsc.unit_cost"   # direct_sale_cost

        cost_field = f"""COALESCE(
            CASE
                -- IN moves (receipt): order-linked bill first, then direct bill, then SVL/POL
                WHEN dest_loc.usage = 'internal' AND src_loc.usage != 'internal'
                    THEN COALESCE({apc_f}, {dpc_f}, {svl_f}, {polc_f})
                WHEN src_loc.usage = 'customer'
                    THEN COALESCE({apc_f}, {dpc_f}, {svl_f}, {polc_f})
                -- OUT moves (delivery): order-linked invoice first, then direct invoice, then SVL/SOL
                WHEN src_loc.usage = 'internal' AND dest_loc.usage != 'internal'
                    THEN COALESCE({asc_f}, {dsc_f}, {svl_f}, {solc_f})
                ELSE COALESCE({svl_f}, {apc_f}, {dpc_f}, {asc_f}, {dsc_f}, {polc_f}, {solc_f})
            END,
            0
        )"""

        # ── JOIN lines ────────────────────────────────────────────────────
        svl_join  = "LEFT JOIN svl_cost svl             ON svl.stock_move_id  = sm.id" if has_svl else ""
        apc_join  = "LEFT JOIN aml_purchase_cost apc    ON apc.stock_move_id  = sm.id" if has_aml_pol and has_sm_pol else ""
        asc_join  = "LEFT JOIN aml_sale_cost asc2       ON asc2.stock_move_id = sm.id" if has_sol_rel and has_sm_sol else ""
        polc_join = "LEFT JOIN pol_cost polc             ON polc.stock_move_id = sm.id" if has_pol_tbl and has_sm_pol else ""
        solc_join = "LEFT JOIN sol_cost solc             ON solc.stock_move_id = sm.id" if has_sol_tbl and has_sm_sol else ""
        # direct cost joins — always active (CTEs are always appended)
        dpc_join  = "LEFT JOIN direct_purchase_cost dpc ON dpc.stock_move_id  = sm.id"
        dsc_join  = "LEFT JOIN direct_sale_cost dsc     ON dsc.stock_move_id  = sm.id"
        # SO/PO invoice ref joins
        sir_join  = "LEFT JOIN so_invoice_ref sir ON sir.stock_move_id = sm.id" if has_sol_rel and has_sm_sol else ""
        pir_join  = "LEFT JOIN po_invoice_ref pir ON pir.stock_move_id = sm.id" if has_aml_pol and has_sm_pol else ""
        sir_inv   = "sir.invoice_name"   if has_sol_rel and has_sm_sol else "NULL::varchar"
        pir_inv   = "pir.invoice_name"   if has_aml_pol and has_sm_pol else "NULL::varchar"
        sir_status = "sir.invoice_status" if has_sol_rel and has_sm_sol else "NULL::varchar"
        pir_status = "pir.invoice_status" if has_aml_pol and has_sm_pol else "NULL::varchar"

        # ── Sale Order join ────────────────────────────────────────────────
        if has_so and has_sm_sol:
            if has_sm_said:
                so_join = "LEFT JOIN sale_order so ON so.id = sm.sale_id"
            else:
                so_join = ("LEFT JOIN sale_order_line _sol ON _sol.id = sm.sale_line_id "
                           "LEFT JOIN sale_order so ON so.id = _sol.order_id")
            so_name = "so.name"
            so_cond = "so.id IS NOT NULL"
            so_inv  = "so.invoice_status" if self._col_exists('sale_order', 'invoice_status') else "NULL::varchar"
        else:
            so_join = ""
            so_name = "NULL::varchar"
            so_cond = "FALSE"
            so_inv  = "NULL::varchar"

        # ── Purchase Order join ────────────────────────────────────────────
        if has_po and has_sm_pol:
            if has_sm_poid:
                po_join = "LEFT JOIN purchase_order po ON po.id = sm.purchase_id"
            else:
                po_join = ("LEFT JOIN purchase_order_line _pol ON _pol.id = sm.purchase_line_id "
                           "LEFT JOIN purchase_order po ON po.id = _pol.order_id")
            po_name = "po.name"
            po_cond = "po.id IS NOT NULL"
            po_inv  = "po.invoice_status" if self._col_exists('purchase_order', 'invoice_status') else "NULL::varchar"
        else:
            po_join = ""
            po_name = "NULL::varchar"
            po_cond = "FALSE"
            po_inv  = "NULL::varchar"

        # ── Assemble final SQL ─────────────────────────────────────────────
        sql = (
            "CREATE OR REPLACE VIEW product_stock_ledger AS\n"
            "WITH\n"
            + ctes_sql +
            f""",
ledger AS (
    SELECT
        sml.id                                               AS id,
        sml.product_id                                       AS product_id,
        COALESCE(wh_src.warehouse_id, wh_dest.warehouse_id) AS warehouse_id,
        sm.date                                              AS date,
        TO_CHAR(sm.date AT TIME ZONE 'UTC', 'DD/MM/YY')     AS date_str,

        -- Voucher: for SO/PO entries show the picking (receipt/delivery) number
        -- For direct invoices sm.origin already holds the invoice ref
        COALESCE(
            sp.name,                           -- picking name = WH/IN/xxxxx or WH/OUT/xxxxx (highest priority)
            {so_name}, {po_name},              -- order ref fallback
            sm.origin, {sm_ref}, ''
        )                                                    AS voucher,
        -- Particulars: show the linked invoice number
        -- SO/PO entries: get from so_invoice_ref / po_invoice_ref CTEs
        -- Direct invoice entries: get from direct_purchase_cost / direct_sale_cost CTEs
        COALESCE(
            {sir_inv},                        -- SO-linked invoice number
            {pir_inv},                        -- PO-linked invoice number
            dpc.invoice_name,                 -- direct purchase invoice number
            dsc.invoice_name,                 -- direct sale invoice number
            sm.origin, {sm_ref}, ''
        )                                                    AS particulars,

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

        {uom_sql}                                            AS uom,

        -- Invoice status: SO/PO entries use order-level status
        -- Direct invoice entries use the invoice ref CTE status
        COALESCE(
            CASE
                WHEN {so_cond} THEN {sir_status}  -- SO-linked: from so_invoice_ref
                WHEN {po_cond} THEN {pir_status}  -- PO-linked: from po_invoice_ref
                ELSE NULL
            END,
            dpc.invoice_status,               -- direct purchase invoice
            dsc.invoice_status,               -- direct sale invoice
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
    LEFT JOIN uom_uom     uom_u ON uom_u.id = sml.product_uom_id
    LEFT JOIN stock_picking  sp ON sp.id    = sml.picking_id
    {svl_join}
    {apc_join}
    {asc_join}
    {polc_join}
    {solc_join}
    {dpc_join}
    {dsc_join}
    {sir_join}
    {pir_join}
    {so_join}
    {po_join}
    WHERE sm.state = 'done'
)
SELECT * FROM ledger
"""
        )

        self.env.cr.execute(sql)

    # ── Guard methods ──────────────────────────────────────────────────────────

    def action_open_delete_wizard(self):
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

    def write(self, vals):
        raise UserError(_('Stock Ledger records are read-only.'))

    def create(self, vals):
        raise UserError(_('Stock Ledger records are read-only.'))

    def unlink(self):
        raise UserError(_('Stock Ledger records are read-only.'))


# ══════════════════════════════════════════════════════════════════════════════

class ProductStockLedgerDeleteWizard(models.TransientModel):
    _name = 'product.stock.ledger.delete.wizard'
    _description = 'Delete Stock Ledger Entries'

    move_ids = fields.Many2many('stock.move', string='Stock Moves to Delete', readonly=True)
    ledger_count = fields.Integer(string='Selected Rows', readonly=True)
    summary = fields.Html(string='Summary', compute='_compute_summary')

    def _compute_summary(self):
        for rec in self:
            rows = []
            for move in rec.move_ids:
                rows.append(
                    f"<tr>"
                    f"<td style='padding:4px 10px'>{move.reference or ''}</td>"
                    f"<td style='padding:4px 10px'>{move.date.strftime('%d/%m/%Y') if move.date else ''}</td>"
                    f"<td style='padding:4px 10px'>{move.product_id.display_name or ''}</td>"
                    f"<td style='padding:4px 10px;text-align:right'>{move.quantity:.4f}</td>"
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
                WHERE table_schema = 'public' AND table_name = %s
            )
        """, (table_name,))
        return self.env.cr.fetchone()[0]

    def action_confirm_delete(self):
        self.ensure_one()
        if not self.env.user.has_group('stock.group_stock_manager'):
            raise AccessError(_('Only Inventory Managers can delete stock ledger entries.'))
        move_ids = self.move_ids.ids
        if not move_ids:
            raise UserError(_('No stock moves to delete.'))
        cr = self.env.cr
        if self._table_exists('stock_valuation_layer'):
            cr.execute("DELETE FROM stock_valuation_layer WHERE stock_move_id = ANY(%s)", (move_ids,))
        if self._table_exists('stock_move_account_move_line_rel'):
            cr.execute("DELETE FROM stock_move_account_move_line_rel WHERE stock_move_id = ANY(%s)", (move_ids,))
        cr.execute("DELETE FROM stock_move_line WHERE move_id = ANY(%s)", (move_ids,))
        cr.execute("DELETE FROM stock_move WHERE id = ANY(%s)", (move_ids,))
        cr.execute("DELETE FROM stock_quant WHERE quantity = 0 AND reserved_quantity = 0")
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Deleted Successfully'),
                'message': _('%d stock move(s) removed from the ledger.') % len(move_ids),
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
