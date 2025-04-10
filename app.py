from flask import Flask, request, session, redirect, url_for, render_template, flash, send_from_directory
import sqlite3
import datetime
import json
import os
import re
from flask_mail import Mail, Message
import random
from flask import session
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pytz import timezone
import psycopg2
import psycopg2.extras 
import os
from dotenv import load_dotenv
load_dotenv()


DATABASE_URL = os.environ.get('DATABASE_URL')

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'query.careerassistance25@gmail.com'      # Change to your email
app.config['MAIL_PASSWORD'] = 'rtho txgj rqfm vnyg'        # Use an App Password
mail = Mail(app)

def get_current_ist_time():
    ist = timezone('Asia/Kolkata')
    return datetime.datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S")

def log_activity(user_id, activity):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    timestamp = get_current_ist_time()
    cursor.execute("INSERT INTO user_activity (user_id, activity,timestamp) VALUES (%s, %s,%s)", (user_id, activity,timestamp))
    conn.commit()
    conn.close()

def update_login_time(user_id):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    login_time = get_current_ist_time()
    cursor.execute("UPDATE users SET login_time=%s WHERE id=%s", (login_time, user_id))
    conn.commit()
    conn.close()

# ✅ Connect to Database
def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    conn.cursor_factory = psycopg2.extras.DictCursor
    return conn

@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('static', 'sitemap.xml')

@app.route('/robots.txt')
def robots():
    return send_from_directory('static', 'robots.txt')

# ✅ Default Page
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/update_group', methods=['POST'])
def update_group():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    log_activity(session['user_id'], 'updated student group')

    student_group = request.form.get('group')

    if not student_group:
        return redirect('/student_dashboard')

    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)


        # Ensure the user exists before updating
        cursor.execute("SELECT id FROM users WHERE id=%s", (user_id,))
        user = cursor.fetchone()
        
        if user:
            cursor.execute("UPDATE users SET student_group=%s WHERE id=%s", (student_group, user_id))
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

        if not is_valid_email(email):
            return render_template('signup.html', error="Invalid email format!")

        if len(password) < 6 or not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
            return render_template('signup.html', error="Password must be at least 6 characters and contain a letter and number!")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            conn.close()
            return render_template('signup.html', error="Email already registered! Please login with same credentials.", email_registered=True)

        # Save user data temporarily in session
        session['pending_user'] = {'name': name, 'email': email, 'password': password}

        # Generate OTP
        otp = random.randint(100000, 999999)
        session['otp'] = str(otp)

        # Email to user with OTP
        msg_user = Message("OTP Verification - Career Assistance Platform",
                           sender="query.careerassistance25@gmail.com",  # Replace with your actual email
                           recipients=[email])
        msg_user.body = f"Hello {name},\n\nYour OTP for verification is: {otp}\n\nThank you!"
        mail.send(msg_user)

        # Email to admin notifying signup OTP request
        msg_admin = Message("New OTP Request - User Signup",
                            sender="your_email@gmail.com",
                            recipients=["query.careerassistance25@gmail.com"])
        msg_admin.body = f"A new OTP was requested during signup.\n\nName: {name}\nEmail: {email}\n\nPlease review if needed."
        mail.send(msg_admin)

        return redirect(url_for('verify_otp'))
   
    return render_template('signup.html')


@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        entered_otp = request.form['otp']
        if entered_otp == session.get('otp'):
            # Retrieve user data and insert into DB
            user = session.pop('pending_user', None)
            if user:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users (name, email, password, is_admin) VALUES (%s, %s, %s, 0)",
                               (user['name'], user['email'], user['password']))
                conn.commit()

                # Get inserted user's ID
                cursor.execute("SELECT id FROM users WHERE email = %s", (user['email'],))
                user_record = cursor.fetchone()
                conn.close()

                if user_record:
                    session['user_id'] = user_record['id']
                    session['is_admin'] = 0

                    # ✅ Log only after successful OTP verification
                    log_activity(session['user_id'], 'otp verified')
                    log_activity(session['user_id'], 'new student signup')

                flash("✅ Verification successful! Please login with the same email and password.", "success")
                session.pop('otp', None)  # Clear OTP

                return redirect(url_for('login'))
        else:
            flash("❌ Invalid OTP. Please try again.", "error")
            return render_template('verify_otp.html')


    if 'otp' in session:
        flash("📧 OTP sent to your email. Please check your inbox or spam folder.")

    return render_template('verify_otp.html')

