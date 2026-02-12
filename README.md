# LUTERVYN IDE

![Dark Theme Screenshot](<screenshots/Screenshot 2026-01-30 040912.png>)
![Light Theme Screenshot](<screenshots/Screenshot 2026-01-30 040925.png>)

An AI-powered lightweight text editor written in Lua.

* **[Get Lutervyn IDE]** — Download for Windows, Linux and Mac OS.
* **[Get plugins]** — Add additional functionality, adapted for Lutervyn IDE.
* **[Get color themes]** — Add additional colors themes.

Please refer to our [website] for the user and developer documentation,
including [build] instructions details. A quick build guide is described below.

Lutervyn IDE has support for high DPI display on Windows and Linux and,
 it supports **retina displays** on macOS.

## Overview

It is a lightweight AI-powered text editor written mostly in Lua — it aims to provide
something practical, pretty, *small* and fast, easy to modify and extend,
or to use without doing either.

The aim of Lutervyn IDE is to be more user friendly,
improve the quality of font rendering, reduce CPU usage, and integrate AI features
for enhanced coding assistance.

## Customization

Additional functionality can be added through plugins which are available in
the [plugins repository].

Additional color themes can be found in the [colors repository].
These color themes are bundled with all releases of Lutervyn IDE by default.

## Quick Build Guide

To compile Lutervyn IDE yourself, you must have the following dependencies installed
via your desired package manager, or manually.

### Prerequisites

- Meson (>=0.63)
- Ninja
- SDL2
- PCRE2
- FreeType2
- Lua 5.4
- A working C compiler (GCC / Clang / MSVC)

SDL2, PCRE2, FreeType2 and Lua will be downloaded by Meson
if `--wrap-mode=forcefallback` or `--wrap-mode=default` is specified.

> [!NOTE]
> MSVC is used in the CI, but MSVC-compiled binaries are not distributed officially
> or tested extensively for bugs.

On Linux, you may install the following dependencies for the SDL2 X11 and/or Wayland backend to work properly:

- `libX11-devel`
- `libXi-devel`
- `libXcursor-devel`
- `libxkbcommon-devel`
- `libXrandr-devel`
- `wayland-devel`
- `wayland-protocols-devel`
- `dbus-devel`
- `ibus-devel`

The following command can be used to install the dependencies in Ubuntu:

```sh
apt-get install python3.8 python3-pip build-essential git cmake wayland-protocols libsdl2-dev
pip3 install meson ninja
```

Please refer to [lutervyn-build-box] for a working Linux build environment used to package official Lutervyn IDE releases.

On macOS, you must install bash via Brew, as the default bash version on macOS is antiquated
and may not run the build script correctly.

### Building

You can use `scripts/build.sh` to set up Lutervyn IDE and build it.

```sh
$ bash build.sh --help
# Usage: scripts/build.sh <OPTIONS>
# 
# Available options:
# 
# -b --builddir DIRNAME         Sets the name of the build directory (not path).
#                               Default: 'build-x86_64-linux'.
#    --debug                    Debug this script.
# -f --forcefallback            Force to build dependencies statically.
# -h --help                     Show this help and exit.
# -d --debug-build              Builds a debug build.
# -p --prefix PREFIX            Install directory prefix. Default: '/'.
# -B --bundle                   Create an App bundle (macOS only)
# -A --addons                   Add in addons
# -P --portable                 Create a portable binary package.
# -r --reconfigure              Tries to reuse the meson build directory, if possible.
#                               Default: Deletes the build directory and recreates it.
# -O --pgo                      Use profile guided optimizations (pgo).
#                               macOS: disabled when used with --bundle,
#                               Windows: Implicit being the only option.
#    --cross-platform PLATFORM  Cross compile for this platform.
#                               The script will find the appropriate
#                               cross file in 'resources/cross'.
#    --cross-arch ARCH          Cross compile for this architecture.
#                               The script will find the appropriate
#                               cross file in 'resources/cross'.
#    --cross-file CROSS_FILE    Cross compile with the given cross file.
```

Alternatively, you can use the following commands to customize the build:

```sh
meson setup --buildtype=release --prefix <prefix> build
meson compile -C build
DESTDIR="$(pwd)/lutervyn-ide" meson install --skip-subprojects -C build
```

where `<prefix>` might be one of `/`, `/usr` or `/opt`, the default is `/`.
To build a bundle application on macOS:

```sh
meson setup --buildtype=release --Dbundle=true --prefix / build
meson compile -C build
DESTDIR="$(pwd)/Lutervyn IDE.app" meson install --skip-subprojects -C build
```

Please note that the package is relocatable to any prefix and the option prefix
affects only the place where the application is actually installed.

## Installing Prebuilt

