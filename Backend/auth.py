import re
import secrets
from datetime import timedelta
from urllib.parse import urlparse

from flask import Blueprint, render_template, redirect, url_for, request, session
from flask_login import login_user, logout_user, login_required, current_user

from Backend.extensions import db, oauth
from Backend.models import User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# ── CSRF helpers ──────────────────────────────────────────────────────────────

def _get_csrf_token() -> str:
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']


def _validate_csrf() -> bool:
    token = session.get('_csrf_token')
    return bool(token and token == request.form.get('_csrf_token'))


# ── Misc helpers ──────────────────────────────────────────────────────────────

def _get_ip() -> str:
    forwarded = request.headers.get('X-Forwarded-For')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or '0.0.0.0'


def _safe_next(next_url: str | None) -> str:
    """Return next_url only if it's a safe relative path (blocks open redirects)."""
    if next_url:
        parsed = urlparse(next_url)
        if not parsed.netloc and not parsed.scheme and next_url.startswith('/'):
            return next_url
    return url_for('index')


_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

# ── Routes ────────────────────────────────────────────────────────────────────

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    error = None
    if request.method == 'POST':
        if not _validate_csrf():
            error = 'Invalid request — please try again.'
        else:
            email    = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            user     = User.query.filter_by(email=email).first()

            if user and user.check_password(password):
                user.record_login(_get_ip())
                db.session.commit()
                login_user(user, remember=True, duration=timedelta(days=30))
                return redirect(_safe_next(request.args.get('next')))

            error = 'Incorrect email or password.'

    return render_template('auth/login.html',
                           error=error,
                           csrf_token=_get_csrf_token())


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    error = None
    if request.method == 'POST':
        if not _validate_csrf():
            error = 'Invalid request — please try again.'
        else:
            name     = request.form.get('name', '').strip()
            email    = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            confirm  = request.form.get('confirm_password', '')

            if not _EMAIL_RE.match(email):
                error = 'Please enter a valid email address.'
            elif len(password) < 8:
                error = 'Password must be at least 8 characters.'
            elif password != confirm:
                error = 'Passwords do not match.'
            elif User.query.filter_by(email=email).first():
                error = 'An account with that email already exists.'
            else:
                user = User(email=email, name=name or None)
                user.set_password(password)
                user.record_login(_get_ip())
                db.session.add(user)
                db.session.commit()
                login_user(user, remember=True, duration=timedelta(days=30))
                return redirect(url_for('index'))

    return render_template('auth/register.html',
                           error=error,
                           csrf_token=_get_csrf_token())


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    if not _validate_csrf():
        return redirect(url_for('index'))
    logout_user()
    return redirect(url_for('index'))


# ── Google OAuth ──────────────────────────────────────────────────────────────

@auth_bp.route('/google')
def google_login():
    if request.args.get('next'):
        session['oauth_next'] = request.args.get('next')
    redirect_uri = url_for('auth.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route('/google/callback')
def google_callback():
    try:
        token = oauth.google.authorize_access_token()
    except Exception:
        return redirect(url_for('auth.login'))

    userinfo = token.get('userinfo') or {}
    google_id  = userinfo.get('sub')
    email      = (userinfo.get('email') or '').lower()
    name       = userinfo.get('name')
    avatar_url = userinfo.get('picture')

    if not google_id or not email:
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(google_id=google_id).first()
    if not user:
        # Try to link an existing email account
        user = User.query.filter_by(email=email).first()
        if user:
            user.google_id  = google_id
            user.name       = user.name or name
            user.avatar_url = user.avatar_url or avatar_url
        else:
            user = User(email=email, google_id=google_id,
                        name=name, avatar_url=avatar_url)
            db.session.add(user)

    user.record_login(_get_ip())
    db.session.commit()
    login_user(user, remember=True, duration=timedelta(days=30))

    next_page = session.pop('oauth_next', None)
    return redirect(_safe_next(next_page))
