# -*- coding: utf-8 -*-
import logging
from odoo import api, models
from .warehouse_analytic_utils import (
    get_user_warehouse,
    get_analytic_from_payment,
    stamp_analytic_on_move_lines,
)

_logger = logging.getLogger(__name__)


def _has_model(env, model_name):
    """Safely check if a model is installed/available in the current environment."""
    return model_name in env.registry


def _match_warehouse_by_name(warehouses, name_to_match):
    """
    Find best-matching warehouse by word-overlap scoring.
    Only matches if score > 0 (at least one meaningful word in common).
    """
    if not name_to_match:
        return False

    target_upper = name_to_match.upper()
    target_words = set(w for w in target_upper.replace('-', ' ').split() if len(w) >= 4)

    best_wh = False
    best_score = 0
    best_unmatched = 999

    for wh in warehouses:
        wh_name_upper = wh.name.upper()
        wh_code_upper = (wh.code or '').upper()
        wh_words = set(w for w in wh_name_upper.replace('-', ' ').split() if len(w) >= 4)

        common = target_words & wh_words
        code_match = wh_code_upper and wh_code_upper in target_upper
        score = len(common) + (1 if code_match else 0)
        unmatched = len(wh_words - target_words)

        if score > best_score or (
            score == best_score and score > 0 and unmatched < best_unmatched
        ):
            best_score = score
            best_unmatched = unmatched
            best_wh = wh

    return best_wh if best_score > 0 else False


def _resolve_analytic_for_statement_line(st_line):
    """
    Resolve the correct analytic account for a bank statement line / BNK1 entry.

    Priority order — designed to avoid cross-branch contamination:

    1. Linked payment record (PBNK1/xxxx) → creator's warehouse
    2. POS session name → warehouse name/code word overlap  [POS-safe]
    3. Journal name → warehouse name/code word overlap
       (generic "Bank" journal will NOT match — intentional)
    4. Session → config → picking_type → warehouse             [POS-safe]
    5. Journal → POS payment method → config → warehouse       [POS-safe]
    6. Current user's warehouse (last resort)

    All POS model accesses are guarded by _has_model() so this works
    even when the point_of_sale module is not installed.
    """
    company_id = st_line.company_id.id
    env = st_line.env

    # -----------------------------------------------------------------
    # Priority 1: Linked payment → creator's warehouse
    # -----------------------------------------------------------------
    payment = getattr(st_line, 'payment_id', False)
    if payment:
        analytic = get_analytic_from_payment(payment)
        if analytic:
            _logger.debug(
                'Stmt analytic P1 payment[%s] creator → %s',
                payment.name, analytic.name,
            )
            return analytic

    # Also check reconciled move lines to find a linked payment
    if st_line.move_id:
        for line in st_line.move_id.line_ids:
            for partial in (line.matched_debit_ids | line.matched_credit_ids):
                other_line = (
                    partial.debit_move_id
                    if partial.debit_move_id != line
                    else partial.credit_move_id
                )
                linked_payment = getattr(other_line.move_id, 'payment_id', False)
                if linked_payment:
                    analytic = get_analytic_from_payment(linked_payment)
                    if analytic:
                        _logger.debug(
                            'Stmt analytic P1b reconciled payment[%s] → %s',
                            linked_payment.name, analytic.name,
                        )
                        return analytic

    # Warehouses with analytic accounts for name-matching
    warehouses = env['stock.warehouse'].search([
        ('analytic_account_id', '!=', False),
        ('company_id', '=', company_id),
    ])

    # -----------------------------------------------------------------
    # Priority 2: POS session name match  [POS-safe]
    # -----------------------------------------------------------------
    session = getattr(st_line, 'pos_session_id', False)
    if session and _has_model(env, 'pos.session'):
        wh = _match_warehouse_by_name(warehouses, session.name)
        if wh:
            _logger.debug(
                'Stmt analytic P2 session[%s] → wh[%s]',
                session.name, wh.name,
            )
            return wh.analytic_account_id

    # -----------------------------------------------------------------
    # Priority 3: Journal name match
    # Generic "Bank" / "Cash" won't match — shop journals like
    # "Cash KDTY" or "Card CHLR" will match correctly.
    # -----------------------------------------------------------------
    journal = getattr(st_line, 'journal_id', False)
    if journal:
        wh = _match_warehouse_by_name(warehouses, journal.name)
        if wh:
            _logger.debug(
                'Stmt analytic P3 journal[%s] → wh[%s]',
                journal.name, wh.name,
            )
            return wh.analytic_account_id

    # -----------------------------------------------------------------
    # Priority 4: session → config → picking_type → warehouse  [POS-safe]
    # -----------------------------------------------------------------
    if session and _has_model(env, 'pos.config'):
        config = getattr(session, 'config_id', False)
        if config:
            picking_type = getattr(config, 'picking_type_id', False)
            if picking_type:
                wh = getattr(picking_type, 'warehouse_id', False)
                if wh and getattr(wh, 'analytic_account_id', False):
                    return wh.analytic_account_id
            wh = getattr(config, 'warehouse_id', False)
            if wh and getattr(wh, 'analytic_account_id', False):
                return wh.analytic_account_id

    # -----------------------------------------------------------------
    # Priority 5: journal → POS payment method → config → warehouse
    # Guarded: only runs if pos.payment.method model exists
    # -----------------------------------------------------------------
    if journal and _has_model(env, 'pos.payment.method'):
        pms = env['pos.payment.method'].search([
            ('journal_id', '=', journal.id),
            ('company_id', '=', company_id),
        ])
        for pm in pms:
            if not _has_model(env, 'pos.config'):
                break
            configs = env['pos.config'].search([
                ('payment_method_ids', 'in', pm.ids),
                ('company_id', '=', company_id),
            ])
            for config in configs:
                picking_type = getattr(config, 'picking_type_id', False)
                if picking_type:
                    wh = getattr(picking_type, 'warehouse_id', False)
                    if wh and getattr(wh, 'analytic_account_id', False):
                        return wh.analytic_account_id
                wh = getattr(config, 'warehouse_id', False)
                if wh and getattr(wh, 'analytic_account_id', False):
                    return wh.analytic_account_id

    # -----------------------------------------------------------------
    # Priority 6: current user's warehouse (last resort)
    # -----------------------------------------------------------------
    wh = get_user_warehouse(st_line.env.user)
    if wh and getattr(wh, 'analytic_account_id', False):
        _logger.debug('Stmt analytic P6 user fallback → wh[%s]', wh.name)
        return wh.analytic_account_id

    return False


