"""Shared utility helpers for the Ticket Master application."""

import uuid
from functools import wraps

from flask import flash, redirect, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash  # noqa: F401


# ── Authentication decorators ───────────────────────────────────────


def login_required(f):
    """Redirect anonymous visitors to the login page."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in first.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Restrict access to admin users only (also checks login)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in first.', 'error')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


# ── Ticket helpers ──────────────────────────────────────────────────


def generate_ticket_code() -> str:
    """Return a new UUID-4 string suitable for use as a ticket code."""
    return str(uuid.uuid4())


def generate_seat_label(index: int) -> str:
    """Return a zero-padded seat label like S-001, S-002, …"""
    return f"S-{index:03d}"
