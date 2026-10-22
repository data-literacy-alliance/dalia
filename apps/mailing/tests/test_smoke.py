from mailing import exceptions


def test_smtp2go_error_message_has_status_and_code_only():
    exc = exceptions.Smtp2goError(status=400, error_code="E_ApiResponseCodeNotFound")
    assert str(exc) == "SMTP2GO HTTP 400 E_ApiResponseCodeNotFound"
    assert exc.status == 400
    assert exc.error_code == "E_ApiResponseCodeNotFound"
