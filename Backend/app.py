import os
import secrets
from datetime import timedelta

from flask import Flask, render_template, request, session, redirect, url_for
from flask_login import current_user
from dotenv import load_dotenv

from Backend.main import generate_questions, evaluate_answers
from Backend.extensions import db, login_manager, oauth
from Backend.models import User

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# ── Database ──────────────────────────────────────────────────────────────────
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 'sqlite:///studyhall.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ── Remember-me cookie (30 days, secure defaults) ─────────────────────────────
app.config['REMEMBER_COOKIE_DURATION']  = timedelta(days=30)
app.config['REMEMBER_COOKIE_HTTPONLY']  = True
app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'
# Enable in production behind HTTPS:
# app.config['REMEMBER_COOKIE_SECURE'] = True

# ── Init extensions ───────────────────────────────────────────────────────────
db.init_app(app)

login_manager.init_app(app)
login_manager.login_view    = 'auth.login'
login_manager.login_message = None

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

oauth.init_app(app)
oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

# ── Auth blueprint ────────────────────────────────────────────────────────────
from Backend.auth import auth_bp          # noqa: E402 (must come after oauth.register)
app.register_blueprint(auth_bp)

# ── CSRF token available in every template ────────────────────────────────────
@app.context_processor
def inject_csrf():
    def csrf_token():
        if '_csrf_token' not in session:
            session['_csrf_token'] = secrets.token_hex(32)
        return session['_csrf_token']
    return dict(csrf_token=csrf_token)

# ── Create tables on first run ────────────────────────────────────────────────
with app.app_context():
    db.create_all()


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generate', methods=['POST'])
def generate():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))

    notes     = request.form.get('notes', '').strip()
    count_raw = request.form.get('count', '5').strip()

    if not notes:
        return render_template('index.html', error='Please paste your notes before generating.')

    try:
        count = int(count_raw)
        if not 1 <= count <= 20:
            raise ValueError
    except ValueError:
        return render_template('index.html',
                               error='Question count must be a number between 1 and 20.',
                               notes=notes)

    try:
        questions = generate_questions(notes, count)
    except Exception as e:
        return render_template('index.html',
                               error=f'Generation failed: {e}',
                               notes=notes, count=count_raw)

    session['questions'] = questions
    return render_template('quiz.html', questions=questions)


@app.route('/submit', methods=['POST'])
def submit():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))

    questions = session.get('questions')
    if not questions:
        return redirect(url_for('index'))

    user_answers = [
        request.form.get(f'answer_{i}', '').strip()
        for i in range(len(questions))
    ]

    try:
        feedback = evaluate_answers(questions, user_answers)
    except Exception as e:
        return render_template('quiz.html', questions=questions,
                               error=f'Evaluation failed: {e}')

    session.pop('questions', None)
    return render_template('results.html',
                           questions=questions,
                           user_answers=user_answers,
                           feedback=feedback)


if __name__ == '__main__':
    app.run(debug=True)
