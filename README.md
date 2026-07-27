# MiniOS Configurator 3.0.0

GTK3 application for editing MiniOS `live-config` settings. It uses a
category-based interface with change tracking, validation, reset, and a
password-redacted review before saving.

## Features

- User identity, encrypted user/root passwords, locale, timezone, and keyboard
- Boot target and systemd or SysV service configuration
- Security profiles and independently editable sudo, PolicyKit, SSH, XRDP, X11,
  password-hint, and screen-lock settings
- User-directory linking or bind mounting on writable MiniOS media
- Current-system and keyboard detection without automatic persistence
- Atomic dirty-only saves preserving comments, ordering, unknown keys,
  ownership, permissions, and extended attributes

## Usage

```bash
minios-configurator
minios-configurator /path/to/config.conf
minios-configurator -i /path/to/config.conf
```

`-i`/`--inherit-cmdline` overlays recognized `/proc/cmdline` settings in the
editor. The selected file remains the save target. Unknown kernel parameters
are ignored.

The default file is `/etc/live/config.conf`. Saving requires PolicyKit
authentication. The application rejects symlinks and non-regular target files
and never changes the running system directly.

## Settings

Main setting groups:

- User: `LIVE_USERNAME`, `LIVE_USER_FULLNAME`, `LIVE_USER_DEFAULT_GROUPS`,
  encrypted user/root passwords, `LIVE_LINK_USER_DIRS`, `LIVE_BIND_USER_DIRS`,
  and `LIVE_USER_DIRS_PATH`
- System: `LIVE_CONFIG_NOROOT`, `LIVE_HOSTNAME`, `LIVE_LOCALES`,
  `LIVE_TIMEZONE`, `DEFAULT_TARGET`, `ENABLE_SERVICES`, and `DISABLE_SERVICES`
- Security: `LIVE_SUDO_MODE`, `LIVE_POLKIT_MODE`, `LIVE_SSH_*`,
  `LIVE_XRDP_MODE`, `LIVE_X11_MODE`, `LIVE_ISSUE_PASSWORD_HINTS`, and
  `LIVE_LOCKSCREEN_MODE`
- Keyboard: `LIVE_KEYBOARD_MODEL`, `LIVE_KEYBOARD_LAYOUTS`,
  `LIVE_KEYBOARD_OPTIONS`, and `LIVE_KEYBOARD_VARIANTS`
- Advanced: `LIVE_MODULE_MODE`, `LIVE_CONFIG_CMDLINE`, `LIVE_CONFIG_DEBUG`, and
  `EXPORT_LOGS`

Security profiles fill the concrete security controls. The profile name is not
written as a runtime configuration key, and every filled value remains editable.

Supported mode values include:

- `DEFAULT_TARGET`: `graphical.target`, `multi-user.target`, `rescue.target`
- `LIVE_MODULE_MODE`: `simple`, `merged`
- `LIVE_SUDO_MODE`, `LIVE_POLKIT_MODE`: `passwordless`, `password`, `disabled`
- `LIVE_XRDP_MODE`: `relaxed`, `hardened`, `disabled`
- `LIVE_X11_MODE`, `LIVE_LOCKSCREEN_MODE`: `relaxed`, `hardened`

## Applicability

Hostname, locale, timezone, services, keyboard, boot controls, user-media, and
log export affect the existing installation after reboot. Account creation,
passwords, `noroot`, and security posture are one-shot settings used when a new
session is created. Each control shows its applicability in the interface.

User-directory link and bind modes are mutually exclusive. They require a safe
media-relative path and are unavailable with `toram`, `toram=full`, or
`toram=trim`. Two populated directory trees are never merged automatically.

`perchmode` and `perchsize` are boot-time persistence parameters and are not
saved by the configurator. When `perchmode=luks` is present, the application
only reports whether `/run/initramfs/etc/minios-initramfs-crypt` exists; it does
not create, open, resize, or unlock persistence containers.

## Build

```bash
make build
sudo make install
```

Runtime requirements are defined in `debian/control`, including Python 3.6+,
GTK3/PyGObject, PolicyKit, `minios-live-config`, and
`python3-minios-security`.

## License

GPL-3.0+
