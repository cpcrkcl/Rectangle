# RectangleWin

RectangleWin is a small Windows window manager inspired by [rxhanson/Rectangle](https://github.com/rxhanson/Rectangle).
The upstream app is a macOS Swift/AppKit project, so this Windows version is implemented separately with Python and the Windows API.

## Run

From PowerShell:

```powershell
.\RectangleWin\Start-RectangleWin.ps1
```

Or run:

```powershell
python .\RectangleWin\rectangle_win.pyw
```

You can also double-click `Launch RectangleWin.cmd`.

If the app is hidden and the show-panel shortcut is not working, double-click `Open Control Panel.cmd`.

## Startup

Install for the current Windows user:

```powershell
.\RectangleWin\Install-Startup.ps1
```

Or double-click `Install Startup.cmd`.

Remove from startup:

```powershell
.\RectangleWin\Remove-Startup.ps1
```

Or double-click `Remove Startup.cmd`.

The app writes `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\RectangleWin`, so it starts after the user signs in.

## Shortcuts

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

If a shortcut is already owned by Windows or another app, RectangleWin leaves the rest running and reports that shortcut in the control panel.

Double-click a row in the control panel to change any shortcut. Settings are saved in `%APPDATA%\RectangleWin\config.json`.

## Upstream

This folder is a Windows implementation added alongside the upstream Rectangle source. Rectangle is MIT licensed by Ryan Hanson and contributors; see the repository `LICENSE`.
