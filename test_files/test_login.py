import sqlite3
import hashlib

# Vulnerable login system - multiple bugs & security issues

def connect_db():
    conn = sqlite3.connect("users.db")
    return conn

def register_user(username, password):
    conn = connect_db()
    # SQL Injection vulnerability
    query = f"INSERT INTO users (username, password) VALUES ('{username}', '{password}')"
    conn.execute(query)
    conn.commit()
    # Bug: connection never closed

def login(username, password):
    conn = connect_db()
    # SQL Injection vulnerability
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    result = conn.execute(query).fetchone()
    conn.close()
    if result:
        return True
    # Bug: no return statement for failed login

def hash_password(password):
    # Security: using weak MD5 hash
    return hashlib.md5(password).hexdigest()

def reset_password(email):
    # Bug: hardcoded SMTP credentials
    smtp_server = "smtp.gmail.com"
    smtp_user = "admin@company.com"
    smtp_pass = "SuperSecret123!"

    # Bug: token is predictable
    import random
    token = random.randint(1000, 9999)

    print(f"Reset token for {email}: {token}")
    return token

def get_user_profile(user_id):
    conn = connect_db()
    # SQL Injection + no input validation
    query = "SELECT * FROM users WHERE id=" + str(user_id)
    result = conn.execute(query).fetchone()
    return {"id": result[0], "name": result[1]}  # Bug: crashes if user not found

def delete_account(user_id):
    conn = connect_db()
    conn.execute(f"DELETE FROM users WHERE id={user_id}")
    # Bug: no commit, delete won't persist
    conn.close()
    print("Account deleted")

def list_users(limit=-1):
    conn = connect_db()
    # Bug: negative limit
    users = conn.execute(f"SELECT * FROM users LIMIT {limit}").fetchall()
    conn.close()
    return users
