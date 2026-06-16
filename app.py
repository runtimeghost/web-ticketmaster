"""Ticket Master – Flask Application Entry Point."""

import atexit
import os
import threading
import time
from datetime import datetime

from flask import Blueprint, Flask, render_template
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from werkzeug.security import generate_password_hash

from config import Config

# ── Application factory ────────────────────────────────────────────


def create_app() -> Flask:
    app = Flask(__name__)

    # Load configuration
    cfg = Config()
    app.config['SECRET_KEY'] = cfg.SECRET_KEY
    app.config['DATABASE_URL'] = cfg.DATABASE_URL

    # ── Connection pool ─────────────────────────────────────────────
    # Use a smaller pool size to prevent exhausting Supabase's limit.
    # Disabling prepare_threshold ensures compatibility with PgBouncer transaction mode.
    pool = ConnectionPool(
        conninfo=cfg.DATABASE_URL,
        min_size=1,
        max_size=4,
        kwargs={"prepare_threshold": None}
    )
    app.pool = pool

    # ── Database initialisation ─────────────────────────────────────
    init_db(app)

    # ── Background lock sweeper ─────────────────────────────────────
    sweeper = threading.Thread(
        target=sweep_expired_locks,
        args=(pool,),
        daemon=True,
    )
    sweeper.start()

    # ── Blueprints ──────────────────────────────────────────────────
    from routes.admin import admin_bp
    from routes.auth import auth_bp
    from routes.booking import booking_bp
    from routes.events import events_bp
    from routes.resale import resale_bp

    # Main index blueprint
    main_bp = Blueprint('main', __name__)

    @main_bp.route('/')
    def index():
        with pool.connection() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT *
                      FROM events
                     WHERE event_date >= CURRENT_DATE
                     ORDER BY event_date ASC
                     LIMIT 6
                    """
                )
                events = cur.fetchall()
        return render_template('index.html', events=events)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(resale_bp, url_prefix='/resale')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # ── Template globals ────────────────────────────────────────────
    app.jinja_env.globals.update(now=datetime.now)

    # ── Cleanup ─────────────────────────────────────────────────────
    atexit.register(pool.close)

    return app


# ── Helpers ─────────────────────────────────────────────────────────


def get_db():
    """Convenience – routes should use ``current_app.pool.connection()``."""
    from flask import current_app
    return current_app.pool.connection()


def init_db(app: Flask) -> None:
    """Execute schema.sql and seed the default admin user."""
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')

    with app.pool.connection() as conn:
        # Run the migration script
        if os.path.exists(schema_path):
            with open(schema_path, 'r', encoding='utf-8') as f:
                sql = f.read()
            conn.execute(sql)
            conn.commit()

        # Seed default admin (password: admin123)
        admin_hash = generate_password_hash('admin123', method='pbkdf2:sha256')
        conn.execute(
            """
            INSERT INTO users (username, email, password_hash, role)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (email) DO NOTHING
            """,
            ('Admin', 'admin@ticketmaster.com', admin_hash, 'admin'),
        )
        conn.commit()


def sweep_expired_locks(pool: ConnectionPool) -> None:
    """Background daemon: every 30 s, release expired ticket locks."""
    while True:
        try:
            with pool.connection() as conn:
                with conn.cursor(row_factory=dict_row) as cur:
                    # Find expired locks
                    cur.execute(
                        """
                        SELECT id, event_id, vip_qty, normal_qty, student_qty
                          FROM ticket_locks
                         WHERE expires_at < NOW()
                        """
                    )
                    expired = cur.fetchall()

                    for lock in expired:
                        # Return seats
                        cur.execute(
                            """
                            UPDATE events
                               SET vip_available = vip_available + %s,
                                   normal_available = normal_available + %s,
                                   student_available = student_available + %s
                             WHERE id = %s
                            """,
                            (lock['vip_qty'], lock['normal_qty'], lock['student_qty'], lock['event_id']),
                        )
                        # Remove the lock
                        cur.execute(
                            "DELETE FROM ticket_locks WHERE id = %s",
                            (lock['id'],),
                        )
                conn.commit()
        except Exception:
            # Pool may be closed on shutdown – silently ignore
            pass

        time.sleep(30)


# ── Run ─────────────────────────────────────────────────────────────

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
