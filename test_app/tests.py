# -*- coding: utf-8 -*-
"""request_token decorator tests."""
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.urlresolvers import reverse
from django.test import TransactionTestCase, Client

from request_token.models import RequestToken, RequestTokenLog
from request_token.settings import JWT_QUERYSTRING_ARG, JWT_SESSION_TOKEN_EXPIRY


def get_url(url_name, token):
    """Helper to format urls with tokens."""
    url = reverse('testing:%s' % url_name)
    if token:
        url += '?%s=%s' % (JWT_QUERYSTRING_ARG, token.jwt())
    return url


class ViewTests(TransactionTestCase):

    """Test the end-to-end use of tokens.

    These tests specifically confirm the way in which request and session tokens
    deal with repeated requests.

    """

    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user('zoidberg')

    def test_request_token(self):
        """Test the request tokens only set the user for a single request."""
        token = RequestToken.objects.create_token(
            scope="foo",
            max_uses=2,
            user=self.user,
            login_mode=RequestToken.LOGIN_MODE_REQUEST
        )
        response = self.client.get(get_url('decorated', token))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request_user, self.user)
        self.assertEqual(RequestTokenLog.objects.count(), 1)

        response = self.client.get(get_url('undecorated', None))
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.request_user, AnonymousUser)
        self.assertEqual(RequestTokenLog.objects.count(), 1)

    def test_session_token(self):
        """Test that session tokens set the user for all requests."""
        token = RequestToken.objects.create_token(
            scope="foo",
            max_uses=1,
            user=self.user,
            login_mode=RequestToken.LOGIN_MODE_SESSION,
            expiration_time=(datetime.now() + timedelta(minutes=JWT_SESSION_TOKEN_EXPIRY))
        )

        response = self.client.get(get_url('decorated', token))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request_user, self.user)
        self.assertEqual(RequestTokenLog.objects.count(), 1)

        # for a session token, all future requests should also be authenticated
        response = self.client.get(get_url('undecorated', None))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request_user, self.user)
        self.assertEqual(RequestTokenLog.objects.count(), 1)
