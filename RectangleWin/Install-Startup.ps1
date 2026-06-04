$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$app = Join-Path $here "rectangle_win.pyw"

function Get-RectangleWinPython {
    $pythonExe = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($pythonExe) {
        return $pythonExe.Source
    }

    $pythonw = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    if ($pythonw) {
        return $pythonw.Source
    }

    return $null
}

$python = Get-RectangleWinPython
if (-not $python) {
    throw "Python is required to run RectangleWin."
}

Start-Process -FilePath $python -ArgumentList @("`"$app`"", "--install-startup") -Wait
