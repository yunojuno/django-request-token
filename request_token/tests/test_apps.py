# -*- coding: utf-8 -*-
from django.template import TemplateDoesNotExist
from django.test import TestCase

from ..apps import check_template, ImproperlyConfigured
from ..compat import mock


class AppTests(TestCase):

    """Tests for request_token.apps functions."""

    @mock.patch('django.template.loader.get_template')
    def test_check_403(self, mock_loader):
        mock_loader.side_effect = TemplateDoesNotExist("Template not found.")
        self.assertRaises(ImproperlyConfigured, check_template, 'foo.html')
