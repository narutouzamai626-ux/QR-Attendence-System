import os
from datetime import datetime, timedelta
import random
import sqlite3

from flask import Flask, redirect, render_template, request, session
from flask_mail import Mail, Message
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

import qrcode

# =========================
# LOAD ENVIRONMENT VARIABLES
# =========================
load_dotenv()

app = Flask(__name__)

# =========================
# SECRET KEY
# =========================
app.secret_key = os.getenv("FLASK_SECRET_KEY", "attendance_system")

# =========================
# FLASK MAIL CONFIGURATION
# =========================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_TIMEOUT'] = 10
app.config['MAIL_USERNAME'] = os.getenv("EMAIL_USER")
app.config['MAIL_PASSWORD'] = os.getenv("EMAIL_PASS")

mail = Mail(app)

# =========================
# DATABASE INITIALIZATION
# =========================
def init_db():

    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    # USERS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        gmail TEXT UNIQUE,
        password TEXT
    )
    """)

    # SUBJECTS TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_name TEXT
    )
    """)

    # ATTENDANCE TABLE
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        subject TEXT,
        date TEXT,
        status TEXT
    )
    """)

    conn.commit()
    conn.close()


# =========================
# ACTIVE QR TRACKER
# =========================
ACTIVE_QR = {
    "subject": None,
    "created_at": None
}


# =========================
# HOME PAGE
# =========================
@app.route("/")
def home():

    return render_template("index.html")


# =========================
# STUDENT LOGIN
# =========================
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("students.db")
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        )

        user = cursor.fetchone()

        conn.close()

        # user[3] = password column
        if user and check_password_hash(user[3], password):

            session["user"] = username

            return redirect("/user_dashboard")

        else:

            return "Invalid Username or Password"

    return render_template("login.html")


# =========================
# SEND OTP
# =========================
@app.route("/send_otp", methods=["POST"])
def send_otp():

    gmail = request.form["gmail"]

    otp = str(random.randint(100000, 999999))

    session["otp"] = otp

    # OTP EXPIRY TIME
    session["otp_time"] = datetime.now().timestamp()

    msg = Message(
        "Email Verification",
        sender=app.config['MAIL_USERNAME'],
        recipients=[gmail]
    )

    msg.body = f"Your OTP is {otp}"

    try:
        with mail.connect() as conn:
            conn.send(msg)

        return "OTP Sent Successfully"

    except Exception as e:

        return f"Mail Error: {str(e)}"


# =========================
# STUDENT SIGNUP
# =========================
@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        username = request.form["username"]
        gmail = request.form["gmail"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        entered_otp = request.form["otp"]

        # PASSWORD CHECK
        if password != confirm_password:

            return "Passwords Do Not Match"

        # OTP EXISTS?
        if "otp" not in session:

            return "Please Generate OTP First"

        # OTP EXPIRY CHECK (5 MINUTES)
        otp_time = session.get("otp_time")

        if datetime.now().timestamp() - otp_time > 300:

            return "OTP Expired. Please Generate Again"

        # OTP VERIFICATION
        if entered_otp != session.get("otp"):

            return "Invalid OTP"

        conn = sqlite3.connect("students.db")
        cursor = conn.cursor()

        # EXISTING USER CHECK
        cursor.execute(
            "SELECT * FROM users WHERE username=? OR gmail=?",
            (username, gmail)
        )

        existing_user = cursor.fetchone()

        if existing_user:

            conn.close()

            return "Username Or Gmail Already Exists"

        # HASH PASSWORD
        hashed_password = generate_password_hash(password)

        # INSERT USER
        cursor.execute(
            "INSERT INTO users (username, gmail, password) VALUES (?, ?, ?)",
            (username, gmail, hashed_password)
        )

        conn.commit()
        conn.close()

        return redirect("/login")

    return render_template("signup.html")


# =========================
# USER DASHBOARD
# =========================
@app.route("/user_dashboard")
def user_dashboard():

    if "user" not in session:

        return redirect("/login")

    return render_template("user_dashboard.html")


# =========================
# USER PROFILE
# =========================
@app.route("/profile")
def profile():

    if "user" not in session:

        return redirect("/login")

    return render_template("profile.html")


# =========================
# ADMIN LOGIN
# =========================
@app.route("/admin", methods=["GET", "POST"])
def admin():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        admin_user = os.getenv("ADMIN_USER")
        admin_pass = os.getenv("ADMIN_PASS")

        if username == admin_user and password == admin_pass:

            session["admin"] = username

            return redirect("/admin_dashboard")

        else:

            return "Invalid Admin Login"

    return render_template("admin.html")


# =========================
# ADMIN DASHBOARD
# =========================
@app.route("/admin_dashboard")
def admin_dashboard():

    if "admin" not in session:

        return redirect("/admin")

    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM subjects")

    subjects = cursor.fetchall()

    conn.close()

    return render_template(
        "admin_dashboard.html",
        subjects=subjects
    )


# =========================
# ADMIN PROFILE
# =========================
@app.route("/admin_profile")
def admin_profile():

    if "admin" not in session:

        return redirect("/admin")

    return render_template(
        "admin_profile.html",
        admin_username=session["admin"]
    )


# =========================
# ADD SUBJECT
# =========================
@app.route("/add_subject", methods=["POST"])
def add_subject():

    if "admin" not in session:

        return redirect("/admin")

    # CLEAN SUBJECT INPUT
    subject = request.form["subject"].strip().title()

    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO subjects (subject_name) VALUES (?)",
        (subject,)
    )

    conn.commit()
    conn.close()

    return redirect("/admin_dashboard")


# =========================
# DELETE SUBJECT
# =========================
@app.route("/delete_subject/<int:id>")
def delete_subject(id):

    if "admin" not in session:

        return redirect("/admin")

    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM subjects WHERE id=?",
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/admin_dashboard")


# =========================
# GENERATE QR
# =========================
@app.route("/generate_qr/<subject>")
def generate_qr(subject):

    if "admin" not in session:

        return redirect("/admin")

    # STORE ACTIVE QR DETAILS
    ACTIVE_QR["subject"] = subject
    ACTIVE_QR["created_at"] = datetime.now()

    # AUTO LIVE URL
    data = request.host_url + f"mark_attendance/{subject}"

    qr = qrcode.make(data)

    qr.save("static/attendance_qr.png")

    return redirect("/admin_dashboard")


# =========================
# MARK ATTENDANCE
# =========================
@app.route("/mark_attendance/<subject>")
def mark_attendance(subject):

    if "user" not in session:

        return redirect("/login")

    username = session["user"]

    today = str(datetime.now().date())

    # ACTIVE QR EXISTS?
    if ACTIVE_QR["created_at"] is None or ACTIVE_QR["subject"] != subject:

        return """
        <h1>Error</h1>
        <p>No Active Attendance Session Found</p>
        <a href='/user_dashboard'>Back</a>
        """, 400

    # 10 MINUTE TIMER CHECK
    time_elapsed = datetime.now() - ACTIVE_QR["created_at"]

    if time_elapsed > timedelta(minutes=10):

        return """
        <h1>Attendance Closed</h1>
        <p>10 Minute Window Expired</p>
        <a href='/user_dashboard'>Back</a>
        """, 403

    conn = sqlite3.connect("students.db")
    cursor = conn.cursor()

    # EXISTING ATTENDANCE CHECK
    cursor.execute(
        """
        SELECT * FROM attendance
        WHERE username=? AND subject=? AND date=?
        """,
        (username, subject, today)
    )

    existing_attendance = cursor.fetchone()

    if existing_attendance:

        conn.close()

        return f"Attendance Already Marked For {subject}"

    # INSERT ATTENDANCE
    cursor.execute(
        """
        INSERT INTO attendance
        (username, subject, date, status)
        VALUES (?, ?, ?, ?)
        """,
        (username, subject, today, "Present")
    )

    conn.commit()
    conn.close()

    return f"""
    <h1>Success</h1>
    <p>Attendance Marked Successfully For {subject}</p>
    <a href='/user_dashboard'>Dashboard</a>
    """


# =========================
# QR SCANNER PAGE
# =========================
@app.route("/scan")
def scan():

    if "user" not in session:

        return redirect("/login")

    return render_template("scanner.html")


# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# =========================
# INITIALIZE DATABASE
# =========================
init_db()


# =========================
# RUN APP
# =========================
if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=8000,
        debug=False
    )