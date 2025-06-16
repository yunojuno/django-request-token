## Supported versions

This project supports Django 4.2+ and Python 3.10+. The latest version supported is Django 5.2
running on Python 3.13.

## Django Request Token

Django app that uses JWT to manage one-time and expiring tokens to protect URLs.

This app currently requires the use of PostgreSQL.

### Background

This project was borne out of our experiences at YunoJuno with 'expiring links' - which is a common
use case of providing users with a URL that performs a single action, and may bypass standard
authentication. A well-known use of this is the ubiquitous 'unsubscribe' link you find at the bottom
of newsletters. You click on the link and it immediately unsubscribes you, irrespective of whether
you are already authenticated or not.

If you google "temporary url", "one-time link" or something similar you will find lots of
StackOverflow articles on supporting this in Django - it's pretty obvious, you have a dedicated
token url, and you store the tokens in a model - when they are used you expire the token, and it
can't be used again. This works well, but it falls down in a number of areas:

-   Hard to support multiple endpoints (views)

If you want to support the same functionality (expiring links) for more than one view in your
project, you either need to have multiple models and token handlers, or you need to store the
specific view function and args in the model; neither of these is ideal.

-   Hard to debug

If you use have a single token url view that proxies view functions, you need to store the function
name, args and it then becomes hard to support - when someone claims that they clicked on
`example.com/t/<token>`, you can't tell what that would resolve to without looking it up in the
database - which doesn't work for customer support.

-   Hard to support multiple scenarios

Some links expire, others have usage quotas - some have both. Links may be for use by a single user,
or multiple users.

This project is intended to provide an easy-to-support mechanism for 'tokenising' URLs without
having to proxy view functions - you can build well-formed Django URLs and views, and then add
request token support afterwards.

### Use Cases

This project supports three core use cases, each of which is modelled using the `login_mode`
attribute of a request token:

1. Public link with payload
2. ~~Single authenticated request~~ (DEPRECATED: use `django-visitor-pass`)
3. ~~Auto-login~~ (DEPRECATED: use `django-magic-link`)

**Public Link** (`RequestToken.LOGIN_MODE_NONE`)

In this mode (the default for a new token), there is no authentication, and no assigned user. The
token is used as a mechanism for attaching a payload to the link. An example of this might be a
custom registration or affiliate link, that renders the standard template with additional
information extracted from the token - e.g. the name of the affiliate, or the person who invited you
to register.

```python
# a token that can be used to access a public url, without authenticating
# as a user, but carrying a payload (affiliate_id).
token = RequestToken.objects.create_token(
    scope="foo",
    login_mode=RequestToken.LOGIN_MODE_NONE,
    data={
        'affiliate_id': 1
    }
)

...

@use_request_token(scope="foo")
function view_func(request):
    # extract the affiliate id from an token _if_ one is supplied
    affiliate_id = (
        request.token.data['affiliate_id']
        if hasattr(request, 'token')
        else None
    )
```

**Single Request** (`RequestToken.LOGIN_MODE_REQUEST`)

In Request mode, the request.user property is overridden by the user specified in the token, but
only for a single request. This is useful for responding to a single action (e.g. RSVP,
unsubscribe). If the user then navigates onto another page on the site, they will not be
authenticated. If the user is already authenticated, but as a different user to the one in the
token, then they will receive a 403 response.

```python
# this token will identify the request.user as a given user, but only for
# a single request - not the entire session.
token = RequestToken.objects.create_token(
    scope="foo",
    login_mode=RequestToken.LOGIN_MODE_REQUEST,
    user=User.objects.get(username="hugo")
)

...

@use_request_token(scope="foo")
function view_func(request):
    assert request.user == User.objects.get(username="hugo")
```

**Auto-login** (`RequestToken.LOGIN_MODE_SESSION`)

This is the nuclear option, and must be treated with extreme care. Using a Session token will
automatically log the user in for an entire session, giving the user who clicks on the link full
access the token user's account. This is useful for automatic logins. A good example of this is the
email login process on medium.com, which takes an email address (no password) and sends out a login
link.

Session tokens have a default expiry of ten minutes.

```python
# this token will log in as the given user for the entire session -
# NB use with caution.
token = RequestToken.objects.create_token(
    scope="foo",
    login_mode=RequestToken.LOGIN_MODE_SESSION,
    user=User.objects.get(username="hugo")
)
```

### Implementation

The project contains middleware and a view function decorator that together validate request tokens
added to site URLs.

**request_token.models.RequestToken** - stores the token details

Step 1 is to create a `RequestToken` - this has various attributes that can be used to modify its
behaviour, and mandatory property - `scope`. This is a text value - it can be anything you like - it
is used by the function decorator (described below) to confirm that the token given matches the
function being called - i.e. the `token.scope` must match the function decorator scope kwarg:

```python
token = RequestToken(scope="foo")

# this will raise a 403 without even calling the function
@use_request_token(scope="bar")
def incorrect_scope(request):
    pass

# this will call the function as expected
@use_request_token(scope="foo")
def correct_scope(request):
    pass
```

The token itself - the value that must be appended to links as a querystring argument - is a JWT -
and comes from the `RequestToken.jwt()` method. For example, if you were sending out an email, you
might render the email as an HTML template like this:

