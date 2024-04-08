% MINIOS_CONFIGURATOR(1) MiniOS Live Manual

## NAME
**MiniOS Configuration** - Configure MiniOS parameters via `/etc/minios/minios.conf`.

## SYNOPSIS
Modifies the `/etc/minios/minios.conf` file using the GUI.

## DESCRIPTION
`minios/minios.conf` is a simple configuration file that allows you to set parameters before booting MiniOS. Some of these parameters can also be set in the boot options, which will take precedence over the configuration file.

Only the following parameters can always be changed when using persistent mode:

```
USER_NAME
ENABLE_SERVICES
DISABLE_SERVICES
SSH_KEY
HIDE_CREDENTIALS
AUTOLOGIN
SYSTEM_TYPE
EXPORT_LOGS
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
SCRIPTS="true"
HIDE_CREDENTIALS="false"
AUTOLOGIN="true"
SYSTEM_TYPE="puzzle"
EXPORT_LOGS="false"
```

## PARAMETERS
| Parameter        | Description                                                          | Example              |
| ---------------- | -------------------------------------------------------------------- | -------------------- |
| USER_NAME        | The name of the user whose profile will be created at first boot.    | USER_NAME=live       |
| USER_PASSWORD    | The password of the main user in clear text.                         | USER_PASSWORD=evil   |
| ROOT_PASSWORD    | Password of the privileged user "root" in clear text.                | ROOT_PASSWORD=toor   |
| HOST_NAME        | The name of the node associated with the system.                     | HOST_NAME=minios     |
| DEFAULT_TARGET   | The purpose of systemd.                                              | DEFAULT_TARGET=graphical |
| ENABLE_SERVICES  | Enable services on boot.                                             | ENABLE_SERVICES=ssh  |
| DISABLE_SERVICES | Disable services on boot.                                            | DISABLE_SERVICES=docker |
| SSH_KEY          | The name of the SSH public key file.                                 | SSH_KEY=authorized_keys |
| SCRIPTS          | Enable or disable running shell scripts from the minios/scripts folder. | SCRIPTS=true        |
| HIDE_CREDENTIALS | Hide credentials displayed as tooltip in tty.                        | HIDE_CREDENTIALS=false |
| AUTOLOGIN        | Enable or disable automatic login.                                   | AUTOLOGIN=true       |
| SYSTEM_TYPE      | Select the operating mode of the system (puzzle or classic).         | SYSTEM_TYPE=puzzle   |
| EXPORT_LOGS      | Enable or disable MiniOS logs copy to minios/logs folder.            | EXPORT_LOGS="false"   |

## IMPORTANT POINTS
- On the first boot in persistent mode, `HOST_NAME` and `DEFAULT_TARGET` can be optionally changed.

## SEE ALSO
[Original Documentation](https://github.com/minios-linux/minios-live/wiki/Configuration-file)