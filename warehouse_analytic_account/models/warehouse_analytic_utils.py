# -*- coding: utf-8 -*-
"""
Shared helpers for warehouse analytic resolution.
Imported by account_move.py and reconcile.py.
"""
import logging

_logger = logging.getLogger(__name__)

_WAREHOUSE_FIELDS = ('property_warehouse_id', 'default_warehouse_id', 'warehouse_id')


def get_user_warehouse(user):
    """Return the default warehouse of a res.users record, or False."""
    for fname in _WAREHOUSE_FIELDS:
        if fname in user._fields:
            return getattr(user, fname, False)
    return False


def get_analytic_from_payment(payment):
    """
    Resolve analytic account from an account.payment record.

    Priority:
    1. The user who CREATED the payment (create_uid) → their default warehouse
       This is correct: the person who registered the payment belongs to a branch.
    2. The user who is currently logged in (env.user) as last resort.

    We deliberately avoid resolving from the journal because a generic "Bank"
    journal is shared across branches and has no warehouse meaning on its own.
    """
    if not payment:
        return False

    # Priority 1: creator of the payment
    try:
        creator = payment.env['res.users'].sudo().browse(payment.sudo().create_uid.id)
        wh = get_user_warehouse(creator)
        if wh and wh.analytic_account_id:
            _logger.debug(
                'Payment analytic from creator %s → wh %s',
                creator.name, wh.name,
            )
            return wh.analytic_account_id
    except Exception:
        pass

    # Priority 2: current user
    wh = get_user_warehouse(payment.env.user)
    if wh and wh.analytic_account_id:
        return wh.analytic_account_id

    return False


def get_analytic_from_move(move):
    """
    Resolve the correct analytic account for an account.move.

    - Invoices / bills / refunds  → creating user's warehouse (env.user at write time)
    - Payment entries (move_type='entry') linked to account.payment
        → creator of the payment record
    - Bank statement entries (linked to statement_line_id)
        → resolved via reconcile.py logic (journal/session/payment matching)
    - Plain journal entries
        → current user's warehouse
    """
    move.ensure_one()

    # --- Invoices / Bills / Refunds ---
    if move.move_type in ('in_invoice', 'in_refund', 'out_invoice', 'out_refund'):
        wh = get_user_warehouse(move.env.user)
        if wh and wh.analytic_account_id:
            return wh.analytic_account_id
        return False

    # --- Payment entry (PBNK1, PCSCHL, etc.) ---
    if move.move_type == 'entry':
        payment = getattr(move, 'payment_id', False)
        if payment:
            analytic = get_analytic_from_payment(payment)
            if analytic:
                return analytic

        # Bank statement line entry: handled via reconcile.py hooks, skip here
        # to avoid double-application with wrong user
        st_line = getattr(move, 'statement_line_id', False)
        if st_line:
            # Do NOT apply here — reconcile.py handles it with proper resolution
            return False

        # Plain manual journal entry → current user
        wh = get_user_warehouse(move.env.user)
        if wh and wh.analytic_account_id:
            return wh.analytic_account_id

    return False


def stamp_analytic_on_move_lines(move, analytic_account):
    """
    Write analytic_distribution on all eligible lines of an account.move.
    Uses sudo() to bypass posted-move lock restrictions.
    Skips lines that already carry this analytic.
    """
    if not move or not analytic_account:
        return

    key = str(analytic_account.id)
    lines = move.line_ids.filtered(
        lambda l: l.account_id and not l.display_type
    ) | move.invoice_line_ids.filtered(
        lambda l: l.account_id and not l.display_type
    )

    for line in lines:
        existing = line.analytic_distribution or {}
        if key not in existing:
            new_dist = dict(existing)
            new_dist[key] = 100.0
            try:
                line.sudo().with_context(
                    check_move_validity=False,
                    skip_account_move_synchronization=True,
                ).analytic_distribution = new_dist
                _logger.debug(
                    'Analytic %s → move %s line %s (%s)',
                    analytic_account.name, move.name,
                    line.id, line.account_id.code,
                )
            except Exception as e:
                _logger.warning(
                    'Could not stamp analytic on move %s line %s: %s',
                    move.name, line.id, e,
                )