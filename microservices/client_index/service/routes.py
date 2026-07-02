"""
API Routes for Client Index Service
Contains authentication, user management, and profile endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, Any, Dict
import logging
from sqlalchemy.orm import Session
import hashlib
import hmac
import random
import smtplib
import ssl
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone

# Import shared components
import sys
sys.path.append('/home/D31337m3/Orm_d31337m3/microservices')

from shared.jwt_utils import (
    create_service_token,
    verify_service_token,
    create_user_token,
    verify_user_token,
    user_has_admin_access,
)
from shared.security_middleware import verify_service_request, verify_user_request, require_service_auth, require_user_auth
from shared.database_models import *
from shared.database import get_db, init_db
from shared.repositories import (
    UserRepository,
    ProfileRepository,
    KeywordRepository,
    UserSecurityRepository,
    AuthChallengeRepository,
    TrustedDeviceRepository,
    AuthAuditRepository,
    SignatureRepository,
    DocumentRepository,
)
from shared.utils import now_iso, hash_password, verify_password, find_promo_for_code, promo_is_expired, build_promo_code, SUPPORTED_COUNTRIES, LEGAL_TEMPLATES, _fill_template
from shared.database import Finding
from shared.secrets_manager import get_secret, get_int_secret

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("client_index.routes")

# Initialize database
try:
    init_db()
except Exception as e:
    logger.warning(f"Database initialization warning: {e}")

# Create routers
auth_router = APIRouter()
user_router = APIRouter()
profile_router = APIRouter()
signature_router = APIRouter()
documents_router = APIRouter()
meta_router = APIRouter()

# Security schemes
bearer = HTTPBearer(auto_error=False)

# Simple in-memory rate limit tracker (in production, use Redis or similar)
RATE_LIMIT_CACHE = {}
RATE_LIMIT_MAX_KEYS = int(get_secret("AUTH_RATE_LIMIT_MAX_KEYS", "50000") or "50000")

OTP_TTL_MINUTES = int(get_secret("AUTH_OTP_TTL_MINUTES", "10") or "10")
OTP_MAX_ATTEMPTS = int(get_secret("AUTH_OTP_MAX_ATTEMPTS", "5") or "5")
TRUSTED_DEVICE_DAYS = int(get_secret("TRUSTED_DEVICE_DAYS", "90") or "90")
OTP_RESEND_COOLDOWN_SECONDS = int(get_secret("AUTH_OTP_RESEND_COOLDOWN_SECONDS", "60") or "60")
OTP_RESEND_MAX_PER_HOUR = int(get_secret("AUTH_OTP_RESEND_MAX_PER_HOUR", "5") or "5")

PROMO_CODES = [
    promo for promo in [
        build_promo_code(
            get_secret("PROMO_CODE_PRIMARY", "OCanada75") or "OCanada75",
            get_int_secret("PROMO_PERCENT_PRIMARY", 75),
            get_secret("PROMO_EXPIRES_PRIMARY", "2026-12-31") or "2026-12-31",
        ),
        build_promo_code(
            get_secret("PROMO_CODE_SECONDARY", "") or "",
            get_int_secret("PROMO_PERCENT_SECONDARY", 0),
            get_secret("PROMO_EXPIRES_SECONDARY", "") or "",
        ),
    ] if promo is not None
]


class VerifyOtpIn(BaseModel):
    challenge_id: str
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)


class RegisterStartResponse(BaseModel):
    requires_verification: bool
    challenge_id: str
    expires_in_seconds: int
    email_hint: str


class LoginVerifyOtpIn(VerifyOtpIn):
    remember_device: bool = True
    device_name: Optional[str] = None


class TwoFAStartIn(BaseModel):
    password: str


class DisableTwoFAIn(BaseModel):
    password: str


class ResendOtpIn(BaseModel):
    challenge_id: str
    email: EmailStr


def _mask_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if len(local) <= 2:
        local_masked = local[0] + "*"
    else:
        local_masked = local[0] + ("*" * (len(local) - 2)) + local[-1]
    return f"{local_masked}@{domain}"


def _serialize_user(user, security=None) -> dict:
    data = user.to_dict()
    data["is_admin"] = user_has_admin_access(user.email, user.is_admin)
    if security is not None:
        data["email_verified"] = security.email_verified
        data["two_fa_enabled"] = security.two_fa_enabled
    return data


def _otp_digest(email: str, purpose: str, otp: str) -> str:
    secret = get_secret("JWT_SECRET", "dev-secret") or "dev-secret"
    msg = f"{email.lower()}|{purpose}|{otp}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def _generate_otp() -> str:
    return f"{random.randint(0, 999999):06d}"


def _get_device_id(request: Request) -> Optional[str]:
    did = (request.headers.get("x-device-id") or "").strip()
    if not did:
        return None
    return did[:255]


def _send_email_via_azure(to: str, subject: str, body: str) -> bool:
    connection_string = get_secret("AZURE_COMM_EMAIL_CONNECTION_STRING")
    if not connection_string:
        return False

    try:
        from azure.communication.email import EmailClient  # type: ignore

        client = EmailClient.from_connection_string(connection_string)
        sender = get_secret("AZURE_COMM_EMAIL_SENDER", "DoNotReply@d31337m3.com") or "DoNotReply@d31337m3.com"
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


def _send_email_sync(to: str, subject: str, body: str) -> bool:
    if _send_email_via_azure(to, subject, body):
        return True

    smtp_host = get_secret("SMTP_HOST")
    smtp_port = get_int_secret("SMTP_PORT", 465)
    smtp_username = get_secret("SMTP_USERNAME")
    smtp_password = get_secret("SMTP_PASSWORD")
    smtp_from = get_secret("SMTP_FROM") or smtp_username
    if not smtp_host or not smtp_username or not smtp_password or not smtp_from:
        logger.info(f"[EMAIL-MOCK] to={to} subject={subject} (SMTP not fully configured)")
        return True
        logger.error("SMTP enabled but config is incomplete")
        return False

    msg = EmailMessage()
    msg["From"] = smtp_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with smtplib.SMTP_SSL(smtp_host, smtp_port, context=ctx, timeout=20) as server:
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
    return True


def _is_smtp_enabled() -> bool:
    return bool(get_secret("SMTP_HOST") and get_secret("SMTP_USERNAME") and get_secret("SMTP_PASSWORD"))


def _create_challenge(db: Session, *, email: str, purpose: str, otp: str, user_id: Optional[str] = None, metadata: Optional[dict] = None):
    expires_at = datetime.utcnow() + timedelta(minutes=OTP_TTL_MINUTES)
    return AuthChallengeRepository.create(db, {
        "email": email.lower(),
        "purpose": purpose,
        "otp_hash": _otp_digest(email, purpose, otp),
        "user_id": user_id,
        "expires_at": expires_at,
        "max_attempts": OTP_MAX_ATTEMPTS,
        "metadata": metadata or {},
    })


def _audit_auth_event(db: Session, event: str, request: Optional[Request], user_id: Optional[str] = None, email: Optional[str] = None, detail: Optional[dict] = None):
    ip = request.client.host if (request and request.client) else None
    try:
        AuthAuditRepository.append(
            db,
            event=event,
            user_id=user_id,
            email=email,
            detail=detail or {},
            ip_address=ip,
        )
    except Exception as e:
        logger.warning(f"failed to append auth audit event={event}: {e}")


def _check_otp_send_limits(email: str, purpose: str) -> tuple[bool, int]:
    cooldown_ok, cooldown_retry = _ratelimit(
        f"otp-cooldown:{purpose}:{email.lower()}",
        max_attempts=1,
        window_seconds=OTP_RESEND_COOLDOWN_SECONDS,
    )
    if not cooldown_ok:
        return False, cooldown_retry

    hourly_ok, hourly_retry = _ratelimit(
        f"otp-hourly:{purpose}:{email.lower()}",
        max_attempts=OTP_RESEND_MAX_PER_HOUR,
        window_seconds=3600,
    )
    if not hourly_ok:
        return False, hourly_retry

    return True, 0


def _require_valid_challenge(db: Session, payload: VerifyOtpIn, purpose: str):
    challenge = AuthChallengeRepository.get_by_id(db, payload.challenge_id)
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    if challenge.email.lower() != payload.email.lower() or challenge.purpose != purpose:
        raise HTTPException(status_code=400, detail="Challenge mismatch")
    if challenge.consumed_at is not None:
        raise HTTPException(status_code=400, detail="Challenge already used")
    if challenge.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP expired")
    if challenge.attempts >= challenge.max_attempts:
        raise HTTPException(status_code=429, detail="OTP attempt limit reached")

    otp_allowed, otp_retry = _ratelimit(
        f"otp-verify:{purpose}:{payload.email.lower()}",
        max_attempts=12,
        window_seconds=15 * 60,
    )
    if not otp_allowed:
        raise HTTPException(status_code=429, detail=f"Too many OTP attempts. Retry in {otp_retry}s")

    incoming_digest = _otp_digest(payload.email, purpose, payload.otp)
    if not hmac.compare_digest(incoming_digest, challenge.otp_hash):
        AuthChallengeRepository.mark_attempt(db, challenge.id, challenge.attempts + 1)
        raise HTTPException(status_code=400, detail="Invalid OTP")
    return challenge

def _ratelimit(key: str, max_attempts: int = 5, window_seconds: int = 300) -> tuple:
    """
    Simple rate limiter. Returns (allowed: bool, retry_after: int)
    """
    import time
    current_time = time.time()

    if len(RATE_LIMIT_CACHE) > RATE_LIMIT_MAX_KEYS:
        for k in list(RATE_LIMIT_CACHE.keys()):
            if not RATE_LIMIT_CACHE.get(k):
                RATE_LIMIT_CACHE.pop(k, None)
        if len(RATE_LIMIT_CACHE) > RATE_LIMIT_MAX_KEYS:
            oldest = sorted(
                RATE_LIMIT_CACHE.items(),
                key=lambda kv: kv[1][0] if kv[1] else current_time,
            )
            for k, _ in oldest[: max(1, len(RATE_LIMIT_CACHE) - RATE_LIMIT_MAX_KEYS)]:
                RATE_LIMIT_CACHE.pop(k, None)
    
    if key not in RATE_LIMIT_CACHE:
        RATE_LIMIT_CACHE[key] = []
    
    # Remove old attempts outside the window
    RATE_LIMIT_CACHE[key] = [t for t in RATE_LIMIT_CACHE[key] if current_time - t < window_seconds]
    
    if len(RATE_LIMIT_CACHE[key]) >= max_attempts:
        # Calculate retry time
        oldest_attempt = RATE_LIMIT_CACHE[key][0]
        retry_after = int(window_seconds - (current_time - oldest_attempt))
        return (False, max(1, retry_after))
    
    # Record this attempt
    RATE_LIMIT_CACHE[key].append(current_time)
    return (True, 0)

# Repository-based database functions using dependency injection

# Authentication endpoints
@auth_router.post("/register")
async def register(payload: UserCreate, background: BackgroundTasks, request: Request, db: Session = Depends(get_db)):
    """Start registration by sending OTP to email."""
    ip = request.client.host if request.client else "anon"
    
    # Rate limiting
    allowed, retry = _ratelimit(f"register:{ip}")
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Too many signups from this IP. Try again in {retry // 60}m.")
    
    # Check if user already exists
    existing_user = UserRepository.get_by_email(db, payload.email.lower())
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Validate promo code if provided
    promo = None
    if payload.promo_code and payload.promo_code.strip():
        promo = find_promo_for_code(payload.promo_code, PROMO_CODES)
        if not promo:
            raise HTTPException(status_code=400, detail="Invalid promo code")
        if promo_is_expired(promo):
            raise HTTPException(status_code=400, detail="Promo code expired")

    otp_allowed, otp_retry = _check_otp_send_limits(payload.email.lower(), "register")
    if not otp_allowed:
        raise HTTPException(status_code=429, detail=f"Please wait {otp_retry}s before requesting another code")

    otp = _generate_otp()
    challenge = _create_challenge(
        db,
        email=payload.email.lower(),
        purpose="register",
        otp=otp,
        metadata={
            "email": payload.email.lower(),
            "name": payload.name or payload.email.split("@")[0],
            "password_hash": hash_password(payload.password),
            "promo": promo,
        },
    )

    body = (
        f"Your d31337m3 verification code is: {otp}\n\n"
        f"This code expires in {OTP_TTL_MINUTES} minutes.\n"
        "If you did not request this, ignore this email."
    )
    try:
        _send_email_sync(payload.email.lower(), "[d31337m3] Verify your email", body)
    except Exception as e:
        logger.error(f"register OTP email failed: {e}")

    _audit_auth_event(
        db,
        "register_otp_sent",
        request,
        user_id=None,
        email=payload.email.lower(),
        detail={"challenge_id": challenge.id},
    )

    return {
        "requires_verification": True,
        "challenge_id": challenge.id,
        "expires_in_seconds": OTP_TTL_MINUTES * 60,
        "email_hint": _mask_email(payload.email.lower()),
    }


@auth_router.post("/register/verify")
async def register_verify(payload: VerifyOtpIn, request: Request, db: Session = Depends(get_db)):
    """Verify registration OTP and create the user account."""
    challenge = _require_valid_challenge(db, payload, "register")
    metadata = AuthChallengeRepository.metadata(challenge)

    existing_user = UserRepository.get_by_email(db, payload.email.lower())
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_data = {
        "id": generate_id(),
        "email": payload.email.lower(),
        "name": metadata.get("name") or payload.email.split("@")[0],
        "password_hash": metadata.get("password_hash"),
        "auth_provider": "password",
        "is_admin": user_has_admin_access(payload.email.lower(), False),
        "is_active": True,
        "plan_id": None,
        "subscription_status": "trial",
        "subscription_started_at": datetime.now(timezone.utc),
    }
    promo = metadata.get("promo")
    if promo:
        user_data["promo_code"] = promo.get("code")
        user_data["promo_discount_percent"] = promo.get("percent_off")
        user_data["promo_expires_at"] = promo.get("expires_raw")

    created_user = UserRepository.create(db, user_data)
    UserSecurityRepository.ensure(db, created_user.id, email_verified=True)

    ProfileRepository.create(db, {
        "user_id": created_user.id,
        "name": created_user.name,
        "address": "",
        "phone": "",
        "country": "CA",
        "state": "ON",
    })

    if created_user.name and len(created_user.name) >= 3 and "@" not in created_user.name:
        KeywordRepository.create(db, {
            "id": generate_id(),
            "user_id": created_user.id,
            "value": created_user.name,
            "type": "name",
        })

    AuthChallengeRepository.mark_verified_and_consumed(db, challenge.id)
    _audit_auth_event(
        db,
        "register_verified",
        request,
        user_id=created_user.id,
        email=created_user.email,
        detail={"challenge_id": challenge.id},
    )

    token = create_user_token(created_user.id, created_user.is_admin, "client_index", email=created_user.email, employee_number=created_user.employee_number)
    response_user = _serialize_user(
        created_user,
        type("SecurityState", (), {"email_verified": True, "two_fa_enabled": False})(),
    )
    if promo:
        response_user["promo_code"] = promo.get("code")
        response_user["promo_discount_percent"] = promo.get("percent_off")
        response_user["promo_expires_at"] = promo.get("expires_raw")
    return {"token": token, "user": response_user}


@auth_router.post("/register/resend")
async def resend_register_otp(payload: ResendOtpIn, request: Request, db: Session = Depends(get_db)):
    challenge = AuthChallengeRepository.get_by_id(db, payload.challenge_id)
    if not challenge or challenge.purpose != "register" or challenge.email.lower() != payload.email.lower():
        raise HTTPException(status_code=404, detail="Challenge not found")
    if challenge.consumed_at is not None:
        raise HTTPException(status_code=400, detail="Challenge already completed")

    otp_allowed, otp_retry = _check_otp_send_limits(payload.email.lower(), "register")
    if not otp_allowed:
        raise HTTPException(status_code=429, detail=f"Please wait {otp_retry}s before requesting another code")

    metadata = AuthChallengeRepository.metadata(challenge)
    otp = _generate_otp()
    new_challenge = _create_challenge(
        db,
        email=payload.email.lower(),
        purpose="register",
        otp=otp,
        metadata=metadata,
    )
    _send_email_sync(payload.email.lower(), "[d31337m3] Verify your email", f"Your d31337m3 verification code is: {otp}\n\nThis code expires in {OTP_TTL_MINUTES} minutes.")
    _audit_auth_event(db, "register_otp_resent", request, email=payload.email.lower(), detail={"challenge_id": new_challenge.id})

    return {
        "requires_verification": True,
        "challenge_id": new_challenge.id,
        "expires_in_seconds": OTP_TTL_MINUTES * 60,
        "email_hint": _mask_email(payload.email.lower()),
    }

@auth_router.post("/login")
async def login(payload: UserLogin, request: Request, db: Session = Depends(get_db)):
    """Login with adaptive OTP challenge for unknown devices and optional 2FA."""
    ip = (request.client.host if request.client else "anon") + ":" + payload.email.lower()
    
    # Rate limiting
    allowed, retry = _ratelimit(f"login:{ip}")
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Too many attempts. Try again in {retry // 60}m {retry % 60}s.")
    
    # Get user by email
    user = UserRepository.get_by_email(db, payload.email.lower())
    if not user or not verify_password(payload.password, user.password_hash):
        _audit_auth_event(db, "login_failed", request, email=payload.email.lower(), detail={"reason": "invalid_credentials"})
        raise HTTPException(status_code=401, detail="Invalid email or password")

    security = UserSecurityRepository.get_by_user_id(db, user.id)
    if security and not security.email_verified:
        _audit_auth_event(db, "login_blocked", request, user_id=user.id, email=user.email, detail={"reason": "email_not_verified"})
        raise HTTPException(status_code=403, detail="Email not verified")

    device_id = _get_device_id(request)
    trusted_device = TrustedDeviceRepository.get_active(db, user.id, device_id) if device_id else None
    needs_otp = bool((security and security.two_fa_enabled) or (not trusted_device))

    if needs_otp:
        reason = "2fa_enabled" if (security and security.two_fa_enabled) else "unrecognized_device"
        if reason == "unrecognized_device" and not _is_smtp_enabled():
            _audit_auth_event(
                db,
                "login_otp_bypassed",
                request,
                user_id=user.id,
                email=user.email,
                detail={"reason": "smtp_unavailable"},
            )
            token = create_user_token(user.id, user.is_admin, "client_index", email=user.email, employee_number=user.employee_number)
            return {
                "token": token,
                "user": _serialize_user(security=security, user=user)
            }

        otp_allowed, otp_retry = _check_otp_send_limits(user.email, "login")
        if not otp_allowed:
            raise HTTPException(status_code=429, detail=f"Please wait {otp_retry}s before requesting another code")

        otp = _generate_otp()
        challenge = _create_challenge(
            db,
            email=user.email,
            user_id=user.id,
            purpose="login",
            otp=otp,
            metadata={"reason": reason, "device_id": device_id},
        )
        try:
            _send_email_sync(
                user.email,
                "[d31337m3] Login verification code",
                f"Your login code is: {otp}\n\nThis code expires in {OTP_TTL_MINUTES} minutes.",
            )
        except Exception as e:
            logger.error(f"login OTP email failed: {e}")

        _audit_auth_event(
            db,
            "login_otp_sent",
            request,
            user_id=user.id,
            email=user.email,
            detail={"challenge_id": challenge.id, "reason": reason},
        )

        return {
            "requires_otp": True,
            "challenge_id": challenge.id,
            "expires_in_seconds": OTP_TTL_MINUTES * 60,
            "email_hint": _mask_email(user.email),
            "reason": reason,
        }

    TrustedDeviceRepository.touch(db, user.id, device_id) if device_id else None
    _audit_auth_event(db, "login_success", request, user_id=user.id, email=user.email, detail={"trusted_device": bool(device_id)})
    
    # Create access token (JWT secret from Infisical)
    token = create_user_token(user.id, user.is_admin, "client_index", email=user.email, employee_number=user.employee_number)
    
    # Return response
    return {
        "token": token,
        "user": _serialize_user(security=security, user=user)
    }


@auth_router.post("/login/verify")
async def login_verify(payload: LoginVerifyOtpIn, request: Request, db: Session = Depends(get_db)):
    """Verify login OTP and issue session token."""
    challenge = _require_valid_challenge(db, payload, "login")
    user = UserRepository.get_by_email(db, payload.email.lower())
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    AuthChallengeRepository.mark_verified_and_consumed(db, challenge.id)
    device_id = _get_device_id(request)
    if payload.remember_device and device_id:
        trusted_until = datetime.utcnow() + timedelta(days=TRUSTED_DEVICE_DAYS)
        TrustedDeviceRepository.upsert(db, user.id, device_id, trusted_until, payload.device_name)
        _audit_auth_event(db, "trusted_device_added", request, user_id=user.id, email=user.email, detail={"device_id": device_id})

    security = UserSecurityRepository.get_by_user_id(db, user.id)
    token = create_user_token(user.id, user.is_admin, "client_index", email=user.email, employee_number=user.employee_number)
    _audit_auth_event(db, "login_otp_verified", request, user_id=user.id, email=user.email, detail={"challenge_id": challenge.id})
    return {
        "token": token,
        "user": _serialize_user(security=security, user=user)
    }


@auth_router.post("/login/resend")
async def resend_login_otp(payload: ResendOtpIn, request: Request, db: Session = Depends(get_db)):
    challenge = AuthChallengeRepository.get_by_id(db, payload.challenge_id)
    if not challenge or challenge.purpose != "login" or challenge.email.lower() != payload.email.lower():
        raise HTTPException(status_code=404, detail="Challenge not found")
    if challenge.consumed_at is not None:
        raise HTTPException(status_code=400, detail="Challenge already completed")

    user = UserRepository.get_by_email(db, payload.email.lower())
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    otp_allowed, otp_retry = _check_otp_send_limits(payload.email.lower(), "login")
    if not otp_allowed:
        raise HTTPException(status_code=429, detail=f"Please wait {otp_retry}s before requesting another code")

    metadata = AuthChallengeRepository.metadata(challenge)
    otp = _generate_otp()
    new_challenge = _create_challenge(
        db,
        email=user.email,
        user_id=user.id,
        purpose="login",
        otp=otp,
        metadata=metadata,
    )
    _send_email_sync(user.email, "[d31337m3] Login verification code", f"Your login code is: {otp}\n\nThis code expires in {OTP_TTL_MINUTES} minutes.")
    _audit_auth_event(db, "login_otp_resent", request, user_id=user.id, email=user.email, detail={"challenge_id": new_challenge.id})

    return {
        "requires_otp": True,
        "challenge_id": new_challenge.id,
        "expires_in_seconds": OTP_TTL_MINUTES * 60,
        "email_hint": _mask_email(user.email),
        "reason": metadata.get("reason", "unrecognized_device"),
    }


@auth_router.get("/2fa")
async def get_2fa_status(user: dict = Depends(verify_user_request), db: Session = Depends(get_db)):
    sec = UserSecurityRepository.get_by_user_id(db, user["sub"])
    if not sec:
        sec = UserSecurityRepository.ensure(db, user["sub"], email_verified=True)
    return {
        "enabled": sec.two_fa_enabled,
        "method": sec.two_fa_method,
        "email_verified": sec.email_verified,
    }


@auth_router.post("/2fa/enable/start")
async def start_enable_2fa(payload: TwoFAStartIn, request: Request, user: dict = Depends(verify_user_request), db: Session = Depends(get_db)):
    user_db = UserRepository.get_by_id(db, user["sub"])
    if not user_db or not verify_password(payload.password, user_db.password_hash):
        raise HTTPException(status_code=401, detail="Invalid password")

    otp = _generate_otp()
    challenge = _create_challenge(db, email=user_db.email, user_id=user_db.id, purpose="enable_2fa", otp=otp)
    _send_email_sync(user_db.email, "[d31337m3] 2FA enable code", f"Use this code to enable 2FA: {otp}")
    _audit_auth_event(db, "2fa_enable_otp_sent", request, user_id=user_db.id, email=user_db.email, detail={"challenge_id": challenge.id})
    return {
        "challenge_id": challenge.id,
        "expires_in_seconds": OTP_TTL_MINUTES * 60,
        "email_hint": _mask_email(user_db.email),
    }


@auth_router.post("/2fa/enable/verify")
async def verify_enable_2fa(payload: VerifyOtpIn, request: Request, user: dict = Depends(verify_user_request), db: Session = Depends(get_db)):
    challenge = _require_valid_challenge(db, payload, "enable_2fa")
    if challenge.user_id and challenge.user_id != user["sub"]:
        raise HTTPException(status_code=403, detail="Challenge does not belong to this user")
    AuthChallengeRepository.mark_verified_and_consumed(db, challenge.id)
    sec = UserSecurityRepository.update(db, user["sub"], {"two_fa_enabled": True, "two_fa_method": "email"})
    _audit_auth_event(db, "2fa_enabled", request, user_id=user["sub"], email=payload.email.lower(), detail={"challenge_id": challenge.id})
    return {"ok": True, "enabled": sec.two_fa_enabled, "method": sec.two_fa_method}


@auth_router.post("/2fa/disable")
async def disable_2fa(payload: DisableTwoFAIn, request: Request, user: dict = Depends(verify_user_request), db: Session = Depends(get_db)):
    user_db = UserRepository.get_by_id(db, user["sub"])
    if not user_db or not verify_password(payload.password, user_db.password_hash):
        raise HTTPException(status_code=401, detail="Invalid password")
    sec = UserSecurityRepository.update(db, user["sub"], {"two_fa_enabled": False})
    _audit_auth_event(db, "2fa_disabled", request, user_id=user["sub"], email=user_db.email)
    return {"ok": True, "enabled": sec.two_fa_enabled}


@auth_router.get("/devices")
async def list_devices(user: dict = Depends(verify_user_request), db: Session = Depends(get_db)):
    rows = TrustedDeviceRepository.list_for_user(db, user["sub"])
    return {"devices": [r.to_dict() for r in rows]}


@auth_router.delete("/devices/{trusted_device_id}")
async def revoke_device(trusted_device_id: str, request: Request, user: dict = Depends(verify_user_request), db: Session = Depends(get_db)):
    ok = TrustedDeviceRepository.revoke(db, user["sub"], trusted_device_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Device not found")
    _audit_auth_event(db, "trusted_device_revoked", request, user_id=user["sub"], detail={"trusted_device_id": trusted_device_id})
    return {"ok": True}


@auth_router.get("/audit/events")
async def auth_audit_events(limit: int = 200, user: dict = Depends(verify_user_request), db: Session = Depends(get_db)):
    user_db = UserRepository.get_by_id(db, user.get("sub"))
    if not user_db or not user_has_admin_access(user_db.email, user_db.is_admin):
        raise HTTPException(status_code=403, detail="Admin only")
    from shared.database import AuthAudit
    rows = (
        db.query(AuthAudit)
        .order_by(AuthAudit.created_at.desc())
        .limit(max(1, min(limit, 1000)))
        .all()
    )
    return {"events": [r.to_dict() for r in rows]}

@auth_router.get("/me")
async def get_current_user_info(user: dict = Depends(verify_user_request), db: Session = Depends(get_db)):
    """Get current user information"""
    # Fetch fresh data from the database
    user_db = UserRepository.get_by_id(db, user.get("sub"))
    if not user_db:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": _serialize_user(user_db)}

# User management endpoints
@user_router.get("/")
async def get_users(skip: int = 0, limit: int = 100, user: dict = Depends(require_service_auth("orchestrator")), db: Session = Depends(get_db)):
    """Get list of users (for orchestrator/service-to-service communication)"""
    users = UserRepository.list_all(db, skip=skip, limit=limit)
    return {
        "users": [_serialize_user(u) for u in users],
        "count": len(users)
    }


@user_router.post("/")
async def create_user_admin(payload: UserCreate, user: dict = Depends(require_service_auth("orchestrator")), db: Session = Depends(get_db)):
    """Create a user directly from orchestrator admin controls (OTP bypass for admin ops)."""
    email = payload.email.lower()
    existing_user = UserRepository.get_by_email(db, email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    promo = None
    if payload.promo_code and payload.promo_code.strip():
        promo = find_promo_for_code(payload.promo_code, PROMO_CODES)
        if not promo:
            raise HTTPException(status_code=400, detail="Invalid promo code")
        if promo_is_expired(promo):
            raise HTTPException(status_code=400, detail="Promo code expired")

    user_data = {
        "id": generate_id(),
        "email": email,
        "name": payload.name or email.split("@")[0],
        "password_hash": hash_password(payload.password),
        "auth_provider": "password",
        "is_admin": bool(payload.is_admin),
        "is_active": bool(payload.is_active),
        "plan_id": None,
        "subscription_status": "trial",
        "subscription_started_at": datetime.now(timezone.utc),
    }
    if promo:
        user_data["promo_code"] = promo.get("code")
        user_data["promo_discount_percent"] = promo.get("percent_off")
        user_data["promo_expires_at"] = promo.get("expires_raw")

    created_user = UserRepository.create(db, user_data)
    UserSecurityRepository.ensure(db, created_user.id, email_verified=True)

    ProfileRepository.create(db, {
        "user_id": created_user.id,
        "name": created_user.name,
        "address": "",
        "phone": "",
        "country": "CA",
        "state": "ON",
    })

    if created_user.name and len(created_user.name) >= 3 and "@" not in created_user.name:
        KeywordRepository.create(db, {
            "id": generate_id(),
            "user_id": created_user.id,
            "value": created_user.name,
            "type": "name",
        })

    _audit_auth_event(
        db,
        "admin_user_created",
        request=None,
        user_id=created_user.id,
        email=created_user.email,
        detail={"created_by": user.get("iss") or "orchestrator", "promo": promo.get("code") if promo else None},
    )

    response_user = _serialize_user(
        created_user,
        type("SecurityState", (), {"email_verified": True, "two_fa_enabled": False})(),
    )
    if promo:
        response_user["promo_code"] = promo.get("code")
        response_user["promo_discount_percent"] = promo.get("percent_off")
        response_user["promo_expires_at"] = promo.get("expires_raw")

    return {"ok": True, "user": response_user}

@user_router.get("/{user_id}")
async def get_user(user_id: str, user: dict = Depends(require_service_auth()), db: Session = Depends(get_db)):
    """Get a specific user by ID"""
    user_data = UserRepository.get_by_id(db, user_id)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": _serialize_user(user_data)}


@user_router.patch("/{user_id}")
async def patch_user(
    user_id: str,
    payload: Dict[str, Any],
    user: dict = Depends(require_service_auth("orchestrator")),
    db: Session = Depends(get_db),
):
    """Update user record from orchestrator admin endpoints."""
    editable_fields = {
        "name",
        "is_admin",
        "is_active",
        "employee_number",
        "plan_id",
        "subscription_status",
    }
    update_data = {k: payload.get(k) for k in editable_fields if k in payload}
    if "employee_number" in update_data and isinstance(update_data.get("employee_number"), str):
        update_data["employee_number"] = update_data["employee_number"].strip() or None
    if not update_data:
        raise HTTPException(status_code=400, detail="No supported fields provided")

    updated = UserRepository.update(db, user_id, update_data)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True, "user": _serialize_user(updated)}

# Profile endpoints
@profile_router.get("/")
async def get_profile(user: dict = Depends(verify_user_request), db: Session = Depends(get_db)):
    """Get current user's profile"""
    profile_data = ProfileRepository.get_by_user_id(db, user["sub"])
    if not profile_data:
        # Return default profile if none exists
        return {
            "profile": {
                "user_id": user["sub"],
                "name": "",
                "address": "",
                "phone": "",
                "country": "CA",
                "state": "ON",
                "updated_at": now_iso(),
            }
        }
    return {"profile": profile_data.to_dict()}

