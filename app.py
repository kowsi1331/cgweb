from flask import Flask, request, session, redirect, url_for, render_template
import sqlite3
import datetime
import json
import os
import re
app = Flask(__name__)
app.secret_key = 'your_secret_key'

@app.route('/index')
def index():
    return render_template('index.html')

def update_login_time(user_id):
    conn = sqlite3.connect('career.db')
    cursor = conn.cursor()
    login_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE users SET login_time=? WHERE id=?", (login_time, user_id))
    conn.commit()
    conn.close()

# ✅ Connect to Database
def get_db_connection():
    conn = sqlite3.connect('career.db')
    conn.row_factory = sqlite3.Row
    return conn

# ✅ Default Page
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/update_group', methods=['POST'])
def update_group():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    student_group = request.form.get('group')

    if not student_group:
        return redirect('/student_dashboard')

    try:
        conn = sqlite3.connect('career.db')
        cursor = conn.cursor()

        # Ensure the user exists before updating
        cursor.execute("SELECT id FROM users WHERE id=?", (user_id,))
        user = cursor.fetchone()
        
        if user:
            cursor.execute("UPDATE users SET student_group=? WHERE id=?", (student_group, user_id))
            conn.commit()
            
    except sqlite3.Error as e:
        print(f"Database error: {e}")  # Logs error instead of showing to user
    
    finally:
        conn.close()

    return redirect('/student_dashboard')



# ✅ Signup Page


def is_valid_email(email):
    return re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        # Email format check
        if not is_valid_email(email):
            return render_template('signup.html', error="Invalid email format!")

        # Password length check
        if len(password) < 6:
            return render_template('signup.html', error="Password must be at least 6 characters!")

        # (Optional) Strong password check: at least 1 letter and 1 number
        if not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
            return render_template('signup.html', error="Password must contain at least one letter and one number!")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            conn.close()
            return render_template('signup.html', error="Email already registered!")

        cursor.execute("INSERT INTO users (name, email, password, is_admin) VALUES (?, ?, ?, 0)", 
               (name, email, password))

        conn.commit()
        conn.close()

        return redirect(url_for('login'))

    return render_template('signup.html')


