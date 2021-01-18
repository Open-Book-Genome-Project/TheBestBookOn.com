
import requests
from flask import session
from internetarchive.config import get_auth_config
from internetarchive.exceptions import AuthenticationError

ol_url = 'https://openlibrary.org'


def is_admin(username):
    url = '%s/usergroup/bestbook_admins.json' % ol_url
    r = requests.get(url).json()
    admins = [member.get('key') for member in r.get('members', [])]
    return '/people/%s' % username in admins


def authenticate(email=None, password=None, s3_keys=None, expected_username=None):
    """
    :parm dict s3_keys: a dict {'secret': 'xxx', 'access': 'yyy'}
    :param str expected_username: expected username for account w/ s3_keys
    """
    username = None

    # We're logged in and thus authenticated
    try:
        if session.get('username'):
            username = session.get('username')
    except RuntimeError:
        # If we don't have web request ctx, skip to keys
        pass

    if not username and (email and password):
        email = email.replace(' ', '+')
        # May raise AuthenticationError
        response = get_auth_config(email, password)
        s3_keys = response.get('s3')

    if not username and s3_keys:
        # We now know the user's credentials are correct.
        # Next, we need to get their OpenLibrary username
        headers = {'Content-Type': 'application/json'}
        r = requests.post(
            '%s/account/login' % ol_url,
            headers=headers,
            json=s3_keys
        )
        username = r.cookies.get('session').split('/')[2].split('%2C')[0]

    if not username:
        raise AuthenticationError("Incorrect credentials")
    if expected_username and username != expected_username:
        raise AuthenticationError("Usernames don't match")
    return {
        'username': username,
        's3_keys': s3_keys
    }

def login(email, password):
    """Authenticates user and returns session"""
    try:
        user = authenticate(email=email, password=password)
        if user:
            session['username'] = user.get('username')
            session['s3'] = user.get('s3_keys')
            return user
    except AuthenticationError:
        return False
