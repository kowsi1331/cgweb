from flask import Flask, request, session, redirect, url_for, render_template
import sqlite3
import datetime
import json
import os
import re
app = Flask(__name__)
app.secret_key = 'your_secret_key'

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

@app.route('/aptitude_test')
def aptitude_test():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT student_group FROM users WHERE id=?", (user_id,))
    result = cursor.fetchone()

    conn.close()

    if not result or not result[0]:
        return render_template('aptitude_test.html', group="", error="No group selected. Please update your group in the dashboard.")

    student_group = result[0]

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

    # ✅ Correct answers for each group
    correct_answers = {
        "Science": {
            "q1": "H2O",
            "q2": "300,000 km/s",
            "q3": "Newton",
            "q4": "Gravity",
            "q5": "Photosynthesis",
            "q6": "Electron",
            "q7": "Cell",
            "q8": "Oxygen",
            "q9": "Brain",
            "q10": "Albert Einstein"
        },
        "Commerce": {
            "q1": "Gross Domestic Product",
            "q2": "All of the above",
            "q3": "Balance Sheet",
            "q4": "Loan Payable",
            "q5": "Demand and Supply",
            "q6": "Income Tax",
            "q7": "Inflation",
            "q8": "Raising capital for companies",
            "q9": "Fiscal Policy",
            "q10": "Reserve Bank of India"
        },
        "Arts": {
            "q1": "Leonardo da Vinci",
            "q2": "Hamlet",
            "q3": "Cultural Revival",
            "q4": "Shakespeare",
            "q5": "Abstract Art",
            "q6": "Realism",
            "q7": "Van Gogh",
            "q8": "Dramatic Monologue",
            "q9": "Surrealism",
            "q10": "Greek Mythology"
        }
    }

    score = 0
    group_answers = correct_answers.get(group, {})

    for question, correct_answer in group_answers.items():
        user_answer = request.form.get(question)
        if user_answer == correct_answer:
            score += 1

    # ✅ Determine recommended degrees based on the score
    degree_recommendations = {
        "Science": ["B.Sc Physics", "B.Sc Chemistry", "B.Sc Computer Science"],
        "Commerce": ["B.Com Accounting", "BBA", "B.Com Banking"],
        "Arts": ["BA Literature", "BA History", "BA Fine Arts"]
    }

    recommended_degrees = ", ".join(degree_recommendations.get(group, []))

    # ✅ Update score and recommended degrees in database
    cursor.execute("UPDATE users SET test_score=?, recommended_degrees=? WHERE id=?", (score, recommended_degrees, user_id))
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
            
            # Define course recommendations based on score & group
            if student_group == "Science":
                if (test_score or  0)>= 80:
                    courses = [("B.Tech", "Engineering courses in various fields"), ("MBBS", "Medical degree")]
                else:
                    courses = [("B.Sc", "Bachelor of Science"), ("B.Pharm", "Pharmacy course")]
            
            elif student_group == "Commerce":
                if (test_score or  0) >= 80:
                    courses = [("CA", "Chartered Accountancy"), ("MBA", "Business Administration")]
                else:
                    courses = [("B.Com", "Bachelor of Commerce"), ("BBA", "Business Management")]
            
            else:  # Arts
                if (test_score or  0) >= 80:
                    courses = [("Law", "Legal Studies"), ("Mass Communication", "Journalism & Media")]
                else:
                    courses = [("BA", "Bachelor of Arts"), ("B.Ed", "Education degree")]
            
            recommended_courses = [{"name": c[0], "description": c[1]} for c in courses]
        else:
            return redirect('/student_dashboard')  # Redirect if student not found
        
        conn.close()

        return render_template("courses.html", 
                               student={"name": student_name, "test_score": test_score}, 
                               recommended_courses=recommended_courses)
    
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