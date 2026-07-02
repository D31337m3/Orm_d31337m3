"""
API Routes for Orchestrator Service
Contains service discovery, registration, and lifecycle management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Security, Request
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, EmailStr
import os
import logging
import json
import smtplib
import ssl
import subprocess
import urllib.request
import urllib.error
import sqlite3
import threading
import shutil
import random
import time
import hmac
import hashlib
import tempfile
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone

# Import shared components
import sys
sys.path.append('/home/D31337m3/Orm_d31337m3/microservices')

from shared.jwt_utils import (
    create_service_token,
    verify_service_token,
    verify_user_token,
    create_user_token,
    user_has_admin_access,
)
from shared.security_middleware import verify_service_request, require_service_auth, verify_user_request
from shared.database_models import generate_id, now_iso
from shared.database import SessionLocal, Finding
from shared.repositories import SignatureRepository, ProfileRepository, UserRepository, DocumentRepository, KeywordRepository
from shared.utils import SUPPORTED_COUNTRIES, DATA_BROKERS, BROKER_DIRECTORY, PLANS, RATE_LIMITS, RATE_WINDOW_SEC, RATE_MAX_ATTEMPTS, LEGAL_TEMPLATES, _fill_template
from shared.secrets_manager import get_secret, get_infisical_status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Import local models (would be defined in a models.py file)
# For now, we'll define them inline

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("orchestrator.routes")

# Create routers
service_router = APIRouter()
health_router = APIRouter()
admin_router = APIRouter()
support_router = APIRouter()
workforce_router = APIRouter()
public_router = APIRouter()
client_router = APIRouter()

# Security schemes
bearing = HTTPBearer(auto_error=False)

# Admin in-memory stores
BROKER_CONTACTS: Dict[str, Dict[str, Any]] = {}
EMAIL_LOG: List[Dict[str, Any]] = []
PAYMENTS: List[Dict[str, Any]] = []
REMOVALS: List[Dict[str, Any]] = []
AUDIT_LOG: List[Dict[str, Any]] = []
DOCUMENTS: List[Dict[str, Any]] = []
SUPPORT_CHATS: Dict[str, Dict[str, Any]] = {}
SUPPORT_MESSAGES: Dict[str, List[Dict[str, Any]]] = {}
SUPPORT_TICKETS: Dict[str, Dict[str, Any]] = {}
SUPPORT_ANON_CHALLENGES: Dict[str, Dict[str, Any]] = {}
SUPPORT_ANON_SESSIONS: Dict[str, Dict[str, Any]] = {}
WORKFORCE_SHIFTS: Dict[str, Dict[str, Any]] = {}
WORKFORCE_TIMESHEETS: Dict[str, Dict[str, Any]] = {}
WORKFORCE_PAYROLL_RUNS: Dict[str, Dict[str, Any]] = {}
SUPPORT_EMAIL_OTP_REQUIRED: bool = True
_state_lock = threading.Lock()

for _broker in BROKER_DIRECTORY:
    BROKER_CONTACTS[_broker["name"]] = {
        "id": generate_id(),
        "broker": _broker["name"],
        "email": _broker.get("privacy_email"),
        "phone": _broker.get("privacy_phone"),
        "address": _broker.get("address"),
        "form": _broker.get("opt_out_url"),
        "region": _broker.get("region"),
        "updated_at": now_iso(),
        "updated_by": "seed",
    }

_support_db_lock = threading.Lock()


def _runtime_state_path() -> str:
    path = get_secret(
        "ORCHESTRATOR_RUNTIME_STATE_PATH",
        "/home/D31337m3/Orm_d31337m3/microservices/state/d31337m3_orchestrator_runtime.json",
    ) or "/home/D31337m3/Orm_d31337m3/microservices/state/d31337m3_orchestrator_runtime.json"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def save_runtime_state() -> None:
    payload = {
        "broker_contacts": BROKER_CONTACTS,
        "email_log": EMAIL_LOG,
        "payments": PAYMENTS,
        "removals": REMOVALS,
        "audit_log": AUDIT_LOG,
        "documents": DOCUMENTS,
        "support_chats": SUPPORT_CHATS,
        "support_messages": SUPPORT_MESSAGES,
        "support_tickets": SUPPORT_TICKETS,
        "support_email_otp_required": SUPPORT_EMAIL_OTP_REQUIRED,
        "workforce_shifts": WORKFORCE_SHIFTS,
        "workforce_timesheets": WORKFORCE_TIMESHEETS,
        "workforce_payroll_runs": WORKFORCE_PAYROLL_RUNS,
        "saved_at": now_iso(),
    }
    target = _runtime_state_path()
    fd, tmp = tempfile.mkstemp(prefix="orchestrator_runtime_", suffix=".json", dir=os.path.dirname(target))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass


def load_runtime_state() -> None:
    global SUPPORT_EMAIL_OTP_REQUIRED
    target = _runtime_state_path()
    if not os.path.exists(target):
        return
    try:
        with open(target, "r", encoding="utf-8") as f:
            payload = json.load(f)

        BROKER_CONTACTS.update(payload.get("broker_contacts") or {})
        EMAIL_LOG[:] = payload.get("email_log") or []
        PAYMENTS[:] = payload.get("payments") or []
        REMOVALS[:] = payload.get("removals") or []
        AUDIT_LOG[:] = payload.get("audit_log") or []
        DOCUMENTS[:] = payload.get("documents") or []
        SUPPORT_CHATS.clear(); SUPPORT_CHATS.update(payload.get("support_chats") or {})
        SUPPORT_MESSAGES.clear(); SUPPORT_MESSAGES.update(payload.get("support_messages") or {})
        SUPPORT_TICKETS.clear(); SUPPORT_TICKETS.update(payload.get("support_tickets") or {})
        SUPPORT_EMAIL_OTP_REQUIRED = bool(payload.get("support_email_otp_required", SUPPORT_EMAIL_OTP_REQUIRED))
        WORKFORCE_SHIFTS.clear(); WORKFORCE_SHIFTS.update(payload.get("workforce_shifts") or {})
        WORKFORCE_TIMESHEETS.clear(); WORKFORCE_TIMESHEETS.update(payload.get("workforce_timesheets") or {})
        WORKFORCE_PAYROLL_RUNS.clear(); WORKFORCE_PAYROLL_RUNS.update(payload.get("workforce_payroll_runs") or {})
    except Exception as e:
        logger.warning(f"orchestrator runtime state load warning: {e}")


with _state_lock:
    load_runtime_state()


def _cfg_int(key: str, default: int) -> int:
    return int(get_secret(key, str(default)) or str(default))


def _cfg_bool(key: str, default: bool) -> bool:
    fallback = "true" if default else "false"
    raw = str(get_secret(key, fallback) or fallback).strip().lower()
    return raw in {"1", "true", "yes", "on"}


SUPPORT_EMAIL_OTP_REQUIRED = _cfg_bool("SUPPORT_ANON_EMAIL_OTP_REQUIRED", True)
TRIAL_PERIOD_DAYS = _cfg_int("TRIAL_PERIOD_DAYS", 30)


def _support_anon_otp_ttl_minutes() -> int:
    return _cfg_int("SUPPORT_ANON_OTP_TTL_MINUTES", 10)


def _support_anon_otp_max_attempts() -> int:
    return _cfg_int("SUPPORT_ANON_OTP_MAX_ATTEMPTS", 5)


def _support_anon_session_hours() -> int:
    return _cfg_int("SUPPORT_ANON_SESSION_HOURS", 12)


def _support_anon_verified_challenge_retention_seconds() -> int:
    return _cfg_int("SUPPORT_ANON_VERIFIED_CHALLENGE_RETENTION_SECONDS", 1800)


def support_anon_cleanup_interval_seconds() -> int:
    return _cfg_int("SUPPORT_ANON_CLEANUP_INTERVAL_SECONDS", 300)


def _max_audit_log_entries() -> int:
    return _cfg_int("MAX_AUDIT_LOG_ENTRIES", 100000)


def _max_email_log_entries() -> int:
    return _cfg_int("MAX_EMAIL_LOG_ENTRIES", 20000)


def _max_payments_entries() -> int:
    return _cfg_int("MAX_PAYMENTS_ENTRIES", 50000)


def _max_removals_entries() -> int:
    return _cfg_int("MAX_REMOVALS_ENTRIES", 50000)


def _max_documents_entries() -> int:
    return _cfg_int("MAX_DOCUMENTS_ENTRIES", 50000)


def _max_support_chats() -> int:
    return _cfg_int("MAX_SUPPORT_CHATS", 20000)


def _max_support_messages_per_chat() -> int:
    return _cfg_int("MAX_SUPPORT_MESSAGES_PER_CHAT", 2000)


def _support_db_path() -> str:
    legacy_path = "/tmp/d31337m3_orchestrator_support.db"
    path = get_secret(
        "ORCHESTRATOR_SUPPORT_DB_PATH",
        "/home/D31337m3/Orm_d31337m3/microservices/state/d31337m3_orchestrator_support.db",
    ) or "/home/D31337m3/Orm_d31337m3/microservices/state/d31337m3_orchestrator_support.db"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(legacy_path) and not os.path.exists(path):
        try:
            shutil.copy2(legacy_path, path)
            logger.warning(f"Migrated legacy DB from {legacy_path} to {path}")
        except Exception as e:
            logger.warning(f"Failed to migrate legacy DB {legacy_path}: {e}")
    return path


class SupportAnonStartIn(BaseModel):
    email: EmailStr


class SupportAnonVerifyIn(BaseModel):
    challenge_id: str
    email: EmailStr
    otp: str


class SupportAnonResendIn(BaseModel):
    challenge_id: str
    email: EmailStr


class SupportAnonMessageIn(BaseModel):
    session_token: str
    text: str


def _support_db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_support_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _init_support_db() -> None:
    with _support_db_lock:
        conn = _support_db_conn()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS support_chats (
                    id TEXT PRIMARY KEY,
                    customer_id TEXT,
                    customer_email TEXT,
                    status TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_support_chats_customer ON support_chats(customer_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_support_chats_updated ON support_chats(updated_at)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS support_messages (
                    id TEXT PRIMARY KEY,
                    chat_id TEXT NOT NULL,
                    sent_at TEXT,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_support_messages_chat ON support_messages(chat_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_support_messages_sent ON support_messages(sent_at)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS support_tickets (
                    id TEXT PRIMARY KEY,
                    customer_id TEXT,
                    customer_email TEXT,
                    chat_id TEXT,
                    status TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    payload_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_support_tickets_customer ON support_tickets(customer_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_support_tickets_chat ON support_tickets(chat_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_support_tickets_updated ON support_tickets(updated_at)")
            conn.commit()
        finally:
            conn.close()


def _persist_support_chat(chat: dict) -> None:
    with _support_db_lock:
        conn = _support_db_conn()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO support_chats
                (id, customer_id, customer_email, status, created_at, updated_at, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    chat.get("id"),
                    chat.get("customer_id"),
                    chat.get("customer_email"),
                    chat.get("status"),
                    chat.get("created_at"),
                    chat.get("updated_at"),
                    json.dumps(chat),
                ),
            )
            conn.commit()
        finally:
            conn.close()


def _persist_support_message(message: dict) -> None:
    with _support_db_lock:
        conn = _support_db_conn()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO support_messages
                (id, chat_id, sent_at, payload_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    message.get("id"),
                    message.get("chat_id"),
                    message.get("sent_at"),
                    json.dumps(message),
                ),
            )
            conn.commit()
        finally:
            conn.close()


def _persist_support_ticket(ticket: dict) -> None:
    with _support_db_lock:
        conn = _support_db_conn()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO support_tickets
                (id, customer_id, customer_email, chat_id, status, created_at, updated_at, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ticket.get("id"),
                    ticket.get("customer_id"),
                    ticket.get("customer_email"),
                    ticket.get("chat_id"),
                    ticket.get("status"),
                    ticket.get("created_at"),
                    ticket.get("updated_at"),
                    json.dumps(ticket),
                ),
            )
            conn.commit()
        finally:
            conn.close()


def _delete_support_chat(chat_id: str) -> None:
    with _support_db_lock:
        conn = _support_db_conn()
        try:
            conn.execute("DELETE FROM support_messages WHERE chat_id = ?", (chat_id,))
            conn.execute("DELETE FROM support_tickets WHERE chat_id = ?", (chat_id,))
            conn.execute("DELETE FROM support_chats WHERE id = ?", (chat_id,))
            conn.commit()
        finally:
            conn.close()


def _load_support_state() -> None:
    with _support_db_lock:
        conn = _support_db_conn()
        try:
            for row in conn.execute("SELECT payload_json FROM support_chats"):
                try:
                    chat = json.loads(row["payload_json"])
                    SUPPORT_CHATS[chat["id"]] = chat
                except Exception:
                    continue

            for row in conn.execute("SELECT payload_json FROM support_messages ORDER BY sent_at ASC"):
                try:
                    msg = json.loads(row["payload_json"])
                    SUPPORT_MESSAGES.setdefault(msg.get("chat_id"), []).append(msg)
                except Exception:
                    continue

            for row in conn.execute("SELECT payload_json FROM support_tickets"):
                try:
                    ticket = json.loads(row["payload_json"])
                    SUPPORT_TICKETS[ticket["id"]] = ticket
                except Exception:
                    continue
        finally:
            conn.close()


_init_support_db()
_load_support_state()

async def verify_admin_or_service(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearing)
) -> dict:
    """Allow either valid service token OR admin user token."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")

    token = credentials.credentials

    # Service token path
    try:
        payload = verify_service_token(token, None)
        payload["auth_type"] = "service"
        return payload
    except Exception:
        pass

    # Admin user token path
    try:
        payload = verify_user_token(token)
        if not user_has_admin_access(payload.get("email"), bool(payload.get("is_admin"))):
            raise HTTPException(status_code=403, detail="Admin only")
        payload["auth_type"] = "user_admin"
        return payload
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


