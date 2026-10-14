"""Google OAuth login (skeleton).

Without GOOGLE_CLIENT_ID/SECRET every request runs as the built-in "local" user.
With them, /auth/google/login signs the user in and requests are scoped to that user via the session cookie.
TODO: token-based auth for Electron/CLI clients, require login when auth is configured.
"""
from authlib.integrations.flask_client import OAuth
from flask import Blueprint, jsonify, redirect, session, url_for

from backend import config, db

bp = Blueprint("auth", __name__, url_prefix="/auth")
oauth = OAuth()


def init(app):
    oauth.init_app(app)
    if config.GOOGLE_CLIENT_ID:
        oauth.register(
            name="google",
            client_id=config.GOOGLE_CLIENT_ID,
            client_secret=config.GOOGLE_CLIENT_SECRET,
            server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
            client_kwargs={"scope": "openid email profile"},
        )


def current_user_id():
    return session.get("user_id", "local")


@bp.get("/google/login")
def google_login():
    if not config.GOOGLE_CLIENT_ID:
        return jsonify(error="Google OAuth is not configured"), 501
    return oauth.google.authorize_redirect(url_for("auth.google_callback", _external=True))


@bp.get("/google/callback")
def google_callback():
    info = oauth.google.authorize_access_token()["userinfo"]
    user_id = f"google:{info['sub']}"
    db.upsert_user(user_id, info.get("email"), info.get("name"))
    session["user_id"] = user_id
    return redirect(config.FRONTEND_URL)


@bp.get("/me")
def me():
    return jsonify(db.get_user(current_user_id()))


@bp.post("/logout")
def logout():
    session.pop("user_id", None)
    return jsonify(ok=True)
