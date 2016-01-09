.. image:: https://travis-ci.org/yunojuno/django-expiring-links.svg
    :target: https://travis-ci.org/yunojuno/django-expiring-links

django-request-token
--------------------

Django app that uses JWT to manage one-time and expiring tokens to protected URLs.

Background
==========

This project was borne out of our experiences at YunoJuno with 'expiring links' -
which is a common use case of providing users with a URL that performs a single
action, and may bypass standard authentication. A well-known use of of this is
the ubiquitous 'unsubscribe' link you find at the bottom of newsletters. You click
on the link and it immediately unsubscribes you, irrespective of whether you are
already authenticated or not.

If you google "temporary url", "one-time link" or something similar you will find
lots of StackOverflow articles on supporting this in Django - it's pretty obvious,
you have a dedicated token url, and you store the tokens in a model - when they
are used you expire the token, and it can't be used again. This works well, but
it falls down in a number of areas:

* Hard to support multiple endpoints (views)

If you want to support the same functionality (expiring links) for more than
one view in your project, you either need to have multiple models and token
handlers, or you need to store the specific view function and args
in the model; neither of these is ideal.

* Hard to debug

If you use have a single token url view that proxies view functions, you need
to store the function name, args and it then becomes hard to support - when
someone claims that they clicked on example.com/t/<token>, you can't tell what
that would resolve to without looking it up in the database - which doesn't
work for customer support.

* Hard to support multiple scenarios

Some links expire, others have usage quotas - some have both. Links may be
for use by a single user, or multiple users.

This project is intended to provide an easy-to-support mechanism for 'tokenising'
URLs without having to proxy view functions - you can build well-formed Django
URLs and views, and then add request token support afterwards.

Use Cases
=========

This project supports three core use cases, each of which is modelled using
the ``login_mode`` attribute of a request token:

1. Public link with payload
2. Single authenticated request
3. Auto-login

**Public Link** (``RequestToken.LOGIN_MODE_NONE``)

In this mode (the default for a new token), there is no authentication, and no
assigned user ('aud' claim). The token is used as a mechanism for attaching a payload
to the link. An example of this might be a custom registration or affiliate link,
that renders the standard template with additional information extracted from
the token - e.g. the name of the affiliate, or the person who invited you to
register.

**Single Request** (``RequestToken.LOGIN_MODE_REQUEST``)

In Request mode, the request.user property is overridden by the user specified
in the token, but only for a single request. This is useful for responding to
a single action (e.g. RSVP, unsubscribe). If the user then navigates onto another
page on the site, they will not be authenticated. If the user is already
authenticated, but as a different user to the one in the token, then they will
receive a 403 response.

**Auto-login** (``RequestToken.LOGIN_MODE_SESSION``)

This is the nuclear option, and must be treated with extreme care. Using a
Session token will automatically log the user in for an entire session, giving
the user who clicks on the link full access the token user's account. This is
useful for automatic logins. A good example of this is the email login process
on medium.com, which takes an email address (no password) and sends out a login
link.

Session tokens must be single-use, and have a fixed expiry of one minute.

Implementation
==============

The project contains middleware and a view function decorator that together
validate request tokens added to site URLs.

**request_token.models.RequestToken** - stores the token details

Step 1 is to create a ``RequestToken`` - this has various attributes that can
be used to modify its behaviour, and mandatory property - ``scope``. This is a
text value - it can be anything you like - it is used by the function decorator
(described below) to confirm that the token given matches the function being
called.

**request_token.middleware.RequestTokenMiddleware** - decodes and verifies tokens

The ``RequestTokenMiddleware`` will look for a querystring token value, and if
it finds one it will verify the token (using the JWT decode verification). If
the token is verified, it will fetch the token object from the database and
perform additional validation against the token attributes. If the token checks
out it is added to the incoming request as a ``token`` attribute. This way you
can add arbitrary data (stored on the token) to incoming requests.

If the token has a user specified, then the ``request.user`` is updated to
reflect this. The middleware must run after the Django auth middleware, and
before any custom middleware that inspects / monkey-patches the ``request.user``.

If the token cannot be verified it returns a 403.

**request_token.decorators.use_request_token** - applies token permissions to views

The ``use_request_token`` decorator is used to indicate that a view function
supports request tokens. If a token is provided (as ``request.token``), then
the ``token.scope`` is matched against the scope specificed in the decorator.

If the scopes do not match then a 403 is returned.

If the scopes do match, the view function is executed as normal.

Installation
============

Download / install the app using pip:

.. code:: shell

    pip install django-request-token

Add the app ``request_token`` to your ``INSTALLED_APPS`` Django setting:

.. code:: python

    # settings.py
    INSTALLED_APPS = (
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'request_token',
        ...
    )

Add the middleware to your settings, **after** the standard authentication middleware,
and before any custom middleware that uses the ``request.user``.

.. code:: python

    MIDDLEWARE_CLASSES = [
        # default django middleware
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'request_token.middleware.RequestTokenMiddleware',
    ]

You can now add ``RequestToken`` objects, either via the shell (or within your
app) or through the admin interface. Once you have added a ``RequestToken`` you
can add the token JWT to your URLs (using the ``jwt()`` method):

.. code:: python

    >>> token = RequestToken.objects.create_token(scope="foo")
    >>> url = "https://example.com/foo?token=" + token.jwt()

You now have a request token enabled URL. You can use this token to protect a
view function using the view decorator:

.. code:: python

    @use_request_token(scope="foo")
    function foo(request):
        pass

NB The 'scope' argument to the decorator is used to bind the function to the
incoming token - if someone tries to use a valid token on another URL, this
will return a 403.

**NB this currently supports only view functions - not class-based views.**

Settings
========

``JWT_QUERYSTRING_ARG``

The default querystring argument name used to extract the token from incoming
requests.

String, defaults to **token**

``JWT_SESSION_TOKEN_EXPIRY``

Session tokens have a default expiry interval, specified in minutes.
The primary use case (above) dictates that the expiry should be no longer
than it takes to receive and open an email.

Integer, defaults to **1** (minute).

Logging
=======

Debugging middleware and decorators can be complex, so the project is verbose in
its logging (by design). If you feel it's providing too much logging, you can
adjust it by setting the standard Django logging for ``request_token``.

Tests
=====

There is a set of tests that are configured to run against Django 1.8 using ``tox``.

Licence
=======

MIT

Contributing
============

This is by no means complete - it can't cope with requirements that are anything other than '==',
and it doesn't (yet) help with updating the requirements file itself. However, it's good enough to
be of value, hence releasing it. If you would like to contribute to the project, usual Github rules
apply:

1. Fork the repo to your own account
2. Submit a pull request
3. Add tests for any new code
4. Follow coding style of existing project

Acknowledgements
================

@jpadilla for `PyJWT <https://github.com/jpadilla/pyjwt/>`_
