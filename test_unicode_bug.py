import datetime
import subprocess
import os

# from django.conf import settings
from urlparse import urlparse

# tika = urlparse(settings.TIKA_SERVER)
tika = urlparse('http://localhost:9998')

from httplib import HTTPConnection, HTTPSConnection
if tika.scheme == 'http':
    conn = HTTPConnection(tika.netloc, None, True, 30)
elif tika.scheme == 'https':
    conn = HTTPSConnection(tika.netloc, None, True, 30)
else:
    raise Exception("Unknown URL scheme '%s' in Apache Tika URL: %s" %
        (tika.scheme, settings.TIKA_SERVER))

buffer = open('fixtures/smartquote-bullet.docx', 'rb')

conn.request('PUT', '%s/tika' % tika.path, buffer)
response = conn.getresponse()

if response.status != 200:
    raise Exception("Unknown response from TIKA server " +
        "(%s): %s: %s" % (settings.TIKA_SERVER, response.status,
            response.reason))

from django.utils.encoding import force_unicode
print force_unicode(response.read())
