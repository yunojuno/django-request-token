django_jwt_expiringlinks
------------------------

Django app that uses JWT to manage one-time and expiring links to protected URLs.

Use Case
========

The primary use case for this app is authenticating users on a per-
request basis, without having to log in to the site first.

The canonical example of this would be unsubscribing from mailing lists -
you want to be able to identify the user, and process the request,
but requiring the user to log in first presents a barrier.

Using JWT we can 'pre-authenticate' access to the URL.

Assumptions
===========

This is not a general purpose link-generating app - it has some implicit
assumptions built-in:

* The link is being sent to a single user, or everyone
* The link will only support GET methods
* If a single recipient, they exist as a Django User object
* The token generated will only authenticate the initial request
* The token will *not* log the user in or bind them to a session
* The view endpoint URL is not sensitive, and contains no sensitive data

Implementation
==============

TODO

* RequestToken model - hold token details
* Middleware - decodes and verifies tokens
* Decorator - applies token permissions to views

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