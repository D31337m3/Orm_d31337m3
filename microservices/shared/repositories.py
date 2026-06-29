"""
Client Index Repository
Handles database operations for user authentication and profiles
"""

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import logging
from shared.database import User, Profile, Keyword
from shared.database_models import generate_id, now_iso
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for user database operations"""

    @staticmethod
    def get_by_email(db: Session, email: str) -> User:
        """Get user by email"""
        return db.query(User).filter(User.email == email.lower()).first()

    @staticmethod
    def get_by_id(db: Session, user_id: str) -> User:
        """Get user by ID"""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def create(db: Session, user_data: dict) -> User:
        """Create new user"""
        try:
            user = User(
                id=user_data.get("id") or generate_id(),
                email=user_data.get("email", "").lower(),
                name=user_data.get("name"),
                password_hash=user_data.get("password_hash"),
                auth_provider=user_data.get("auth_provider", "password"),
                is_admin=user_data.get("is_admin", False),
                is_active=user_data.get("is_active", True),
                plan_id=user_data.get("plan_id"),
                subscription_status=user_data.get("subscription_status", "trial"),
                subscription_started_at=user_data.get("subscription_started_at"),
                promo_code=user_data.get("promo_code"),
                promo_discount_percent=user_data.get("promo_discount_percent"),
                promo_expires_at=user_data.get("promo_expires_at"),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"User created: {user.id} ({user.email})")
            return user
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Failed to create user: {e}")
            raise ValueError("Email already registered")
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating user: {e}")
            raise

    @staticmethod
    def update(db: Session, user_id: str, update_data: dict) -> User:
        """Update user"""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return None

            for key, value in update_data.items():
                if hasattr(user, key) and key not in ["id", "created_at"]:
                    setattr(user, key, value)

            user.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(user)
            logger.info(f"User updated: {user.id}")
            return user
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating user: {e}")
            raise

    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 100):
        """List all users with pagination"""
        return db.query(User).offset(skip).limit(limit).all()

    @staticmethod
    def delete(db: Session, user_id: str) -> bool:
        """Delete user"""
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            db.delete(user)
            db.commit()
            logger.info(f"User deleted: {user_id}")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting user: {e}")
            raise


class ProfileRepository:
    """Repository for user profile database operations"""

    @staticmethod
    def get_by_user_id(db: Session, user_id: str) -> Profile:
        """Get profile by user ID"""
        return db.query(Profile).filter(Profile.user_id == user_id).first()

    @staticmethod
    def create(db: Session, profile_data: dict) -> Profile:
        """Create new profile"""
        try:
            profile = Profile(
                user_id=profile_data.get("user_id"),
                name=profile_data.get("name"),
                address=profile_data.get("address", ""),
                phone=profile_data.get("phone", ""),
                country=profile_data.get("country", "CA"),
                state=profile_data.get("state"),
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)
            logger.info(f"Profile created for user: {profile.user_id}")
            return profile
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating profile: {e}")
            raise

    @staticmethod
    def update(db: Session, user_id: str, update_data: dict) -> Profile:
        """Update profile"""
        try:
            profile = db.query(Profile).filter(Profile.user_id == user_id).first()
            if not profile:
                return None

            for key, value in update_data.items():
                if hasattr(profile, key) and key != "user_id":
                    setattr(profile, key, value)

            profile.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(profile)
            logger.info(f"Profile updated for user: {user_id}")
            return profile
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating profile: {e}")
            raise


class KeywordRepository:
    """Repository for keyword database operations"""

    @staticmethod
    def get_by_id(db: Session, keyword_id: str) -> Keyword:
        """Get keyword by ID"""
        return db.query(Keyword).filter(Keyword.id == keyword_id).first()

    @staticmethod
    def get_by_user(db: Session, user_id: str) -> list:
        """Get all keywords for a user"""
        return db.query(Keyword).filter(Keyword.user_id == user_id).all()

    @staticmethod
    def create(db: Session, keyword_data: dict) -> Keyword:
        """Create new keyword"""
        try:
            keyword = Keyword(
                id=keyword_data.get("id") or generate_id(),
                user_id=keyword_data.get("user_id"),
                value=keyword_data.get("value"),
                type=keyword_data.get("type", "name"),
            )
            db.add(keyword)
            db.commit()
            db.refresh(keyword)
            logger.info(f"Keyword created: {keyword.id} for user {keyword.user_id}")
            return keyword
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating keyword: {e}")
            raise

    @staticmethod
    def update(db: Session, keyword_id: str, update_data: dict) -> Keyword:
        """Update keyword"""
        try:
            keyword = db.query(Keyword).filter(Keyword.id == keyword_id).first()
            if not keyword:
                return None

            for key, value in update_data.items():
                if hasattr(keyword, key) and key not in ["id", "user_id", "created_at"]:
                    setattr(keyword, key, value)

            db.commit()
            db.refresh(keyword)
            return keyword
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating keyword: {e}")
            raise

    @staticmethod
    def delete(db: Session, keyword_id: str) -> bool:
        """Delete keyword"""
        try:
            keyword = db.query(Keyword).filter(Keyword.id == keyword_id).first()
            if not keyword:
                return False
            db.delete(keyword)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting keyword: {e}")
            raise
