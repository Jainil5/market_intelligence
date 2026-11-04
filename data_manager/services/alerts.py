from __future__ import annotations

import json
import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Any

import requests

logger = logging.getLogger(__name__)


def _count_failures(result: dict[str, Any]) -> int:
    failed = int(result.get("failed") or 0)
    for key in ("news", "announcements", "prices"):
        section = result.get(key)
        if isinstance(section, dict):
            failed += len(section.get("errors") or [])
            failed += int(section.get("failed") or 0)
    results = result.get("results")
    if isinstance(results, list):
        failed += sum(1 for row in results if row.get("status") == "error")
    if result.get("status") == "error":
        failed += 1
    return failed


def _slack_message(job_name: str, result: dict[str, Any], failures: int) -> str:
    return (
        f":warning: *Market Intelligence* `{job_name}` completed with *{failures}* failure(s).\n"
        f"```\n{json.dumps(result, default=str)[:3500]}\n```"
    )


def _send_slack(text: str) -> bool:
    webhook = os.getenv("ALERT_SLACK_WEBHOOK_URL", "").strip()
    if not webhook:
        return False
    response = requests.post(webhook, json={"text": text}, timeout=15)
    response.raise_for_status()
    return True


def _send_email(subject: str, body: str) -> bool:
    host = os.getenv("ALERT_SMTP_HOST", "").strip()
    to_addr = os.getenv("ALERT_EMAIL_TO", "").strip()
    from_addr = os.getenv("ALERT_EMAIL_FROM", "").strip()
    if not host or not to_addr or not from_addr:
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.set_content(body)
    port = int(os.getenv("ALERT_SMTP_PORT", "587"))
    user = os.getenv("ALERT_SMTP_USER", "").strip()
    password = os.getenv("ALERT_SMTP_PASSWORD", "").strip()
    with smtplib.SMTP(host, port, timeout=20) as smtp:
        smtp.starttls()
        if user and password:
            smtp.login(user, password)
        smtp.send_message(msg)
    return True


def notify_job_result(job_name: str, result: dict[str, Any]) -> dict[str, Any]:
    """Send alerts when a batch job reports failures. No-op if nothing failed or alerts disabled."""
    failures = _count_failures(result)
    if failures <= 0:
        return {"sent": False, "reason": "no_failures"}
    if os.getenv("ALERT_ON_FAILURE", "true").lower() not in {"1", "true", "yes", "on"}:
        return {"sent": False, "reason": "alerts_disabled"}

    text = _slack_message(job_name, result, failures)
    sent_channels: list[str] = []
    try:
        if _send_slack(text):
            sent_channels.append("slack")
    except Exception:
        logger.exception("Slack alert failed")

    try:
        if _send_email(f"Market Intelligence: {job_name} failures={failures}", text):
            sent_channels.append("email")
    except Exception:
        logger.exception("Email alert failed")

    if not sent_channels:
        logger.error("Job %s had %s failures but no alert channel is configured", job_name, failures)
        return {"sent": False, "reason": "no_channels_configured", "failures": failures}
    return {"sent": True, "channels": sent_channels, "failures": failures}
