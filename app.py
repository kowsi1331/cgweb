from flask import Flask, request, session, redirect, url_for, render_template,flash
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

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'query.careerassistance25@gmail.com'      # Change to your email
app.config['MAIL_PASSWORD'] = 'rtho txgj rqfm vnyg'        # Use an App Password
mail = Mail(app)

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

        if not is_valid_email(email):
            return render_template('signup.html', error="Invalid email format!")

        if len(password) < 6 or not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
            return render_template('signup.html', error="Password must be at least 6 characters and contain a letter and number!")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
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
                cursor.execute("INSERT INTO users (name, email, password, is_admin) VALUES (?, ?, ?, 0)",
                               (user['name'], user['email'], user['password']))
                conn.commit()
                conn.close()

                session.pop('otp', None)
                return redirect(url_for('login'))
        else:
            return render_template('verify_otp.html', error="Invalid OTP. Please try again.")
    if 'otp' in session:
        flash("OTP sent to your email. Please check your inbox or spam folder.")

    return render_template('verify_otp.html')

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

        # First, check if the email exists
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
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

        login_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE users SET login_time=? WHERE id=?", (login_time, user['id']))
        cursor.execute("INSERT INTO user_activity (user_id, activity) VALUES (?, ?)", (user['id'], "Logged in"))

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
        print("No user in session")
        return redirect(url_for('login'))

    user_id = session['user_id']
    print(f"User ID: {user_id}")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Get student group
    cursor.execute("SELECT student_group FROM users WHERE id=?", (user_id,))
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
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
            "UPDATE users SET test_score=?, recommended_degrees=? WHERE id=?",
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
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT group_name, answers FROM aptitude_results WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    conn.close()

    if not result:
        return "No test results found for user ID: {}".format(user_id)

    group_name, answers_json = result
    submitted_answers = json.loads(answers_json)

    # Map full question text for each group
    group_questions = {
        "Bio-Maths": {
            "q1": "What is the powerhouse of the cell?",
            "q2": "Which trigonometric function is periodic?",
            "q3": "Who discovered the laws of motion?",
            "q4": "Which blood group is called the universal donor?",
            "q5": "What is the derivative of sin(x)?",
            "q6": "Which organ secretes insulin?",
            "q7": "DNA is made up of?",
            "q8": "What is the SI unit of speed?",
            "q9": "What is Avogadro’s number?",
            "q10": "Who is the father of genetics?"
        },
        "Science with Computer Science": {
            "q1": "What does CPU stand for?",
            "q2": "Which data structure follows LIFO?",
            "q3": "Binary of decimal 8 is?",
            "q4": "Which device routes data packets in networks?",
            "q5": "Binary representation of decimal 10 is?",
            "q6": "Which protocol is used for web communication?",
            "q7": "Who founded Microsoft?",
            "q8": "Which language is used to design web pages?",
            "q9": "What executes instructions in a computer?",
            "q10": "Which operator checks equality in Python?"
        },
        "Commerce with Computer Applications": {
            "q1": "Which software is used for accounting?",
            "q2": "Which is used to design websites?",
            "q3": "Which MS Office tool is spreadsheet-based?",
            "q4": "Which is the primary storage device in a computer?",
            "q5": "What is e-commerce?",
            "q6": "Shortcut for copy in Windows is?",
            "q7": "What is an email scam called?",
            "q8": "Macro language in MS Excel is?",
            "q9": "LAN stands for?",
            "q10": "Which software is used for presentations?"
        },
        "Pure Commerce": {
            "q1": "What does GDP stand for?",
            "q2": "Which document shows assets and liabilities?",
            "q3": "What type of tax is based on income?",
            "q4": "What is an example of an expense?",
            "q5": "What is the most liquid asset?",
            "q6": "Which two terms are key in accounting?",
            "q7": "Which body manages India's monetary policy?",
            "q8": "Outstanding salary is shown as?",
            "q9": "A bill sent by the seller is called?",
            "q10": "Basic accounting equation is?"
        },
        "Arts with Computer Applications": {
            "q1": "Which tool is used for graphic design?",
            "q2": "Which software is used for 3D animation?",
            "q3": "Who painted 'Starry Night'?",
            "q4": "What tool is used with a drawing tablet?",
            "q5": "Which art style uses geometric shapes?",
            "q6": "Which software is best for document editing?",
            "q7": "Which image format is widely used?",
            "q8": "What does GUI stand for?",
            "q9": "Which feature changes font size and style?",
            "q10": "Which site is used to showcase portfolios?"
        },
        "Pure Arts": {
            "q1": "Who wrote 'Romeo and Juliet'?",
            "q2": "Which classical dance originated in Tamil Nadu?",
            "q3": "Which color is a secondary color?",
            "q4": "Who painted the Mona Lisa?",
            "q5": "What is a 14-line poem called?",
            "q6": "What is folklore?",
            "q7": "Who is a famous fable writer?",
            "q8": "Which instrument is used in classical music?",
            "q9": "What type of performance includes acting?",
            "q10": "Who is known as the greatest English writer?"
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
    user_email = request.form['email']
    message = request.form['message']
    id=request.form['id']

    # Store in database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO feedback (name, email, message,id)
        VALUES (?, ?, ?, ?)
    ''', (name, user_email, message,id))
    conn.commit()

    # Get the latest inserted feedback with timestamp
    cursor.execute('SELECT timestamp FROM feedback WHERE email = ? ORDER BY id DESC LIMIT 1', (user_email,))
    feedback_timestamp = cursor.fetchone()[0]
    conn.close()

    # Email configuration
    sender_email = "query.careerassistance@gmail.com"
    sender_password = "rtho txgj rqfm vnyg"
    admin_email = "careerassistancefeedback@gmail.com"
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    # Email to admin
    admin_msg = MIMEMultipart()
    admin_msg['From'] = sender_email
    admin_msg['To'] = admin_email
    admin_msg['Subject'] = "New Feedback Received"

    admin_body = f"""
    📬 New Feedback Received

    ID: {id}
    Name: {name}
    Email: {user_email}
    Message: {message}
    Submitted on: {feedback_timestamp}
    """
    admin_msg.attach(MIMEText(admin_body, 'plain'))

    # Email to user
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
    user_msg.attach(MIMEText(user_body, 'plain'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)

        server.sendmail(sender_email, admin_email, admin_msg.as_string())
        server.sendmail(sender_email, user_email, user_msg.as_string())

        server.quit()
    except Exception as e:
        print("Error sending email:", e)
    
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
            group = (student_group or "").strip()

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
                courses = ["General – Group not identified. Explore common career paths."]

            # Convert to list of dicts (optional descriptions could be added later)
            recommended_courses = [{"name": c, "description": ""} for c in courses]

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