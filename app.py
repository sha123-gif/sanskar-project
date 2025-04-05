from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'top-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.permanent_session_lifetime = timedelta(minutes=5)

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# Constants
ADMIN_PASSCODE = "galaxy42"

# Models
class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(150))
    file_path = db.Column(db.String(200))
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)

# Routes
@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    pagination = Announcement.query.order_by(Announcement.date_posted.desc()).paginate(page=page, per_page=6)

    # Fetch image announcements for the ticker (filter only image files)
    image_announcements = Announcement.query.filter(
        Announcement.file_path.isnot(None)
    ).filter(
        Announcement.file_path.ilike('%.jpg') |
        Announcement.file_path.ilike('%.jpeg') |
        Announcement.file_path.ilike('%.png') |
        Announcement.file_path.ilike('%.gif')
    ).order_by(Announcement.date_posted.desc()).limit(10).all()

    return render_template(
        'index.html',
        announcements=pagination.items,
        pagination=pagination,
        image_announcements=image_announcements
    )


@app.route('/announcements')
def announcements_redirect():
    return redirect(url_for('index'))

@app.route('/announcement/<int:announcement_id>')
def view_announcement(announcement_id):
    ann = Announcement.query.get_or_404(announcement_id)
    return render_template('view_announcement.html', ann=ann)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if session.get('passcode_verified'):
        if request.method == 'POST':
            title = request.form['title']
            content = request.form['content']
            description = request.form.get('description')
            location = request.form.get('location')
            uploaded_file = request.files.get('file')
            file_path = None

            if uploaded_file and uploaded_file.filename:
                filename = secure_filename(uploaded_file.filename)
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                uploaded_file.save(upload_path)

                # Save only path relative to "static"
                file_path = os.path.relpath(upload_path, 'static').replace("\\", "/")

            new_announcement = Announcement(
                title=title,
                content=content,
                description=description,
                location=location,
                file_path=file_path
            )
            db.session.add(new_announcement)
            db.session.commit()
            flash('Announcement posted successfully!', 'success')
            return redirect(url_for('index'))

        return render_template('admin.html', verified=True)

    if request.method == 'POST':
        passcode = request.form.get('passcode')
        if passcode == ADMIN_PASSCODE:
            session['passcode_verified'] = True
            return redirect(url_for('admin'))
        else:
            flash('Incorrect passcode. Access denied.', 'danger')
            return redirect(url_for('admin'))

    return render_template('admin.html', verified=False)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# Initialize DB
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
