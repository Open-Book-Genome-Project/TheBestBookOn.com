
import requests
from flask import session
from internetarchive.config import get_auth_config
from internetarchive.exceptions import AuthenticationError


def login(email, password):
    """Authenticates user and returns session"""

    email = email.replace(' ', '+')

    # We're already logged in, so return a True value
    if session.get('username'):
        return session.get('username')

    try:
        response = get_auth_config(email, password)
        
        # We now know the user's credentials are correct.
        # Next, we need to get their OpenLibrary username        
        headers = {'Content-Type': 'application/json'}
        r = requests.post('https://openlibrary.org/account/login', headers=headers, json=response.get('s3'))
        username = r.cookies.get('session').split('/')[2].split('%2C')[0]        
        session['username'] = username
        return username

    except AuthenticationError:
        return False