# ✅ Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()

        # First, check if the email exists
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if not user:
            conn.close()
            return render_template('login.html', error="Email not registered!")

        # Then check password
        if user['password'] != password:
            conn.close()
            return render_template('login.html', error="Invalid password!")

        # Successful login
        session['user_id'] = user['id']
        session['is_admin'] = user['is_admin']
        log_activity(session['user_id'], 'logged in')
        login_time = get_current_ist_time()

        cursor.execute("UPDATE users SET login_time=%s WHERE id=%s", (login_time, user['id']))

        conn.commit()
        conn.close()

        if user['is_admin'] == 1:
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('student_dashboard'))
    
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
    log_activity(session['user_id'], 'Visited Student Dashboard')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, email, student_group, test_score, recommended_degrees FROM users WHERE id=%s", (user_id,))
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
    log_activity(session['user_id'], 'Visited instrution page')
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if user has already taken the test
    cursor.execute("SELECT test_score FROM users WHERE id=%s", (user_id,))
    test_score = cursor.fetchone()

    # Get the user's +2 group
    cursor.execute("SELECT student_group FROM users WHERE id=%s", (user_id,))
    group_result = cursor.fetchone()
    conn.close()

    # Redirect to dashboard if test already taken
    if test_score and test_score[0] is not None:
        return redirect('/student_dashboard')

    # Pass the group to the template (can be None)
    group = group_result[0] if group_result and group_result[0] else None
    
    return render_template('aptitude_instructions.html', group=group)

@app.route('/aptitude_test')
def aptitude_test():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    log_activity(session['user_id'], 'Visited test page')
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get user's +2 group
    cursor.execute("SELECT student_group FROM users WHERE id=%s", (user_id,))
    result = cursor.fetchone()

    if not result or not result[0]:
        conn.close()
        return render_template(
            'aptitude_test.html',
            group="",
            error="No group selected. Please update your group in the dashboard."
        )

    student_group = result[0]

    # Check if test already submitted
    cursor.execute("SELECT * FROM aptitude_results WHERE user_id=%s", (user_id,))
    test_result = cursor.fetchone()
    conn.close()

    if test_result:
        return render_template('test_already_taken.html')
   
    return render_template('aptitude_test.html', group=student_group)

