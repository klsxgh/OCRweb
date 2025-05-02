from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import pytesseract
from PIL import Image
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'super-secret-key'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ocr.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))

class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    filename = db.Column(db.String(200))
    ocr_text = db.Column(db.Text)
    model_used = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])

        if User.query.filter_by(username=username).first():
            flash("Username already exists.")
            return redirect(url_for('register'))

        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash("Registered successfully! Please log in.")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('dashboard'))
        flash("Invalid credentials.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    models = ["default", "fast", "accurate"]  
    selected_model = request.form.get("model") if request.method == "POST" else "default"
    ocr_text = ""
    filename = ""

    if request.method == 'POST':
        file = request.files['image']
        if file:
            filename = file.filename
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(path)

            try:
                img = Image.open(path)
                ocr_text = pytesseract.image_to_string(img)
            except Exception as e:
                ocr_text = f"Error: {str(e)}"

            new_record = History(
                user_id=session['user_id'],
                filename=filename,
                ocr_text=ocr_text,
                model_used=selected_model
            )
            db.session.add(new_record)
            db.session.commit()

    history = History.query.filter_by(user_id=session['user_id']).order_by(History.timestamp.desc()).all()
    total_uploads = len(history)

    return render_template('index.html',
                           ocr_text=ocr_text,
                           filename=filename,
                           model=selected_model,
                           models=models,
                           history=history,
                           total_uploads=total_uploads,
                           username=session['username'])


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000)
