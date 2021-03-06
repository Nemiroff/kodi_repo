import six


# -*- coding: utf-8 -*-


def equal_dicts(d1, d2, ignore_keys):
    ignored = set(ignore_keys)
    for k1, v1 in six.iteritems(d1):
        if k1 not in ignored and (k1 not in d2 or not d2[k1] == v1):
            return False
    for k2, v2 in six.iteritems(d2):
        if k2 not in ignored and k2 not in d1:
            return False
    return True
