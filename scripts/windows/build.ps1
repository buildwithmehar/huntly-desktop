param(
    [string]$Python = 'py',
    [string]$MakeNsis = "${env:ProgramFiles(x86)}\NSIS\Bin\makensis.exe"
)

$ErrorActionPreference = 'Stop'

function Invoke-Checked {
    param([string]$Program)
    & $Program @args
    if ($LASTEXITCODE -ne 0) {
        throw "$Program failed with exit code $LASTEXITCODE."
    }
}

Push-Location (Join-Path $PSScriptRoot '..\..')
$previousBrowserPath = $env:PLAYWRIGHT_BROWSERS_PATH
try {
    $nsis = Get-Command -Name $MakeNsis -CommandType Application -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if (-not $nsis) {
        throw "NSIS compiler not found at '$MakeNsis'. Install NSIS 3 or pass -MakeNsis with the compiler path."
    }
    $buildInterpreter = 'build/windows-venv/Scripts/python.exe'
    $checkPython = "import struct, sys; sys.exit(0 if sys.version_info[:2] == (3, 11) and struct.calcsize('P') == 8 else 'Use Python 3.11 x64')"
    if (-not (Test-Path -LiteralPath $buildInterpreter)) {
        if ($Python -eq 'py') {
            Invoke-Checked $Python -3.11 -c $checkPython
            Invoke-Checked $Python -3.11 -m venv build/windows-venv
        } else {
            Invoke-Checked $Python -c $checkPython
            Invoke-Checked $Python -m venv build/windows-venv
        }
    }
    $buildPython = (Resolve-Path -LiteralPath $buildInterpreter).Path
    Invoke-Checked $buildPython -c $checkPython
    Invoke-Checked $buildPython -m pip install --disable-pip-version-check -r scripts/windows/requirements-build.txt -e .

    $env:PLAYWRIGHT_BROWSERS_PATH = '0'
    Invoke-Checked $buildPython -m playwright install chromium --only-shell
    Invoke-Checked $buildPython -m PyInstaller --noconfirm --workpath build/freeze scripts/windows/huntly.spec
    Invoke-Checked $buildPython scripts/windows/copy_licenses.py dist/Huntly

    $bootstrapper = 'build/WebView2Setup.exe'
    if (-not (Test-Path -LiteralPath $bootstrapper)) {
        Invoke-WebRequest -Uri 'https://go.microsoft.com/fwlink/p/?LinkId=2124703' -OutFile $bootstrapper
    }
    $signature = Get-AuthenticodeSignature -LiteralPath $bootstrapper
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'CN=Microsoft Corporation,') {
        throw 'The WebView2 installer does not have a valid Microsoft signature.'
    }
    $version = & $buildPython -c 'from importlib.metadata import version; print(version("huntly"))'
    if ($LASTEXITCODE -ne 0 -or $version -notmatch '^\d+\.\d+\.\d+$') {
        throw 'A three-part release version is required.'
    }
    Invoke-Checked $nsis.Source "/DVERSION=$version" scripts/windows/installer.nsi

    $sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath 'dist/Huntly-Setup.exe').Hash.ToLowerInvariant()
    "$sha256  Huntly-Setup.exe" | Set-Content -Encoding ascii 'dist/Huntly-Setup.exe.sha256'
    Get-Item -LiteralPath 'dist/Huntly-Setup.exe'
} finally {
    $env:PLAYWRIGHT_BROWSERS_PATH = $previousBrowserPath
    Pop-Location
}
