import sqlite3
import os

def reset_database():
    db_path = "career.db"
    #if os.path.exists(db_path):
        #os.remove(db_path)  # Delete old database

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    student_group TEXT,
    test_score INTEGER,
    recommended_degrees TEXT,
    login_time TIMESTAMP
);

INSERT INTO users (name, email, password, is_admin) VALUES
('Kowsalya', 's.kowsalya3103@gmail.com', 'Kowsi_0731', TRUE),
('Lavanya', 'anand.lavanya2005@gmail.com', 'lava@123', TRUE)
ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS user_activity (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    activity TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    message TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS aptitude_results (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    group_name TEXT,
    questions TEXT,
    correct_answers TEXT,
    answers TEXT,
    score INTEGER,
    time_taken INTEGER,
    submitted_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

);

""")

    conn.commit()
    conn.close()
    print("✅ Database reset and tables created!")

reset_database()
# This function resets the database and creates the necessary tables.