__author__ = 'aviraldg'

import datetime
from zipfile import ZipFile, ZIP_STORED, ZIP_DEFLATED
from StringIO import StringIO
deflate = True
try:
    import zlib
except ImportError:
    deflate = False

from flask import render_template
from .models import User, Item

def generate_zip(username):
    u = User.query(User.username == username).fetch(1)

    if u:
        u = u[0]
    else:
        return None

    blobfile = StringIO()
    try:
        with ZipFile(blobfile, 'w', [ZIP_STORED, ZIP_DEFLATED][deflate]) as zf:
            zf.writestr('README.txt', render_template('datalib/README.txt', user=u, date=datetime.datetime.now()))
            for item in Item.query(Item.seller_id == str(u.key.id())).iter():
                zf.writestr('items/' + '%s-%s.html' % (item.key.id(), item.slug),
                            render_template('datalib/item.html', item=item))


        return blobfile.getvalue()
    finally:
        blobfile.close()
