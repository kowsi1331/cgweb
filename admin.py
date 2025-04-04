import sqlite3
import os

def reset_database():
    db_path = "career.db"
    if os.path.exists(db_path):
        os.remove(db_path)  # Delete old database

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    is_admin INTEGER DEFAULT 0,
    student_group TEXT,
    test_score INTEGER,
    recommended_degrees TEXT,
    login_time TEXT
);

INSERT OR IGNORE INTO users (name, email, password, is_admin) VALUES
('Kowsalya', 's.kowsalya3103@gmail.com', 'Kowsi_0731', 1),
('Lavanya', 'anand.lavanya2005@gmail.com', 'lava@123', 1);

CREATE TABLE IF NOT EXISTS user_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    activity TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
""")

    conn.commit()
    conn.close()
    print("✅ Database reset and tables created!")

reset_database()
# This function resets the database and creates the necessary tables.