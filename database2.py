# database2.py
# SQLite DB for TerraPower ATV chatbot

import sqlite3
from datetime import datetime
import os

DB_NAME = "chatbot2.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    if not os.path.exists(DB_NAME):
        conn = get_connection()
        cursor = conn.cursor()

        # Chat history
        cursor.execute("""
        CREATE TABLE chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            user_message TEXT,
            bot_reply TEXT,
            intent TEXT,
            created_at TEXT
        );
        """)

        # Tickets
        cursor.execute("""
        CREATE TABLE tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            issue_category TEXT,
            description TEXT,
            status TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        """)

        # Service centers
        cursor.execute("""
        CREATE TABLE service_centers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            city TEXT,
            address TEXT,
            phone TEXT
        );
        """)

        centers = [
            ("TerraPower Service – Pune", "Pune", "Hinjewadi Phase 2, Pune", "+91-8788-9400"),
            ("TerraPower Service – Mumbai", "Mumbai", "Andheri East, Mumbai", "+91-8788-9400"),
            ("TerraPower Service – Bengaluru", "Bengaluru", "Whitefield, Bengaluru", "+91-8788-9400"),
            ("TerraPower Service – Delhi", "Delhi", "Okhla Industrial Area, Delhi", "+91-8788-9400"),
        ]
        cursor.executemany(
            "INSERT INTO service_centers (name, city, address, phone) VALUES (?, ?, ?, ?)",
            centers
        )

        conn.commit()
        conn.close()


def save_chat(session_id, user_message, bot_reply, intent):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chats (session_id, user_message, bot_reply, intent, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (session_id, user_message, bot_reply, intent, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def get_chat_history(session_id, limit=50):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_message, bot_reply, intent, created_at
        FROM chats
        WHERE session_id = ?
        ORDER BY id DESC
        LIMIT ?
    """, (session_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows][::-1]  # oldest first


def clear_history(session_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chats WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()


def create_ticket(session_id, issue_category, description):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    cursor.execute("""
        INSERT INTO tickets (session_id, issue_category, description, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (session_id, issue_category, description, "Open", now, now))
    ticket_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return ticket_id


def get_tickets(session_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, issue_category, description, status, created_at, updated_at
        FROM tickets
        WHERE session_id = ?
        ORDER BY id DESC
    """, (session_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_service_centers_by_city(city):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name, city, address, phone
        FROM service_centers
        WHERE LOWER(city) = LOWER(?)
    """, (city,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