async def verify_employee_or_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearing)
) -> dict:
    """Allow service token, admin user, OR employee user (has employee_number)."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")

    token = credentials.credentials

    # Service token path
    try:
        payload = verify_service_token(token, None)
        payload["auth_type"] = "service"
        return payload
    except Exception:
        pass

    # User token path (admin OR employee)
    try:
        payload = verify_user_token(token)
        is_admin = user_has_admin_access(payload.get("email"), bool(payload.get("is_admin")))
        has_employee_number = bool(payload.get("employee_number"))
        if not is_admin and not has_employee_number:
            raise HTTPException(status_code=403, detail="Admin or employee access required")
        payload["auth_type"] = "user_admin" if is_admin else "user_employee"
        return payload
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


async def verify_authenticated_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearing)
) -> dict:
    """Allow authenticated users (admin or customer) for support endpoints."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")

    token = credentials.credentials
    try:
        payload = verify_user_token(token)
        _enforce_trial_paywall_for_request(
            path=request.url.path,
            auth_header=request.headers.get("authorization"),
            payload=payload,
        )
        payload["auth_type"] = "user"
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def _is_admin(payload: dict) -> bool:
    return user_has_admin_access(payload.get("email"), bool(payload.get("is_admin")))


def _chat_owner(chat: Dict[str, Any]) -> Optional[str]:
    return chat.get("customer_id")


def _ensure_chat_access(chat_id: str, payload: dict) -> Dict[str, Any]:
    chat = SUPPORT_CHATS.get(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    if not _is_admin(payload) and _chat_owner(chat) != payload.get("sub"):
        raise HTTPException(status_code=403, detail="Access denied")
    return chat


def _chat_ticket_count(chat_id: str) -> int:
    return sum(1 for t in SUPPORT_TICKETS.values() if t.get("chat_id") == chat_id)


def _mask_email(email: str) -> str:
    try:
        local, domain = email.split("@", 1)
    except ValueError:
        return "***"
    if len(local) <= 2:
        local_masked = local[0] + "*"
    else:
        local_masked = local[:2] + "*" * max(1, len(local) - 2)
    return f"{local_masked}@{domain}"


def _support_otp_digest(email: str, purpose: str, otp: str) -> str:
    secret = get_secret("JWT_SECRET", "dev-secret") or "dev-secret"
    msg = f"{email.lower()}|{purpose}|{otp}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def _support_generate_otp() -> str:
    return f"{random.randint(0, 999999):06d}"


def _send_email_via_azure(to: str, subject: str, body: str) -> bool:
    connection_string = _secret("AZURE_COMM_EMAIL_CONNECTION_STRING")
    if not connection_string:
        return False

    try:
        from azure.communication.email import EmailClient  # type: ignore

        client = EmailClient.from_connection_string(connection_string)
        sender = _secret("AZURE_COMM_EMAIL_SENDER", "DoNotReply@d31337m3.com") or "DoNotReply@d31337m3.com"
        message = {
            "senderAddress": sender,
            "recipients": {"to": [{"address": to}]},
            "content": {
                "subject": subject,
                "plainText": body,
                "html": f"<html><body><pre>{body}</pre></body></html>",
            },
        }
        poller = client.begin_send(message)
        result = poller.result()
        logger.info(f"Azure email sent: {getattr(result, 'message_id', None)}")
        return True
    except Exception as e:
        logger.warning(f"Azure email send failed, falling back to SMTP: {e}")
        return False


def _ratelimit(key: str, max_attempts: int, window_seconds: int) -> tuple[bool, int]:
    now = time.time()
    bucket = [t for t in RATE_LIMITS.get(key, []) if now - t < window_seconds]
    RATE_LIMITS[key] = bucket
    if len(bucket) >= max_attempts:
        retry = int(window_seconds - (now - bucket[0]))
        return False, max(1, retry)
    bucket.append(now)
    RATE_LIMITS[key] = bucket
    return True, 0


def _send_email_sync(to: str, subject: str, body: str) -> bool:
    if _send_email_via_azure(to, subject, body):
        return True

    smtp_host = _secret("SMTP_HOST")
    smtp_port = int(_secret("SMTP_PORT", "465") or "465")
    smtp_username = _secret("SMTP_USERNAME")
    smtp_password = _secret("SMTP_PASSWORD")
    smtp_from = _secret("SMTP_FROM") or smtp_username
    if not smtp_host or not smtp_username or not smtp_password or not smtp_from:
        logger.info(f"[EMAIL-MOCK] to={to} subject={subject} (SMTP not fully configured)")
        EMAIL_LOG.append({
            "id": generate_id(),
            "to": to,
            "subject": subject,
            "body": body,
            "mocked": True,
            "delivered": True,
            "sent_at": now_iso(),
        })
        return True

    msg = EmailMessage()
    msg["From"] = smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ctx, timeout=20) as server:
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        EMAIL_LOG.append({
            "id": generate_id(),
            "to": to,
            "subject": subject,
            "body": body,
            "mocked": False,
            "delivered": True,
            "sent_at": now_iso(),
        })
        return True
    except Exception as e:
        logger.error(f"support anon email send failed: {e}")
        EMAIL_LOG.append({
            "id": generate_id(),
            "to": to,
            "subject": subject,
            "body": body,
            "mocked": False,
            "delivered": False,
            "error": str(e),
            "sent_at": now_iso(),
        })
        return False


def _create_anon_chat(email: str) -> Dict[str, Any]:
    for c in SUPPORT_CHATS.values():
        if c.get("customer_id") is None and c.get("customer_email") == email and c.get("status") in ["open", "waiting", "active"]:
            return c

    chat_id = generate_id()
    chat = {
        "id": chat_id,
        "customer_id": None,
        "customer_email": email,
        "status": "open",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "last_message_at": None,
        "source": "anonymous",
    }
    SUPPORT_CHATS[chat_id] = chat
    SUPPORT_MESSAGES[chat_id] = []
    _persist_support_chat(chat)
    return chat