@app.route('/submit_test', methods=['POST'])
def submit_test():
    if 'user_id' not in session:
        print("No user in session")
        return redirect(url_for('login'))

    user_id = session['user_id']
    log_activity(session['user_id'], 'Submitted test')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get student group
    cursor.execute("SELECT student_group FROM users WHERE id=%s", (user_id,))
    row = cursor.fetchone()
    if not row:
        print("No user found in DB.")
        return redirect(url_for('student_dashboard'))

    group = row[0]
    print(f"Student group: {group}")

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
    user_answers = {}

    for i in range(1, 11):
        qid = f"q{i}"
        user_answer = request.form.get(qid, "N/A")
        user_answers[qid] = user_answer
        if user_answer == group_answers.get(qid):
            score += 1

    submitted_at = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    print(f"User answers: {user_answers}")
    print(f"Score: {score}")
    
    try:
        # Save the aptitude result
        cursor.execute("""
            INSERT INTO aptitude_results (
                user_id, group_name, answers, questions, correct_answers, score, time_taken, submitted_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id,
            group,
            json.dumps(user_answers),
            10,
            json.dumps(group_answers),
            score,
            0,  # Time taken (optional enhancement)
            submitted_at
        ))
        print("Inserted into aptitude_results.")

        degree_recommendations = {
    "Bio-Maths": [
        "B.Sc Mathematics", "B.Sc Statistics", "B.Sc Physics", "B.Sc Chemistry",
        "B.Sc Computer Science", "B.Sc Plant Biology & Plant Biotechnology",
        "B.Sc Data Science and Artificial Intelligence", "B.Sc (Clinical Nutrition and Dietetics)",
        "B.Sc (Nutrition Food Service Management and Dietetics)",
        "B.Sc Computer Science with Data Science", "B.Sc Computer Science with Cognitive Systems",
        "B.Sc Computer Science with Artificial Intelligence","B.C.A"
    ],

    "Science with Computer Science": [
        "B.Sc Computer Science", "B.Sc Mathematics", "B.Sc Statistics", "B.Sc Physics", "B.Sc Chemistry",
        "B.C.A", "B.Sc Computer Science with Data Science", "B.Sc Computer Science with Artificial Intelligence",
        "B.Sc Computer Science with Cognitive Systems", "B.Sc Data Science and Artificial Intelligence"
    ],

    "Commerce with Computer Applications": [
        "B.Com (Computer Applications)", "B.Com", "B.Com (Corporate Secretaryship)",
        "B.Com (Banking and Insurance Management)", "B.Com (Information Systems Management)",
        "B.Com (Professional Accounting)", "B.Com (Honours)", "B.Com Fintech with AI",
        "B.Com (Accounting and Finance)", "B.B.A", "B.B.A (Digital Marketing and Business Analytics)",
        "B.C.A", "B.Sc Computer Science", "MBA Business Analytics"
    ],

    "Pure Commerce": [
        "B.Com", "B.Com (Corporate Secretaryship)", "B.Com (Banking and Insurance Management)",
        "B.Com (Information Systems Management)", "B.Com (Professional Accounting)", "B.Com (Honours)",
        "B.Com Fintech with AI", "B.Com (Accounting and Finance)", "B.B.A",
        "B.B.A (Digital Marketing and Business Analytics)"
    ],

    "Arts with Computer Applications": [
        "B.A. English", "B.A. History and Tourism", "B.A. Economics","B.Voc. (Travel & Tourism)", "B.C.A", "B.Sc Computer Science",
        "B.Sc Visual Communication", "B.Sc Psychology", "B.Sc Computer Science with AI",
        "B.Sc Computer Science with Data Science", "B.Sc Computer Science with Cognitive Systems"
    ],

    "Pure Arts": [
        "B.A. English", "B.A. History and Tourism", "B.A. Economics",
        "B.Voc. (Travel & Tourism)", "B.Sc Visual Communication", "B.Sc Psychology",
        "B.Sc (Home Science - Clinical Nutrition and Dietetics)",
        "B.Sc (Home Science - Nutrition Food Service Management and Dietetics)"
    ]
}

        recommended_degrees = ", ".join(degree_recommendations.get(group, []))
        cursor.execute(
            "UPDATE users SET test_score=%s, recommended_degrees=%s WHERE id=%s",
            (score, recommended_degrees, user_id)
        )
        conn.commit()
        print("Committed changes.")

    except Exception as e:
        print("Error inserting into DB:", e)
    finally:
        conn.close()
       
    return redirect(url_for('student_dashboard'))

@app.route('/view_test_results')
def view_test_results():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    log_activity(session['user_id'], 'Viewed test results')
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT group_name, answers FROM aptitude_results WHERE user_id=%s", (user_id,))
    result = cursor.fetchone()
    conn.close()

    if not result:
        return "No test results found for user ID: {}".format(user_id)

    group_name, answers_json = result
    submitted_answers = json.loads(answers_json)

    # Map full question text for each group
    group_questions = {
        "Bio-Maths": {
            "q1": "What is the powerhouse of the cell%s",
            "q2": "Which trigonometric function is periodic%s",
            "q3": "Who discovered the laws of motion%s",
            "q4": "Which blood group is called the universal donor%s",
            "q5": "What is the derivative of sin(x)%s",
            "q6": "Which organ secretes insulin%s",
            "q7": "DNA is made up of%s",
            "q8": "What is the SI unit of speed%s",
            "q9": "What is Avogadro’s number%s",
            "q10": "Who is the father of genetics%s"
        },
        "Science with Computer Science": {
            "q1": "What does CPU stand for%s",
            "q2": "Which data structure follows LIFO%s",
            "q3": "Binary of decimal 8 is%s",
            "q4": "Which device routes data packets in networks%s",
            "q5": "Binary representation of decimal 10 is%s",
            "q6": "Which protocol is used for web communication%s",
            "q7": "Who founded Microsoft%s",
            "q8": "Which language is used to design web pages%s",
            "q9": "What executes instructions in a computer%s",
            "q10": "Which operator checks equality in Python%s"
        },
        "Commerce with Computer Applications": {
            "q1": "Which software is used for accounting%s",
            "q2": "Which is used to design websites%s",
            "q3": "Which MS Office tool is spreadsheet-based%s",
            "q4": "Which is the primary storage device in a computer%s",
            "q5": "What is e-commerce%s",
            "q6": "Shortcut for copy in Windows is%s",
            "q7": "What is an email scam called%s",
            "q8": "Macro language in MS Excel is%s",
            "q9": "LAN stands for%s",
            "q10": "Which software is used for presentations%s"
        },
        "Pure Commerce": {
            "q1": "What does GDP stand for%s",
            "q2": "Which document shows assets and liabilities%s",
            "q3": "What type of tax is based on income%s",
            "q4": "What is an example of an expense%s",
            "q5": "What is the most liquid asset%s",
            "q6": "Which two terms are key in accounting%s",
            "q7": "Which body manages India's monetary policy%s",
            "q8": "Outstanding salary is shown as%s",
            "q9": "A bill sent by the seller is called%s",
            "q10": "Basic accounting equation is%s"
        },
        "Arts with Computer Applications": {
            "q1": "Which tool is used for graphic design%s",
            "q2": "Which software is used for 3D animation%s",
            "q3": "Who painted 'Starry Night'%s",
            "q4": "What tool is used with a drawing tablet%s",
            "q5": "Which art style uses geometric shapes%s",
            "q6": "Which software is best for document editing%s",
            "q7": "Which image format is widely used%s",
            "q8": "What does GUI stand for%s",
            "q9": "Which feature changes font size and style%s",
            "q10": "Which site is used to showcase portfolios%s"
        },
        "Pure Arts": {
            "q1": "Who wrote 'Romeo and Juliet'%s",
            "q2": "Which classical dance originated in Tamil Nadu%s",
            "q3": "Which color is a secondary color%s",
            "q4": "Who painted the Mona Lisa%s",
            "q5": "What is a 14-line poem called%s",
            "q6": "What is folklore%s",
            "q7": "Who is a famous fable writer%s",
            "q8": "Which instrument is used in classical music%s",
            "q9": "What type of performance includes acting%s",
            "q10": "Who is known as the greatest English writer%s"
        }
    }

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

    group_q_text = group_questions.get(group_name, {})
    group_correct = correct_answers.get(group_name, {})

    questions = []
    for qid, user_ans in submitted_answers.items():
        question_text = group_q_text.get(qid, f"Question ID: {qid}")
        correct_ans = group_correct.get(qid, "N/A")
        questions.append({
            "question": question_text,
            "your_answer": user_ans,
            "correct_answer": correct_ans
        })
        
    return render_template('view_test_results.html', questions=questions)

@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user_id' not in session or session['is_admin'] == 0:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT 
        id, name, email, student_group, login_time,
        (SELECT COUNT(*) FROM user_activity WHERE user_activity.user_id = users.id) AS activity_count,
        (SELECT timestamp FROM user_activity WHERE user_activity.user_id = users.id ORDER BY timestamp DESC LIMIT 1) AS last_activity
    FROM users 
    WHERE is_admin = 0
""")

    users = cursor.fetchall()
    conn.close()

    return render_template('admin_dashboard.html', users=users)


