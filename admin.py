import psycopg2
from psycopg2 import sql
import os

# Make sure this is the full and correct connection string with host ending in `.render.com`
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://career_nspr_user:1gUxsqTSBQQ3FZt0PS7hwY28gVIUNYve@dpg-cvrov0je5dus738em5jg-a.oregon-postgres.render.com/career_nspr")


def clear_database():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Disable foreign key constraints temporarily
        cursor.execute("SET session_replication_role = 'replica';")

        # Truncate all tables
        cursor.execute("TRUNCATE TABLE user_activity, feedback, aptitude_results, users RESTART IDENTITY CASCADE;")

        # Re-enable constraints
        cursor.execute("SET session_replication_role = 'origin';")

        conn.commit()
        print("✅ Database cleared successfully.")

    except Exception as e:
        print("❌ Error clearing database:", e)

    finally:
        cursor.close()
        conn.close()

clear_database()
