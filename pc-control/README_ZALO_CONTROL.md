# Zalo Control Channel

Command bus for the Zalo personal project uses GitHub Issues, not `command.json`.

Trusted command issues must:
- be created by `nguyenlinhns-arch`
- have title beginning `[ZALO-CONTROL]`
- use one of: `PING`, `RESTART_DESKTOP_COMMANDER`, `ZALO_STATUS`, `ZALO_CLASSIFY_OLD`

This avoids command collisions with other PC-control projects.