@profile_router.put("/")
async def update_profile_endpoint(payload: ProfileBase, user: dict = Depends(verify_user_request), db: Session = Depends(get_db)):
    """Update current user's profile"""

    # Update user name if provided
    if payload.name:
        UserRepository.update(db, user["sub"], {"name": payload.name})
    
    # Update profile
    update_data = {
        "name": payload.name,
        "address": payload.address,
        "phone": payload.phone,
        "country": payload.country,
        "state": payload.state,
    }
    
    # Remove None values
    update_data = {k: v for k, v in update_data.items() if v is not None}
    
    updated_profile = ProfileRepository.update(db, user["sub"], update_data)
    if not updated_profile:
        updated_profile = ProfileRepository.create(db, {"user_id": user["sub"], **update_data})
    return {"profile": updated_profile.to_dict()}


@meta_router.get("/countries")
async def get_countries(user: dict = Depends(verify_user_request)):
    return {"countries": SUPPORTED_COUNTRIES}


@signature_router.get("")
async def get_signature(user: dict = Depends(verify_user_request), db: Session = Depends(get_db)):
    rec = SignatureRepository.get_latest_by_user_id(db, user["sub"])
    return {"signature": rec.to_dict() if rec else None}


@signature_router.post("")
async def upsert_signature(payload: SignatureBase, user: dict = Depends(verify_user_request), db: Session = Depends(get_db)):
    data_url = (payload.data_url or "").strip()
    full_name = (payload.full_name or "").strip()
    if not data_url.startswith("data:image/"):
        raise HTTPException(status_code=400, detail="Invalid signature image payload")
    if not full_name:
        raise HTTPException(status_code=400, detail="full_name is required")
    rec = SignatureRepository.upsert_for_user(db, user["sub"], data_url, full_name)
    return {"ok": True, "signature": rec.to_dict()}


