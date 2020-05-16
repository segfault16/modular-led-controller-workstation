# MIDI Sysex specification for MOLECOLE

## General

Each midi sysex message consists of
- Midi Sysex start `0xF0`
- Vendor ID?
- Request/Response ID
- Data
- Midi Sysex end `0xF7`

### Binary data encode/decode

The number of usable bits for each byte in sysex midi is limited to 7 bits (a 1 in the most significant bit would terminate the sysex message).

Therefore bytes are grouped into packages of 7 bytes, followed by an additional byte encoding the most significant bit of each byte.

Example:

`0x00 0xA1 0xB2 0xC3 0xD4 0xE5 0xF6`

will be encoded to:
- `0x00` -> `0x00` (`0 0 ? ? ? ? ? ?`)
- `0xA1` -> `0x21` (`0 0 1 ? ? ? ? ?`)
- `0xB2` -> `0x32` (`0 0 1 1 ? ? ? ?`)
- `0xC3` -> `0x43` (`0 0 1 1 1 ? ? ?`)
- `0xD4` -> `0x54` (`0 0 1 1 1 1 ? ?`)
- `0xE5` -> `0x65` (`0 0 1 1 1 1 1 ?`)
- `0xF6` -> `0x76` (`0 0 1 1 1 1 1 1`)
- `0x3F`

followed by `0xf7` for Midi Sysex End.


In case the data doesn't need the entire block, the byte encoding the most significant bits will be added before the Midi Sysex End byte.

Example:
`0x00 0xA1`

will be encoded to:
- `0x00` -> `0x00` (`0 0 ? ? ? ? ? ?`)
- `0xA1` -> `0x21` (`0 0 1 ? ? ? ? ?`)
- `0x20`

followed by `0xf7` for Midi Sysex End.

| REQ/RESP | Request name                            | ID             | Data                                                                  | Description         |
| -------- | --------------------------------------- | -------------- | --------------------------------------------------------------------- | ------------------- |
| REQ      | Get Version                             | `0x00`, `0x00` |                                                                       |                     |
| RESP     | Get Version                             | `0x00`, `0x00` | Binary data encode of utf8 version string                             |                     |
| REQ      | Check update Version                    | `0x00`, `0x11` |                                                                       |                     |
| RESP     | Check update Version                    | `0x00`, `0x11` | Binary data encode of utf8 version string of available update version | Update available    |
| RESP     | Check update Version                    | `0x00`, `0x1F` |                                                                       | No update available |
| REQ      | Update server                           | `0x00`, `0x10` |                                                                       |                     |
| RESP     | Update server                           | `0x00`, `0x10` |                                                                       | Update successful   |
| RESP     | Update server                           | `0x00`, `0x10` |                                                                       | No update available |
| REQ      | Get active project                      | `0x00`, `0x20` |                                                                       |                     |
| RESP     | Get active project                      | `0x00`, `0x20` | Binary data encode of utf8 active project metadata json               |                     |
| REQ      | Get projects                            |                |                                                                       |                     |
| REQ      | Activate project                        |                |                                                                       |                     |
| REQ      | Export project                          |                |                                                                       |                     |
| REQ      | Import project                          |                |                                                                       |                     |
| REQ      | Get available scenes in project         |                |                                                                       |                     |
| REQ      | Get active scene                        |                |                                                                       |                     |
| REQ      | Get enabled controller for active scene |                |                                                                       |                     |