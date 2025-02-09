% MINIOS_CONFIGURATOR(1) MiniOS Live Manual

## NAME
**MiniOS Configuration** - Configure MiniOS parameters via `/etc/minios/minios.conf`.

## SYNOPSIS
Modifies the `/etc/minios/minios.conf` file using the GUI.

## DESCRIPTION
`/etc/minios/minios.conf` is a simple configuration file that allows you to set parameters before booting MiniOS. Some of these parameters can also be set in the boot options, which will take precedence over the configuration file.

Only the following parameters can always be changed when using persistent mode:

```
USER_NAME
ENABLE_SERVICES
DISABLE_SERVICES
SSH_KEY
HIDE_CREDENTIALS
AUTOLOGIN
LINK_USER_DIRS
SYSTEM_TYPE
EXPORT_LOGS
KEYBOARD_LAYOUTS
KEYBOARD_MODEL
KEYBOARD_OPTIONS
KEYBOARD_VARIANTS
LOCALES
TIMEZONE
```

## EXAMPLES
Below is an example of a standard configuration file:
```bash
USER_NAME="live"
USER_PASSWORD="evil"
ROOT_PASSWORD="toor"
HOST_NAME="minios"
DEFAULT_TARGET="graphical"
ENABLE_SERVICES="ssh"
DISABLE_SERVICES=""
SSH_KEY="authorized_keys"
SCRIPTS=true
HIDE_CREDENTIALS=false
AUTOLOGIN=true
ELEVATION_PASSWORD_REQUIRED=true
LINK_USER_DIRS=false
SYSTEM_TYPE="puzzle"
EXPORT_LOGS=false
LOCALES="en_US.UTF-8,ru_RU.UTF-8"
TIMEZONE="Europe/Moscow"
KEYBOARD_LAYOUTS="us,ru"
KEYBOARD_MODEL="pc105"
KEYBOARD_OPTIONS="grp:alt_shift_toggle"
KEYBOARD_VARIANTS=","
```

## PARAMETERS
| Parameter                   | Description                                                          | Example                                 |
| --------------------------- | -------------------------------------------------------------------- | --------------------------------------- |
| USER_NAME                   | The name of the user whose profile will be created at first boot.    | USER_NAME=live                          |
| USER_PASSWORD               | The password of the main user in clear text.                         | USER_PASSWORD=evil                      |
| ROOT_PASSWORD               | Password of the privileged user "root" in clear text.                | ROOT_PASSWORD=toor                      |
| HOST_NAME                   | The name of the node associated with the system.                     | HOST_NAME=minios                        |
| DEFAULT_TARGET              | The purpose of systemd.                                              | DEFAULT_TARGET=graphical                |
| ENABLE_SERVICES             | Enable services on boot.                                             | ENABLE_SERVICES=ssh                     |
| DISABLE_SERVICES            | Disable services on boot.                                            | DISABLE_SERVICES=docker                 |
| SSH_KEY                     | The name of the SSH public key file.                                 | SSH_KEY=authorized_keys                 |
| SCRIPTS                     | Enable/disable running shell scripts from the minios/scripts folder. | SCRIPTS=true                            |
| HIDE_CREDENTIALS            | Hide credentials displayed as tooltip in tty.                        | HIDE_CREDENTIALS=false                  |
| AUTOLOGIN                   | Enable/disable automatic login.                                      | AUTOLOGIN=true                          |
| ELEVATION_PASSWORD_REQUIRED | Require password for sudo/pkexec commands.                           | ELEVATION_PASSWORD_REQUIRED=true        |
| LINK_USER_DIRS              | Link user directories to persistent storage.                         | LINK_USER_DIRS=false                    |
| SYSTEM_TYPE                 | Select system mode: "puzzle" (modular) or "classic".                 | SYSTEM_TYPE=puzzle                      |
| EXPORT_LOGS                 | Copy MiniOS logs to minios/logs folder.                              | EXPORT_LOGS=false                       |
| LOCALES                     | System locales (comma-separated).                                    | LOCALES="en_US.UTF-8"                   |
| TIMEZONE                    | System timezone.                                                     | TIMEZONE="Europe/London"                |
| KEYBOARD_LAYOUTS            | Keyboard layouts (comma-separated).                                  | KEYBOARD_LAYOUTS="us,ru"                |
| KEYBOARD_MODEL              | Keyboard model identifier.                                           | KEYBOARD_MODEL="pc105"                  |
| KEYBOARD_OPTIONS            | Keyboard configuration options.                                      | KEYBOARD_OPTIONS="grp:alt_shift_toggle" |
| KEYBOARD_VARIANTS           | Keyboard layout variants (comma-separated).                          | KEYBOARD_VARIANTS=","                   |

## IMPORTANT POINTS
- On the first boot in persistent mode, the following parameters can be optionally changed:
  `HOST_NAME`, `DEFAULT_TARGET`, `LINK_USER_DIRS`.

## SEE ALSO
[Original Documentation](https://github.com/minios-linux/minios-live/wiki/Configuration-file)