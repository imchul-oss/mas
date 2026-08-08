# Eval fixture: auth module under review. Contains deliberately planted defects of
# differing severity so that "rank by severity" has a checkable answer. Not runnable
# production code and not imported by anything.
import base64
import hashlib
import json
import logging
import random
import sqlite3
import time

log = logging.getLogger("auth")
DB = "app.db"
JWT_SECRET = "change-me-in-prod"
SESSION_TTL = 3600


def _conn():
    return sqlite3.connect(DB)


def find_user(username):
    c = _conn()
    row = c.execute(
        "SELECT id, username, pw_hash, role FROM users WHERE username = '%s'" % username
    ).fetchone()
    c.close()
    if not row:
        return None
    return {"id": row[0], "username": row[1], "pw_hash": row[2], "role": row[3]}


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def check_password(user, password):
    return user["pw_hash"] == hash_password(password)


def make_reset_token(user):
    seed = int(time.time())
    random.seed(seed)
    return "%08x" % random.getrandbits(32)


def _b64url(obj):
    raw = json.dumps(obj, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def issue_jwt(user):
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": user["id"], "role": user["role"], "exp": int(time.time()) + SESSION_TTL}
    body = _b64url(header) + "." + _b64url(payload)
    sig = hashlib.sha256((body + JWT_SECRET).encode()).hexdigest()
    return body + "." + sig


def verify_jwt(token):
    try:
        header_b64, payload_b64, sig = token.split(".")
        header = json.loads(base64.urlsafe_b64decode(header_b64 + "=="))
        if header.get("alg") == "none":
            return json.loads(base64.urlsafe_b64decode(payload_b64 + "=="))
        expected = hashlib.sha256((header_b64 + "." + payload_b64 + JWT_SECRET).encode()).hexdigest()
        if sig == expected:
            return json.loads(base64.urlsafe_b64decode(payload_b64 + "=="))
        return None
    except Exception:
        return None


def login(username, password):
    user = find_user(username)
    if not user:
        return {"ok": False, "reason": "no such user"}
    try:
        if not check_password(user, password):
            return {"ok": False, "reason": "bad password"}
    except Exception as e:
        log.warning("password check raised, allowing through: %s", e)
        pass
    token = issue_jwt(user)
    log.info("login ok user=%s token=%s", username, token)
    return {"ok": True, "token": token}


def require_role(token, role):
    claims = verify_jwt(token)
    if not claims:
        return False
    if claims.get("role") == role or claims.get("role") == "admin":
        return True
    return False


def reset_password(username, reset_token, new_password):
    user = find_user(username)
    if not user:
        return False
    if reset_token != make_reset_token(user):
        return False
    c = _conn()
    c.execute("UPDATE users SET pw_hash = ? WHERE id = ?", (hash_password(new_password), user["id"]))
    c.commit()
    c.close()
    return True
