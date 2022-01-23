import re
import requests

from api import OL_API


def clean_olid(olid):
    """
    Extract just the first work or edition olid from
    some olid-containing string.

    >>> clean_olid(None)
    ''
    >>> clean_olid('')
    ''
    >>> clean_olid('OL12345A,OL6789W')
    'OL6789W'
    >>> clean_olid('/books/OL13579M')
    'OL13579M'
    """
    if not olid:
        return ''
    olid = olid.upper()
    if olid.startswith('OL') and olid.endswith(('M', 'W')):
        return olid
    return re.findall(r'OL[0-9]+[MW]', olid)[0]


def get_one(olid):
    return get_many([olid]).get('olid', {})


def get_many(olids):
    if not olids:
        return {}
    q = 'key:(%s)' % ' OR '.join(
        '/%s/%s' % (
            'works' if olid.endswith('W') else 'editions',
            olid
        ) for olid in olids
    )
    url = '%s/search.json?q=%s&fields=*,availability' % (OL_API, q)
    r = requests.get(url)

    books = {}
    try:
        r.raise_for_status()
    except requests.exceptions.HTTPError:
        return books

    for doc in r.json().get('docs', {}):
        books[doc.get('key', '').split('/')[-1]] = doc
    return books

def fetch_work(olid):
    base_url = "https://openlibrary.org/works/{}".format(olid)
    response = requests.get(base_url + ".json")

    return {
        "title": response.json()["title"] if response.status_code == 200 else olid,
        "link": base_url
    }
