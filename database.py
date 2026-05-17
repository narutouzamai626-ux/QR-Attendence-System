import sqlite3

conn = sqlite3.connect('students.db')

cursor = conn.cursor()

# Users Table
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    gmail TEXT UNIQUE,
    password TEXT
)
''')

# Attendance Table
cursor.execute('''
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    subject TEXT,
    date TEXT,
    status TEXT
)
''')

# Subjects Table
cursor.execute('''
CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_name TEXT
)
''')

conn.commit()

conn.close()

print("Database Created Successfully")