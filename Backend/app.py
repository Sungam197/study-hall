import os
import secrets
from datetime import timedelta

import stripe
from flask import Flask, render_template, request, session, redirect, url_for
from flask_login import current_user, logout_user
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

from Backend.main import generate_questions, evaluate_answers
from Backend.extensions import db, login_manager, migrate, oauth
from Backend.models import User

load_dotenv()

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# ── Database ──────────────────────────────────────────────────────────────────
_db_url = os.environ.get('DATABASE_URL', 'sqlite:///studyhall.db')
if _db_url.startswith('postgres://'):          # Render gives postgres://, SQLAlchemy needs postgresql://
    _db_url = _db_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = _db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ── Remember-me cookie (30 days) ──────────────────────────────────────────────
app.config['REMEMBER_COOKIE_DURATION']  = timedelta(days=30)
app.config['REMEMBER_COOKIE_HTTPONLY']  = True
app.config['REMEMBER_COOKIE_SAMESITE'] = 'Lax'

# ── Stripe ────────────────────────────────────────────────────────────────────
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

# ── Init extensions ───────────────────────────────────────────────────────────
db.init_app(app)
migrate.init_app(app, db)

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
from Backend.auth import auth_bp          # noqa: E402
app.register_blueprint(auth_bp)

# ── Template globals ──────────────────────────────────────────────────────────
@app.context_processor
def inject_globals():
    def csrf_token():
        if '_csrf_token' not in session:
            session['_csrf_token'] = secrets.token_hex(32)
        return session['_csrf_token']
    return dict(csrf_token=csrf_token)

# ── Create tables (new deployments) ──────────────────────────────────────────
with app.app_context():
    db.create_all()

_TERMS_EXEMPT = {'terms', 'accept_terms', 'auth.logout', 'stripe_webhook', 'static'}

# ── Terms acceptance gate ─────────────────────────────────────────────────────
@app.before_request
def enforce_terms_accepted():
    if not current_user.is_authenticated:
        return
    if current_user.terms_accepted:
        return
    if request.endpoint is None or request.endpoint in _TERMS_EXEMPT:
        return
    return redirect(url_for('terms'))

# ── Single-device enforcement ─────────────────────────────────────────────────
@app.before_request
def enforce_single_device():
    if not current_user.is_authenticated:
        return
    stored       = current_user.session_token
    device_token = session.get('_device_token')

    if stored is None and device_token is None:
        # Pre-feature session: assign a token so future logins are blocked
        new_token = secrets.token_hex(32)
        current_user.session_token = new_token
        session['_device_token'] = new_token
        db.session.commit()
    elif stored is None or stored != device_token:
        # Token was cleared (user logged out on another device) → sign out here too
        logout_user()
        session.clear()
        return redirect(url_for('auth.login'))


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/terms')
def terms():
    return render_template('terms.html')


@app.route('/accept-terms', methods=['POST'])
def accept_terms():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    if session.get('_csrf_token') != request.form.get('_csrf_token'):
        return redirect(url_for('terms'))
    current_user.terms_accepted = True
    db.session.commit()
    return redirect(url_for('index'))


@app.route('/generate', methods=['POST'])
def generate():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))

    # Paywall: block after 1 free use
    if current_user.has_used_free and not current_user.has_paid:
        return render_template('index.html', paywall=True)

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

    # Mark free use on first quiz
    if not current_user.has_used_free:
        current_user.has_used_free = True
        db.session.commit()

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


# ── Stripe checkout ───────────────────────────────────────────────────────────

@app.route('/checkout', methods=['POST'])
def checkout():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))

    # CSRF check
    if session.get('_csrf_token') != request.form.get('_csrf_token'):
        return redirect(url_for('index'))

    checkout_session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{'price': os.environ.get('STRIPE_PRICE_ID', ''), 'quantity': 1}],
        mode='payment',
        success_url=url_for('payment_success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=url_for('index', _external=True),
        customer_email=current_user.email,
        metadata={'user_id': str(current_user.id)},
    )
    return redirect(checkout_session.url, code=303)


@app.route('/payment-success')
def payment_success():
    session_id = request.args.get('session_id')
    if session_id and current_user.is_authenticated and not current_user.has_paid:
        try:
            checkout_session = stripe.checkout.Session.retrieve(session_id)
            if checkout_session.payment_status == 'paid':
                uid = (checkout_session.metadata or {}).get('user_id')
                if uid and int(uid) == current_user.id:
                    current_user.has_paid = True
                    db.session.commit()
        except Exception:
            pass
    return render_template('payment_success.html')


@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    payload   = request.get_data(as_text=False)
    sig       = request.headers.get('Stripe-Signature', '')
    secret    = os.environ.get('STRIPE_WEBHOOK_SECRET', '')

    app.logger.info(f"Webhook received, sig: {bool(sig)}, secret: {bool(secret)}")

    try:
        event = stripe.Webhook.construct_event(payload, sig, secret)
    except ValueError as e:
        app.logger.error(f"Webhook ValueError: {e}")
        return '', 400
    except stripe.SignatureVerificationError as e:
        app.logger.error(f"Webhook SignatureVerificationError: {e}")
        return '', 400

    app.logger.info(f"Webhook event type: {event['type']}")

    if event['type'] == 'checkout.session.completed':
        data    = event['data']['object']
        try:
            user_id = data.metadata['user_id']
        except (KeyError, AttributeError):
            user_id = None
        app.logger.info(f"Payment completed for user_id: {user_id}")
        if user_id:
            user = db.session.get(User, int(user_id))
            if user:
                user.has_paid = True
                db.session.commit()

    return '', 200

if __name__ == '__main__':
    app.run(debug=True)
