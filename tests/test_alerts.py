from unittest.mock import patch

from data_manager.services.alerts import notify_job_result


def test_alert_skipped_when_no_failures():
    result = notify_job_result("update_prices", {"failed": 0, "updated": 3})
    assert result["sent"] is False
    assert result["reason"] == "no_failures"


def test_alert_when_failures_without_channels():
    result = notify_job_result("update_prices", {"failed": 2, "results": [{"status": "error"}]})
    assert result["sent"] is False
    assert result["reason"] == "no_channels_configured"


def test_alert_slack_sent(monkeypatch):
    monkeypatch.setenv("ALERT_SLACK_WEBHOOK_URL", "https://hooks.example.test/slack")
    with patch("data_manager.services.alerts.requests.post") as mock_post:
        mock_post.return_value.raise_for_status = lambda: None
        result = notify_job_result("update_stocks", {"failed": 1})
    assert result["sent"] is True
    assert "slack" in result["channels"]
    mock_post.assert_called_once()
