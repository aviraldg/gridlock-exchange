__author__ = 'aviraldg'

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
