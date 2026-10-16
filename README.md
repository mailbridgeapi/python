# MailBridgeAPI for Python

Official dependency-free Python client for all public MailBridgeAPI endpoints.

## Requirements

- Python 3.9 or newer
- A MailBridgeAPI account key and mailbox key

## Installation

```bash
pip install mailbridgeapi
```

Until the first PyPI release, install directly from this GitHub repository.

## Send an email

```python
import os
from mailbridgeapi import MailBridgeAPI

mail = MailBridgeAPI(
    os.environ["MAILBRIDGE_ACCOUNT_KEY"],
    os.environ["MAILBRIDGE_MAILBOX_KEY"],
)

result = mail.send_email(
    recipient_email="customer@example.com",
    mail_subject="Order update",
    mail_body="<p>Your order is ready.</p>",
    format="html",
    from_source="python-application",
)

print(result["result"]["id"])
```

## Read and monitor

```python
status = mail.mailbox_status()
received = mail.list_received(per_page=10)
errors = mail.list_sent(status="error")
activity = mail.activity(days=30)
matches = mail.search_emails("order 12345", direction="all")
```

See the [complete API documentation](https://github.com/mailbridgeapi/mailbridgeapi).

## Security

Load API keys from environment variables or a secret manager. Do not put them in source control, browser code, mobile binaries, logs, or screenshots.

