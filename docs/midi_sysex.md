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

| REQ/RESP | Request name                               | ID             | Data                                                                  | Description                  |
| -------- | ------------------------------------------ | -------------- | --------------------------------------------------------------------- | ---------------------------- |
| REQ      | Get Version                                | `0x00`, `0x00` |                                                                       |                              |
| RESP     | Get Version                                | `0x00`, `0x00` | Binary data encode of utf8 version string                             |                              |
| REQ      | Check update Version                       | `0x00`, `0x11` |                                                                       |                              |
| RESP     | Check update Version                       | `0x00`, `0x11` | Binary data encode of utf8 version string of available update version | Update available             |
| RESP     | Check update Version                       | `0x00`, `0x1E` |                                                                       | Busy, try later              |
| RESP     | Check update Version                       | `0x00`, `0x1F` |                                                                       | No update available          |
| REQ      | Update server                              | `0x00`, `0x10` |                                                                       |                              |
| RESP     | Update server                              | `0x00`, `0x10` |                                                                       | Update successful            |
| RESP     | Update server                              | `0x00`, `0x1E` |                                                                       | Busy, try later              |
| RESP     | Update server                              | `0x00`, `0x1F` |                                                                       | No update available          |
| REQ      | Get active project                         | `0x00`, `0x20` |                                                                       |                              |
| RESP     | Get active project                         | `0x00`, `0x20` | Binary data encode of utf8 active project metadata json               |                              |
| REQ      | Get projects                               | `0x00`, `0x30` |                                                                       |                              |
| RESP     | Get projects                               | `0x00`, `0x30` | Binary data encode of utf8 projects metadata json                     |                              |
| REQ      | Activate project                           | `0x00`, `0x40` | Binary data encode of utf8 project id                                 |                              |
| RESP     | Activate project                           | `0x00`, `0x40` |                                                                       | Successful                   |
| RESP     | Activate project                           | `0x00`, `0x4F` |                                                                       | Project not found            |
| REQ      | Import project                             | `0x00`, `0x50` | Binary data encode of utf8 project json compressed with zlib          |                              |
| RESP     | Import project                             | `0x00`, `0x50` |                                                                       | Successful                   |
| RESP     | Import project                             | `0x00`, `0x5F` |                                                                       | Error                        |
| REQ      | Export project                             | `0x00`, `0x60` |                                                                       |                              |
| RESP     | Export project                             | `0x00`, `0x60` | Binary data encode of utf8 project json compressed with zlib          |                              |
| RESP     | Export project                             | `0x00`, `0x6F` |                                                                       | Project not found            |
| REQ      | Delete project                             | `0x00`, `0x70` | Binary data encode of utf8 project id                                 |                              |
| RESP     | Delete project                             | `0x00`, `0x70` |                                                                       | Successful                   |
| RESP     | Delete project                             | `0x00`, `0x7F` |                                                                       | Project not found            |
| REQ      | Get active scene ID                        | `0x01`, `0x00` |                                                                       |                              |
| RESP     | Get active scene ID                        | `0x01`, `0x00` | Binary data encode of utf8 active scene ID string                     |                              |
| REQ      | Get active scene                           | `0x01`, `0x10` |                                                                       |                              |
| RESP     | Get active scene                           | `0x01`, `0x10` | Binary data encode of utf8 active scene metadata json                 |                              |
| REQ      | Get scenes                                 | `0x01`, `0x20` |                                                                       |                              |
| RESP     | Get scenes                                 | `0x01`, `0x20` | Binary data encode of utf8 scene metadata json                        |                              |
| REQ      | Get enabled controller for active scene    | `0x01`, `0x30` |                                                                       |                              |
| RESP     | Get enabled controller for active scene    | `0x01`, `0x30` | Binary data encode of utf8 json dict controller -> True/False         |                              |
| REQ      | Request controller values for active scene | `0x01`, `0x40` |                                                                       | Response on corresponding CC |
| REQ      | Get server configuration                   | `0x02`, `0x00` |                                                                       |                              |
| RESP     | Get server configuration                   | `0x02`, `0x00` | Binary data encode of utf8 server config json compressed with zlib    |                              |
| REQ      | Update server configuration                | `0x02`, `0x10` | Binary data encode of utf8 server config json compressed with zlib    |                              |
| RESP     | Update server configuration                | `0x02`, `0x10` |                                                                       | Successful                   |
| RESP     | Update server configuration                | `0x02`, `0x1F` |                                                                       | Error                        |
| REQ      | Get audio rms                              | `0x02`, `0x20` |                                                                       |                              |
| RESP     | Get audio rms                              | `0x02`, `0x20` | Binary data encode of uft8 json dict channel -> rms of last chunk     |                              |