# Rectangle

Rectangle is a small Windows window manager inspired by [Rectangle for macOS](https://github.com/rxhanson/Rectangle) by Ryan Hanson.

This is an independent Windows application. It is not affiliated with or endorsed by the original Rectangle project. Credit and the original MIT license notice are included in `THIRD_PARTY_NOTICES.md`.

## Features

- Move the focused window with global keyboard shortcuts.
- Edit shortcuts from the built-in control panel.
- Use halves, thirds, two-thirds, quarters, centered, maximize, and display-to-display moves.
- Start automatically when you sign in to Windows.

## Run

Double-click `Launch RectangleWin.cmd`, or run this from PowerShell:

```powershell
.\Start-RectangleWin.ps1
```

If the control panel is hidden and the show-panel shortcut is unavailable, double-click `Open Control Panel.cmd`.

## Startup

Install startup launch for the current Windows user:

```powershell
.\Install-Startup.ps1
```

Remove startup launch:

```powershell
.\Remove-Startup.ps1
```

The app writes `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\RectangleWin`, so it starts after sign-in.

## Default Shortcuts

| Shortcut | Action |
| --- | --- |
| `Ctrl+Alt+Left` | Left half |
| `Ctrl+Alt+Right` | Right half |
| `Ctrl+Alt+Up` | Maximize |
| `Ctrl+Alt+Down` | Center |
| `Ctrl+Alt+Shift+Up` | Top half |
| `Ctrl+Alt+Shift+Down` | Bottom half |
| `Ctrl+Alt+U` | Top left quarter |
| `Ctrl+Alt+I` | Top right quarter |
| `Ctrl+Alt+J` | Bottom left quarter |
| `Ctrl+Alt+K` | Bottom right quarter |
| `Ctrl+Alt+1` | Left third |
| `Ctrl+Alt+2` | Center third |
| `Ctrl+Alt+3` | Right third |
| `Ctrl+Alt+Shift+1` | First two thirds |
| `Ctrl+Alt+Shift+3` | Last two thirds |
| `Ctrl+Alt+Shift+Left` | Previous display |
| `Ctrl+Alt+Shift+Right` | Next display |
| `Ctrl+Alt+Shift+R` | Show the control panel |

Double-click any command row in the control panel to change its shortcut. Settings are saved in `%APPDATA%\RectangleWin\config.json`.

## Requirements

Windows with Python 3 and Tkinter available.
