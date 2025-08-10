# MiniOS Configurator

GTK3 graphical tool for configuring MiniOS system settings via live-config parameters.

## Features

- System identity configuration (hostname, username)
- Localization settings (locales, timezone, keyboard)
- Security configuration (user, root, sudo passwords)
- Service management (enable/disable systemd services)
- Input validation and auto-completion
- PolicyKit authentication

## Usage

```bash
# Default configuration file
minios-configurator

# Custom configuration file
minios-configurator /path/to/config.conf
```

Or from Applications Menu: System → Configure MiniOS

## Build

```bash
make build
sudo make install
```

## License

GPL-3.0+

## Author

crims0n <crims0n@minios.dev>