def _require_anon_session(session_token: str, chat_id: str, request: Request) -> Dict[str, Any]:
    session = SUPPORT_ANON_SESSIONS.get(session_token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid anonymous session")
    if session.get("chat_id") != chat_id:
        raise HTTPException(status_code=403, detail="Session not authorized for this chat")
    expires_at = session.get("expires_at")
    if not expires_at or datetime.fromisoformat(expires_at) < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Anonymous session expired")
    ip = request.client.host if request.client else "anon"
    if session.get("ip") != ip:
        raise HTTPException(status_code=403, detail="Session IP mismatch")
    return session


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def run_support_state_cleanup() -> Dict[str, int]:
    """Prune expired anonymous OTP challenges/sessions from in-memory stores."""
    now_dt = datetime.now(timezone.utc)
    removed_challenges = 0
    removed_sessions = 0
    trimmed_audit = 0
    trimmed_email = 0
    trimmed_payments = 0
    trimmed_removals = 0
    trimmed_documents = 0
    removed_chats = 0
    trimmed_messages = 0

    for challenge_id, challenge in list(SUPPORT_ANON_CHALLENGES.items()):
        expires_at = _parse_iso_datetime(challenge.get("expires_at"))
        created_at = _parse_iso_datetime(challenge.get("created_at"))
        is_verified = bool(challenge.get("verified"))
        expired = bool(expires_at and expires_at < now_dt)
        stale_verified = bool(
            is_verified
            and created_at
            and (now_dt - created_at).total_seconds() > _support_anon_verified_challenge_retention_seconds()
        )
        if expired or stale_verified:
            SUPPORT_ANON_CHALLENGES.pop(challenge_id, None)
            removed_challenges += 1

    for session_token, session in list(SUPPORT_ANON_SESSIONS.items()):
        expires_at = _parse_iso_datetime(session.get("expires_at"))
        chat_id = session.get("chat_id")
        expired = bool(expires_at and expires_at < now_dt)
        missing_chat = bool(chat_id and chat_id not in SUPPORT_CHATS)
        if expired or missing_chat:
            SUPPORT_ANON_SESSIONS.pop(session_token, None)
            removed_sessions += 1

    if len(AUDIT_LOG) > _max_audit_log_entries():
        trimmed_audit = len(AUDIT_LOG) - _max_audit_log_entries()
        del AUDIT_LOG[:trimmed_audit]

    if len(EMAIL_LOG) > _max_email_log_entries():
        trimmed_email = len(EMAIL_LOG) - _max_email_log_entries()
        del EMAIL_LOG[:trimmed_email]

    if len(PAYMENTS) > _max_payments_entries():
        trimmed_payments = len(PAYMENTS) - _max_payments_entries()
        del PAYMENTS[:trimmed_payments]

    if len(REMOVALS) > _max_removals_entries():
        trimmed_removals = len(REMOVALS) - _max_removals_entries()
        del REMOVALS[:trimmed_removals]

    if len(DOCUMENTS) > _max_documents_entries():
        trimmed_documents = len(DOCUMENTS) - _max_documents_entries()
        del DOCUMENTS[:trimmed_documents]

    if len(SUPPORT_CHATS) > _max_support_chats():
        over = len(SUPPORT_CHATS) - _max_support_chats()
        ordered = sorted(SUPPORT_CHATS.items(), key=lambda kv: str(kv[1].get("created_at", "")))
        for chat_id, _ in ordered[:over]:
            SUPPORT_CHATS.pop(chat_id, None)
            SUPPORT_MESSAGES.pop(chat_id, None)
            _delete_support_chat(chat_id)
            removed_chats += 1

    for chat_id, bucket in list(SUPPORT_MESSAGES.items()):
        if len(bucket) > _max_support_messages_per_chat():
            over = len(bucket) - _max_support_messages_per_chat()
            del bucket[:over]
            trimmed_messages += over

    with _state_lock:
        save_runtime_state()

    return {
        "removed_challenges": removed_challenges,
        "removed_sessions": removed_sessions,
        "trimmed_audit": trimmed_audit,
        "trimmed_email": trimmed_email,
        "trimmed_payments": trimmed_payments,
        "trimmed_removals": trimmed_removals,
        "trimmed_documents": trimmed_documents,
        "removed_chats": removed_chats,
        "trimmed_messages": trimmed_messages,
    }

def _fetch_users() -> List[Dict[str, Any]]:
    """Fetch users from client_index service."""
    token = create_service_token("orchestrator")
    req = urllib.request.Request(
        "http://127.0.0.1:8002/api/users/",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("users", [])
    except Exception:
        return []

def _find_user(user_id: str) -> Optional[Dict[str, Any]]:
    """Find user by ID."""
    for u in _fetch_users():
        if u.get("id") == user_id:
            return u
    return None


def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _is_subscription_active(status_value: Optional[str]) -> bool:
    status_norm = str(status_value or "").strip().lower()
    return status_norm in {"active", "paid", "subscribed"}


def _payment_gate_allowed_path(path: str) -> bool:
    normalized = str(path or "").rstrip("/")
    if normalized.startswith("/api/payments"):
        return True
    return normalized in {
        "/api/plans",
        "/api/subscribe",
        "/api/auth/me",
    }


def _get_subscription_status_from_payments(auth_header: Optional[str]) -> Optional[str]:
    if not auth_header:
        return None
    try:
        data = _payments_user_proxy("GET", "/api/subscriptions/", auth_header)
        sub = data.get("subscription") or {}
        return str(sub.get("status") or "").strip().lower() or None
    except Exception:
        return None


def _enforce_trial_paywall_for_request(path: str, auth_header: Optional[str], payload: dict) -> None:
    if _payment_gate_allowed_path(path):
        return

    if user_has_admin_access(payload.get("email"), bool(payload.get("is_admin"))):
        return
    if payload.get("employee_number"):
        return

    user_id = payload.get("sub")
    if not user_id:
        return

    user = _find_user(user_id) or {}
    created_at = _parse_iso_datetime(user.get("created_at"))
    trial_started_at = _parse_iso_datetime(user.get("subscription_started_at")) or created_at
    if not trial_started_at:
        return

    active_from_user = _is_subscription_active(user.get("subscription_status"))
    active_from_payments = _is_subscription_active(_get_subscription_status_from_payments(auth_header))
    if active_from_user or active_from_payments:
        return

    trial_days = max(1, int(TRIAL_PERIOD_DAYS))
    trial_expires_at = trial_started_at + timedelta(days=trial_days)
    now = datetime.now(timezone.utc)
    if now < trial_expires_at:
        return

    raise HTTPException(
        status_code=402,
        detail={
            "code": "TRIAL_EXPIRED",
            "message": "Your free trial has ended. Subscribe to continue using features.",
            "trial_period_days": trial_days,
            "trial_started_at": trial_started_at.isoformat(),
            "trial_expires_at": trial_expires_at.isoformat(),
        },
    )

# Service registry (in production, this would be more sophisticated and persistent)
SERVICE_REGISTRY: Dict[str, dict] = {}
SERVICE_STARTUP_ORDER = [
    "auditor",      # 1. Available for event recording
    "client_index", # 2. Identity and auth ready
    "data_handling",# 3. Data store ready
    "payments",     # 4. Billing flows ready
    "support_hub",  # 5. Customer chat and ticket operations
    "workforce_ops",# 6. Employee scheduling and payroll operations
    "watchdog",     # 5. Monitoring can begin
    "orchestrator"  # 7. Coordinates the others and exposes global state
]

SERVICE_PORTS: Dict[str, int] = {
    "auditor": 8005,
    "client_index": 8002,
    "data_handling": 8004,
    "payments": 8003,
    "support_hub": 8008,
    "workforce_ops": 8009,
    "watchdog": 8007,
    "orchestrator": 8006,
}

SYSTEMD_UNITS: Dict[str, str] = {
    "auditor": "d31337m3-auditor",
    "client_index": "d31337m3-client-index",
    "data_handling": "d31337m3-data-handling",
    "payments": "d31337m3-payments",
    "support_hub": "d31337m3-support-hub",
    "workforce_ops": "d31337m3-workforce-ops",
    "watchdog": "d31337m3-watchdog",
    "orchestrator": "d31337m3-orchestrator",
}

# Service health check intervals (in seconds)
HEALTH_CHECK_INTERVAL = 30

# Pydantic models for service registration
class ServiceRegistration(BaseModel):
    service_name: str
    host: str
    port: int
    health_endpoint: str = "/health"
    metadata: Optional[Dict[str, Any]] = None

class ServiceInfo(BaseModel):
    service_name: str
    host: str
    port: int
    status: str  # "starting", "healthy", "unhealthy", "stopping", "stopped"
    last_health_check: Optional[str] = None
    health_endpoint: str
    metadata: Optional[Dict[str, Any]] = None
    registered_at: str
    updated_at: str

class ServiceResponse(BaseModel):
    service_name: str
    host: str
    port: int
    status: str
    last_health_check: Optional[str] = None

# Helper functions
def is_service_authorized(service_name: str, token_payload: dict) -> bool:
    """Check if a service is authorized to perform an action"""
    # In a real implementation, this would check permissions/roles
    issuer = token_payload.get("iss")
    return issuer is not None  # Simplified for example

def get_next_service_to_start() -> Optional[str]:
    """Get the next service that should be started based on dependencies"""
    for service_name in SERVICE_STARTUP_ORDER:
        if service_name not in SERVICE_REGISTRY or SERVICE_REGISTRY[service_name].get("status") != "healthy":
            return service_name
    return None


def _secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Read from Infisical cache only."""
    return get_secret(key, default)


def _env_bool(key: str, default: bool = False) -> bool:
    val = _secret(key, "true" if default else "false")
    return str(val).strip().lower() == "true"


def _host_controls_enabled() -> bool:
    return _env_bool("ADMIN_ENABLE_HOST_CONTROLS", False)


def _systemctl_base_cmd() -> List[str]:
    if os.geteuid() == 0:
        return ["systemctl"]
    return ["sudo", "-n", "systemctl"]


def _run_cmd(cmd: List[str], timeout: int = 30) -> Dict[str, Any]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return {
            "ok": proc.returncode == 0,
            "code": proc.returncode,
            "stdout": (proc.stdout or "").strip(),
            "stderr": (proc.stderr or "").strip(),
            "command": " ".join(cmd),
        }
    except Exception as e:
        return {"ok": False, "code": -1, "stdout": "", "stderr": str(e), "command": " ".join(cmd)}


def _probe_service_status(service_name: str) -> dict:
    """Probe a service's /health endpoint and return status + metadata."""
    if service_name == "orchestrator":
        return {
            "status": "healthy",
            "version": "1.0.5",
            "started_at": now_iso(),
            "db_path": _support_db_path(),
            "last_health_check": now_iso(),
        }

    port = SERVICE_PORTS.get(service_name)
    if port is None:
        return {"status": "not_registered", "version": None, "started_at": None, "db_path": None, "last_health_check": None}

    url = f"http://127.0.0.1:{port}/health"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw = str(data.get("status", "healthy")).lower()
            return {
                "status": "healthy" if raw in ["healthy", "ok"] else "unhealthy",
                "version": str(data.get("version", "") or ""),
                "started_at": str(data.get("started_at", "") or ""),
                "db_path": data.get("db_path"),
                "last_health_check": now_iso(),
            }
    except Exception:
        return {"status": "unhealthy", "version": None, "started_at": None, "db_path": None, "last_health_check": now_iso()}


def _ensure_service_entry(service_name: str) -> Dict[str, Any]:
    """Ensure a service has a registry entry, creating a synthetic one when absent."""
    existing = SERVICE_REGISTRY.get(service_name)
    if existing:
        return existing

    port = SERVICE_PORTS.get(service_name)
    host = "127.0.0.1"
    probe = _probe_service_status(service_name)
    rec = {
        "service_name": service_name,
        "host": host,
        "port": port,
        "status": probe["status"],
        "version": probe.get("version") or "",
        "last_version": "",
        "started_at": probe.get("started_at") or "",
        "db_path": probe.get("db_path"),
        "last_health_check": probe["last_health_check"],
        "health_endpoint": "/health",
        "metadata": {},
        "registered_at": now_iso(),
        "updated_at": now_iso(),
    }
    SERVICE_REGISTRY[service_name] = rec
    return rec


def _refresh_registry_snapshot() -> None:
    """Refresh in-memory registry using live local health probes."""
    for service_name in SERVICE_STARTUP_ORDER:
# Public changelog endpoint (no auth — serves changes.md for the public security portal)
        rec = _ensure_service_entry(service_name)
        probe = _probe_service_status(service_name)
        new_version = probe.get("version") or ""
        if new_version and new_version != rec.get("version"):
            rec["last_version"] = rec.get("version", "")
            rec["version"] = new_version
        rec["status"] = probe["status"]
        if probe.get("started_at"):
            rec["started_at"] = probe["started_at"]
        rec["db_path"] = probe.get("db_path")
        rec["last_health_check"] = probe["last_health_check"]
        rec["updated_at"] = now_iso()

# Service registration and discovery endpoints
@service_router.post("/register")
async def register_service(
    service_data: ServiceRegistration,
    background: BackgroundTasks,
    token: dict = Depends(verify_admin_or_service)
):
    """Register a service with the orchestrator"""
    service_name = service_data.service_name
    
    # Verify the service is authorized to register (in a real implementation)
    # if not is_service_authorized(service_name, token):
    #     raise HTTPException(status_code=403, detail="Not authorized to register service")
    
    # Check if service is in the expected startup order
    if service_name not in SERVICE_STARTUP_ORDER:
        logger.warning(f"Service {service_name} is not in the predefined startup order")
    
    # Create service info
    service_info = ServiceInfo(
        service_name=service_name,
        host=service_data.host,
        port=service_data.port,
        status="starting",
        last_health_check=now_iso(),
        health_endpoint=service_data.health_endpoint,
        metadata=service_data.metadata or {},
        registered_at=now_iso(),
        updated_at=now_iso()
    )
    
    # Register the service
    SERVICE_REGISTRY[service_name] = service_info.dict()
    
    logger.info(f"Service registered: {service_name} at {service_data.host}:{service_data.port}")
    
    # Start health checking in background (in a real implementation)
    # background.add_task(health_check_service, service_name)
    
    # Check if we can start the next service in the sequence
    # background.add_task(check_startup_sequence)
    
    return {
        "message": f"Service {service_name} registered successfully",
        "service": service_info
    }

@service_router.get("/")
async def list_services(token: dict = Depends(verify_admin_or_service)):
    """List all registered services"""
    _refresh_registry_snapshot()
    services = []
    for service_name, service_info in SERVICE_REGISTRY.items():
        services.append(ServiceResponse(
            service_name=service_info["service_name"],
            host=service_info["host"],
            port=service_info["port"],
            status=service_info["status"],
            last_health_check=service_info["last_health_check"]
        ))
    
    return {
        "services": services,
        "count": len(services),
        "startup_order": SERVICE_STARTUP_ORDER
    }

@service_router.get("/{service_name}")
async def get_service(
    service_name: str,
    token: dict = Depends(verify_admin_or_service)
):
    """Get information about a specific service"""
    if service_name not in SERVICE_STARTUP_ORDER and service_name not in SERVICE_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Service {service_name} not found")

    service_info = _ensure_service_entry(service_name)
    return ServiceResponse(
        service_name=service_info["service_name"],
        host=service_info["host"],
        port=service_info["port"],
        status=service_info["status"],
        last_health_check=service_info["last_health_check"]
    )

@service_router.put("/{service_name}/heartbeat")
async def service_heartbeat(
    service_name: str,
    token: dict = Depends(verify_admin_or_service)
):
    """Update service heartbeat (called by services to indicate they're healthy)"""
    if service_name not in SERVICE_STARTUP_ORDER and service_name not in SERVICE_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
    _ensure_service_entry(service_name)
    
    # Update service status to healthy
    SERVICE_REGISTRY[service_name]["status"] = "healthy"
    SERVICE_REGISTRY[service_name]["last_health_check"] = now_iso()
    SERVICE_REGISTRY[service_name]["updated_at"] = now_iso()
    
    logger.debug(f"Heartbeat received from {service_name}")
    
    return {
        "message": f"Heartbeat updated for {service_name}",
        "status": "healthy",
        "timestamp": now_iso()
    }

@service_router.put("/{service_name}/status")
async def update_service_status(
    service_name: str,
    status_update: dict,
    token: dict = Depends(verify_admin_or_service)
):
    """Update service status (called by services or monitoring systems)"""
    if service_name not in SERVICE_STARTUP_ORDER and service_name not in SERVICE_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
    _ensure_service_entry(service_name)
    
    valid_statuses = ["starting", "healthy", "unhealthy", "stopping", "stopped"]
    if status_update.get("status") not in valid_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid status. Must be one of: {valid_statuses}"
        )
    
    # Update service status
    SERVICE_REGISTRY[service_name]["status"] = status_update["status"]
    SERVICE_REGISTRY[service_name]["last_health_check"] = now_iso() if status_update["status"] in ["healthy", "unhealthy"] else SERVICE_REGISTRY[service_name]["last_health_check"]
    SERVICE_REGISTRY[service_name]["updated_at"] = now_iso()
    
    logger.info(f"Service {service_name} status updated to: {status_update['status']}")
    
    return {
        "message": f"Service {service_name} status updated",
        "status": status_update["status"],
        "timestamp": now_iso()
    }

@service_router.delete("/{service_name}")
async def deregister_service(
    service_name: str,
    token: dict = Depends(verify_admin_or_service)
):
    """Deregister a service from the orchestrator"""
    if service_name not in SERVICE_REGISTRY:
        raise HTTPException(status_code=404, detail=f"Service {service_name} not found")
    
    # Remove service from registry
    deregistered_service = SERVICE_REGISTRY.pop(service_name)
    
    logger.info(f"Service deregistered: {service_name}")
    
    return {
        "message": f"Service {service_name} deregistered successfully",
        "service": deregistered_service
    }

# Health check endpoints for the orchestrator itself
@health_router.get("/")
async def orchestrator_health():
    """Get orchestrator health status"""
    _refresh_registry_snapshot()
    healthy_services = sum(1 for service in SERVICE_REGISTRY.values() if service.get("status") == "healthy")
    total_services = len(SERVICE_REGISTRY)
    
    return {
        "service": "orchestrator",
        "status": "healthy",
        "timestamp": now_iso(),
        "registered_services": total_services,
        "healthy_services": healthy_services,
        "startup_order": SERVICE_STARTUP_ORDER,
        "next_service_to_start": get_next_service_to_start()
    }

@health_router.get("/startup-sequence")
async def get_startup_sequence(token: dict = Depends(verify_admin_or_service)):
    """Get the current startup sequence status"""
    _refresh_registry_snapshot()
    sequence_status = []
    for service_name in SERVICE_STARTUP_ORDER:
        if service_name in SERVICE_REGISTRY:
            service_info = SERVICE_REGISTRY[service_name]
            sequence_status.append({
                "service_name": service_name,
                "status": service_info["status"],
                "version": service_info.get("version", ""),
                "last_version": service_info.get("last_version", ""),
                "started_at": service_info.get("started_at", ""),
                "db_path": service_info.get("db_path"),
                "host": service_info["host"],
                "port": service_info["port"],
                "last_health_check": service_info["last_health_check"]
            })
        else:
            sequence_status.append({
                "service_name": service_name,
                "status": "not_registered",
                "version": None,
                "last_version": None,
                "started_at": None,
                "db_path": None,
                "host": None,
                "port": None,
                "last_health_check": None
            })
    
    return {
        "startup_order": SERVICE_STARTUP_ORDER,
        "sequence_status": sequence_status,
        "all_services_healthy": all(
            s.get("status") == "healthy" 
            for s in SERVICE_REGISTRY.values() 
            if s.get("service_name") in SERVICE_STARTUP_ORDER
        )
    }

# Public health summary (no auth required — used by the landing page)
@public_router.get("/health-summary")
async def public_health_summary():
    """Get a lightweight health summary for all services (public, no auth)."""
    _refresh_registry_snapshot()
    services = []
    for service_name in SERVICE_STARTUP_ORDER:
        if service_name in SERVICE_REGISTRY:
            info = SERVICE_REGISTRY[service_name]
            services.append({
                "service": service_name,
                "status": info["status"],
                "version": info.get("version", ""),
                "started_at": info.get("started_at", ""),
                "db_path": info.get("db_path"),
            })
        else:
            services.append({
                "service": service_name,
                "status": "unknown",
                "version": None,
                "started_at": None,
                "db_path": None,
            })
    return {
        "services": services,
        "infisical": get_infisical_status(),
        "timestamp": now_iso(),
    }



@public_router.get("/changelogs")
async def public_changelogs():
    """Aggregate all microservice changes.md files for public auditing."""
    import os as _os
    base = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    services_dir = _os.path.dirname(base)
    logs = {}
    for entry in sorted(_os.listdir(services_dir)):
        changes_path = _os.path.join(services_dir, entry, "changes.md")
        if _os.path.isfile(changes_path):
            try:
                with open(changes_path) as f:
                    logs[entry] = f.read()
            except Exception as e:
                logs[entry] = f"Error reading changelog: {e}"
    return {"changelogs": logs, "timestamp": now_iso()}

# Background tasks (would be implemented in a real system)
async def health_check_service(service_name: str):
    """Periodically check the health of a registered service"""
    svc = SERVICE_REGISTRY.get(service_name)
    if not svc:
        return None

    host = svc.get("host")
    port = svc.get("port")
    if not host or not port:
        svc["status"] = "unknown"
        svc["last_health_check"] = now_iso()
        return svc

    url = f"http://{host}:{port}/health"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            svc["status"] = "healthy" if 200 <= resp.status < 300 else "degraded"
    except urllib.error.HTTPError as e:
        svc["status"] = "unhealthy"
        svc["last_error"] = f"HTTP {e.code}"
    except Exception as e:
        svc["status"] = "unhealthy"
        svc["last_error"] = str(e)

    svc["last_health_check"] = now_iso()
    return svc

async def check_startup_sequence():
    """Check if services can be started in the correct sequence"""
    sequence_status = []
    previous_ok = True
    for name in SERVICE_STARTUP_ORDER:
        svc = SERVICE_REGISTRY.get(name)
        status = (svc or {}).get("status", "not_registered")
        ready = previous_ok and status in {"healthy", "running", "ready"}
        sequence_status.append({
            "service_name": name,
            "status": status,
            "ready_for_next": ready,
        })
        previous_ok = previous_ok and ready

    return {
        "startup_order": SERVICE_STARTUP_ORDER,
        "sequence_status": sequence_status,
        "all_services_ready": all(row["ready_for_next"] for row in sequence_status) if sequence_status else False,
    }


def _client_index_user_proxy(method: str, path: str, auth_header: Optional[str], payload: Optional[dict] = None) -> Dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if auth_header:
        headers["Authorization"] = auth_header

    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        f"http://127.0.0.1:8002{path}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = "Upstream request failed"
        try:
            err_raw = e.read().decode("utf-8")
            err_json = json.loads(err_raw) if err_raw else {}
            detail = err_json.get("detail") or detail
        except Exception:
            pass
        raise HTTPException(status_code=e.code, detail=detail)
    except Exception:
        raise HTTPException(status_code=502, detail="Client index service unavailable")


def _payments_user_proxy(method: str, path: str, auth_header: Optional[str], payload: Optional[dict] = None) -> Dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if auth_header:
        headers["Authorization"] = auth_header

    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        f"http://127.0.0.1:8003{path}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = "Payments request failed"
        try:
            err_raw = e.read().decode("utf-8")
            err_json = json.loads(err_raw) if err_raw else {}
            detail = err_json.get("detail") or detail
        except Exception:
            pass
        raise HTTPException(status_code=e.code, detail=detail)
    except Exception:
        raise HTTPException(status_code=502, detail="Payments service unavailable")


def _can_fallback_from_proxy(err: HTTPException) -> bool:
    status_code = int(getattr(err, "status_code", 500) or 500)
    return status_code >= 500 or status_code in {404, 405, 501}


@client_router.get("/signature")
async def get_signature_proxy(request: Request, token: dict = Depends(verify_authenticated_user)):
    auth_header = request.headers.get("authorization")
    try:
        return _client_index_user_proxy("GET", "/api/signature", auth_header)
    except HTTPException as e:
        if not _can_fallback_from_proxy(e):
            raise

    db = SessionLocal()
    try:
        rec = SignatureRepository.get_latest_by_user_id(db, token.get("sub"))
        return {"signature": rec.to_dict() if rec else None}
    finally:
        db.close()


@client_router.post("/signature")
async def upsert_signature_proxy(payload: dict, request: Request, token: dict = Depends(verify_authenticated_user)):
    auth_header = request.headers.get("authorization")
    try:
        return _client_index_user_proxy("POST", "/api/signature", auth_header, payload)
    except HTTPException as e:
        if not _can_fallback_from_proxy(e):
            raise

    data_url = str(payload.get("data_url") or "").strip()
    full_name = str(payload.get("full_name") or "").strip()
    if not data_url.startswith("data:image/"):
        raise HTTPException(status_code=400, detail="Invalid signature image payload")
    if not full_name:
        raise HTTPException(status_code=400, detail="full_name is required")

    db = SessionLocal()
    try:
        rec = SignatureRepository.upsert_for_user(db, token.get("sub"), data_url, full_name)
        return {"ok": True, "signature": rec.to_dict()}
    finally:
        db.close()


@client_router.get("/profile")
async def get_profile_proxy(request: Request, token: dict = Depends(verify_authenticated_user)):
    auth_header = request.headers.get("authorization")
    try:
        return _client_index_user_proxy("GET", "/api/profile/", auth_header)
    except HTTPException as e:
        if not _can_fallback_from_proxy(e):
            raise

    user_id = token.get("sub")
    db = SessionLocal()
    try:
        rec = ProfileRepository.get_by_user_id(db, user_id)
        if not rec:
            return {
                "profile": {
                    "user_id": user_id,
                    "name": "",
                    "address": "",
                    "phone": "",
                    "country": "CA",
                    "state": "ON",
                    "updated_at": now_iso(),
                }
            }
        return {"profile": rec.to_dict()}
    finally:
        db.close()


@client_router.put("/profile")
async def update_profile_proxy(payload: dict, request: Request, token: dict = Depends(verify_authenticated_user)):
    auth_header = request.headers.get("authorization")
    try:
        return _client_index_user_proxy("PUT", "/api/profile/", auth_header, payload)
    except HTTPException as e:
        if not _can_fallback_from_proxy(e):
            raise

    user_id = token.get("sub")
    db = SessionLocal()
    try:
        name_val = payload.get("name")
        if isinstance(name_val, str) and name_val.strip():
            UserRepository.update(db, user_id, {"name": name_val.strip()})

        update_data = {
            "name": payload.get("name"),
            "address": payload.get("address"),
            "phone": payload.get("phone"),
            "country": payload.get("country"),
            "state": payload.get("state"),
        }
        update_data = {k: v for k, v in update_data.items() if v is not None}

        rec = ProfileRepository.update(db, user_id, update_data)
        if not rec:
            rec = ProfileRepository.create(db, {"user_id": user_id, **update_data})
        return {"profile": rec.to_dict()}
    finally:
        db.close()


@client_router.get("/countries")
async def get_countries_proxy(request: Request, token: dict = Depends(verify_authenticated_user)):
    auth_header = request.headers.get("authorization")
    try:
        return _client_index_user_proxy("GET", "/api/countries", auth_header)
    except HTTPException as e:
        if not _can_fallback_from_proxy(e):
            raise

    return {"countries": SUPPORTED_COUNTRIES}


@client_router.get("/plans")
async def list_plans_proxy(request: Request, token: dict = Depends(verify_authenticated_user)):
    plans = []
    for _, plan in PLANS.items():
        plans.append({
            "id": plan.get("id"),
            "name": plan.get("name"),
            "price_usd": plan.get("price_usd"),
            "features": [
                f"Up to {plan.get('keyword_limit', 0)} monitored keywords",
                f"{str(plan.get('scan_freq', 'daily')).capitalize()} scan cadence",
                "Legal document workflow",
            ],
        })
    return {"plans": plans}


@client_router.get("/payments")
async def list_payments_proxy(request: Request, token: dict = Depends(verify_authenticated_user)):
    auth_header = request.headers.get("authorization")
    return _payments_user_proxy("GET", "/api/payments/", auth_header)


@client_router.post("/subscribe")
async def subscribe_proxy(payload: dict, request: Request, token: dict = Depends(verify_authenticated_user)):
    auth_header = request.headers.get("authorization")
    normalized = {
        "plan_id": payload.get("plan_id"),
        "payment_method": payload.get("payment_method"),
        "network": payload.get("network"),
        "tx_hash": payload.get("tx_hash"),
    }
    return _payments_user_proxy("POST", "/api/payments/", auth_header, normalized)


@client_router.get("/findings")
async def list_findings_proxy(request: Request, token: dict = Depends(verify_authenticated_user)):
    auth_header = request.headers.get("authorization")
    try:
        return _client_index_user_proxy("GET", "/api/findings", auth_header)
    except HTTPException as e:
        if not _can_fallback_from_proxy(e):
            raise

    db = SessionLocal()
    try:
        rows = (
            db.query(Finding)
            .filter(Finding.user_id == token.get("sub"))
            .order_by(Finding.discovered_at.desc())
            .limit(500)
            .all()
        )
        return {"findings": [r.to_dict() for r in rows]}
    finally:
        db.close()


@client_router.post("/findings/removal-request")
async def create_removal_request_proxy(payload: dict, request: Request, token: dict = Depends(verify_authenticated_user)):
    auth_header = request.headers.get("authorization")
    try:
        return _client_index_user_proxy("POST", "/api/findings/removal-request", auth_header, payload)
    except HTTPException as e:
        if not _can_fallback_from_proxy(e):
            raise

    finding_id = str(payload.get("finding_id") or "").strip()
    if not finding_id:
        raise HTTPException(status_code=400, detail="finding_id is required")

    db = SessionLocal()
    try:
        finding = (
            db.query(Finding)
            .filter(Finding.id == finding_id, Finding.user_id == token.get("sub"))
            .first()
        )
        if not finding:
            raise HTTPException(status_code=404, detail="Finding not found")

        broker_contact = BROKER_CONTACTS.get(finding.broker) or {}
        rec = {
            "id": generate_id(),
            "user_id": token.get("sub"),
            "finding_id": finding.id,
            "broker": finding.broker,
            "broker_email": broker_contact.get("email"),
            "broker_form": broker_contact.get("form"),
            "status": "submitted",
            "created_at": now_iso(),
            "removal_requested_at": now_iso(),
        }
        REMOVALS.append(rec)
        with _state_lock:
            save_runtime_state()
        return {"ok": True, "removal": rec}
    finally:
        db.close()


@client_router.get("/documents/templates")
async def get_document_templates_proxy(request: Request, token: dict = Depends(verify_authenticated_user)):
    auth_header = request.headers.get("authorization")
    try:
        return _client_index_user_proxy("GET", "/api/documents/templates", auth_header)
    except HTTPException as e:
        if not _can_fallback_from_proxy(e):
            raise

    db = SessionLocal()
    try:
        profile_data = ProfileRepository.get_by_user_id(db, token.get("sub"))
        country = (profile_data.country if profile_data and profile_data.country else "CA").upper()
        templates = []
        for _, tpl in LEGAL_TEMPLATES.items():
            allowed = tpl.get("jurisdictions") or []
            templates.append({
                "id": tpl.get("id"),
                "title": tpl.get("title"),
                "summary": tpl.get("summary"),
                "jurisdictions": allowed,
                "available": country in allowed,
            })
        return {"templates": templates}
    finally:
        db.close()


@client_router.get("/documents")
async def list_documents_proxy(request: Request, token: dict = Depends(verify_authenticated_user)):
    auth_header = request.headers.get("authorization")
    try:
        return _client_index_user_proxy("GET", "/api/documents", auth_header)
    except HTTPException as e:
        if not _can_fallback_from_proxy(e):
            raise

    db = SessionLocal()
    try:
        rows = DocumentRepository.list_by_user_id(db, token.get("sub"), limit=500)
        return {"documents": [r.to_dict() for r in rows]}
    finally:
        db.close()


@client_router.get("/documents/{document_id}")
async def get_document_proxy(document_id: str, request: Request, token: dict = Depends(verify_authenticated_user)):
    auth_header = request.headers.get("authorization")
    try:
        return _client_index_user_proxy("GET", f"/api/documents/{document_id}", auth_header)
    except HTTPException as e:
        if not _can_fallback_from_proxy(e):
            raise

    db = SessionLocal()
    try:
        rec = DocumentRepository.get_by_id_for_user(db, document_id, token.get("sub"))
        if not rec:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"document": rec.to_dict()}
    finally:
        db.close()