@documents_router.get("/templates")
async def get_document_templates(user: dict = Depends(verify_user_request), db: Session = Depends(get_db)):
    profile_data = ProfileRepository.get_by_user_id(db, user["sub"])
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


@documents_router.get("")
async def list_documents(user: dict = Depends(verify_user_request), db: Session = Depends(get_db)):
    rows = DocumentRepository.list_by_user_id(db, user["sub"], limit=500)
    return {"documents": [r.to_dict() for r in rows]}


@documents_router.get("/{document_id}")
async def get_document(document_id: str, user: dict = Depends(verify_user_request), db: Session = Depends(get_db)):
    rec = DocumentRepository.get_by_id_for_user(db, document_id, user["sub"])
    if not rec:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"document": rec.to_dict()}


@documents_router.delete("/{document_id}")
async def delete_document(document_id: str, user: dict = Depends(verify_user_request), db: Session = Depends(get_db)):
    ok = DocumentRepository.delete_for_user(db, document_id, user["sub"])
    if not ok:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"ok": True}


@documents_router.post("/generate")
async def generate_document(payload: DocumentCreate, user: dict = Depends(verify_user_request), db: Session = Depends(get_db)):
    template = LEGAL_TEMPLATES.get(payload.template_id)
    if not template:
        raise HTTPException(status_code=400, detail="Unsupported template_id")

    user_db = UserRepository.get_by_id(db, user["sub"])
    profile_data = ProfileRepository.get_by_user_id(db, user["sub"])

    country = (profile_data.country if profile_data and profile_data.country else "CA").upper()
    country_cfg = SUPPORTED_COUNTRIES.get(country) or SUPPORTED_COUNTRIES["CA"]
    if country not in (template.get("jurisdictions") or []):
        raise HTTPException(status_code=400, detail="Template is not available for this country")

    finding_url = ""
    finding_data = ""
    recipient_broker = (payload.recipient_broker or "").strip()
    recipient_address = (payload.recipient_address or "").strip()
    if payload.finding_id:
        finding = db.query(Finding).filter(Finding.id == payload.finding_id, Finding.user_id == user["sub"]).first()
        if finding:
            finding_url = finding.url or ""
            finding_data = finding.data_found or ""
            recipient_broker = recipient_broker or finding.broker

    state_val = (profile_data.state if profile_data else "") or ""
    state_clause = f", {state_val}" if state_val else ""

    body = _fill_template(
        payload.template_id,
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
            "user_id": user["sub"],
            "template_id": payload.template_id,
            "finding_id": payload.finding_id,
            "recipient_broker": recipient_broker,
            "recipient_address": recipient_address,
            "country": country,
            "title": template.get("title") or payload.template_id,
            "body": body,
        },
    )
    return {"ok": True, "document": rec.to_dict()}


@documents_router.post("/sign")
async def sign_document(payload: Dict[str, Any], user: dict = Depends(verify_user_request), db: Session = Depends(get_db)):
    document_id = str(payload.get("document_id") or "").strip()
    if not document_id:
        raise HTTPException(status_code=400, detail="document_id is required")

    signature = SignatureRepository.get_latest_by_user_id(db, user["sub"])
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
        user["sub"],
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