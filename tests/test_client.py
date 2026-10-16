import json
import unittest
from unittest.mock import patch

from mailbridgeapi import MailBridgeAPI, MailBridgeAPIError


class FakeResponse:
    def __init__(self, data, status=200):
        self.data = json.dumps(data).encode()
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return self.data


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.client = MailBridgeAPI("account_test", "mailbox_test")

    @patch("urllib.request.urlopen")
    def test_mailbox_status_uses_headers(self, urlopen):
        urlopen.return_value = FakeResponse({"ok": True, "data": {}, "meta": {}})
        self.client.mailbox_status()
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("X-api-key"), "account_test")
        self.assertEqual(request.get_header("X-mailbox-key"), "mailbox_test")

    @patch("urllib.request.urlopen")
    def test_send_email_uses_legacy_fields(self, urlopen):
        urlopen.return_value = FakeResponse(
            {"result": {"error": "0", "sent": "OK", "id": "message_1"}}
        )
        result = self.client.send_email(
            recipient_email="customer@example.com",
            mail_subject="Hello",
            mail_body="Test",
        )
        request = urlopen.call_args.args[0]
        body = request.data.decode()
        self.assertIn("apikey=account_test", body)
        self.assertIn("apikeybox=mailbox_test", body)
        self.assertEqual(result["result"]["id"], "message_1")

    @patch("urllib.request.urlopen")
    def test_delivery_error_is_raised(self, urlopen):
        urlopen.return_value = FakeResponse(
            {"result": {"error": "1", "sent": "smtp_error"}}
        )
        with self.assertRaises(MailBridgeAPIError):
            self.client.send_email(
                recipient_email="customer@example.com",
                mail_subject="Hello",
                mail_body="Test",
            )


if __name__ == "__main__":
    unittest.main()