@client_router.delete("/documents/{document_id}")
async def delete_document_proxy(document_id: str, request: Request, token: dict = Depends(verify_authenticated_user)):
    auth_header = request.headers.get("authorization")
    try:
        return _client_index_user_proxy("DELETE", f"/api/documents/{document_id}", auth_header)
    except HTTPException as e:
        if not _can_fallback_from_proxy(e):
            raise

    db = SessionLocal()
    try:
        ok = DocumentRepository.delete_for_user(db, document_id, token.get("sub"))
        if not ok:
            raise HTTPException(status_code=404, detail="Document not found")
        return {"ok": True}
    finally:
        db.close()


@client_router.post("/documents/generate")
async def generate_document_proxy(payload: dict, request: Request, token: dict = Depends(verify_authenticated_user)):
    auth_header = request.headers.get("authorization")
    try:
        return _client_index_user_proxy("POST", "/api/documents/generate", auth_header, payload)
    except HTTPException as e:
        if not _can_fallback_from_proxy(e):
            raise

    template_id = str(payload.get("template_id") or "").strip()
    if not template_id:
        raise HTTPException(status_code=400, detail="template_id is required")

    template = LEGAL_TEMPLATES.get(template_id)
    if not template:
        raise HTTPException(status_code=400, detail="Unsupported template_id")

    db = SessionLocal()
    try:
        user_id = token.get("sub")
        user_db = UserRepository.get_by_id(db, user_id)
        profile_data = ProfileRepository.get_by_user_id(db, user_id)
        country = (profile_data.country if profile_data and profile_data.country else "CA").upper()
        country_cfg = SUPPORTED_COUNTRIES.get(country) or SUPPORTED_COUNTRIES["CA"]
        if country not in (template.get("jurisdictions") or []):
            raise HTTPException(status_code=400, detail="Template is not available for this country")

        finding_id = payload.get("finding_id")
        finding_url = ""
        finding_data = ""
        recipient_broker = str(payload.get("recipient_broker") or "").strip()
        recipient_address = str(payload.get("recipient_address") or "").strip()
        if finding_id:
            finding = db.query(Finding).filter(Finding.id == finding_id, Finding.user_id == user_id).first()
            if finding:
                finding_url = finding.url or ""
                finding_data = finding.data_found or ""
                recipient_broker = recipient_broker or finding.broker

        state_val = (profile_data.state if profile_data else "") or ""
        state_clause = f", {state_val}" if state_val else ""
        body = _fill_template(
            template_id,
            {
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "recipient_broker": recipient_broker,
                "recipient_address": recipient_address,
                "user_name": (profile_data.name if profile_data and profile_data.name else (user_db.name if user_db else "")) or "",
                "user_email": (user_db.email if user_db else "") or "",
                "user_address": (profile_data.address if profile_data else "") or "",
                "user_phone": (profile_data.phone if profile_data else "") or "",
                "finding_url": finding_url,
                "finding_data": finding_data,
                "country_name": country_cfg.get("name", ""),
                "privacy_law": country_cfg.get("privacy_law", ""),
                "state_clause": state_clause,
            },
        )

        rec = DocumentRepository.create(
            db,
            {
                "user_id": user_id,
                "template_id": template_id,
                "finding_id": finding_id,
                "recipient_broker": recipient_broker,
                "recipient_address": recipient_address,
                "country": country,
                "title": template.get("title") or template_id,
                "body": body,
            },
        )
        return {"ok": True, "document": rec.to_dict()}
    finally:
        db.close()


