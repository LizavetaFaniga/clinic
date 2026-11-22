from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "clinic_secret_2026"
DATABASE = 'clinic.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            login TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            role TEXT DEFAULT 'user'
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            specialization TEXT NOT NULL,
            cabinet TEXT NOT NULL
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            appointment_date TEXT NOT NULL,
            status TEXT DEFAULT 'Новая' CHECK (status IN ('Новая', 'В обработке', 'Прием завершен')),
            review_text TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(id)
        )''')
        
        if conn.execute("SELECT COUNT(*) FROM doctors").fetchone()[0] == 0:
            doctors = [
                ('Иванов Иван Иванович', 'Терапевт', '101'),
                ('Петрова Анна Сергеевна', 'Кардиолог', '204'),
                ('Сидоров Олег Дмитриевич', 'Стоматолог', '302')
            ]
            conn.executemany("INSERT INTO doctors (full_name, specialization, cabinet) VALUES (?, ?, ?)", doctors)
        
        if conn.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0] == 0:
            hashed_pw = generate_password_hash("admin")
            conn.execute("INSERT INTO users (login, password, full_name, phone, role) VALUES (?, ?, ?, ?, ?)",
                         ('Admin', hashed_pw, 'Главный врач', '8(999)000-00-00', 'admin'))
        conn.commit()

@app.route("/")
def index():
    if not session.get('user_id'):
        return redirect(url_for('login'))
    if session.get('role') == 'admin':
        return redirect(url_for('admin_panel'))
    
    db = get_db()
    doctors = db.execute("SELECT * FROM doctors").fetchall()
    appointments = db.execute('''
        SELECT a.*, d.full_name as doctor_name, d.specialization 
        FROM appointments a JOIN doctors d ON a.doctor_id = d.id
        WHERE a.user_id = ? ORDER BY a.id DESC
    ''', (session['user_id'],)).fetchall()
    return render_template("dashboard.html", doctors=doctors, appointments=appointments)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login = request.form.get("login")
        password = request.form.get("password")
        user = get_db().execute("SELECT * FROM users WHERE login = ?", (login,)).fetchone()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['full_name'] = user['full_name']
            session['role'] = user['role']
            return redirect(url_for('index'))
        flash("Неверный логин или пароль", "error")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        login = request.form.get("login")
        password = request.form.get("password")
        full_name = request.form.get("full_name")
        phone = request.form.get("phone")
        db = get_db()
        if db.execute("SELECT id FROM users WHERE login = ?", (login,)).fetchone():
            flash("Этот логин уже занят!", "error")
            return redirect(url_for('register'))
        db.execute("INSERT INTO users (login, password, full_name, phone) VALUES (?, ?, ?, ?)",
                   (login, generate_password_hash(password), full_name, phone))
        db.commit()
        flash("Регистрация успешна! Войдите в систему.", "success")
        return redirect(url_for('login'))
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route("/book/<int:doctor_id>", methods=["POST"])
def book(doctor_id):
    date = request.form.get("date")
    if date:
        db = get_db()
        db.execute("INSERT INTO appointments (user_id, doctor_id, appointment_date) VALUES (?, ?, ?)",
                   (session['user_id'], doctor_id, date))
        db.commit()
        flash("Вы успешно записались на прием!", "success")
    return redirect(url_for('index'))

@app.route("/review/<int:app_id>", methods=["POST"])
def review(app_id):
    text = request.form.get("review_text")
    if text and len(text) >= 5:
        db = get_db()
        db.execute("UPDATE appointments SET review_text = ? WHERE id = ? AND user_id = ?",
                   (text, app_id, session['user_id']))
        db.commit()
        flash("Спасибо за отзыв!", "success")
    return redirect(url_for('index'))

@app.route("/admin")
def admin_panel():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    status_filter = request.args.get('status', '')
    page = max(1, int(request.args.get('page', 1)))
    per_page = 5
    
    db = get_db()
    query = '''SELECT a.*, u.full_name as patient, d.full_name as doctor 
               FROM appointments a 
               JOIN users u ON a.user_id = u.id 
               JOIN doctors d ON a.doctor_id = d.id'''
    params = []
    
    if status_filter:
        query += " WHERE a.status = ?"
        params.append(status_filter)
    
    query += " ORDER BY a.id DESC LIMIT ? OFFSET ?"
    params.extend([per_page, (page - 1) * per_page])
    
    apps = db.execute(query, params).fetchall()
    return render_template("admin.html", appointments=apps, status_filter=status_filter, page=page)

@app.route("/admin/status/<int:app_id>", methods=["POST"])
def update_status(app_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    new_status = request.form.get("status")
    db = get_db()
    db.execute("UPDATE appointments SET status = ? WHERE id = ?", (new_status, app_id))
    db.commit()
    flash("Статус обновлен", "success")
    return redirect(url_for('admin_panel', status=request.form.get('current_filter'), page=request.form.get('current_page')))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)