```html
{% if token %}
    <a href="{{url}}?rt={{token.jwt}}>click here</a>
{% else %}
    <a href="{{url}}">click here</a>
{% endif %}
```

If you haven't come across JWT before you can find out more on the [jwt.io](https://jwt.io/)
website. The token produced will include the following JWT claims (available as the property
`RequestToken.claims`:

-   `max`: maximum times the token can be used
-   `sub`: the scope
-   `mod`: the login mode
-   `jti`: the token id
-   `aud`: (optional) the user the token represents
-   `exp`: (optional) the expiration time of the token
-   `iat`: (optional) the time the token was issued
-   `ndf`: (optional) the not-before-time of the token

**request_token.models.RequestTokenLog** - stores usage data for tokens

Each time a token is used successfully, a log object is written to the database. This provided an
audit log of the usage, and it stores client IP address and user agent, so can be used to debug
issues. This can be disabled using the `REQUEST_TOKEN_DISABLE_LOGS` setting. The logs table can be
maintained using the management command as described below.

**request_token.middleware.RequestTokenMiddleware** - decodes and verifies tokens

The `RequestTokenMiddleware` will look for a querystring token value (the argument name defaults to
'rt' and can overridden using the `JWT_QUERYSTRING_ARG` setting), and if it finds one it will verify
the token (using the JWT decode verification). If the token is verified, it will fetch the token
object from the database and perform additional validation against the token attributes. If the
token checks out it is added to the incoming request as a `token` attribute. This way you can add
arbitrary data (stored on the token) to incoming requests.

If the token has a user specified, then the `request.user` is updated to reflect this. The
middleware must run after the Django auth middleware, and before any custom middleware that inspects
/ monkey-patches the `request.user`.

If the token cannot be verified it returns a 403.

**request_token.decorators.use_request_token** - applies token permissions to views

A function decorator that takes one mandatory kwargs (`scope`) and one optional kwargs (`required`).
The `scope` is used to match tokens to view functions - it's just a straight text match - the value
can be anything you like, but if the token scope is 'foo', then the corresponding view function
decorator scope must match. The `required` kwarg is used to indicate whether the view **must** have
a token in order to be used, or not. This defaults to False - if a token **is** provided, then it
will be validated, if not, the view function is called as is.

If the scopes do not match then a 403 is returned.

If required is True and no token is provided the a 403 is returned.

### Installation

Download / install the app using pip:

```shell
pip install django-request-token
```

Add the app `request_token` to your `INSTALLED_APPS` Django setting:

```python
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
```

Add the middleware to your settings, **after** the standard authentication middleware, and before
any custom middleware that uses the `request.user`.

```python
MIDDLEWARE_CLASSES = [
    # default django middleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'request_token.middleware.RequestTokenMiddleware',
]
```

You can now add `RequestToken` objects, either via the shell (or within your app) or through the
admin interface. Once you have added a `RequestToken` you can add the token JWT to your URLs (using
the `jwt()` method):

```python
>>> token = RequestToken.objects.create_token(scope="foo")
>>> url = "https://example.com/foo?rt=" + token.jwt()
```

You now have a request token enabled URL. You can use this token to protect a view function using
the view decorator:

```python
@use_request_token(scope="foo")
function foo(request):
    pass
```

NB The 'scope' argument to the decorator is used to bind the function to the incoming token - if
someone tries to use a valid token on another URL, this will return a 403.

**NB this currently supports only view functions - not class-based views.**

### Management commands

There is a single management command, `truncate_request_token_log` which can be used to manage the
size of the log table (each token usage is logged to the database). It supports two arguments -
`--max-count` and `--max-days` which are self-explanatory:

```
$ python manage.py truncate_request_token_log --max-count=100
Truncating request token log records:
-> Retaining last 100 request token log records
-> Truncating request token log records from 2021-08-01 00:00:00
-> Truncating 0 request token log records.
$
```

### Settings

-   `REQUEST_TOKEN_QUERYSTRING`

The querystring argument name used to extract the token from incoming requests, defaults to **rt**.

-   `REQUEST_TOKEN_EXPIRY`

Session tokens have a default expiry interval, specified in minutes. The primary use case (above)
dictates that the expiry should be no longer than it takes to receive and open an email, defaults to
**10** (minutes).

-   `REQUEST_TOKEN_403_TEMPLATE`

Specifying the 403-template so that for prettyfying the 403-response, in production with a setting
like:

```python
FOUR03_TEMPLATE = os.path.join(BASE_DIR,'...','403.html')
```

-   `REQUEST_TOKEN_DISABLE_LOGS`

Set to `True` to disable the creation of `RequestTokenLog` objects on each use of a token. This is
not recommended in production, as the auditing of token use is a valuable part of the library.

### Tests

There is a set of `tox` tests.

### License

MIT

### Contributing

This is by no means complete, however, it's good enough to be of value, hence releasing it. If you
would like to contribute to the project, usual Github rules apply:

1. Fork the repo to your own account
2. Submit a pull request
3. Add tests for any new code
4. Follow coding style of existing project

### Acknowledgements

@jpadilla for [PyJWT](https://github.com/jpadilla/pyjwt/)
