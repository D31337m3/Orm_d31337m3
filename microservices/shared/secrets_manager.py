"""
Infisical Secrets Manager Integration
Replaces direct environment variable loading with secure secret retrieval from Infisical
"""

import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_secrets_cache: Dict[str, str] = {}
_initialized = False


def _build_client(cfg: "InfisicalConfig"):
    """Create an Infisical client compatible with either SDK variant."""
    # Legacy SDK variant
    try:
        from infisical_python import InfisicalClient as LegacyClient  # type: ignore

        client_kwargs: Dict[str, Any] = {
            "site_url": cfg.site_url,
            "environment": cfg.environment,
        }

        if cfg.service_token:
            client_kwargs["token"] = cfg.service_token
        elif cfg.client_id and cfg.client_secret:
            client_kwargs["client_id"] = cfg.client_id
            client_kwargs["client_secret"] = cfg.client_secret
        else:
            return None

        return LegacyClient(**client_kwargs)
    except ImportError:
        pass

    # Current SDK variant
    try:
        from infisical_client import InfisicalClient, ClientSettings  # type: ignore

        settings_kwargs: Dict[str, Any] = {
            "site_url": cfg.site_url,
        }
        if cfg.service_token:
            settings_kwargs["access_token"] = cfg.service_token
        elif cfg.client_id and cfg.client_secret:
            settings_kwargs["client_id"] = cfg.client_id
            settings_kwargs["client_secret"] = cfg.client_secret
        else:
            return None

        return InfisicalClient(ClientSettings(**settings_kwargs))
    except ImportError:
        raise


def _list_secrets(client, cfg: "InfisicalConfig"):
    """List secrets across both SDK variants and normalize to an iterable."""
    if hasattr(client, "list_secrets"):
        return client.list_secrets(
            environment=cfg.environment,
            path=cfg.secrets_path,
            project_id=cfg.project_id,
        )

    from infisical_client import schemas  # type: ignore

    opts = schemas.ListSecretsOptions(
        environment=cfg.environment,
        project_id=cfg.project_id,
        path=cfg.secrets_path,
    )
    return client.listSecrets(opts)


def _extract_secret_fields(secret) -> tuple[Optional[str], Optional[str]]:
    """Extract secret key/value across SDK response shapes."""
    key = getattr(secret, "secret_key", None) or getattr(secret, "secretKey", None)
    val = getattr(secret, "secret_value", None) or getattr(secret, "secretValue", None)
    return key, val


@dataclass
class InfisicalConfig:
    site_url: str = field(default_factory=lambda: os.environ.get("INFISICAL_SITE_URL", "https://app.infisical.com"))
    client_id: Optional[str] = field(default_factory=lambda: os.environ.get("INFISICAL_CLIENT_ID"))
    client_secret: Optional[str] = field(default_factory=lambda: os.environ.get("INFISICAL_CLIENT_SECRET"))
    service_token: Optional[str] = field(default_factory=lambda: os.environ.get("INFISICAL_SERVICE_TOKEN"))
    project_id: str = field(default_factory=lambda: os.environ.get("INFISICAL_PROJECT_ID", ""))
    environment: str = field(default_factory=lambda: os.environ.get("INFISICAL_ENVIRONMENT", "prod"))
    secrets_path: str = field(default_factory=lambda: os.environ.get("INFISICAL_SECRETS_PATH", "/"))


def init_infisical(config: Optional[InfisicalConfig] = None) -> None:
    global _initialized, _secrets_cache

    if _initialized:
        return

    cfg = config or InfisicalConfig()

    if not cfg.project_id:
        logger.warning("INFISICAL_PROJECT_ID is empty. Falling back to environment variables.")
        return

    try:
        client = _build_client(cfg)

        if not client:
            logger.warning(
                "No Infisical credentials configured. "
                "Falling back to environment variables. "
                "Set INFISICAL_SERVICE_TOKEN or INFISICAL_CLIENT_ID/INFISICAL_CLIENT_SECRET."
            )
            return

        secrets = _list_secrets(client, cfg)

        for secret in secrets:
            key, value = _extract_secret_fields(secret)
            if key is not None and value is not None:
                _secrets_cache[key] = value

        _initialized = True
        logger.info(
            f"Infisical initialized successfully. Loaded {len(_secrets_cache)} secrets "
            f"from project {cfg.project_id}/{cfg.environment}"
        )

    except ImportError:
        logger.warning(
            "No supported Infisical SDK installed. "
            "Install with: pip install infisical-python"
        )
    except Exception as e:
        logger.error(f"Failed to initialize Infisical: {e}")
        logger.warning("Falling back to environment variables for secrets.")


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    if key in _secrets_cache:
        return _secrets_cache[key]
    return os.environ.get(key, default)


def load_service_secrets(service_name: str) -> Dict[str, str]:
    cfg = InfisicalConfig()
    if not cfg.project_id:
        return {}

    secrets_path = f"/{service_name}" if cfg.secrets_path == "/" else f"{cfg.secrets_path}/{service_name}"

    try:
        client = _build_client(cfg)

        if not client:
            return {}

        # Use temporary config to target a service-specific path.
        service_cfg = InfisicalConfig(
            site_url=cfg.site_url,
            client_id=cfg.client_id,
            client_secret=cfg.client_secret,
            service_token=cfg.service_token,
            project_id=cfg.project_id,
            environment=cfg.environment,
            secrets_path=secrets_path,
        )
        service_secrets = _list_secrets(client, service_cfg)

        result = {}
        for secret in service_secrets:
            key, value = _extract_secret_fields(secret)
            if key is not None and value is not None:
                result[key] = value
                _secrets_cache[key] = value

        return result

    except Exception as e:
        logger.error(f"Failed to load secrets for service '{service_name}': {e}")
        return {}