@client_router.post("/documents/sign")
async def sign_document_proxy(payload: dict, request: Request, token: dict = Depends(verify_authenticated_user)):
    auth_header = request.headers.get("authorization")
    try:
        return _client_index_user_proxy("POST", "/api/documents/sign", auth_header, payload)
    except HTTPException as e:
        if not _can_fallback_from_proxy(e):
            raise

    document_id = str(payload.get("document_id") or "").strip()
    if not document_id:
        raise HTTPException(status_code=400, detail="document_id is required")

    db = SessionLocal()
    try:
        signature = SignatureRepository.get_latest_by_user_id(db, token.get("sub"))
        if not signature:
            raise HTTPException(status_code=400, detail="No signature on file")

        witness_signed_at = payload.get("witness_signed_at")
        witness_signed_at_dt = None
        if witness_signed_at:
            try:
                witness_signed_at_dt = datetime.fromisoformat(str(witness_signed_at).replace("Z", "+00:00"))
            except Exception:
                witness_signed_at_dt = datetime.now(timezone.utc)

        rec = DocumentRepository.sign_for_user(
            db,
            document_id,
            token.get("sub"),
            {
                "signed_at": datetime.now(timezone.utc),
                "signature_image": signature.data_url,
                "signed_name": signature.full_name,
                "witness_signature_image": payload.get("witness_signature_image"),
                "witness_signed_name": payload.get("witness_signed_name"),
                "witness_role": payload.get("witness_role"),
                "witness_signed_at": witness_signed_at_dt,
                "auto_filled_witness": payload.get("auto_filled_witness"),
            },
        )
        if not rec:
            raise HTTPException(status_code=404, detail="Document not found")

        return {
            "ok": True,
            "document": rec.to_dict(),
            "dispatch": {
                "delivered": False,
                "broker_email": None,
                "form_url": None,
            },
        }
    finally:
        db.close()


@client_router.get("/keywords")
async def list_keywords_proxy(request: Request, token: dict = Depends(verify_authenticated_user)):
    auth_header = request.headers.get("authorization")
    try:
        return _client_index_user_proxy("GET", "/api/keywords", auth_header)
    except HTTPException as e:
        if not _can_fallback_from_proxy(e):
            raise

    db = SessionLocal()
    try:
        rows = KeywordRepository.get_by_user(db, token.get("sub"))
        return {"keywords": [r.to_dict() for r in rows]}
    finally:
        db.close()


@client_router.post("/keywords")
async def create_keyword_proxy(payload: dict, request: Request, token: dict = Depends(verify_authenticated_user)):
    auth_header = request.headers.get("authorization")
    try:
        return _client_index_user_proxy("POST", "/api/keywords", auth_header, payload)
    except HTTPException as e:
        if not _can_fallback_from_proxy(e):
            raise

    value = str(payload.get("value") or "").strip()
    key_type = str(payload.get("type") or "name").strip().lower() or "name"
    if not value:
        raise HTTPException(status_code=400, detail="value is required")

    db = SessionLocal()
    try:
        rec = KeywordRepository.create(
            db,
            {
                "user_id": token.get("sub"),
                "value": value,
                "type": key_type,
            },
        )
        return {"ok": True, "keyword": rec.to_dict()}
    finally:
        db.close()


@client_router.delete("/keywords/{keyword_id}")
async def delete_keyword_proxy(keyword_id: str, request: Request, token: dict = Depends(verify_authenticated_user)):
    auth_header = request.headers.get("authorization")
    try:
        return _client_index_user_proxy("DELETE", f"/api/keywords/{keyword_id}", auth_header)
    except HTTPException as e:
        if not _can_fallback_from_proxy(e):
            raise

    db = SessionLocal()
    try:
        rec = KeywordRepository.get_by_id(db, keyword_id)
        if not rec or rec.user_id != token.get("sub"):
            raise HTTPException(status_code=404, detail="Keyword not found")
        KeywordRepository.delete(db, keyword_id)
        return {"ok": True}
    finally:
        db.close()


@client_router.post("/scan/run")
async def run_scan_proxy(payload: dict, request: Request, token: dict = Depends(verify_authenticated_user)):
    auth_header = request.headers.get("authorization")
    try:
        return _client_index_user_proxy("POST", "/api/scan/run", auth_header, payload)
    except HTTPException as e:
        if not _can_fallback_from_proxy(e):
            raise

    keyword_id = str(payload.get("keyword_id") or "").strip()
    db = SessionLocal()
    try:
        if keyword_id:
            rec = KeywordRepository.get_by_id(db, keyword_id)
            if not rec or rec.user_id != token.get("sub"):
                raise HTTPException(status_code=404, detail="Keyword not found")
            KeywordRepository.update(db, keyword_id, {"last_scan_at": datetime.now(timezone.utc)})
            return {"ok": True, "message": "Scan queued for selected keyword."}

        for rec in KeywordRepository.get_by_user(db, token.get("sub")):
            KeywordRepository.update(db, rec.id, {"last_scan_at": datetime.now(timezone.utc)})
        return {"ok": True, "message": "Scan queued across your monitored keywords."}
    finally:
        db.close()


@client_router.get("/reputation")
async def reputation_proxy(request: Request, token: dict = Depends(verify_authenticated_user)):
    auth_header = request.headers.get("authorization")
    try:
        return _client_index_user_proxy("GET", "/api/reputation", auth_header)
    except HTTPException as e:
        if not _can_fallback_from_proxy(e):
            raise

    db = SessionLocal()
    try:
        user_id = token.get("sub")
        findings = db.query(Finding).filter(Finding.user_id == user_id).all()
        active = sum(1 for f in findings if (f.status or "active") == "active")
        removed = sum(1 for f in findings if (f.status or "") == "removed")
        high_severity = sum(1 for f in findings if (f.status or "active") == "active" and (f.severity or "").lower() in {"high", "critical"})
        pending_removal = sum(1 for r in REMOVALS if r.get("user_id") == user_id and r.get("status") not in {"removed", "closed"})

        risk = (active * 8) + (high_severity * 10) + (pending_removal * 4)
        score = max(0, min(100, 100 - risk))
        return {
            "score": score,
            "breakdown": {
                "active": active,
                "removed": removed,
                "pending_removal": pending_removal,
                "high_severity": high_severity,
            },
        }
    finally:
        db.close()


# ==================== SUPPORT API ====================
def _create_support_anon_session(email: str, ip: str) -> Dict[str, Any]:
    chat = _create_anon_chat(email)
    session_token = generate_id()
    session_expires = datetime.now(timezone.utc) + timedelta(hours=_support_anon_session_hours())
    SUPPORT_ANON_SESSIONS[session_token] = {
        "session_token": session_token,
        "chat_id": chat["id"],
        "email": email,
        "ip": ip,
        "expires_at": session_expires.isoformat(),
        "created_at": now_iso(),
    }
    return {
        "session_token": session_token,
        "session_expires_at": session_expires.isoformat(),
        "chat": chat,
        "messages": SUPPORT_MESSAGES.get(chat["id"], []),
    }


@support_router.post("/anon/start")
async def support_anon_start(payload: SupportAnonStartIn, request: Request):
    run_support_state_cleanup()
    email = payload.email.lower()
    ip = request.client.host if request.client else "anon"

    if not SUPPORT_EMAIL_OTP_REQUIRED:
        session_data = _create_support_anon_session(email, ip)
        AUDIT_LOG.append({
            "id": generate_id(),
            "at": now_iso(),
            "actor_email": email,
            "action": "support_anon_otp_bypassed",
            "target_chat_id": session_data["chat"]["id"],
        })
        return {
            "ok": True,
            "otp_required": False,
            **session_data,
        }

    allowed, retry = _ratelimit(f"support-anon-start-ip:{ip}", max_attempts=8, window_seconds=15 * 60)
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Too many support OTP requests from this IP. Retry in {retry}s")

    allowed, retry = _ratelimit(f"support-anon-start-email:{email}", max_attempts=4, window_seconds=60 * 60)
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Too many OTP requests for this email. Retry in {retry}s")

    otp = _support_generate_otp()
    challenge_id = generate_id()
    otp_ttl_minutes = _support_anon_otp_ttl_minutes()
    otp_max_attempts = _support_anon_otp_max_attempts()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=otp_ttl_minutes)
    SUPPORT_ANON_CHALLENGES[challenge_id] = {
        "id": challenge_id,
        "email": email,
        "purpose": "support_anon",
        "otp_hash": _support_otp_digest(email, "support_anon", otp),
        "expires_at": expires_at.isoformat(),
        "attempts": 0,
        "max_attempts": otp_max_attempts,
        "created_ip": ip,
        "verified": False,
        "created_at": now_iso(),
    }

    body = (
        f"Your d31337m3 support verification code is: {otp}\n\n"
        f"This code expires in {otp_ttl_minutes} minutes.\n"
        "If you did not request this, you can ignore this email."
    )
    if not _send_email_sync(email, "[d31337m3] Support chat verification code", body):
        raise HTTPException(status_code=500, detail="Failed to send verification code")

    AUDIT_LOG.append({
        "id": generate_id(),
        "at": now_iso(),
        "actor_email": email,
        "action": "support_anon_otp_sent",
        "target_email": email,
    })
    return {
        "ok": True,
        "otp_required": True,
        "challenge_id": challenge_id,
        "email_hint": _mask_email(email),
        "expires_in_seconds": otp_ttl_minutes * 60,
    }


@support_router.post("/anon/resend")
async def support_anon_resend(payload: SupportAnonResendIn, request: Request):
    run_support_state_cleanup()
    email = payload.email.lower()
    if not SUPPORT_EMAIL_OTP_REQUIRED:
        session_data = _create_support_anon_session(email, request.client.host if request.client else "anon")
        return {
            "ok": True,
            "otp_required": False,
            **session_data,
        }

    challenge = SUPPORT_ANON_CHALLENGES.get(payload.challenge_id)
    if not challenge or challenge.get("email") != email:
        raise HTTPException(status_code=404, detail="Challenge not found")
    if challenge.get("verified"):
        raise HTTPException(status_code=400, detail="Challenge already verified")

    return await support_anon_start(SupportAnonStartIn(email=email), request)


