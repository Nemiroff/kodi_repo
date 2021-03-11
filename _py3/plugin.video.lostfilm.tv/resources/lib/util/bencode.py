# The contents of this file are subject to the BitTorrent Open Source License
# Version 1.1 (the License).  You may not copy or use this file, in either
# source code or executable form, except in compliance with the License.  You
# may obtain a copy of the License at http://www.bittorrent.com/license/.
#
# Software distributed under the License is distributed on an AS IS basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied.  See the License
# for the specific language governing rights and limitations under the
# License.

# Written by Petru Paler

class BTFailure(Exception):
    pass

def to_binary(s):
    if isinstance(s, bytes):
        return s
    if isinstance(s, str):
        return s.encode('utf-8', 'strict')
    raise TypeError("expected binary or text (found %s)" % type(s))

def decode_int(x, f):
    # type: (bytes, int) -> Tuple[int, int]
    f += 1
    newf = x.index(b'e', f)
    n = int(x[f:newf])
    if x[f:f+1] == b'-':
        if x[f+1:f+2] == b'0':
            raise ValueError
    elif x[f:f+1] == b'0' and newf != f+1:
        raise ValueError
    return n, newf+1

def decode_string(x, f, kind='value'):
    # type: (bytes, int) -> Tuple[bytes, int]
    colon = x.index(b':', f)
    n = int(x[f:colon])
    if x[f:f+1] == b'0' and colon != f+1:
        raise ValueError
    colon += 1
    s = x[colon:colon+n]
    try:
        return s.decode('utf-8'), colon + n
    except UnicodeDecodeError:
        return bytes(s), colon+n

def decode_list(x, f):
    # type: (bytes, int) -> Tuple[List, int]
    r, f = [], f+1
    while x[f:f+1] != b'e':
        v, f = decode_func[x[f:f+1]](x, f)
        r.append(v)
    return r, f + 1

def decode_dict(x, f):
    f += 1
    r = {}
    while x[f:f+1] != b'e':
        k, f = decode_string(x, f, kind='key')
        r[k], f = decode_func[x[f:f+1]](x, f)
    return r, f + 1

decode_func  = {}
decode_func[b'l'] = decode_list
decode_func[b'i'] = decode_int
decode_func[b'0'] = decode_string
decode_func[b'1'] = decode_string
decode_func[b'2'] = decode_string
decode_func[b'3'] = decode_string
decode_func[b'4'] = decode_string
decode_func[b'5'] = decode_string
decode_func[b'6'] = decode_string
decode_func[b'7'] = decode_string
decode_func[b'8'] = decode_string
decode_func[b'9'] = decode_string
decode_func[b'd'] = decode_dict

def bdecode(x):
    try:
        value = to_binary(x)
        data, length = decode_func[value[0:1]](value, 0)
    except (IndexError, KeyError, ValueError):
        raise BTFailure("not a valid bencoded string")
    if length != len(value):
        raise BTFailure("invalid bencoded value (data after valid prefix)")
    return data