def toSysTime(twoBytes):
    timeHigh = twoBytes[0] & 0x3F  # Take 6 bits
    timeLow = twoBytes[1] & 0x7F  # Tage 7 bits
    # Shift low timestamp one left
    timeLow = timeLow << 1
    # Shift one right again
    return int.from_bytes([timeHigh, timeLow], byteorder='big') >> 1

def toMidiTime(millis):
    newTime = (millis & 0x1FFF) << 1
    twoBytes = [(newTime >> i & 0xff) for i in (8, 0)]
    twoBytes[0] = twoBytes[0] & 0x3F  # Header and reserved bytes
    twoBytes[1] = twoBytes[1] >> 1
    return twoBytes