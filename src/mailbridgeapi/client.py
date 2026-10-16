from __future__ import annotations

import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Mapping, Optional


class MailBridgeAPIError(RuntimeError):
    def __init__(
        self,
        message: str,
        status: int = 0,
        response: Optional[Mapping[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.response = dict(response or {})
        meta = self.response.get("meta")
        self.request_id = meta.get("request_id") if isinstance(meta, dict) else None


class MailBridgeAPI:
    def __init__(
        self,
        account_key: str,
        mailbox_key: str,
        *,
        base_url: str = "https://api.mailbridgeapi.com",
        timeout: float = 30.0,
    ) -> None:
        if not account_key or not mailbox_key:
            raise ValueError("account_key and mailbox_key are required.")
        self.account_key = account_key
        self.mailbox_key = mailbox_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def health(self) -> Dict[str, Any]:
        return self._request("GET", "/health/", authenticated=False)

    def mailbox_status(self) -> Dict[str, Any]:
        return self._request("GET", "/mailbox/status/")

    def mailbox_insights(self, days: int = 30) -> Dict[str, Any]:
        return self._request("GET", "/mailbox/insights/", query={"days": days})

    def send_email(self, **message: Any) -> Dict[str, Any]:
        for field in ("recipient_email", "mail_subject", "mail_body"):
            if not str(message.get(field, "")).strip():
                raise ValueError(f"{field} is required.")
        payload = {
            "apikey": self.account_key,
            "apikeybox": self.mailbox_key,
            **message,
        }
        response = self._request(
            "POST",
            "/sendemail/",
            data=payload,
            form=True,
            authenticated=False,
        )
        result = response.get("result", {})
        if str(result.get("error", "1")) != "0":
            raise MailBridgeAPIError(
                str(result.get("sent", "Email delivery failed.")),
                200,
                response,
            )
        return response

    def get_email(self, folder: str = "INBOX", start: int = 0) -> Dict[str, Any]:
        return self._request(
            "GET",
            "/getemail/",
            query={
                "apikey": self.account_key,
                "apikeybox": self.mailbox_key,
                "mbox": folder,
                "start": start,
            },
            authenticated=False,
        )

    def list_unsubscribed(self, email: Optional[str] = None) -> Dict[str, Any]:
        query: Dict[str, Any] = {
            "apikey": self.account_key,
            "apikeybox": self.mailbox_key,
        }
        if email:
            query["email"] = email
        return self._request(
            "GET",
            "/email/unsubscribed/",
            query=query,
            authenticated=False,
        )

    def list_sent(self, **filters: Any) -> Dict[str, Any]:
        return self._request("GET", "/email/sent/", query=filters)

    def list_received(self, **filters: Any) -> Dict[str, Any]:
        return self._request("GET", "/email/received/", query=filters)

    def get_message(self, direction: str, message_id: str) -> Dict[str, Any]:
        if direction not in ("sent", "received"):
            raise ValueError("direction must be sent or received.")
        return self._request(
            "GET",
            "/email/message/",
            query={"direction": direction, "id": message_id},
        )

    def search_emails(
        self,
        query_text: str,
        **filters: Any,
    ) -> Dict[str, Any]:
        if not query_text.strip():
            raise ValueError("query_text is required.")
        return self._request(
            "GET",
            "/email/search/",
            query={**filters, "query": query_text},
        )

    def activity(self, days: int = 30) -> Dict[str, Any]:
        return self._request("GET", "/email/activity/", query={"days": days})

    def validate_email(self, **message: Any) -> Dict[str, Any]:
        return self._request("POST", "/email/validate/", data=message)

    def _request(
        self,
        method: str,
        path: str,
        *,
        query: Optional[Mapping[str, Any]] = None,
        data: Optional[Mapping[str, Any]] = None,
        form: bool = False,
        authenticated: bool = True,
    ) -> Dict[str, Any]:
        url = self.base_url + "/" + path.lstrip("/")
        if query:
            values = {
                key: value
                for key, value in query.items()
                if value is not None and value != ""
            }
            url += "?" + urllib.parse.urlencode(values)

        headers = {"Accept": "application/json", "User-Agent": "mailbridgeapi-python/1.0"}
        if authenticated:
            headers["X-API-Key"] = self.account_key
            headers["X-Mailbox-Key"] = self.mailbox_key

        body: Optional[bytes] = None
        if data is not None:
            if form:
                body = urllib.parse.urlencode(data).encode("utf-8")
                headers["Content-Type"] = "application/x-www-form-urlencoded"
            else:
                body = json.dumps(data).encode("utf-8")
                headers["Content-Type"] = "application/json"

        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                status = int(response.status)
                raw = response.read()
        except urllib.error.HTTPError as error:
            status = int(error.code)
            raw = error.read()
        except (urllib.error.URLError, socket.timeout) as error:
            raise MailBridgeAPIError(f"MailBridgeAPI network error: {error}") from error

        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise MailBridgeAPIError(
                "MailBridgeAPI returned invalid JSON.",
                status,
            ) from error
        if not isinstance(decoded, dict):
            raise MailBridgeAPIError(
                "MailBridgeAPI returned an unexpected response.",
                status,
            )
        if status < 200 or status >= 300 or (
            authenticated and decoded.get("ok") is False
        ):
            error_data = decoded.get("error")
            message = (
                error_data.get("message", "MailBridgeAPI request failed.")
                if isinstance(error_data, dict)
                else "MailBridgeAPI request failed."
            )
            raise MailBridgeAPIError(str(message), status, decoded)
        return decoded

