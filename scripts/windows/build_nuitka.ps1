$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path

Push-Location $ProjectRoot
try {
    python -m nuitka `
      --standalone `
      --windows-console-mode=disable `
      --windows-icon-from-ico=assets/icons/app_icon.ico `
      --enable-plugin=pyside6 `
      --include-package=tzdata `
      --include-package-data=tzdata `
      --include-data-file=VERSION=VERSION `
      --include-data-file=LICENSE=LICENSE `
      --include-data-dir=assets=assets `
      --jobs=8 `
      --output-filename=BlinkCall.exe `
      blink_call/setup_app.py
} finally {
    Pop-Location
}
