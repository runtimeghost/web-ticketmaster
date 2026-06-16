"""Resale marketplace routes."""

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

from utils import login_required

resale_bp = Blueprint('resale', __name__)

@resale_bp.route('/create', methods=['POST'])
@login_required
def create():
    user_id = session['user_id']
    ticket_code = request.form.get('ticket_code', '').strip()

    if not ticket_code:
        flash('Ticket code is required.', 'error')
        return redirect(url_for('booking.booking_history'))

    with current_app.pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT t.id AS ticket_id, t.ticket_type,
                       e.vip_price, e.normal_price, e.student_price
                  FROM tickets t
                  JOIN bookings b ON b.id = t.booking_id
                  JOIN events e ON e.id = b.event_id
                 WHERE t.ticket_code = %s
                   AND b.user_id = %s
                """,
                (ticket_code, user_id),
            )
            ticket = cur.fetchone()

            if ticket is None:
                flash('Ticket not found or you do not own it.', 'error')
                return redirect(url_for('booking.booking_history'))

            # Check ticket not already listed
            cur.execute(
                """
                SELECT id FROM resale_requests
                 WHERE ticket_id = %s
                   AND status IN ('pending', 'approved')
                """,
                (ticket['ticket_id'],),
            )
            if cur.fetchone():
                flash('This ticket is already listed for resale.', 'error')
                return redirect(url_for('booking.booking_history'))

            # Calculate 5% loss resale price
            if ticket['ticket_type'] == 'VIP':
                orig_price = float(ticket['vip_price'])
            elif ticket['ticket_type'] == 'Student':
                orig_price = float(ticket['student_price'])
            else:
                orig_price = float(ticket['normal_price'])
                
            resale_price = orig_price * 0.95

            # Create resale request
            cur.execute(
                """
                INSERT INTO resale_requests (ticket_id, seller_id, price, status)
                VALUES (%s, %s, %s, 'pending')
                """,
                (ticket['ticket_id'], user_id, resale_price),
            )

        conn.commit()

    flash('Ticket listed for resale (at 5%% loss). Awaiting admin approval.', 'info')
    return redirect(url_for('booking.booking_history'))

@resale_bp.route('/marketplace')
def marketplace():
    with current_app.pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT rr.id,
                       t.ticket_code, t.ticket_type,
                       e.title      AS event_title,
                       e.event_date,
                       e.event_time,
                       e.venue      AS event_venue,
                       e.vip_price, e.normal_price, e.student_price,
                       rr.price     AS resale_price,
                       u.username   AS seller_username,
                       rr.seller_id
                  FROM resale_requests rr
                  JOIN tickets  t ON t.id  = rr.ticket_id
                  JOIN bookings b ON b.id  = t.booking_id
                  JOIN events   e ON e.id  = b.event_id
                  JOIN users    u ON u.id  = rr.seller_id
                 WHERE rr.status = 'approved'
                 ORDER BY rr.created_at DESC
                """
            )
            raw_tickets = cur.fetchall()
            
            resale_tickets = []
            for item in raw_tickets:
                if item['ticket_type'] == 'VIP':
                    orig_price = float(item['vip_price'])
                elif item['ticket_type'] == 'Student':
                    orig_price = float(item['student_price'])
                else:
                    orig_price = float(item['normal_price'])
                    
                item['original_price'] = orig_price
                resale_tickets.append(item)

    return render_template('resale/marketplace.html', resale_tickets=resale_tickets)

@resale_bp.route('/<int:resale_id>/buy', methods=['POST'])
@login_required
def buy(resale_id: int):
    buyer_id = session['user_id']

    with current_app.pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # Fetch resale request
            cur.execute(
                """
                SELECT rr.*, t.booking_id AS original_booking_id, t.ticket_type,
                       b.event_id
                  FROM resale_requests rr
                  JOIN tickets  t ON t.id = rr.ticket_id
                  JOIN bookings b ON b.id = t.booking_id
                 WHERE rr.id = %s
                   AND rr.status = 'approved'
                """,
                (resale_id,),
            )
            resale = cur.fetchone()

            if resale is None:
                flash('Resale listing not found or already sold.', 'error')
                return redirect(url_for('resale.marketplace'))

            if resale['seller_id'] == buyer_id:
                flash('You cannot buy your own ticket.', 'error')
                return redirect(url_for('resale.marketplace'))

            resale_price = float(resale['price'])
            ticket_type = resale['ticket_type']
            
            vip_qty = 1 if ticket_type == 'VIP' else 0
            student_qty = 1 if ticket_type == 'Student' else 0
            normal_qty = 1 if ticket_type == 'Normal' else 0

            # 1. Mark resale as sold
            cur.execute(
                """
                UPDATE resale_requests
                   SET buyer_id = %s, status = 'sold'
                 WHERE id = %s
                """,
                (buyer_id, resale_id),
            )

            # 2. Create new booking for buyer
            cur.execute(
                """
                INSERT INTO bookings (user_id, event_id, vip_qty, normal_qty, student_qty, total_price, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'confirmed')
                RETURNING id
                """,
                (buyer_id, resale['event_id'], vip_qty, normal_qty, student_qty, resale_price),
            )
            new_booking = cur.fetchone()

            # 3. Transfer ticket to new booking
            cur.execute(
                """
                UPDATE tickets
                   SET booking_id = %s
                 WHERE id = %s
                """,
                (new_booking['id'], resale['ticket_id']),
            )

            # 4. Create payment record
            cur.execute(
                """
                INSERT INTO payments (booking_id, amount, payment_method, status)
                VALUES (%s, %s, 'resale', 'completed')
                """,
                (new_booking['id'], resale_price),
            )

        conn.commit()

    flash('Ticket purchased successfully!', 'success')
    return redirect(url_for('booking.booking_history'))
