
import requests
from api import graph
from configs import AUTH_SERVER


def authenticate(email, password):
    r = requests.post('%s/authorize' % AUTH_SERVER, data={'email': email, 'password': password})
    resp = r.json()
    if 'http_error_code' not in resp:
        return resp
    raise Exception(resp['msg'])


def login(email, password):
    """Authenticates user and returns session"""
    resp = authenticate(email, password)
    if 'http_error_code' not in resp and 'session' in resp:
        s = resp.get('session')
        email = s.get('email')
        if not email:
            raise Exception("Account corrupt, has no email")

        try:
            u = graph.User.get(email=email)
        except Exception as e:
            username = s.get('username')
            u = graph.User(email=email, username=username)
            u.create()

        s['username'] = u.username
        s['id'] = u.id
        s['logged'] = True
        return s
    raise Exception(resp['msg'])