def _inject_analytic_into_data(data, analytic):
    if not data or not analytic:
        return data
    key = str(analytic.id)
    for line in data:
        existing = line.get('analytic_distribution') or {}
        if key not in existing:
            new_dist = dict(existing)
            new_dist[key] = 100.0
            line['analytic_distribution'] = new_dist
    return data


def _inject_analytic_into_reconcile_info(reconcile_info, analytic):
    if not reconcile_info or not analytic:
        return reconcile_info
    _inject_analytic_into_data(reconcile_info.get('data', []), analytic)
    return reconcile_info


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    @api.model_create_multi
    def create(self, vals_list):
        st_lines = super().create(vals_list)
        for st_line in st_lines:
            analytic = _resolve_analytic_for_statement_line(st_line)
            if analytic and st_line.move_id:
                stamp_analytic_on_move_lines(st_line.move_id, analytic)
        return st_lines

    def write(self, vals):
        result = super().write(vals)
        if 'pos_session_id' in vals or 'payment_id' in vals:
            for st_line in self:
                analytic = _resolve_analytic_for_statement_line(st_line)
                if analytic and st_line.move_id:
                    stamp_analytic_on_move_lines(st_line.move_id, analytic)
        return result

    def _default_reconcile_data(self, from_unreconcile=False):
        result = super()._default_reconcile_data(from_unreconcile=from_unreconcile)
        analytic = _resolve_analytic_for_statement_line(self)
        if analytic:
            _inject_analytic_into_reconcile_info(result, analytic)
        return result

    def _recompute_suspense_line(self, data, reconcile_auxiliary_id, manual_reference):
        result = super()._recompute_suspense_line(
            data, reconcile_auxiliary_id, manual_reference
        )
        analytic = _resolve_analytic_for_statement_line(self)
        if analytic:
            _inject_analytic_into_reconcile_info(result, analytic)
        return result

    def _reconcile_data_by_model(self, data, reconcile_model, reconcile_auxiliary_id):
        new_data, new_id = super()._reconcile_data_by_model(
            data, reconcile_model, reconcile_auxiliary_id
        )
        analytic = _resolve_analytic_for_statement_line(self)
        if analytic:
            _inject_analytic_into_data(new_data, analytic)
        return new_data, new_id

    def _get_reconcile_line(self, line, kind, is_counterpart=False,
                            max_amount=False, from_unreconcile=False,
                            reconcile_auxiliary_id=False, move=False,
                            is_reconciled=False):
        reconcile_auxiliary_id, lines = super()._get_reconcile_line(
            line, kind,
            is_counterpart=is_counterpart,
            max_amount=max_amount,
            from_unreconcile=from_unreconcile,
            reconcile_auxiliary_id=reconcile_auxiliary_id,
            move=move,
            is_reconciled=is_reconciled,
        )
        analytic = _resolve_analytic_for_statement_line(self)
        if analytic:
            _inject_analytic_into_data(lines, analytic)
        return reconcile_auxiliary_id, lines

    def reconcile_bank_line(self):
        result = super().reconcile_bank_line()
        for st_line in self:
            analytic = _resolve_analytic_for_statement_line(st_line)
            if not analytic or not st_line.move_id:
                continue
            stamp_analytic_on_move_lines(st_line.move_id, analytic)
        return result