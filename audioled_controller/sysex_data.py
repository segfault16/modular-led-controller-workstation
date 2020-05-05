def encode(data):
    """
    Encodes a byte-array for use in midi sysex (msb of each byte must be 0, 8th byte encodes msbs of 7 preceding bytes)
    """
    if isinstance(data, str):
        data = data.encode('utf8')
    ret = []
    cnt = 0
    msbs = 0
    for d in data:
        # Most significant bit
        msb = d & 0x80
        # Least significant bits
        enc = d & 0x7F
        ret.append(enc)
        if msb:
            msbs = msbs | 1 << (7 - cnt - 1)
        if cnt == 6:
            ret.append(msbs)
            msbs = 0
            cnt = 0
        else:
            cnt = cnt + 1
    if cnt != 0:
        ret.append(msbs)
    return ret

def decode(data):
    """
    Decodes a byte-array used in midi sysex
    """
    ret = []
    while len(data) >= 8:
        msbs = data[7]
        for i in range(7):
            d = data[i]
            if msbs & 1 << (7 - i - 1):
                d = d | 0x80
            ret.append(d)
        data = data[8:]

    if len(data) > 0:
        msbs = data[-1]
        for i in range(len(data) - 1):
            d = data[i]
            if msbs & 1 << (7 - i - 1):
                d = d | 0x80
            ret.append(d)
    return ret