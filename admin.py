import sqlite3
from flask import Flask, render_template

conn = sqlite3.connect('career.db')
cursor = conn.cursor()

cursor.execute(''' CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    is_admin INTEGER DEFAULT 0,  -- 0 = Student, 1 = Admin
    student_group TEXT,  -- Stores the +2 group of the student
    test_score INTEGER,  -- Stores the aptitude test score
    recommended_degrees TEXT  -- Stores recommended courses (comma-separated)
)
''')
print("✅ table created successfully!")
# Insert admin user (if not already exists)
cursor.execute('''
    INSERT OR IGNORE INTO users (name, email, password, is_admin)
    VALUES 
        (?, ?, ?, ?),
        (?, ?, ?, ?)
''', 
(
    'Kowsalya', 's.kowsalya3103@gmail.com', 'Kowsi_0731', 1,
    'Lavanya', 'anand.lavanya2005@gmail.com', 'lava@123', 1
))
cursor.execute('''CREATE TABLE IF NOT EXISTS user_activity (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,  -- Timestamp is set automatically
    activity TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
 ''')
conn.commit()
conn.close()

print("✅ Admin Kowsalya added successfully!")

app = Flask(__name__)

def get_users():
    conn = sqlite3.connect('career.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, password, is_admin FROM users")
    users = cursor.fetchall()
    conn.close()
    return users

@app.route('/admin')
def admin_dashboard():
    users = get_users()
    return render_template('admin.html', users=users)

if __name__ == '__main__':
    app.run(debug=True)

