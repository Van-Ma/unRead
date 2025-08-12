"""
UserAuthentication
- Verifies credentials (bcrypt or Argon2)
- Issues signed JWTs
- Reads auth from Authorization header (Bearer <token>) or secure cookie
- Sets/clears secure session cookies
- Small helpers to wire into Flask endpoints

Dependencies:
    pip install PyJWT bcrypt argon2-cffi
"""

from __future__ import annotations
import time
from typing import Any, Dict, Optional, Tuple

try:
    import bcrypt
    HAVE_BCRYPT = True
except Exception:
    HAVE_BCRYPT = False

try:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError
    HAVE_ARGON2 = True
except Exception:
    HAVE_ARGON2 = False

import jwt


class UserAuthentication:
    def __init__(
        self,
        jwt_secret: str,
        issuer: str = "auth-service",
        audience: Optional[str] = None,
        algo: str = "HS256",
        access_ttl_seconds: int = 3600,
        cookie_name: str = "session",
        cookie_domain: Optional[str] = None,
        cookie_path: str = "/",
        cookie_secure: bool = True,
        cookie_samesite: str = "Lax",
        cookie_http_only: bool = True,
    ):
        if not jwt_secret:
            raise ValueError("jwt_secret is required")
        self.jwt_secret = jwt_secret
        self.issuer = issuer
        self.audience = audience
        self.algo = algo
        self.access_ttl_seconds = access_ttl_seconds

        self.cookie_name = cookie_name
        self.cookie_domain = cookie_domain
        self.cookie_path = cookie_path
        self.cookie_secure = cookie_secure
        self.cookie_samesite = cookie_samesite
        self.cookie_http_only = cookie_http_only

        self._argon2 = PasswordHasher() if HAVE_ARGON2 else None

    @staticmethod
    def hash_password(password: str, algo: str = "bcrypt") -> Tuple[str, str]:
        if algo == "argon2":
            if not HAVE_ARGON2:
                raise RuntimeError("argon2-cffi not installed")
            ph = PasswordHasher()
            return ph.hash(password), "argon2"
        if not HAVE_BCRYPT:
            raise RuntimeError("bcrypt not installed")
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8"), "bcrypt"

    def verify_password(self, password: str, stored_hash: str, algo: Optional[str] = None) -> bool:
        algo = (algo or "").lower()
        if algo == "argon2":
            if not HAVE_ARGON2:
                return False
            try:
                self._argon2.verify(stored_hash, password)
                return True
            except VerifyMismatchError:
                return False
            except Exception:
                return False
        if not HAVE_BCRYPT:
            return False
        try:
            return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
        except Exception:
            return False

    def generate_jwt(self, sub: str, claims: Optional[Dict[str, Any]] = None, ttl_seconds: Optional[int] = None) -> str:
        now = int(time.time())
        exp = now + int(ttl_seconds or self.access_ttl_seconds)
        payload = {
            "iss": self.issuer,
            "iat": now,
            "nbf": now,
            "exp": exp,
            "sub": sub,
        }
        if self.audience:
            payload["aud"] = self.audience
        if claims:
            payload.update(claims)

        token = jwt.encode(payload, self.jwt_secret, algorithm=self.algo)
        return token if isinstance(token, str) else token.decode("utf-8")

    def verify_jwt(self, token: str) -> Dict[str, Any]:
        options = {"verify_aud": bool(self.audience)}
        return jwt.decode(
            token,
            self.jwt_secret,
            algorithms=[self.algo],
            audience=self.audience,
            issuer=self.issuer,
            options=options,
        )

    @staticmethod
    def get_bearer_from_header(request) -> Optional[str]:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        return auth.split(" ", 1)[1].strip() or None

    def get_token_from_cookie(self, request) -> Optional[str]:
        return request.cookies.get(self.cookie_name)

    def get_token_from_request(self, request) -> Optional[str]:
        return self.get_bearer_from_header(request) or self.get_token_from_cookie(request)

    def set_session_cookie(self, response, token: str, ttl_seconds: Optional[int] = None) -> None:
        max_age = int(ttl_seconds or self.access_ttl_seconds)
        response.set_cookie(
            key=self.cookie_name,
            value=token,
            max_age=max_age,
            secure=self.cookie_secure,
            httponly=self.cookie_http_only,
            samesite=self.cookie_samesite,
            domain=self.cookie_domain,
            path=self.cookie_path,
        )

    def clear_session_cookie(self, response) -> None:
        response.delete_cookie(
            key=self.cookie_name,
            domain=self.cookie_domain,
            path=self.cookie_path,
        )

    def perform_login_issue_token(
        self,
        email: str,
        password: str,
        user_lookup_fn,
        extra_claims_fn=None,
        set_cookie: bool = False,
        flask_response_factory=None,
    ):
        user = user_lookup_fn(email)
        if not user:
            return False, {"status": "error", "message": "Invalid credentials"}

        ok = self.verify_password(password, user["password_hash"], user.get("hash_algo"))
        if not ok:
            return False, {"status": "error", "message": "Invalid credentials"}

        claims = {"email": user.get("email"), "role": user.get("role")}
        if extra_claims_fn:
            claims.update(extra_claims_fn(user) or {})

        token = self.generate_jwt(sub=str(user["id"]), claims=claims)

        if set_cookie:
            if not flask_response_factory:
                raise ValueError("flask_response_factory is required when set_cookie=True")
            resp = flask_response_factory({"status": "success", "userId": user["id"]}, 200)
            self.set_session_cookie(resp, token)
            return True, resp

        return True, {"status": "success", "token": token, "userId": user["id"]}

    def require_auth(self, request) -> Dict[str, Any]:
        token = self.get_token_from_request(request)
        if not token:
            raise ValueError("Missing authentication token")
        try:
            return self.verify_jwt(token)
        except Exception as e:
            raise ValueError(f"Invalid token: {e}")
