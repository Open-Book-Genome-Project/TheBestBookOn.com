
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
        # This authenticates credentials or throws an error

        response = get_auth_config(email, password)

        # Here, we now know the user's credentials are correct.
        # Next, we need to get their OpenLibrary username
        session['username'] = email
        
        # Aasif, can you please look into how to get a patron's Open
        # Library username if they're logged in?
        return session['username']

    except AuthenticationError:
        return False

