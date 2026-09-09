# Installation

## Requirements

* Python 3.11 or higher, which the `python-xbox` library requires
* Libraries: [python-xbox](https://github.com/tr4nt0r/python-xbox), `python-dateutil`, `httpx`, `pytz`, `tzlocal`, `python-dotenv`, `wcwidth`, `colorama` (Windows only, optional)

`tzlocal`, `python-dotenv` and `wcwidth` are optional. Without `tzlocal` the local time zone has to be set manually, without `python-dotenv` secrets have to come from the environment or the command line, and without `wcwidth` screen truncation is switched off.

Tested on:

* **macOS**: Ventura, Sonoma, Sequoia, Tahoe
* **Linux**: Raspberry Pi OS (Bullseye, Bookworm, Trixie), Ubuntu 24/25, Rocky Linux 8.x/9.x, Kali Linux 2024/2025
* **Windows**: 10, 11

It should work on other versions of macOS, Linux, Unix and Windows as well.

## Install from PyPI

```sh
pip install xbox_monitor
```

## Manual Installation

Download the [xbox_monitor.py](https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/xbox_monitor.py) file to the desired location.

Install the dependencies:

```sh
pip install python-xbox python-dateutil httpx pytz tzlocal python-dotenv wcwidth
```

Alternatively, from the downloaded [requirements.txt](https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/requirements.txt):

```sh
pip install -r requirements.txt
```

Commands printed by the tool itself adapt to how it was installed, so a manual install is told to run `python3 xbox_monitor.py` rather than `xbox_monitor`.

## Upgrading

To upgrade to the latest version when installed from PyPI:

```sh
pip install xbox_monitor -U
```

If you installed manually, download the newest [xbox_monitor.py](https://raw.githubusercontent.com/misiektoja/xbox_monitor/refs/heads/main/xbox_monitor.py) file to replace your existing installation.