def log_activity(user_id, activity):
    conn = sqlite3.connect('career.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO user_activity (user_id, activity) VALUES (?, ?)", (user_id, activity))
    conn.commit()
    conn.close()

# ✅ Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
        user = cursor.fetchone()

        if user:
            session['user_id'] = user['id']
            session['is_admin'] = user['is_admin']

            # Update login time
            login_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("UPDATE users SET login_time=? WHERE id=?", (login_time, user['id']))

            # Log activity
            cursor.execute("INSERT INTO user_activity (user_id, activity) VALUES (?, ?)", (user['id'], "Logged in"))

            conn.commit()
            conn.close()

            if user['is_admin'] == 1:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            conn.close()
            return render_template('login.html', error="Invalid email or password")

    return render_template('login.html')


        # Log activity
    cursor.execute("INSERT INTO user_activity (user_id, activity) VALUES (?, ?)", (user[0], "Logged in"))
    conn.commit()
        
    conn.close()
    return render_template('login.html')

@app.route('/track_activity/<activity>')
def track_activity(activity):
    if 'user_id' in session:
        log_activity(session['user_id'], activity)
    return '', 204  # No content response

# ✅ Student Dashboard
@app.route('/student_dashboard')
def student_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, student_group, test_score, recommended_degrees FROM users WHERE id=?", (user_id,))
    student = cursor.fetchone()
    conn.close()

    if student:
        student_data = {
            "id": student["id"],
            "name": student["name"],
            "email": student["email"],
            "student_group": student["student_group"] or "Not Selected",
            "test_score": student["test_score"],
            "recommended_degrees": student["recommended_degrees"] or "Not Available"
        }

        return render_template('student_dashboard.html', student=student_data)

    return redirect(url_for('login'))

@app.route('/aptitude_instructions')
def aptitude_instructions():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT test_score FROM users WHERE id=?", (user_id,))
    test_score = cursor.fetchone()
    conn.close()

    if test_score and test_score[0] is not None:
        return redirect('/student_dashboard')  # Already taken the test

    return render_template('aptitude_instructions.html')

@app.route('/aptitude_test')
def aptitude_test():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get the group
    cursor.execute("SELECT student_group FROM users WHERE id=?", (user_id,))
    result = cursor.fetchone()

    if not result or not result[0]:
        conn.close()
        print("DEBUG: No group found for user")
        return render_template('aptitude_test.html', group="", error="No group selected. Please update your group in the dashboard.")

    student_group = result[0]

    # Check if the user already completed the test
    cursor.execute("SELECT * FROM aptitude_results WHERE user_id=?", (user_id,))
    test_result = cursor.fetchone()
    conn.close()

    if test_result:
        return render_template('test_already_taken.html')

    print(f"DEBUG: Rendering aptitude test for group: {student_group}")
    return render_template('aptitude_test.html', group=student_group)


@app.route('/submit_test', methods=['POST'])
def submit_test():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT student_group FROM users WHERE id=?", (user_id,))
    group = cursor.fetchone()[0]

    # Correct answers matching the frontend test
    correct_answers = {
        "Bio-Maths": {
            "q1": "Powerhouse of the cell",
            "q2": "Sin",
            "q3": "Newton",
            "q4": "O Negative",
            "q5": "cos(x)",
            "q6": "Pancreas",
            "q7": "Nucleotides",
            "q8": "Speed",
            "q9": "6.022 × 10^23",
            "q10": "Mendel"
        },
        "Science with Computer Science": {
            "q1": "Central Processing Unit",
            "q2": "Stack",
            "q3": "8",
            "q4": "Router",
            "q5": "1010",
            "q6": "HTTP",
            "q7": "Bill Gates",
            "q8": "HTML",
            "q9": "CPU",
            "q10": "=="
        },
        "Commerce with Computer Applications": {
            "q1": "Tally",
            "q2": "Web Page Design",
            "q3": "Excel",
            "q4": "Hard Disk",
            "q5": "Buying/Selling Online",
            "q6": "Ctrl+C",
            "q7": "Phishing",
            "q8": "VBA",
            "q9": "Local Area Network",
            "q10": "PowerPoint"
        },
        "Pure Commerce": {
            "q1": "Gross Domestic Product",
            "q2": "Balance Sheet",
            "q3": "Income Tax",
            "q4": "Rent Paid",
            "q5": "Cash",
            "q6": "Debit & Credit",
            "q7": "RBI",
            "q8": "Amount payable",
            "q9": "Invoice",
            "q10": "Assets = Liabilities + Capital"
        },
        "Arts with Computer Applications": {
            "q1": "Canva",
            "q2": "Blender",
            "q3": "Van Gogh",
            "q4": "Stylus",
            "q5": "Cubism",
            "q6": "MS Word",
            "q7": "JPEG",
            "q8": "Graphical User Interface",
            "q9": "Text Formatting",
            "q10": "Behance"
        },
        "Pure Arts": {
            "q1": "Shakespeare",
            "q2": "Bharatanatyam",
            "q3": "Orange",
            "q4": "Leonardo da Vinci",
            "q5": "Sonnet",
            "q6": "Traditional stories",
            "q7": "Aesop",
            "q8": "Violin",
            "q9": "Drama",
            "q10": "William Shakespeare"
        }
    }

    group_answers = correct_answers.get(group, {})
    score = 0

    for i in range(1, 11):
        user_answer = request.form.get(f"q{i}")
        correct = group_answers.get(f"q{i}")
        if user_answer == correct:
            score += 1

    # Degree recommendations (adjust if needed)
    degree_recommendations = {
        "Bio-Maths": ["MBBS", "BDS", "B.Pharm", "B.Tech Biotechnology"],
        "Science with Computer Science": ["B.Tech IT", "B.Sc Computer Science", "BCA"],
        "Commerce with Computer Applications": ["B.Com CA", "BBA", "B.Com IT"],
        "Pure Commerce": ["B.Com", "BBA", "CA Foundation"],
        "Arts with Computer Applications": ["BA English", "BA Journalism", "BFA"],
        "Pure Arts": ["BA History", "BA Political Science", "BA Literature"]
    }

    recommended_degrees = ", ".join(degree_recommendations.get(group, []))

    # Store result in DB
    cursor.execute(
        "UPDATE users SET test_score=?, recommended_degrees=? WHERE id=?",
        (score, recommended_degrees, user_id)
    )
    conn.commit()
    conn.close()

    return redirect(url_for('student_dashboard'))


@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session or session['is_admin'] == 0:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, student_group,login_time,(SELECT COUNT(*) FROM user_activity WHERE user_activity.user_id = users.id) AS activity_count FROM users WHERE is_admin = 0")
    users = cursor.fetchall()
    conn.close()

    return render_template('admin_dashboard.html', users=users)


@app.route('/user_details/<int:user_id>')
def user_details(user_id):
    conn = sqlite3.connect('career.db')
    cursor = conn.cursor()
    
    # Fetch user details
    cursor.execute("SELECT id, name, email, student_group, login_time FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()
    
    # Fetch user activities
    cursor.execute("SELECT timestamp, activity FROM user_activity WHERE user_id=?", (user_id,))
    activities = cursor.fetchall()

    # Count total activities
    activity_count = len(activities)

    # Log admin action
    if 'user_id' in session:
        log_activity(session['user_id'], f"Viewed user {user[1]}'s details")

    conn.close()
    return render_template('user_details.html', user=user, activities=activities, activity_count=activity_count)


# ✅ Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/feedback')
def feedback():
    return render_template('feedback.html')

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    name = request.form['name']
    email = request.form['email']
    message = request.form['message']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO feedback (name, email, message) VALUES (?, ?, ?)''', (name, email, message))
    conn.commit()

    return "Thank you for your feedback!"


@app.route('/trending')
def trending_courses():
    return render_template('trending.html')

@app.route('/courses')
def recommended_courses():
    if 'user_id' in session:
        user_id = session['user_id']
        
        conn = sqlite3.connect('career.db')
        cursor = conn.cursor()
        
        # Fetch student details
        cursor.execute("SELECT name, test_score, student_group FROM users WHERE id=?", (user_id,))
        student = cursor.fetchone()
        
        if student:
            student_name, test_score, student_group = student
            test_score = test_score or 0  # Handle NULL scores
            group = (student_group or "").strip().lower()

            # Recommendations based on group and score
            if group in ["bio-maths", "science with computer science"]:
                if test_score >= 80:
                    courses = [
                        ("MBBS", "Medical degree for Biology students"),
                        ("B.Tech", "Engineering in top specializations")
                    ]
                else:
                    courses = [
                        ("B.Sc", "Bachelor of Science in your field"),
                        ("B.Pharm", "Pharmacy and allied health courses")
                    ]

            elif group in ["commerce with computer applications", "pure commerce"]:
                if test_score >= 80:
                    courses = [
                        ("CA", "Chartered Accountancy"),
                        ("MBA", "Master of Business Administration")
                    ]
                else:
                    courses = [
                        ("B.Com", "Bachelor of Commerce"),
                        ("BBA", "Bachelor of Business Administration")
                    ]

            elif group in ["arts with computer applications", "pure arts"]:
                if test_score >= 80:
                    courses = [
                        ("Law", "Pursue a career in Law and Legal Studies"),
                        ("Mass Communication", "Media, journalism & communication")
                    ]
                else:
                    courses = [
                        ("BA", "Bachelor of Arts in various fields"),
                        ("B.Ed", "Education and teaching program")
                    ]
            else:
                courses = [("General", "Group not identified. Explore common career paths.")]

            recommended_courses = [{"name": c[0], "description": c[1]} for c in courses]

            conn.close()
            return render_template("courses.html", 
                                   student={"name": student_name, "test_score": test_score}, 
                                   recommended_courses=recommended_courses)
        
        conn.close()
        return redirect('/student_dashboard')

    return redirect('/login')


@app.route('/details')
def details():
    return render_template('details.html')

@app.route('/QAE')
def quantitative_exams():
    return render_template('QAE.html')

@app.route('/sample')
def sample():
    return render_template('sample.html')

if __name__ == '__main__':
     port = int(os.environ.get("PORT", 5000))
     app.run(host="0.0.0.0", port=port)