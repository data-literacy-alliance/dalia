"""Email backend that sends through the SMTP2GO HTTP API using ``requests``.

Redirects are never followed, TLS verification is always on, and neither the API
key, the payload nor the response body ever reaches exception text or logs.
"""

import base64
import re

import requests
from django.core.mail.backends.base import BaseEmailBackend
from django.views.decorators.debug import sensitive_variables
from mailing.exceptions import Smtp2goError

DEFAULT_API_URL = "https://api.smtp2go.com/v3/email/send"
DEFAULT_TIMEOUT = (3.1, 10)
API_KEY_HEADER = "X-Smtp2go-Api-Key"
MAX_ERROR_CODE_LENGTH = 64
_ERROR_CODE_RE = re.compile(r"^[A-Za-z0-9_.\-]+$")


class EmailBackend(BaseEmailBackend):
    @sensitive_variables("api_key")
    def __init__(
        self,
        api_key=None,
        api_url=DEFAULT_API_URL,
        timeout=DEFAULT_TIMEOUT,
        fail_silently=False,
        **kwargs,
    ):
        # fail_silently is accepted for the Django API but never suppresses errors.
        super().__init__(fail_silently=False, **kwargs)
        if not api_key:
            raise ValueError("api_key is required")
        self._api_key = api_key
        self.api_url = api_url
        self.timeout = timeout

    @sensitive_variables("headers")
    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        # Build every payload first so a bad header aborts before any request.
        payloads = [self._build_payload(m) for m in email_messages]
        headers = {
            API_KEY_HEADER: self._api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        for payload in payloads:
            self._post(payload, headers)
        return len(payloads)

    def _post(self, payload, headers):
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=self.timeout,
                allow_redirects=False,
            )
        except requests.RequestException:
            raise Smtp2goError(None, None) from None
        status = response.status_code
        data = self._response_data(response)
        error_code = self._clean_error_code(data.get("error_code") if data else None)
        if not 200 <= status < 300:
            raise Smtp2goError(status, error_code)
        if data is None or not data.get("succeeded"):
            raise Smtp2goError(status, error_code)

    def _response_data(self, response):
        """Return the ``data`` dict of the JSON response or None if absent/invalid."""
        try:
            body = response.json()
        except ValueError:
            return None
        data = body.get("data") if isinstance(body, dict) else None
        return data if isinstance(data, dict) else None

    def _clean_error_code(self, value):
        if not isinstance(value, str) or len(value) > MAX_ERROR_CODE_LENGTH:
            return None
        if not _ERROR_CODE_RE.match(value) or self._api_key in value:
            return None
        return value

    def _build_payload(self, message):
        payload = {
            "sender": message.from_email,
            "to": list(message.to),
            "subject": message.subject,
            "text_body": message.body,
        }
        if message.cc:
            payload["cc"] = list(message.cc)
        if message.bcc:
            payload["bcc"] = list(message.bcc)
        html = self._html_body(message)
        if html is not None:
            payload["html_body"] = html
        custom_headers = self._custom_headers(message)
        if custom_headers:
            payload["custom_headers"] = custom_headers
        attachments = [self._attachment(a) for a in message.attachments]
        if attachments:
            payload["attachments"] = attachments
        return payload

    @staticmethod
    def _html_body(message):
        for content, mimetype in getattr(message, "alternatives", None) or []:
            if mimetype == "text/html":
                return content
        if getattr(message, "content_subtype", "plain") == "html":
            return message.body
        return None

    @staticmethod
    def _custom_headers(message):
        headers = dict(message.extra_headers or {})
        if message.reply_to:
            headers["Reply-To"] = ", ".join(message.reply_to)
        result = []
        for name, value in headers.items():
            name, value = str(name), str(value)
            if any(c in text for text in (name, value) for c in "\r\n"):
                raise Smtp2goError(None, None)
            result.append({"header": name, "value": value})
        return result

    @staticmethod
    def _attachment(attachment):
        if isinstance(attachment, (tuple, list)):
            filename, content, mimetype = attachment
        else:  # MIMEBase instance
            filename = attachment.get_filename()
            content = attachment.get_payload(decode=True)
            mimetype = attachment.get_content_type()
        if isinstance(content, str):
            content = content.encode("utf-8")
        return {
            "filename": filename or "attachment",
            "fileblob": base64.b64encode(content).decode("ascii"),
            "mimetype": mimetype or "application/octet-stream",
        }
