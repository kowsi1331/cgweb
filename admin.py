import psycopg2
from psycopg2 import sql
import os

# Make sure this is the full and correct connection string with host ending in `.render.com`
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://career_nspr_user:1gUxsqTSBQQ3FZt0PS7hwY28gVIUNYve@dpg-cvrov0je5dus738em5jg-a.oregon-postgres.render.com/career_nspr")

def reset_database():
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        cursor.execute("""
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
        """)

        cursor.execute("""
        INSERT INTO users (name, email, password, is_admin) VALUES
        ('Kowsalya', 's.kowsalya3103@gmail.com', 'Kowsi_0731', TRUE),
        ('Lavanya', 'anand.lavanya2005@gmail.com', 'lava@123', TRUE)
        ON CONFLICT (email) DO NOTHING;
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_activity (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            activity TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
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
        """)

        conn.commit()
        print("✅ PostgreSQL database reset and tables created!")

    except Exception as e:
        print("❌ Error:", e)

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

reset_database()