@app.route('/user_details/<int:user_id>')
def user_details(user_id):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Fetch user details
    cursor.execute("SELECT id, name, email, student_group, login_time FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()
    
    # Fetch user activities
    cursor.execute("SELECT timestamp, activity FROM user_activity WHERE user_id=%s", (user_id,))
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
    if 'user_id' in session:
        log_activity(session['user_id'], 'Visited feedback page')
    return render_template('feedback.html')

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    try:
        name = request.form['name']
        user_email = request.form['email']
        message = request.form['message']

        # Store in database
        conn = get_db_connection()
        cursor = conn.cursor()
        timestamp = get_current_ist_time()
        cursor.execute('''
            INSERT INTO feedback (name, email, message,timestamp)
            VALUES (%s, %s, %s, %s)
        ''', (name, user_email, message, timestamp))
        conn.commit()

        # Get the latest inserted feedback with timestamp
        cursor.execute('SELECT timestamp FROM feedback WHERE email = %s ORDER BY id DESC LIMIT 1', (user_email,))
        result = cursor.fetchone()
        feedback_timestamp = timestamp
        conn.close()

        if session.get('user_id'):
            log_activity(session['user_id'], 'submitted feedback')

        # Email configuration
        sender_email = "query.careerassistance25@gmail.com"
        sender_password = "xayx ahbm bzgm ueza"  # App password
        admin_email = "careerassistancefeedback@gmail.com"
        smtp_server = "smtp.gmail.com"
        smtp_port = 587

        # --- Admin Email ---
        admin_msg = MIMEMultipart()
        admin_msg['From'] = sender_email
        admin_msg['To'] = admin_email
        admin_msg['Subject'] = "New Feedback Received"

        admin_body = f"""
 New Feedback Received

Name: {name}
Email: {user_email}
Message: {message}
Submitted on: {feedback_timestamp}
        """
        admin_msg.attach(MIMEText(admin_body, 'plain', _charset='utf-8'))

        # --- User Email ---
        user_msg = MIMEMultipart()
        user_msg['From'] = sender_email
        user_msg['To'] = user_email
        user_msg['Subject'] = "Thanks for your feedback!"

        user_body = f"""
Hi {name},

Thank you for reaching out to us. We've received your feedback:

"{message}"

Submitted on: {feedback_timestamp}

We appreciate your input!

- Career Assistance Team
        """
        user_msg.attach(MIMEText(user_body, 'plain', _charset='utf-8'))

        # Send the emails
        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)

            server.sendmail(sender_email, admin_email, admin_msg.as_string())
            server.sendmail(sender_email, user_email, user_msg.as_string())

            server.quit()
            print("✅ Emails sent successfully.")
        except Exception as email_err:
            print("❌ Email sending failed:", str(email_err))

        flash("✅ Thank you for your feedback! We've emailed a confirmation to you.", "success")
        return redirect(url_for('feedback'))

    except Exception as err:
        print("❌ Feedback submission failed:", str(err))
        flash("⚠️ Something went wrong. Please try again later.", "error")
        
        return redirect(url_for('feedback'))