Head over to [releases](https://github.com/lutervyn/lutervyn-ide/releases) and download the version for your operating system.

The prebuilt releases supports the following OSes:

- Windows 7 and above
- Ubuntu 18.04 and above (glibc 2.27 and above)
- OS X El Capitan and above (version 10.11 and above)

Some distributions may provide custom binaries for their platforms.

### Windows

Lutervyn IDE comes with installers on Windows for typical installations.
Alternatively, we provide ZIP archives that you can download and extract anywhere and run directly.

To make Lutervyn IDE portable (e.g. running Lutervyn IDE from a thumb drive),
simply create a `user` folder where `lutervyn.exe` is located.
Lutervyn IDE will load and store all your configurations and plugins in the folder.

### macOS

We provide DMG files for macOS. Simply drag the program into your Applications folder.

> **Important**
> Newer versions of Lutervyn IDE are signed with a self-signed certificate,
> so you'll have to follow these steps when running Lutervyn IDE for the first time.
>
> 1. Find Lutervyn IDE in Finder (do not open it in Launchpad).
> 2. Control-click Lutervyn IDE, then choose `Open` from the shortcut menu.
> 3. Click `Open` in the popup menu.
>
> The correct steps may vary between macOS versions, so you should refer to
> the [macOS User Guide](https://support.apple.com/en-my/guide/mac-help/mh40616/mac).
>
> On an older version of Lutervyn IDE, you will need to run these commands instead:
> 
> ```sh
> # clears attributes from the directory
> xattr -cr /Applications/Lutervyn\ IDE.app
> ```
>
> Otherwise, macOS will display a **very misleading error** saying that the application is damaged.

### Linux

Unzip the file and `cd` into the `lutervyn-ide` directory:

```sh
tar -xzf <file>
cd lutervyn-ide
```

To run lutervyn-ide without installing:

```sh
./lutervyn-ide
```

To install lutervyn-ide copy files over into appropriate directories:

```sh
rm -rf  $HOME/.local/share/lutervyn-ide $HOME/.local/bin/lutervyn-ide
mkdir -p $HOME/.local/bin && cp lutervyn-ide $HOME/.local/bin/
mkdir -p $HOME/.local/share/lutervyn-ide && cp -r data/* $HOME/.local/share/lutervyn-ide/
```

#### Add Lutervyn IDE to PATH

To run Lutervyn IDE from the command line, you must add it to PATH.

If `$HOME/.local/bin` is not in PATH:

```sh
echo -e 'export PATH=$PATH:$HOME/.local/bin' >> $HOME/.bashrc
```

Alternatively on recent versions of GNOME and KDE Plasma,
you can add `$HOME/.local/bin` to PATH via `~/.config/environment.d/envvars.conf`:

```ini
PATH=$HOME/.local/bin:$PATH
```

> **Note**
> Some systems might not load `.bashrc` when logging in.
> This can cause problems with launching applications from the desktop / menu.

#### Add Lutervyn IDE to application launchers

To get the icon to show up in app launcher, you need to create a desktop
entry and put it into `/usr/share/applications` or `~/.local/share/applications`.

Here is an example for a desktop entry in `~/.local/share/applications/com.lutervyn.LutervynIDE.desktop`,
assuming Lutervyn IDE is in PATH:

```ini
[Desktop Entry]
Type=Application
Name=Lutervyn IDE
Comment=An AI-powered lightweight text editor written in Lua
Exec=lutervyn-ide %F
Icon=lutervyn-ide
Terminal=false
StartupWMClass=lutervyn-ide
Categories=Development;IDE;
MimeType=text/plain;inode/directory;
```

To get the icon to show up in app launcher immediately, run:

```sh
xdg-desktop-menu forceupdate
```

Alternatively, you may log out and log in again.

#### Uninstall

To uninstall Lutervyn IDE, run:

```sh
rm -f $HOME/.local/bin/lutervyn-ide
rm -rf $HOME/.local/share/icons/hicolor/scalable/apps/lutervyn-ide.svg \
          $HOME/.local/share/applications/com.lutervyn.LutervynIDE.desktop \
          $HOME/.local/share/metainfo/com.lutervyn.LutervynIDE.appdata.xml \
          $HOME/.local/share/lutervyn-ide
```

## Contributing

Any additional functionality that can be added through a plugin should be done
as a plugin, after which a pull request to the [Lutervyn IDE plugins repository] can be made.

Pull requests to improve or modify the editor itself are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for more details.

## Licenses

This project is free software; you can redistribute it and/or modify it under
the terms of the MIT license. See [LICENSE] for details.

See the [licenses] file for details on licenses used by the required dependencies.


[CI]:                         https://github.com/lutervyn/lutervyn-ide/actions/workflows/build.yml/badge.svg
[Discord Badge Image]:        https://img.shields.io/discord/847122429742809208?label=discord&logo=discord
[screenshot-dark]:            https://user-images.githubusercontent.com/433545/111063905-66943980-84b1-11eb-9040-3876f1133b20.png
[website]:                    https://lutervyn-ide.com
[build]:                      https://lutervyn-ide.com/setup/building-from-source/
[Get Lutervyn IDE]:           https://github.com/lutervyn/lutervyn-ide/releases/latest
[Get plugins]:                https://github.com/lutervyn/lutervyn-ide-plugins
[Get color themes]:           https://github.com/lutervyn/lutervyn-ide-colors
[changelog]:                  https://github.com/lutervyn/lutervyn-ide/blob/master/changelog.md
[plugins repository]:         https://github.com/lutervyn/lutervyn-ide-plugins
[colors repository]:          https://github.com/lutervyn/lutervyn-ide-colors
[LICENSE]:                    LICENSE
[licenses]:                   licenses/licenses.md
[lutervyn-build-box]:         https://github.com/lutervyn/lutervyn-build-box
