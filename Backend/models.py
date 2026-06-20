from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from Backend.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)
    google_id     = db.Column(db.String(120), unique=True, nullable=True)
    name          = db.Column(db.String(120), nullable=True)
    avatar_url    = db.Column(db.String(500), nullable=True)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime, nullable=True)
    last_login_ip = db.Column(db.String(45), nullable=True)

    # ── Payment ───────────────────────────────────────────
    has_used_free = db.Column(db.Boolean, default=False, nullable=False)
    has_paid      = db.Column(db.Boolean, default=False, nullable=False)

    # ── Single-device enforcement ─────────────────────────
    session_token = db.Column(db.String(64), nullable=True, index=True)

    # --- password helpers ---

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(
            password, method='pbkdf2:sha256:600000'
        )

    def check_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    # --- login tracking ---

    def record_login(self, ip: str) -> None:
        self.last_login_at = datetime.utcnow()
        self.last_login_ip = ip

    # --- helpers ---

    @property
    def display_name(self) -> str:
        return self.name or self.email.split('@')[0]