@support_router.post("/anon/verify")
async def support_anon_verify(payload: SupportAnonVerifyIn, request: Request):
    run_support_state_cleanup()
    email = payload.email.lower()
    ip = request.client.host if request.client else "anon"

    if not SUPPORT_EMAIL_OTP_REQUIRED:
        session_data = _create_support_anon_session(email, ip)
        return {
            "ok": True,
            "otp_required": False,
            **session_data,
        }

    challenge = SUPPORT_ANON_CHALLENGES.get(payload.challenge_id)
    if not challenge or challenge.get("email") != email:
        raise HTTPException(status_code=404, detail="Challenge not found")

    if datetime.fromisoformat(challenge["expires_at"]) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="OTP expired")
    if challenge.get("attempts", 0) >= challenge.get("max_attempts", _support_anon_otp_max_attempts()):
        raise HTTPException(status_code=429, detail="OTP attempt limit reached")

    allowed, retry = _ratelimit(f"support-anon-verify-ip:{ip}", max_attempts=20, window_seconds=15 * 60)
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Too many verification attempts. Retry in {retry}s")

    incoming = _support_otp_digest(email, "support_anon", payload.otp)
    if not hmac.compare_digest(incoming, challenge.get("otp_hash", "")):
        challenge["attempts"] = challenge.get("attempts", 0) + 1
        raise HTTPException(status_code=400, detail="Invalid OTP")

    challenge["verified"] = True
    session_data = _create_support_anon_session(email, ip)

    AUDIT_LOG.append({
        "id": generate_id(),
        "at": now_iso(),
        "actor_email": email,
        "action": "support_anon_verified",
        "target_chat_id": session_data["chat"]["id"],
    })
    return {
        "ok": True,
        "otp_required": True,
        **session_data,
    }


@support_router.get("/anon/chats/{chat_id}/messages")
async def support_anon_messages(chat_id: str, session_token: str, request: Request):
    run_support_state_cleanup()
    _require_anon_session(session_token, chat_id, request)
    if chat_id not in SUPPORT_CHATS:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"chat": SUPPORT_CHATS[chat_id], "messages": SUPPORT_MESSAGES.get(chat_id, [])}


@support_router.post("/anon/chats/{chat_id}/messages")
async def support_anon_send_message(chat_id: str, payload: SupportAnonMessageIn, request: Request):
    run_support_state_cleanup()
    session = _require_anon_session(payload.session_token, chat_id, request)
    if chat_id not in SUPPORT_CHATS:
        raise HTTPException(status_code=404, detail="Chat not found")

    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    if len(text) > 2000:
        raise HTTPException(status_code=400, detail="Message too long")

    allowed, retry = _ratelimit(f"support-anon-msg:{payload.session_token}", max_attempts=20, window_seconds=5 * 60)
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Too many messages. Retry in {retry}s")

    msg = {
        "id": generate_id(),
        "chat_id": chat_id,
        "sender_role": "customer",
        "sender_id": None,
        "sender_email": session.get("email"),
        "text": text,
        "sent_at": now_iso(),
        "source": "anonymous",
    }
    SUPPORT_MESSAGES.setdefault(chat_id, []).append(msg)
    SUPPORT_CHATS[chat_id]["updated_at"] = now_iso()
    SUPPORT_CHATS[chat_id]["last_message_at"] = msg["sent_at"]
    if SUPPORT_CHATS[chat_id].get("status") == "closed":
        SUPPORT_CHATS[chat_id]["status"] = "active"
    _persist_support_message(msg)
    _persist_support_chat(SUPPORT_CHATS[chat_id])

    AUDIT_LOG.append({
        "id": generate_id(),
        "at": now_iso(),
        "actor_email": session.get("email"),
        "action": "support_anon_message",
        "target_chat_id": chat_id,
    })
    return {"ok": True, "message": msg}


@support_router.get("/chats/me")
async def support_my_chat(token: dict = Depends(verify_authenticated_user)):
    user_id = token.get("sub")
    chats = [c for c in SUPPORT_CHATS.values() if c.get("customer_id") == user_id]
    chats = sorted(chats, key=lambda c: c.get("updated_at", ""), reverse=True)
    if not chats:
        return {"chat": None, "messages": []}
    chat = chats[0]
    return {"chat": chat, "messages": SUPPORT_MESSAGES.get(chat["id"], [])}


@support_router.post("/chats/me/start")
async def support_start_chat(token: dict = Depends(verify_authenticated_user)):
    user_id = token.get("sub")
    # Reuse existing open chat if present.
    for c in SUPPORT_CHATS.values():
        if c.get("customer_id") == user_id and c.get("status") in ["open", "waiting", "active"]:
            return {"ok": True, "chat": c, "messages": SUPPORT_MESSAGES.get(c["id"], [])}

    user = _find_user(user_id)
    chat_id = generate_id()
    chat = {
        "id": chat_id,
        "customer_id": user_id,
        "customer_email": user.get("email") if user else None,
        "status": "open",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "last_message_at": None,
    }
    SUPPORT_CHATS[chat_id] = chat
    SUPPORT_MESSAGES[chat_id] = []
    _persist_support_chat(chat)
    AUDIT_LOG.append({
        "id": generate_id(),
        "at": now_iso(),
        "actor_email": chat.get("customer_email") or user_id,
        "action": "support_chat_start",
        "target_chat_id": chat_id,
    })
    return {"ok": True, "chat": chat, "messages": []}


@support_router.get("/chats/{chat_id}/messages")
async def support_chat_messages(chat_id: str, token: dict = Depends(verify_authenticated_user)):
    _ensure_chat_access(chat_id, token)
    return {"messages": SUPPORT_MESSAGES.get(chat_id, [])}


@support_router.post("/chats/{chat_id}/messages")
async def support_send_message(chat_id: str, payload: dict, token: dict = Depends(verify_authenticated_user)):
    chat = _ensure_chat_access(chat_id, token)
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    sender_role = "admin" if _is_admin(token) else "customer"
    sender_id = token.get("sub")
    sender = _find_user(sender_id)
    msg = {
        "id": generate_id(),
        "chat_id": chat_id,
        "sender_role": sender_role,
        "sender_id": sender_id,
        "sender_email": sender.get("email") if sender else None,
        "text": text,
        "sent_at": now_iso(),
    }
    SUPPORT_MESSAGES.setdefault(chat_id, []).append(msg)
    chat["updated_at"] = now_iso()
    chat["last_message_at"] = msg["sent_at"]
    if chat.get("status") == "closed":
        chat["status"] = "active"
    _persist_support_message(msg)
    _persist_support_chat(chat)

    AUDIT_LOG.append({
        "id": generate_id(),
        "at": now_iso(),
        "actor_email": msg.get("sender_email") or sender_id,
        "action": "support_chat_message",
        "target_chat_id": chat_id,
    })
    return {"ok": True, "message": msg}


@support_router.get("/tickets/me")
async def support_my_tickets(token: dict = Depends(verify_authenticated_user)):
    user_id = token.get("sub")
    rows = [t for t in SUPPORT_TICKETS.values() if t.get("customer_id") == user_id]
    rows = sorted(rows, key=lambda t: t.get("updated_at", ""), reverse=True)
    return {"tickets": rows, "count": len(rows)}


@support_router.post("/tickets")
async def support_create_ticket(payload: dict, token: dict = Depends(verify_authenticated_user)):
    user_id = token.get("sub")
    subject = (payload.get("subject") or "").strip()
    description = (payload.get("description") or "").strip()
    if not subject:
        raise HTTPException(status_code=400, detail="subject is required")

    chat_id = payload.get("chat_id")
    if chat_id:
        _ensure_chat_access(chat_id, token)

    user = _find_user(user_id)
    ticket_id = generate_id()
    ticket = {
        "id": ticket_id,
        "customer_id": user_id,
        "customer_email": user.get("email") if user else None,
        "chat_id": chat_id,
        "subject": subject,
        "description": description,
        "status": "open",
        "priority": payload.get("priority") or "normal",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "created_by": "customer",
    }
    SUPPORT_TICKETS[ticket_id] = ticket
    _persist_support_ticket(ticket)

    if chat_id and chat_id in SUPPORT_CHATS:
        SUPPORT_CHATS[chat_id]["updated_at"] = now_iso()
        _persist_support_chat(SUPPORT_CHATS[chat_id])

    AUDIT_LOG.append({
        "id": generate_id(),
        "at": now_iso(),
        "actor_email": ticket.get("customer_email") or user_id,
        "action": "support_ticket_create",
        "target_ticket_id": ticket_id,
        "target_chat_id": chat_id,
    })
    return {"ok": True, "ticket": ticket}


@support_router.get("/admin/chats")
async def support_admin_chats(token: dict = Depends(verify_employee_or_admin)):
    rows = sorted(SUPPORT_CHATS.values(), key=lambda c: c.get("updated_at", ""), reverse=True)
    shaped = []
    for c in rows:
        shaped.append({
            **c,
            "messages_count": len(SUPPORT_MESSAGES.get(c["id"], [])),
            "tickets_count": _chat_ticket_count(c["id"]),
        })
    return {"chats": shaped, "count": len(shaped)}


@support_router.get("/admin/chats/{chat_id}/messages")
async def support_admin_chat_messages(chat_id: str, token: dict = Depends(verify_employee_or_admin)):
    if chat_id not in SUPPORT_CHATS:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {
        "chat": SUPPORT_CHATS[chat_id],
        "messages": SUPPORT_MESSAGES.get(chat_id, []),
    }


@support_router.post("/admin/chats/{chat_id}/messages")
async def support_admin_send_message(chat_id: str, payload: dict, token: dict = Depends(verify_employee_or_admin)):
    if chat_id not in SUPPORT_CHATS:
        raise HTTPException(status_code=404, detail="Chat not found")
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    sender_id = token.get("sub") or token.get("iss")
    sender = _find_user(sender_id) if token.get("sub") else None
    msg = {
        "id": generate_id(),
        "chat_id": chat_id,
        "sender_role": "admin",
        "sender_id": sender_id,
        "sender_email": sender.get("email") if sender else sender_id,
        "text": text,
        "sent_at": now_iso(),
    }
    SUPPORT_MESSAGES.setdefault(chat_id, []).append(msg)
    SUPPORT_CHATS[chat_id]["updated_at"] = now_iso()
    SUPPORT_CHATS[chat_id]["last_message_at"] = msg["sent_at"]
    if SUPPORT_CHATS[chat_id].get("status") == "closed":
        SUPPORT_CHATS[chat_id]["status"] = "active"
    _persist_support_message(msg)
    _persist_support_chat(SUPPORT_CHATS[chat_id])

    AUDIT_LOG.append({
        "id": generate_id(),
        "at": now_iso(),
        "actor_email": msg.get("sender_email") or sender_id,
        "action": "support_chat_admin_reply",
        "target_chat_id": chat_id,
    })
    return {"ok": True, "message": msg}


@support_router.get("/admin/tickets")
async def support_admin_tickets(token: dict = Depends(verify_employee_or_admin)):
    rows = sorted(SUPPORT_TICKETS.values(), key=lambda t: t.get("updated_at", ""), reverse=True)
    return {"tickets": rows, "count": len(rows)}


