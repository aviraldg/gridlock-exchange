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
from .models import UserProfile, Item

def generate_zip(id):
    user_profile = UserProfile.get_by_id(id)
    if not user_profile:
        return None

    blobfile = StringIO()
    try:
        with ZipFile(blobfile, 'w', [ZIP_STORED, ZIP_DEFLATED][deflate]) as zf:
            zf.writestr('README.txt', render_template('datalib/README.txt', user_profile=user_profile, date=datetime.datetime.now()))
            for item in Item.query(Item.seller_id == user_profile.get_id()).iter():
                zf.writestr('items/' + '%s-%s.html' % (item.key.id(), item.slug),
                            render_template('datalib/item.html', item=item))


        return blobfile.getvalue()
    finally:
        blobfile.close()
