"""Authentication routes – login, register, logout."""

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from psycopg.rows import dict_row
from werkzeug.security import check_password_hash, generate_password_hash

auth_bp = Blueprint('auth', __name__)


# ── Login ───────────────────────────────────────────────────────────


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('auth/login.html')

    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')

    if not email or not password:
        flash('Please fill in all fields.', 'error')
        return redirect(url_for('auth.login'))

    with current_app.pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT * FROM users WHERE email = %s",
                (email,),
            )
            user = cur.fetchone()

    if user is None or not check_password_hash(user['password_hash'], password):
        flash('Invalid email or password.', 'error')
        return redirect(url_for('auth.login'))

    session['user_id'] = user['id']
    session['username'] = user['username']
    session['role'] = user['role']

    flash('Welcome back!', 'success')
    return redirect(url_for('main.index'))


# ── Register ────────────────────────────────────────────────────────


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('auth/register.html')

    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')

    # ── Validation ──────────────────────────────────────────────────
    if not all([username, email, password, confirm_password]):
        flash('Please fill in all fields.', 'error')
        return redirect(url_for('auth.register'))

    if password != confirm_password:
        flash('Passwords do not match.', 'error')
        return redirect(url_for('auth.register'))

    if len(password) < 6:
        flash('Password must be at least 6 characters.', 'error')
        return redirect(url_for('auth.register'))

    with current_app.pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # Check for existing email
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                flash('An account with that email already exists.', 'error')
                return redirect(url_for('auth.register'))

            # Create user
            hashed = generate_password_hash(password, method='pbkdf2:sha256')
            cur.execute(
                """
                INSERT INTO users (username, email, password_hash, role)
                VALUES (%s, %s, %s, 'customer')
                """,
                (username, email, hashed),
            )
        conn.commit()

    flash('Registration successful! Please log in.', 'success')
    return redirect(url_for('auth.login'))


# ── Logout ──────────────────────────────────────────────────────────


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Logged out.', 'info')
    return redirect(url_for('main.index'))
