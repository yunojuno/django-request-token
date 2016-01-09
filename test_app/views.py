# -*- coding:utf-8 -*-
from django.http import HttpResponse

from request_token.decorators import use_request_token


def undecorated(request):
    response = HttpResponse(u"Hello, %s" % request.user)
    response.request_user = request.user
    return response


@use_request_token(scope="foo")
def decorated(request):
    response = HttpResponse(u"Hello, %s" % request.user)
    response.request_user = request.user
    return response