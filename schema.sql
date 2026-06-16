-- Enable UUID extension (used for ticket codes)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ------------------------------------------------
-- USERS
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id          SERIAL PRIMARY KEY,
    username    VARCHAR(80)  NOT NULL,
    email       VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    role        VARCHAR(20)  DEFAULT 'customer'
                CHECK (role IN ('admin', 'customer')),
    created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------
-- EVENTS
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS events (
    id                  SERIAL PRIMARY KEY,
    title               VARCHAR(200)   NOT NULL,
    description         TEXT,
    venue               VARCHAR(200)   NOT NULL,
    event_date          DATE           NOT NULL,
    event_time          TIME           NOT NULL,
    
    vip_seats           INTEGER        NOT NULL DEFAULT 0,
    vip_available       INTEGER        NOT NULL DEFAULT 0,
    vip_price           DECIMAL(10, 2) NOT NULL DEFAULT 0,
    
    normal_seats        INTEGER        NOT NULL DEFAULT 0,
    normal_available    INTEGER        NOT NULL DEFAULT 0,
    normal_price        DECIMAL(10, 2) NOT NULL DEFAULT 0,
    
    student_seats       INTEGER        NOT NULL DEFAULT 0,
    student_available   INTEGER        NOT NULL DEFAULT 0,
    student_price       DECIMAL(10, 2) NOT NULL DEFAULT 0,
    
    image_url           VARCHAR(500),
    created_by          INTEGER REFERENCES users(id),
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------
-- BOOKINGS
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS bookings (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES users(id),
    event_id    INTEGER REFERENCES events(id),
    
    vip_qty     INTEGER DEFAULT 0,
    normal_qty  INTEGER DEFAULT 0,
    student_qty INTEGER DEFAULT 0,
    
    total_price DECIMAL(10, 2) NOT NULL,
    status      VARCHAR(20) DEFAULT 'confirmed'
                CHECK (status IN ('pending', 'confirmed', 'cancelled')),
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------
-- TICKET LOCKS  (temporary seat reservations)
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS ticket_locks (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER   REFERENCES users(id),
    event_id    INTEGER   REFERENCES events(id),
    
    vip_qty     INTEGER DEFAULT 0,
    normal_qty  INTEGER DEFAULT 0,
    student_qty INTEGER DEFAULT 0,
    
    locked_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at  TIMESTAMP NOT NULL
);

-- ------------------------------------------------
-- TICKETS
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS tickets (
    id          SERIAL PRIMARY KEY,
    booking_id  INTEGER     REFERENCES bookings(id) ON DELETE CASCADE,
    ticket_code VARCHAR(36) UNIQUE NOT NULL,
    seat_label  VARCHAR(20),
    ticket_type VARCHAR(20) NOT NULL -- 'VIP', 'Normal', 'Student'
);

-- ------------------------------------------------
-- RESALE REQUESTS
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS resale_requests (
    id         SERIAL PRIMARY KEY,
    ticket_id  INTEGER REFERENCES tickets(id),
    seller_id  INTEGER REFERENCES users(id),
    buyer_id   INTEGER REFERENCES users(id),
    price      DECIMAL(10, 2) NOT NULL,
    status     VARCHAR(20) DEFAULT 'pending'
               CHECK (status IN ('pending', 'approved', 'rejected', 'sold')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------
-- PAYMENTS
-- ------------------------------------------------
CREATE TABLE IF NOT EXISTS payments (
    id             SERIAL PRIMARY KEY,
    booking_id     INTEGER REFERENCES bookings(id),
    amount         DECIMAL(10, 2) NOT NULL,
    payment_method VARCHAR(50),
    status         VARCHAR(20) DEFAULT 'completed',
    paid_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
