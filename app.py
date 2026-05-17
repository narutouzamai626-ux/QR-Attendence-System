import os
from datetime import datetime, timedelta
import sqlite3

from flask import Flask, redirect, render_template, request, session
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

        if user and check_password_hash(user[3], password):

            session["user"] = username

            return redirect("/user_dashboard")

        else:

            return "Invalid Username or Password"

    return render_template("login.html")


# =========================
# STUDENT SIGNUP
# =========================
@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        # PASSWORD CHECK
        if password != confirm_password:

            return "Passwords Do Not Match"

        conn = sqlite3.connect("students.db")
        cursor = conn.cursor()

        # EXISTING USER CHECK
        cursor.execute(
            "SELECT * FROM users WHERE username=?",
            (username,)
        )

        existing_user = cursor.fetchone()

        if existing_user:

            conn.close()

            return "Username Already Exists"

        # HASH PASSWORD
        hashed_password = generate_password_hash(password)

        # INSERT USER
        cursor.execute(
            "INSERT INTO users (username, gmail, password) VALUES (?, ?, ?)",
            (username, "", hashed_password)
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

    ACTIVE_QR["subject"] = subject
    ACTIVE_QR["created_at"] = datetime.now()

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

    today = str(datetime)