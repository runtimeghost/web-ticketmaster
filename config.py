import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Central configuration – values fall back to environment variables."""

    SECRET_KEY = os.environ.get(
        'SECRET_KEY', 'ticket-master-secret-key-change-in-production'
    )

    # ── Supabase PostgreSQL credentials ─────────────────────────────
    # Replace the defaults below with your own, or set the matching
    # environment variables before starting the app.
    DB_HOST     = os.environ.get('DB_HOST',     'YOUR_SUPABASE_HOST')
    DB_PORT     = os.environ.get('DB_PORT',     '5432')
    DB_NAME     = os.environ.get('DB_NAME',     'postgres')
    DB_USER     = os.environ.get('DB_USER',     'postgres')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'YOUR_SUPABASE_PASSWORD')

    @property
    def DATABASE_URL(self):
        """Return a libpq-style connection string for psycopg 3."""
        return (
            f"host={self.DB_HOST} "
            f"port={self.DB_PORT} "
            f"dbname={self.DB_NAME} "
            f"user={self.DB_USER} "
            f"password={self.DB_PASSWORD}"
        )