@app.route('/trending')
def trending_courses():
    if 'user_id' in session:
        log_activity(session['user_id'], 'Visited trending courses')
    return render_template('trending.html')

@app.route('/courses')
def recommended_courses():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    log_activity(session['user_id'], 'Visited recommended courses')
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    # Fetch student details
    cursor.execute("SELECT name, test_score, student_group FROM users WHERE id=%s", (user_id,))
    student = cursor.fetchone()

    if student:
        student_name, test_score, student_group = student

        if test_score is None:
            conn.close()
            flash("⚠️ Please complete the aptitude test to view recommended courses.")
            return redirect('/aptitude_instructions')

        group = (student_group or "").strip()
        test_score = test_score or 0

        if group == "Bio-Maths":
            courses = [
                    "B.Sc Mathematics", 
                    "B.Sc Statistics", 
                    "B.Sc Physics", 
                    "B.Sc Chemistry",
                    "B.Sc Computer Science", 
                    "B.Sc Plant Biology & Plant Biotechnology",
                    "B.Sc Data Science and Artificial Intelligence", 
                    "B.Sc (Clinical Nutrition and Dietetics)",
                    "B.Sc (Nutrition Food Service Management and Dietetics)",
                    "B.Sc Computer Science with Data Science", 
                    "B.Sc Computer Science with Cognitive Systems",
                    "B.Sc Computer Science with Artificial Intelligence",
                    "B.C.A"
                ]

        elif group == "Science with Computer Science":
            courses = [
                    "B.Sc Computer Science", 
                    "B.Sc Mathematics",
                    "B.Sc Statistics", 
                    "B.Sc Physics", 
                    "B.Sc Chemistry",
                    "B.C.A", 
                    "B.Sc Computer Science with Data Science", 
                    "B.Sc Computer Science with Artificial Intelligence",
                    "B.Sc Computer Science with Cognitive Systems", 
                    "B.Sc Data Science and Artificial Intelligence"
                ]

        elif group == "Commerce with Computer Applications":
                courses = [
                    "B.Com (Computer Applications)", 
                    "B.Com", 
                    "B.Com (Corporate Secretaryship)",
                    "B.Com (Banking and Insurance Management)", 
                    "B.Com (Information Systems Management)",
                    "B.Com (Professional Accounting)", 
                    "B.Com (Honours)", 
                    "B.Com Fintech with AI",
                    "B.Com (Accounting and Finance)", 
                    "B.B.A", 
                    "B.B.A (Digital Marketing and Business Analytics)",
                    "B.C.A", 
                    "B.Sc Computer Science", 
                    "MBA Business Analytics"
                ]

        elif group == "Pure Commerce":
                courses = [
                    "B.Com", 
                    "B.Com (Corporate Secretaryship)", 
                    "B.Com (Banking and Insurance Management)",
                    "B.Com (Information Systems Management)", 
                    "B.Com (Professional Accounting)", 
                    "B.Com (Honours)",
                    "B.Com Fintech with AI", 
                    "B.Com (Accounting and Finance)", 
                    "B.B.A",
                    "B.B.A (Digital Marketing and Business Analytics)"
                ]

        elif group == "Arts with Computer Applications":
                courses = [
                    "B.A. English", 
                    "B.A. History and Tourism", 
                    "B.A. Economics", 
                    "B.voc. (Travel & Tourism)",
                    "B.C.A", 
                    "B.Sc Computer Science",
                    "B.Sc Visual Communication", 
                    "B.Sc Psychology", 
                    "B.Sc Computer Science with AI",
                    "B.Sc Computer Science with Data Science", 
                    "B.Sc Computer Science with Cognitive Systems"
                ]

        elif group == "Pure Arts":
                courses = [
                    "B.A. English",
                    "B.A. History and Tourism", 
                    "B.A. Economics",
                    "B.Voc. (Travel & Tourism)", 
                    "B.Sc Visual Communication", 
                    "B.Sc Psychology",
                    "B.Sc (Home Science - Clinical Nutrition and Dietetics)",
                    "B.Sc (Home Science - Nutrition Food Service Management and Dietetics)"
                ]

        else:
            # Group not matched with any known categories
            conn.close()
            flash("Please update your profile by completing the test.")
            return redirect('/student_dashboard')

        recommended_courses = [{"name": c, "description": ""} for c in courses]
        conn.close()

        return render_template("courses.html",
                               student={"name": student_name, "test_score": test_score},
                               recommended_courses=recommended_courses)

    conn.close()

    return redirect('/student_dashboard')

@app.route('/details')
def details():
    if 'user_id' in session: 
        log_activity(session['user_id'], 'Visited course details')
    return render_template('details.html')

@app.route('/QAE')
def quantitative_exams():
    if 'user_id' in session:
        log_activity(session['user_id'], 'Visited QAE page')
    return render_template('QAE.html')

@app.route('/sample')
def sample():
    if 'user_id' in session:
        log_activity(session['user_id'], 'Visited sample qae paper')
    return render_template('sample.html')

if __name__ == '__main__':
     port = int(os.environ.get("PORT", 5000))
     app.run(host="0.0.0.0", port=port)