@support_router.patch("/admin/tickets/{ticket_id}")
async def support_admin_patch_ticket(ticket_id: str, payload: dict, token: dict = Depends(verify_employee_or_admin)):
    ticket = SUPPORT_TICKETS.get(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    for key in ["status", "priority"]:
        if key in payload and payload.get(key) is not None:
            ticket[key] = payload.get(key)
    ticket["updated_at"] = now_iso()
    ticket["updated_by"] = token.get("sub") or token.get("iss")
    _persist_support_ticket(ticket)

    AUDIT_LOG.append({
        "id": generate_id(),
        "at": now_iso(),
        "actor_email": ticket.get("updated_by"),
        "action": "support_ticket_update",
        "target_ticket_id": ticket_id,
    })
    return {"ok": True, "ticket": ticket}


@support_router.post("/admin/tickets/from-chat/{chat_id}")
async def support_admin_create_ticket_from_chat(chat_id: str, payload: dict, token: dict = Depends(verify_employee_or_admin)):
    chat = SUPPORT_CHATS.get(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    subject = (payload.get("subject") or "Support request from live chat").strip()
    description = (payload.get("description") or "Created from active customer chat").strip()
    ticket_id = generate_id()
    ticket = {
        "id": ticket_id,
        "customer_id": chat.get("customer_id"),
        "customer_email": chat.get("customer_email"),
        "chat_id": chat_id,
        "subject": subject,
        "description": description,
        "status": "open",
        "priority": payload.get("priority") or "normal",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "created_by": "admin",
    }
    SUPPORT_TICKETS[ticket_id] = ticket
    _persist_support_ticket(ticket)

    AUDIT_LOG.append({
        "id": generate_id(),
        "at": now_iso(),
        "actor_email": token.get("sub") or token.get("iss"),
        "action": "support_ticket_create_from_chat",
        "target_ticket_id": ticket_id,
        "target_chat_id": chat_id,
    })
    return {"ok": True, "ticket": ticket}


# ==================== WORKFORCE OPS API ====================
@workforce_router.get("/admin/shifts")
async def workforce_admin_shifts(token: dict = Depends(verify_employee_or_admin)):
    rows = sorted(WORKFORCE_SHIFTS.values(), key=lambda s: s.get("start_at", ""))
    return {"shifts": rows, "count": len(rows)}


@workforce_router.post("/admin/shifts")
async def workforce_admin_create_shift(payload: dict, token: dict = Depends(verify_employee_or_admin)):
    employee_id = (payload.get("employee_id") or "").strip()
    start_at = payload.get("start_at")
    end_at = payload.get("end_at")
    if not employee_id or not start_at or not end_at:
        raise HTTPException(status_code=400, detail="employee_id, start_at and end_at are required")

    rec = {
        "id": generate_id(),
        "employee_id": employee_id,
        "employee_email": payload.get("employee_email"),
        "role": payload.get("role") or "support",
        "location": payload.get("location") or "remote",
        "start_at": start_at,
        "end_at": end_at,
        "status": payload.get("status") or "scheduled",
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    WORKFORCE_SHIFTS[rec["id"]] = rec
    AUDIT_LOG.append({
        "id": generate_id(),
        "at": now_iso(),
        "actor_email": token.get("sub") or token.get("iss"),
        "action": "workforce_shift_create",
        "target_shift_id": rec["id"],
    })
    return {"ok": True, "shift": rec}


@workforce_router.patch("/admin/shifts/{shift_id}")
async def workforce_admin_patch_shift(shift_id: str, payload: dict, token: dict = Depends(verify_employee_or_admin)):
    rec = WORKFORCE_SHIFTS.get(shift_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Shift not found")
    for key in ["role", "location", "start_at", "end_at", "status", "employee_email"]:
        if key in payload and payload.get(key) is not None:
            rec[key] = payload.get(key)
    rec["updated_at"] = now_iso()
    AUDIT_LOG.append({
        "id": generate_id(),
        "at": now_iso(),
        "actor_email": token.get("sub") or token.get("iss"),
        "action": "workforce_shift_update",
        "target_shift_id": shift_id,
    })
    return {"ok": True, "shift": rec}


@workforce_router.get("/admin/timesheets")
async def workforce_admin_timesheets(token: dict = Depends(verify_employee_or_admin)):
    rows = sorted(WORKFORCE_TIMESHEETS.values(), key=lambda t: t.get("date", ""), reverse=True)
    return {"timesheets": rows, "count": len(rows)}


@workforce_router.post("/admin/timesheets")
async def workforce_admin_create_timesheet(payload: dict, token: dict = Depends(verify_employee_or_admin)):
    employee_id = (payload.get("employee_id") or "").strip()
    date = payload.get("date")
    hours = payload.get("hours")
    if not employee_id or not date or hours is None:
        raise HTTPException(status_code=400, detail="employee_id, date and hours are required")

    rec = {
        "id": generate_id(),
        "employee_id": employee_id,
        "employee_email": payload.get("employee_email"),
        "date": date,
        "hours": float(hours),
        "overtime_hours": float(payload.get("overtime_hours") or 0),
        "approved": bool(payload.get("approved", False)),
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    WORKFORCE_TIMESHEETS[rec["id"]] = rec
    AUDIT_LOG.append({
        "id": generate_id(),
        "at": now_iso(),
        "actor_email": token.get("sub") or token.get("iss"),
        "action": "workforce_timesheet_create",
        "target_timesheet_id": rec["id"],
    })
    return {"ok": True, "timesheet": rec}


@workforce_router.patch("/admin/timesheets/{timesheet_id}")
async def workforce_admin_patch_timesheet(timesheet_id: str, payload: dict, token: dict = Depends(verify_employee_or_admin)):
    rec = WORKFORCE_TIMESHEETS.get(timesheet_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    for key in ["hours", "overtime_hours", "approved", "employee_email", "date"]:
        if key in payload and payload.get(key) is not None:
            rec[key] = float(payload[key]) if key in ["hours", "overtime_hours"] else payload[key]
    rec["updated_at"] = now_iso()
    AUDIT_LOG.append({
        "id": generate_id(),
        "at": now_iso(),
        "actor_email": token.get("sub") or token.get("iss"),
        "action": "workforce_timesheet_update",
        "target_timesheet_id": timesheet_id,
    })
    return {"ok": True, "timesheet": rec}


@workforce_router.get("/admin/payroll-runs")
async def workforce_admin_payroll_runs(token: dict = Depends(verify_employee_or_admin)):
    rows = sorted(WORKFORCE_PAYROLL_RUNS.values(), key=lambda p: p.get("created_at", ""), reverse=True)
    return {"payroll_runs": rows, "count": len(rows)}


@workforce_router.post("/admin/payroll-runs")
async def workforce_admin_create_payroll_run(payload: dict, token: dict = Depends(verify_employee_or_admin)):
    period_start = payload.get("period_start")
    period_end = payload.get("period_end")
    if not period_start or not period_end:
        raise HTTPException(status_code=400, detail="period_start and period_end are required")

    rec = {
        "id": generate_id(),
        "period_start": period_start,
        "period_end": period_end,
        "status": payload.get("status") or "draft",
        "total_gross": float(payload.get("total_gross") or 0),
        "total_net": float(payload.get("total_net") or 0),
        "line_items": payload.get("line_items") or [],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    WORKFORCE_PAYROLL_RUNS[rec["id"]] = rec
    AUDIT_LOG.append({
        "id": generate_id(),
        "at": now_iso(),
        "actor_email": token.get("sub") or token.get("iss"),
        "action": "workforce_payroll_create",
        "target_payroll_run_id": rec["id"],
    })
    return {"ok": True, "payroll_run": rec}


@workforce_router.patch("/admin/payroll-runs/{run_id}")
async def workforce_admin_patch_payroll_run(run_id: str, payload: dict, token: dict = Depends(verify_employee_or_admin)):
    rec = WORKFORCE_PAYROLL_RUNS.get(run_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Payroll run not found")
    for key in ["status", "line_items", "period_start", "period_end"]:
        if key in payload and payload.get(key) is not None:
            rec[key] = payload.get(key)
    for key in ["total_gross", "total_net"]:
        if key in payload and payload.get(key) is not None:
            rec[key] = float(payload.get(key))
    rec["updated_at"] = now_iso()
    AUDIT_LOG.append({
        "id": generate_id(),
        "at": now_iso(),
        "actor_email": token.get("sub") or token.get("iss"),
        "action": "workforce_payroll_update",
        "target_payroll_run_id": run_id,
    })
    return {"ok": True, "payroll_run": rec}


# ==================== ADMIN API ====================
@admin_router.get("/stats")
async def admin_stats(token: dict = Depends(verify_admin_or_service)):
    users = _fetch_users()
    active_subs = sum(1 for u in users if u.get("subscription_status") == "active")
    return {
        "users": len(users),
        "active_subs": active_subs,
        "keywords": 0,
        "findings_total": 0,
        "findings_active": 0,
        "pending_payments": len([p for p in PAYMENTS if p.get("status") not in ["confirmed", "rejected"]]),
        "removal_requests": len(REMOVALS),
    }


@admin_router.get("/users")
async def admin_users(token: dict = Depends(verify_admin_or_service)):
    return {"users": _fetch_users()}


@admin_router.post("/users")
async def admin_create_user(payload: dict, token: dict = Depends(verify_admin_or_service)):
    actor = token.get("sub") or token.get("iss")
    AUDIT_LOG.append({
        "id": generate_id(),
        "at": now_iso(),
        "actor_email": actor,
        "action": "user_create",
        "target_email": payload.get("email"),
    })

    svc_token = create_service_token("orchestrator")
    req = urllib.request.Request(
        "http://127.0.0.1:8002/api/users/",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {svc_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except urllib.error.HTTPError as e:
        detail = "Failed to create user"
        try:
            err = json.loads(e.read().decode("utf-8"))
            detail = err.get("detail") or detail
        except Exception:
            pass
        raise HTTPException(status_code=e.code, detail=detail)
    except Exception:
        raise HTTPException(status_code=502, detail="User service unavailable")


@admin_router.get("/users/{user_id}")
async def admin_get_user(user_id: str, token: dict = Depends(verify_admin_or_service)):
    user = _find_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": user}


@admin_router.patch("/users/{user_id}")
async def admin_patch_user(user_id: str, payload: dict, token: dict = Depends(verify_admin_or_service)):
    AUDIT_LOG.append({
        "id": generate_id(),
        "at": now_iso(),
        "actor_email": token.get("sub") or token.get("iss"),
        "action": "user_patch",
        "target_user_id": user_id,
        "changes": payload,
    })
    user = _find_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    svc_token = create_service_token("orchestrator")
    req = urllib.request.Request(
        f"http://127.0.0.1:8002/api/users/{user_id}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {svc_token}",
            "Content-Type": "application/json",
        },
        method="PATCH",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return {"ok": bool(data.get("ok", True)), "user": data.get("user")}
    except urllib.error.HTTPError as e:
        detail = "Failed to patch user"
        try:
            err = json.loads(e.read().decode("utf-8"))
            detail = err.get("detail") or detail
        except Exception:
            pass
        raise HTTPException(status_code=e.code, detail=detail)
    except Exception:
        raise HTTPException(status_code=502, detail="User service unavailable")


@admin_router.delete("/users/{user_id}")
async def admin_delete_user(user_id: str, token: dict = Depends(verify_admin_or_service)):
    AUDIT_LOG.append({
        "id": generate_id(),
        "at": now_iso(),
        "actor_email": token.get("sub") or token.get("iss"),
        "action": "user_delete",
        "target_user_id": user_id,
    })
    return {"ok": True, "deleted": user_id}


@admin_router.post("/users/{user_id}/reset-password")
async def admin_reset_password(user_id: str, payload: dict, token: dict = Depends(verify_admin_or_service)):
    AUDIT_LOG.append({
        "id": generate_id(),
        "at": now_iso(),
        "actor_email": token.get("sub") or token.get("iss"),
        "action": "password_reset",
        "target_user_id": user_id,
    })
    return {"ok": True}


@admin_router.post("/users/{user_id}/scan")
async def admin_scan(user_id: str, token: dict = Depends(verify_admin_or_service)):
    AUDIT_LOG.append({
        "id": generate_id(),
        "at": now_iso(),
        "actor_email": token.get("sub") or token.get("iss"),
        "action": "admin_scan",
        "target_user_id": user_id,
    })
    return {"ok": True}


@admin_router.post("/users/{user_id}/impersonate")
async def admin_impersonate(user_id: str, token: dict = Depends(verify_admin_or_service)):
    user = _find_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    imp_token = create_user_token(
        user_id,
        bool(user.get("is_admin")),
        "client_index",
        email=user.get("email"),
        employee_number=user.get("employee_number"),
    )
    AUDIT_LOG.append({
        "id": generate_id(),
        "at": now_iso(),
        "actor_email": token.get("sub") or token.get("iss"),
        "action": "impersonate",
        "target_user_id": user_id,
        "target_email": user.get("email"),
    })
    return {"ok": True, "token": imp_token, "user": user}


@admin_router.get("/payments")
async def admin_payments(token: dict = Depends(verify_admin_or_service)):
    return {"payments": PAYMENTS}


@admin_router.post("/payments/{payment_id}/confirm")
async def admin_confirm_payment(payment_id: str, token: dict = Depends(verify_admin_or_service)):
    for p in PAYMENTS:
        if p.get("id") == payment_id:
            p["status"] = "confirmed"
            p["confirmed_at"] = now_iso()
            break
    return {"ok": True, "payment_id": payment_id}


@admin_router.post("/payments/{payment_id}/reject")
async def admin_reject_payment(payment_id: str, token: dict = Depends(verify_admin_or_service)):
    for p in PAYMENTS:
        if p.get("id") == payment_id:
            p["status"] = "rejected"
            p["rejected_at"] = now_iso()
            break
    return {"ok": True, "payment_id": payment_id}


@admin_router.get("/email-log")
async def admin_email_log(token: dict = Depends(verify_admin_or_service)):
    return {"emails": EMAIL_LOG}


@admin_router.get("/removals")
async def admin_removals(token: dict = Depends(verify_admin_or_service)):
    return {"removals": REMOVALS}


@admin_router.post("/removals/{removal_id}/mark-removed")
async def admin_mark_removed(removal_id: str, token: dict = Depends(verify_admin_or_service)):
    for r in REMOVALS:
        if r.get("id") == removal_id:
            r["status"] = "removed"
            r["removed_at"] = now_iso()
            break
    return {"ok": True, "removal_id": removal_id}


@admin_router.get("/audit-log")
async def admin_audit(token: dict = Depends(verify_admin_or_service)):
    return {"audit": sorted(AUDIT_LOG, key=lambda x: x.get("at", ""), reverse=True)[:500]}


@admin_router.get("/documents")
async def admin_documents(token: dict = Depends(verify_admin_or_service)):
    return {"documents": DOCUMENTS}


@admin_router.get("/documents/{document_id}")
async def admin_document(document_id: str, token: dict = Depends(verify_admin_or_service)):
    for d in DOCUMENTS:
        if d.get("id") == document_id:
            return {"document": d}
    raise HTTPException(status_code=404, detail="Document not found")


@admin_router.get("/analytics")
async def admin_analytics(token: dict = Depends(verify_admin_or_service)):
    users = _fetch_users()
    active_subs = sum(1 for u in users if u.get("subscription_status") == "active")
    trial_users = sum(1 for u in users if u.get("subscription_status") == "trial")
    suspended_users = sum(1 for u in users if u.get("subscription_status") == "suspended")
    total_revenue = sum(int(p.get("amount_usd", 0)) for p in PAYMENTS if p.get("status") == "confirmed")

    today = datetime.now(timezone.utc).date()
    timeseries = []
    for i in range(29, -1, -1):
        d = today - timedelta(days=i)
        timeseries.append({"d": d.isoformat(), "revenue": 0, "signups": 0, "findings": 0, "removals": 0})

    return {
        "mrr_total": total_revenue,
        "totals": {
            "total_revenue": total_revenue,
            "active_subs": active_subs,
            "trial_users": trial_users,
            "suspended_users": suspended_users,
            "documents_signed": len([d for d in DOCUMENTS if d.get("status") == "signed"]),
            "documents_dispatched": len([d for d in DOCUMENTS if d.get("dispatched_to")]),
        },
        "timeseries": timeseries,
        "mrr_by_plan": [{"plan": "basic", "subs": 0, "mrr": 0, "color": "#00FF41"}, {"plan": "pro", "subs": 0, "mrr": 0, "color": "#FFD700"}, {"plan": "enterprise", "subs": 0, "mrr": 0, "color": "#FF3333"}],
        "method_split": [{"name": "interac", "value": len([p for p in PAYMENTS if p.get("method") == "interac"])}, {"name": "paypal", "value": len([p for p in PAYMENTS if p.get("method") == "paypal"])}, {"name": "crypto", "value": len([p for p in PAYMENTS if p.get("method") == "crypto"])}],
        "severity_distribution": [{"name": "low", "value": 0}, {"name": "medium", "value": 0}, {"name": "high", "value": 0}, {"name": "critical", "value": 0}],
    }


@admin_router.get("/health")
async def admin_health(token: dict = Depends(verify_admin_or_service)):
    _refresh_registry_snapshot()
    inf_status = get_infisical_status()
    inf_check = {
        "name": "Infisical",
        "status": "ok" if inf_status["connected"] else ("warn" if inf_status["initialized"] else "fail"),
        "detail": (
            f"connected, {inf_status['cached_secrets']} secrets cached"
            if inf_status["connected"]
            else (f"not connected, last error: {inf_status['error']}" if inf_status["error"] else "not initialized")
        ),
    }
    checks = [
        {
            "name": "Service Registry",
            "status": "ok" if len(SERVICE_REGISTRY) >= len(SERVICE_STARTUP_ORDER) else "warn",
            "detail": f"registered services: {len(SERVICE_REGISTRY)}",
        },
        inf_check,
        {
            "name": "SMTP",
            "status": "ok" if _secret("SMTP_HOST") and _secret("SMTP_USERNAME") else "warn",
            "detail": f"host={_secret('SMTP_HOST', '') or 'not set'}",
        },
        {
            "name": "PayPal",
            "status": "ok" if _secret("PAYPAL_CLIENT_ID") else "warn",
            "detail": "configured" if _secret("PAYPAL_CLIENT_ID") else "not configured",
        },
    ]
    service_db_paths = [
        {
            "service": name,
            "status": SERVICE_REGISTRY.get(name, {}).get("status", "unknown"),
            "db_path": SERVICE_REGISTRY.get(name, {}).get("db_path"),
        }
        for name in SERVICE_STARTUP_ORDER
    ]
    overall_ok = all(c["status"] != "fail" for c in checks)
    return {"ok": overall_ok, "checked_at": now_iso(), "checks": checks, "service_db_paths": service_db_paths}


@admin_router.post("/health/smtp-test")
async def admin_smtp_test(payload: dict, token: dict = Depends(verify_admin_or_service)):
    to = payload.get("to")
    if not to:
        raise HTTPException(status_code=400, detail="'to' is required")

    subject = "[d31337m3] SMTP test"
    body = (
        "This is a real SMTP test message from d31337m3 orchestrator.\n\n"
        f"sent_at={now_iso()}\n"
        f"triggered_by={(token.get('sub') or token.get('iss') or 'unknown')}\n"
    )

    smtp_host = _secret("SMTP_HOST")
    smtp_port = int(_secret("SMTP_PORT", "465") or "465")
    smtp_username = _secret("SMTP_USERNAME")
    smtp_password = _secret("SMTP_PASSWORD")
    smtp_from = _secret("SMTP_FROM") or smtp_username

    missing = [
        k for k, v in {
            "SMTP_HOST": smtp_host,
            "SMTP_USERNAME": smtp_username,
            "SMTP_PASSWORD": smtp_password,
            "SMTP_FROM": smtp_from,
        }.items() if not v
    ]
    if missing:
        logger.info(f"[EMAIL-MOCK] to={to} subject={subject} (SMTP not fully configured)")
        EMAIL_LOG.append({
            "id": generate_id(),
            "to": to,
            "subject": subject,
            "body": body,
            "mocked": True,
            "delivered": True,
            "sent_at": now_iso(),
        })
        return {"ok": True, "to": to, "mocked": True}

    msg = EmailMessage()
    msg["From"] = smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        # SMTP provider currently has cert/hostname mismatch; use tolerant TLS context.
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ctx, timeout=20) as server:
            server.login(smtp_username, smtp_password)
            server.send_message(msg)

        EMAIL_LOG.append({
            "id": generate_id(),
            "to": to,
            "subject": subject,
            "body": body,
            "mocked": False,
            "delivered": True,
            "sent_at": now_iso(),
        })
        return {"ok": True, "to": to, "mocked": False}
    except Exception as e:
        logger.error(f"SMTP test failed: {e}")
        EMAIL_LOG.append({
            "id": generate_id(),
            "to": to,
            "subject": subject,
            "body": body,
            "mocked": False,
            "delivered": False,
            "error": str(e),
            "sent_at": now_iso(),
        })
        return {"ok": False, "to": to, "mocked": False, "error": str(e)}


@admin_router.get("/broker-contacts")
async def admin_broker_contacts(token: dict = Depends(verify_admin_or_service)):
    contacts = list(BROKER_CONTACTS.values())
    return {"contacts": sorted(contacts, key=lambda x: x.get("broker", "").lower())}


@admin_router.post("/broker-contacts")
async def admin_upsert_broker_contact(payload: dict, token: dict = Depends(verify_admin_or_service)):
    broker = (payload.get("broker") or "").strip()
    if not broker:
        raise HTTPException(status_code=400, detail="broker is required")
    rec = {"id": generate_id(), "broker": broker, "email": payload.get("email"), "form": payload.get("form"), "updated_at": now_iso(), "updated_by": token.get("sub") or token.get("iss")}
    if broker in BROKER_CONTACTS:
        rec["id"] = BROKER_CONTACTS[broker].get("id", rec["id"])
    BROKER_CONTACTS[broker] = rec
    return {"ok": True, "contact": rec}


@admin_router.delete("/broker-contacts/{broker}")
async def admin_delete_broker_contact(broker: str, token: dict = Depends(verify_admin_or_service)):
    if broker in BROKER_CONTACTS:
        BROKER_CONTACTS.pop(broker, None)
    return {"ok": True}


@admin_router.get("/settings")
async def admin_settings(token: dict = Depends(verify_admin_or_service)):
    return {
        "environment": {
            "mongo_db": _secret("DB_NAME"),
            "admin_email": _secret("ADMIN_EMAIL"),
            "cors_origins": _secret("CORS_ORIGINS"),
            "jwt_algorithm": _secret("JWT_ALGORITHM", "HS256"),
            "token_expiry_minutes": int(_secret("ACCESS_TOKEN_EXPIRE_MINUTES", "1440") or "1440"),
            "smtp_enabled": bool(_secret("SMTP_HOST") and _secret("SMTP_USERNAME")),
            "smtp_host": _secret("SMTP_HOST"),
            "smtp_port": _secret("SMTP_PORT"),
            "smtp_username": _secret("SMTP_USERNAME"),
            "smtp_password_masked": "***" if _secret("SMTP_PASSWORD") else None,
            "smtp_from": _secret("SMTP_FROM"),
            "payments_email": _secret("PAYMENTS_EMAIL"),
            "crypto_wallet": _secret("CRYPTO_WALLET"),
            "paypal_configured": bool(_secret("PAYPAL_CLIENT_ID")),
            "paypal_api_base": _secret("PAYPAL_API_BASE"),
            "ethereum_rpc": _secret("ETHEREUM_RPC_URL"),
            "polygon_rpc": _secret("POLYGON_RPC_URL"),
            "base_rpc": _secret("BASE_RPC_URL"),
        },
        "rate_limiter": {"window_seconds": RATE_WINDOW_SEC, "max_attempts": RATE_MAX_ATTEMPTS, "active_buckets": len(RATE_LIMITS)},
        "plans": list(PLANS.values()),
        "supported_countries": list(SUPPORTED_COUNTRIES.keys()),
        "broker_count_db": len(BROKER_CONTACTS),
        "broker_count_builtin": len(DATA_BROKERS),
    }


@admin_router.get("/ops/capabilities")
async def admin_ops_capabilities(token: dict = Depends(verify_admin_or_service)):
    return {
        "host_controls_enabled": _host_controls_enabled(),
        "service_units": SYSTEMD_UNITS,
        "support_email_otp_required": SUPPORT_EMAIL_OTP_REQUIRED,
        "note": "Set ADMIN_ENABLE_HOST_CONTROLS=true to enable restart/reboot endpoints.",
    }


@admin_router.get("/ops/support-email-otp")
async def admin_support_email_otp_state(token: dict = Depends(verify_admin_or_service)):
    return {
        "ok": True,
        "enabled": SUPPORT_EMAIL_OTP_REQUIRED,
        "scope": "support_anonymous_chat",
    }


@admin_router.post("/ops/support-email-otp")
async def admin_set_support_email_otp(payload: dict, token: dict = Depends(verify_admin_or_service)):
    global SUPPORT_EMAIL_OTP_REQUIRED
    if "enabled" not in payload:
        raise HTTPException(status_code=400, detail="enabled is required")

    SUPPORT_EMAIL_OTP_REQUIRED = bool(payload.get("enabled"))
    save_runtime_state()
    AUDIT_LOG.append({
        "id": generate_id(),
        "at": now_iso(),
        "actor_email": token.get("sub") or token.get("iss"),
        "action": "support_email_otp_toggle",
        "ok": True,
        "changes": {"enabled": SUPPORT_EMAIL_OTP_REQUIRED},
    })
    return {
        "ok": True,
        "enabled": SUPPORT_EMAIL_OTP_REQUIRED,
        "scope": "support_anonymous_chat",
    }


@admin_router.post("/ops/restart-service/{service_name}")
async def admin_restart_service(service_name: str, token: dict = Depends(verify_admin_or_service)):
    if not _host_controls_enabled():
        raise HTTPException(status_code=403, detail="Host controls are disabled")
    if service_name not in SYSTEMD_UNITS:
        raise HTTPException(status_code=404, detail=f"Unknown service: {service_name}")

    unit = SYSTEMD_UNITS[service_name]
    actor = token.get("sub") or token.get("iss") or "unknown"
    cmd = _systemctl_base_cmd() + ["restart", unit]
    result = _run_cmd(cmd)
    AUDIT_LOG.append({
        "id": generate_id(),
        "at": now_iso(),
        "actor_email": actor,
        "action": "restart_service",
        "target_service": service_name,
        "unit": unit,
        "ok": result["ok"],
        "stderr": result.get("stderr"),
    })
    return {"ok": result["ok"], "service": service_name, "unit": unit, "result": result}


@admin_router.post("/ops/restart-all")
async def admin_restart_all_services(token: dict = Depends(verify_admin_or_service)):
    if not _host_controls_enabled():
        raise HTTPException(status_code=403, detail="Host controls are disabled")

    actor = token.get("sub") or token.get("iss") or "unknown"
    results: List[Dict[str, Any]] = []
    for service_name in SERVICE_STARTUP_ORDER:
        # Avoid restarting orchestrator inside its own request lifecycle.
        if service_name == "orchestrator":
            results.append({
                "service": service_name,
                "unit": SYSTEMD_UNITS.get(service_name),
                "result": {"ok": True, "code": 0, "stdout": "", "stderr": "skipped in restart-all", "command": ""},
            })
            continue
        unit = SYSTEMD_UNITS.get(service_name)
        if not unit:
            continue
        cmd = _systemctl_base_cmd() + ["restart", unit]
        result = _run_cmd(cmd)
        results.append({"service": service_name, "unit": unit, "result": result})

    ok = all(r["result"].get("ok") for r in results)
    AUDIT_LOG.append({
        "id": generate_id(),
        "at": now_iso(),
        "actor_email": actor,
        "action": "restart_all_services",
        "ok": ok,
    })
    return {"ok": ok, "results": results}


@admin_router.post("/ops/reboot-server")
async def admin_reboot_server(payload: dict, token: dict = Depends(verify_admin_or_service)):
    if not _host_controls_enabled():
        raise HTTPException(status_code=403, detail="Host controls are disabled")

    confirm = str(payload.get("confirm") or "")
    if confirm != "REBOOT_PHYSICAL_SERVER":
        raise HTTPException(status_code=400, detail="Missing confirmation token")

    actor = token.get("sub") or token.get("iss") or "unknown"
    cmd = _systemctl_base_cmd() + ["reboot"]
    result = _run_cmd(cmd)
    AUDIT_LOG.append({
        "id": generate_id(),
        "at": now_iso(),
        "actor_email": actor,
        "action": "reboot_server",
        "ok": result["ok"],
        "stderr": result.get("stderr"),
    })
    return {"ok": result["ok"], "result": result}