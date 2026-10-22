import base64
import logging
from unittest import mock

import pytest
import requests
from django.core.mail import EmailMessage, EmailMultiAlternatives
from mailing.backends.smtp2go import EmailBackend
from mailing.exceptions import Smtp2goError

KEY = "not-a-real-key"


def make_response(status=200, body=None, json_error=False):
    resp = mock.Mock()
    resp.status_code = status
    if json_error:
        resp.json.side_effect = ValueError("bad json")
    else:
        resp.json.return_value = (
            body if body is not None else {"data": {"succeeded": 1, "failed": 0}}
        )
    return resp


def backend(**kw):
    return EmailBackend(api_key=KEY, **kw)


def test_api_key_required():
    with pytest.raises(ValueError):
        EmailBackend()


@mock.patch("requests.post")
def test_payload_mapping(post):
    post.return_value = make_response()
    msg = EmailMultiAlternatives(
        "Subj",
        "plain",
        "from@example.org",
        ["to@example.org"],
        cc=["cc@example.org"],
        bcc=["bcc@example.org"],
        reply_to=["reply@example.org"],
        headers={"X-Custom": "yes"},
    )
    msg.attach_alternative("<p>html</p>", "text/html")
    msg.attach("a.txt", "hello", "text/plain")
    assert backend().send_messages([msg]) == 1
    payload = post.call_args.kwargs["json"]
    assert payload["sender"] == "from@example.org"
    assert payload["to"] == ["to@example.org"]
    assert payload["cc"] == ["cc@example.org"]
    assert payload["bcc"] == ["bcc@example.org"]
    assert payload["subject"] == "Subj"
    assert payload["text_body"] == "plain"
    assert payload["html_body"] == "<p>html</p>"
    assert {"header": "Reply-To", "value": "reply@example.org"} in payload["custom_headers"]
    assert {"header": "X-Custom", "value": "yes"} in payload["custom_headers"]
    att = payload["attachments"][0]
    assert att["filename"] == "a.txt"
    assert base64.b64decode(att["fileblob"]) == b"hello"
    assert att["mimetype"] == "text/plain"


@mock.patch("requests.post")
def test_key_in_header_not_body_and_call_kwargs(post):
    post.return_value = make_response()
    msg = EmailMessage("s", "b", "f@example.org", ["t@example.org"])
    backend(timeout=(3.1, 7)).send_messages([msg])
    kwargs = post.call_args.kwargs
    assert kwargs["headers"]["X-Smtp2go-Api-Key"] == KEY
    assert KEY not in repr(kwargs["json"])
    assert kwargs["allow_redirects"] is False
    assert kwargs["timeout"] == (3.1, 7)
    assert "verify" not in kwargs
    assert post.call_args.args[0] == "https://api.smtp2go.com/v3/email/send"


@mock.patch("requests.post")
def test_default_timeout_and_custom_url(post):
    post.return_value = make_response()
    msg = EmailMessage("s", "b", "f@example.org", ["t@example.org"])
    backend(api_url="https://eu-api.smtp2go.com/v3/email/send").send_messages([msg])
    assert post.call_args.kwargs["timeout"] == (3.1, 10)
    assert post.call_args.args[0] == "https://eu-api.smtp2go.com/v3/email/send"


@mock.patch("requests.post")
def test_one_request_per_message(post):
    post.return_value = make_response()
    msgs = [EmailMessage("s", "b", "f@example.org", ["t@example.org"]) for _ in range(3)]
    assert backend().send_messages(msgs) == 3
    assert post.call_count == 3


@mock.patch("requests.post")
def test_empty_list(post):
    assert backend().send_messages([]) == 0
    post.assert_not_called()


@pytest.mark.parametrize("status", [301, 302, 400, 401, 500, 503])
@mock.patch("requests.post")
def test_http_errors_raise(post, status):
    post.return_value = make_response(status, {"data": {"error_code": "E_Some_Code"}})
    msg = EmailMessage("s", "b", "f@example.org", ["t@example.org"])
    with pytest.raises(Smtp2goError) as info:
        backend().send_messages([msg])
    assert info.value.status == status
    assert info.value.error_code == "E_Some_Code"
    assert str(info.value) == f"SMTP2GO HTTP {status} E_Some_Code"


@mock.patch("requests.post", side_effect=requests.Timeout(f"timeout for {KEY}"))
def test_timeout_raises_without_details(post):
    msg = EmailMessage("s", "b", "f@example.org", ["t@example.org"])
    with pytest.raises(Smtp2goError) as info:
        backend().send_messages([msg])
    assert info.value.status is None
    assert KEY not in str(info.value)
    assert info.value.__cause__ is None


@mock.patch("requests.post")
def test_succeeded_zero_raises(post):
    post.return_value = make_response(
        200, {"data": {"succeeded": 0, "failed": 1, "error_code": "E_Fail"}}
    )
    msg = EmailMessage("s", "b", "f@example.org", ["t@example.org"])
    with pytest.raises(Smtp2goError) as info:
        backend().send_messages([msg])
    assert (info.value.status, info.value.error_code) == (200, "E_Fail")


@mock.patch("requests.post")
def test_invalid_json_raises(post):
    post.return_value = make_response(200, json_error=True)
    msg = EmailMessage("s", "b", "f@example.org", ["t@example.org"])
    with pytest.raises(Smtp2goError) as info:
        backend().send_messages([msg])
    assert info.value.status == 200


@mock.patch("requests.post")
def test_fail_silently_does_not_suppress(post):
    post.return_value = make_response(500)
    msg = EmailMessage("s", "b", "f@example.org", ["t@example.org"])
    with pytest.raises(Smtp2goError):
        backend(fail_silently=True).send_messages([msg])


@pytest.mark.parametrize(
    "kwargs",
    [
        {"reply_to": ["a@example.org\r\nBcc: evil@example.org"]},
        {"headers": {"X-Custom": "v\nInjected: 1"}},
        {"headers": {"X-Bad\r\nName": "v"}},
    ],
)
@mock.patch("requests.post")
def test_crlf_in_headers_rejected_before_sending(post, kwargs):
    msg = EmailMessage("s", "b", "f@example.org", ["t@example.org"], **kwargs)
    with pytest.raises(Smtp2goError):
        backend().send_messages([msg])
    post.assert_not_called()


@mock.patch("requests.post")
def test_bad_message_blocks_all_requests(post):
    post.return_value = make_response()
    good = EmailMessage("s", "b", "f@example.org", ["t@example.org"])
    bad = EmailMessage("s", "b", "f@example.org", ["t@example.org"], headers={"X": "a\nb"})
    with pytest.raises(Smtp2goError):
        backend().send_messages([good, bad])
    post.assert_not_called()


@mock.patch("requests.post")
def test_key_echoed_in_response_never_leaks(post, caplog):
    post.return_value = make_response(400, {"data": {"error_code": KEY}, "error": f"bad key {KEY}"})
    msg = EmailMessage("s", "b", "f@example.org", ["t@example.org"])
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(Smtp2goError) as info:
            backend().send_messages([msg])
    assert info.value.error_code is None
    assert KEY not in str(info.value)
    assert KEY not in caplog.text
