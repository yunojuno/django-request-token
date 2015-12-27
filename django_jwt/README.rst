django_jwt
----------

Django app that uses JWT to support access to restricted URLs.

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

* The link is being sent to a single user
* The recipient is a known Django User
* The token generated will only authenticate the initial request
* The token will *not* log the user in
* The link is not sensitive, and contains no sensitive data

As a real-world example, at YunoJuno we run a 'member-get-member' scheme. A
registered user can send out invitations to friends / colleagues to join. Each
invitation has a custom link, which is restricted to just one person. We can
use a tokenised URL to the public 'sign-up' form to enforce this. (NB in this
case we pre-generate the User object based on the information given to us, so
although the recipient has never registered, we know about them.)

Implementation
==============

The underlying technology used is JWT - see `jwt.io <https://jwt.io>`_ for more
details on the specifics. The summary is that it can be used to generate a Base64 encoded and signed token based on an arbitrary JSON payload. The signature is used to ensure that the payload has not been tampered with. The payload itself is not encrypted, and can be decoded by anyone - hence ensuring that no sensitive data is included. (NB You can encrypt the token, but the base assumption is that you're not sending sensitive data, you just want to ensure that the data you receive is the same data you sent.)

The implementation within Django consists of two parts: adding the token to a URL as it leaves the app (e.g. in an email), and then validating the token when someone clicks on the link and returns to the site.

In order to add the token, you need to create a new RequestToken object, and
then call the ``encode`` method on it. This will return the 3-part signed JWT
(header.payload.signature). You will need to initialise the token with the
recipient ``User``, and the target URL - to ensure that the token is only used
to access the intended endpoint.

..code ::python

    >>> from django_jwt.models import RequestToken
    >>> # create a new RequestToken, and encode the contents
    >>> token = RequestToken.objects.create(
            audience=User.objects.filter(...),
            target_url=reverse('foobar')
        ).encode()

    1234567.qwertyuiop.zxcvbnm
    >>>

You now have a token that is bound to a taget URL, and an intended recipient.
If a user (any user - remmember, we are *not* authenticating the end user) clicks on this URL, they will hit the endpoint as an unauthenticated user. If the URL requires authentication, the request will fail, as the user is not yet authenticated. In order to use the JWT instead of full authentication, we must add a decorator to the view function to expand out the token, verify it (against tampering, and in line with the "not before time" and "expiration time" attributes of the token payload) and then set the user.

.. code::python

    @user_passes_test(u.is_authenticated)
    def my_view(request):
        logging.debug("View is not executed")

    @verify_token
    @user_passes_test(u.is_authenticated):
        logging.debug("View is executed")

The ``verify_token`` function decorator is responsible for expanding the token according to the following rules:

1. Extract the token from the querystring if it exists
2. Verify the token matches the signature
3. Validate the token ``target_url`` matches the current ``request.path``
4. If the request is already authenticated, check that the request user and the token user match
5. If the token has a ``max_uses`` attribute, check that it hasn't been used too many times already
6. If all the above pass, then set the request.user to the token.user

At this point, we have set the ``request.user`` property, and so the request now resembles an authenticated request - and should pass any other relevant decorators.

The decorator does one more important task, once the function has run - it records the use of the token - extracting the source IP and user-agent from the request (for auditing purposes), and updating the token ``use_count`` property, along with the response status_code - this enables fine-grained reporting on the use of the tokens.

