.. image:: https://travis-ci.org/yunojuno/django-expiring-links.svg
    :target: https://travis-ci.org/yunojuno/django-expiring-links

django-request-token
--------------------

Django app that uses JWT to manage one-time and expiring tokens to protected URLs.

Background
==========

Use Cases
=========

This library supports three core use cases, each of which is modelled using
the ``login_mode`` attribute of a request token:

1. Public link with payload
2. Single authenticated request
3. Auto-login

**Public Link** (``login_mode==RequestToken.LOGIN_MODE_NONE``)

In this mode (the default for a new token), there is no authentication, and no
assigned user ('aud' claim). The token is used as a mechanism for attaching a payload
to the link. An example of this might be a custom registration or affiliate link,
that renders the standard template with additional information extracted from
the token - e.g. the name of the affiliate, or the person who invited you to
register.

**Single Request** (``login_mode==RequestToken.LOGIN_MODE_REQUEST``)

In Request mode, the request.user property is overridden by the user specified
in the token, but only for a single request. This is useful for responding to
a single action (e.g. RSVP, unsubscribe). If the user then navigates onto another
page on the site, they will not be authenticated. If the user is already
authenticated, but as a different user to the one in the token, then they will
receive a 403 response.

**Auto-login** (``login_mode==RequestToken.LOGIN_MODE_SESSION``)

This is the nuclear option, and must be treated with extreme care. Using a
Session token will automatically log the user in for an entire session, giving
the user who clicks on the link full access the token user's account. This is
useful for automatic logins. A good example of this is the email login process
on medium.com, which takes an email address (no password) and sends out a login
link.

Session tokens must be single-use, and have a fixed expiry of one minute.

Implementation
==============

TODO

* RequestToken model - hold token details
* Middleware - decodes and verifies tokens
* Decorator - applies token permissions to views

Settings
========

``JWT_QUERYSTRING_ARG``

The default querystring argument name used to extract the token from incoming
requests.

String, defaults to **token**

``JWT_SESSION_TOKEN_EXPIRY``

Session tokens have a fixed expiry interval (i.e. you can't set a Session token
to expire in a day), specified in minutes. The primary use case (above) dictates
that the expiry should be no longer than it takes to receive and open an email.

Integer, defaults to **1** (minute).

Logging
=======

TODO

Tests
=====

TODO

Licence
=======

MIT

Contributing
============

TODO

Acknowledgements
================

@jpadilla for PyJWT
