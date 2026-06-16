"""Event browsing routes."""

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    url_for,
)
from psycopg.rows import dict_row

events_bp = Blueprint('events', __name__)


@events_bp.route('/events')
def list_events():
    """List all events ordered by date."""
    with current_app.pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT *
                  FROM events
                 ORDER BY event_date ASC
                """
            )
            events = cur.fetchall()

    return render_template('events/list.html', events=events)


@events_bp.route('/events/<int:event_id>')
def event_detail(event_id: int):
    """Show a single event's details."""
    with current_app.pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT *
                  FROM events
                 WHERE id = %s
                """,
                (event_id,),
            )
            event = cur.fetchone()

    if event is None:
        flash('Event not found.', 'error')
        return redirect(url_for('events.list_events'))

    return render_template('events/detail.html', event=event)
