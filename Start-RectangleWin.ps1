$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$app = Join-Path $here "rectangle_win.pyw"

function Get-RectangleWinPython {
    $pythonExe = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($pythonExe) {
        $candidate = & $pythonExe.Source -c "import os, sys; print(os.path.join(os.path.dirname(sys.executable), 'pythonw.exe'))" 2>$null
        if ($LASTEXITCODE -eq 0 -and (Test-Path $candidate)) {
            return $candidate
        }
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

Start-Process -FilePath $python -ArgumentList @("`"$app`"")
