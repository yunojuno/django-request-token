from __future__ import annotations

from unittest import mock

import pytest
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory

from request_token.commands import log_token_use, parse_xff, request_meta
from request_token.models import RequestToken


@pytest.mark.django_db
def test_log_token_use(rf: RequestFactory) -> None:
    token = RequestToken().save()
    request = rf.get("/")
    request.user = AnonymousUser()
    request.META = {
        "HTTP_X_FORWARDED_FOR": None,
        "REMOTE_ADDR": "192.168.0.1",
        "HTTP_USER_AGENT": "magical device",
    }
    response = HttpResponse("foo", status=123)

    log = log_token_use(token, request, response.status_code)
    assert token.logs.count() == 1
    assert log.user is None
    assert log.token == token
    assert log.user_agent == "magical device"
    assert log.client_ip == "192.168.0.1"
    assert log.status_code == 123
    assert token.used_to_date == 1


@pytest.mark.django_db
def test_log_token_use__disabled(rf: RequestFactory) -> None:
    token = RequestToken().save()
    request = rf.get("/")
    request.user = AnonymousUser()
    request.META = {}
    response = HttpResponse("foo", status=123)

    with mock.patch("request_token.commands.DISABLE_LOGS", lambda: True):
        log = log_token_use(token, request, response.status_code)
        assert log is None
        assert not token.logs.exists()


@pytest.mark.parametrize(
    "remote_addr,xff,client_ip",
    [
        ("192.168.0.1", "", "192.168.0.1"),
        ("192.168.0.1", "192.168.0.2", "192.168.0.2"),
        ("192.168.0.1", "192.168.0.2,192.168.0.3", "192.168.0.2"),
    ],
)
def test_request_meta__client_ip(
    rf: RequestFactory, remote_addr: str, xff: str, client_ip: str
) -> None:
    request = rf.get("/")
    request.user = AnonymousUser()
    request.META = {"HTTP_X_FORWARDED_FOR": xff, "REMOTE_ADDR": remote_addr}
    meta = request_meta(request)
    assert meta["client_ip"] == client_ip


@pytest.mark.django_db
@pytest.mark.parametrize(
    "input, output",
    [
        (None, None),
        ("", ""),
        ("foo", "foo"),
        ("foo, bar, baz", "foo"),
        ("foo , bar, baz", "foo"),
        ("8.8.8.8, 123.124.125.126", "8.8.8.8"),
    ],
)
def test_parse_xff(input: str, output: str) -> None:  # noqa: A002
    assert parse_xff(input) == output
