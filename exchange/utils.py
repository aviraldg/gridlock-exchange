__author__ = 'aviraldg'

import re
from unicodedata import normalize

def secure_compare(s1, s2):
    """
    Avoid timing attacks by taking constant time for compares.
    """

    if len(s1) != len(s2):
        return False

    eq = True
    for i, j in zip(s1, s2):
        if i != j:
            eq = False
    return eq

punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')

def slugify(text, delim=u'-'):
    result = []
    for word in punct_re.split(text.lower()):
        word = normalize('NFKD', word).encode('ascii', 'ignore')
        if word:
            result.append(word)
    return unicode(delim.join(result))
