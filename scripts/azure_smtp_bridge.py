#!/usr/bin/env python3
"""SMTP bridge that forwards inbound mail to Azure Communication Email.

Run this on the host and point Mailcow relayhost at it. The bridge reads
AZURE_COMM_EMAIL_CONNECTION_STRING and AZURE_COMM_EMAIL_SENDER from Infisical
via the repository secret loader.
"""

from __future__ import annotations

import asyncore
import logging
import os
import smtpd
import sys
from email import policy
from email.parser import BytesParser
from typing import List, Tuple

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MICROSERVICES_DIR = os.path.join(ROOT_DIR, "microservices")
if MICROSERVICES_DIR not in sys.path:
    sys.path.insert(0, MICROSERVICES_DIR)

from shared.secrets_manager import init_infisical, get_secret  # noqa: E402


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("azure_smtp_bridge")


def _pick_text_parts(data) -> Tuple[str, str]:
    msg = BytesParser(policy=policy.default).parsebytes(data if isinstance(data, (bytes, bytearray)) else str(data).encode("utf-8", errors="ignore"))
    plain_parts: List[str] = []
    html_parts: List[str] = []

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            try:
                content = part.get_content()
            except Exception:
                continue
            if not isinstance(content, str):
                content = str(content)
            if part.get_content_type() == "text/html":
                html_parts.append(content)
            elif part.get_content_type() == "text/plain":
                plain_parts.append(content)
    else:
        try:
            content = msg.get_content()
        except Exception:
            content = msg.get_payload(decode=True)
            if isinstance(content, (bytes, bytearray)):
                content = content.decode("utf-8", errors="replace")
        if msg.get_content_type() == "text/html":
            html_parts.append(str(content))
        else:
            plain_parts.append(str(content))

    plain_text = "\n\n".join(part.strip() for part in plain_parts if part and part.strip())
    html_text = "\n\n".join(part.strip() for part in html_parts if part and part.strip())
    return plain_text, html_text


def _send_via_azure(mailfrom: str, rcpttos: List[str], data) -> None:
    connection_string = get_secret("AZURE_COMM_EMAIL_CONNECTION_STRING")
    if not connection_string:
        raise RuntimeError("AZURE_COMM_EMAIL_CONNECTION_STRING not configured in Infisical")

    from azure.communication.email import EmailClient  # type: ignore

    sender = get_secret("AZURE_COMM_EMAIL_SENDER", "DoNotReply@d31337m3.com") or "DoNotReply@d31337m3.com"
    message = BytesParser(policy=policy.default).parsebytes(data if isinstance(data, (bytes, bytearray)) else str(data).encode("utf-8", errors="ignore"))
    subject = str(message.get("subject") or "(no subject)")
    plain_text, html_text = _pick_text_parts(data)

    content = {"subject": subject, "plainText": plain_text or subject}
    if html_text:
        content["html"] = html_text

    azure_message = {
        "senderAddress": sender,
        "recipients": {"to": [{"address": addr} for addr in rcpttos]},
        "content": content,
    }

    client = EmailClient.from_connection_string(connection_string)
    poller = client.begin_send(azure_message)
    result = poller.result()
    logger.info("forwarded email via Azure message_id=%s to=%s", getattr(result, "message_id", None), ",".join(rcpttos))


class AzureSMTPBridge(smtpd.SMTPServer):
    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
        try:
            _send_via_azure(mailfrom, list(rcpttos or []), data)
            return None
        except Exception as exc:
            logger.exception("Failed to forward mail from %s to %s: %s", mailfrom, rcpttos, exc)
            return f"451 4.3.0 temporary failure: {exc}"


def main() -> int:
    host = os.environ.get("AZURE_SMTP_BRIDGE_HOST", "0.0.0.0")
    port = int(os.environ.get("AZURE_SMTP_BRIDGE_PORT", "2525"))

    if not init_infisical():
        logger.warning("Infisical init failed; bridge will still start and may work once secrets are available.")

    server = AzureSMTPBridge((host, port), None, decode_data=True)
    logger.info("Azure SMTP bridge listening on %s:%s", host, port)
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        logger.info("Azure SMTP bridge shutting down")
    finally:
        try:
            server.close()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())