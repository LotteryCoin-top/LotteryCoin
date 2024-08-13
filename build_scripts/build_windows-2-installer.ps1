# $env:path should contain a path to editbin.exe and signtool.exe

$ErrorActionPreference = "Stop"

mkdir build_scripts\win_build

git status
git submodule

if (-not (Test-Path env:LOTTERY_INSTALLER_VERSION)) {
  $env:LOTTERY_INSTALLER_VERSION = '0.0.0'
  Write-Output "WARNING: No environment variable LOTTERY_INSTALLER_VERSION set. Using 0.0.0"
}
Write-Output "Lottery Version is: $env:LOTTERY_INSTALLER_VERSION"
Write-Output "   ---"

Write-Output "   ---"
Write-Output "Use pyinstaller to create lottery .exe's"
Write-Output "   ---"
$SPEC_FILE = (py -c 'import sys; from pathlib import Path; path = Path(sys.argv[1]); print(path.absolute().as_posix())' "pyinstaller.spec")
pyinstaller --log-level INFO $SPEC_FILE

Write-Output "   ---"
Write-Output "Creating a directory of licenses from pip and npm packages"
Write-Output "   ---"
bash ./build_win_license_dir.sh

Write-Output "   ---"
Write-Output "Copy lottery executables to LotteryCoin-gui\"
Write-Output "   ---"
Copy-Item "dist\daemon" -Destination "..\LotteryCoin-gui\packages\gui\" -Recurse

Write-Output "   ---"
Write-Output "Setup npm packager"
Write-Output "   ---"
Set-Location -Path ".\npm_windows" -PassThru
npm ci
$NPM_PATH = $pwd.PATH + "\node_modules\.bin"

Set-Location -Path "..\..\" -PassThru

Write-Output "   ---"
Write-Output "Prepare Electron packager"
Write-Output "   ---"
$Env:NODE_OPTIONS = "--max-old-space-size=3000"

# Change to the GUI directory
Set-Location -Path "LotteryCoin-gui\packages\gui" -PassThru

Write-Output "   ---"
Write-Output "Increase the stack for lottery command for (lottery plots create) chiapos limitations"
# editbin.exe needs to be in the path
editbin.exe /STACK:8000000 daemon\lottery.exe
Write-Output "   ---"

$packageVersion = "$env:LOTTERY_INSTALLER_VERSION"
$packageName = "LotteryCoin-$packageVersion"

Write-Output "packageName is $packageName"

Write-Output "   ---"
Write-Output "fix version in package.json"
choco install jq
cp package.json package.json.orig
jq --arg VER "$env:LOTTERY_INSTALLER_VERSION" '.version=$VER' package.json > temp.json
rm package.json
mv temp.json package.json
Write-Output "   ---"

Write-Output "   ---"
Write-Output "electron-builder create package directory"
$OLD_ENV_PATH = $Env:Path
$Env:Path = $NPM_PATH + ";" + $Env:Path
electron-builder build --win --x64 --config.productName="LotteryCoin" --dir --config ../../../build_scripts/electron-builder.json
$Env:Path = $OLD_ENV_PATH
Get-ChildItem dist\win-unpacked\resources
Write-Output "   ---"

If ($env:HAS_SIGNING_SECRET) {
   Write-Output "   ---"
   Write-Output "Sign all EXEs"
   Get-ChildItem ".\dist\win-unpacked" -Recurse | Where-Object { $_.Extension -eq ".exe" } | ForEach-Object {
      $exePath = $_.FullName
      Write-Output "Signing $exePath"
      signtool.exe sign /sha1 $env:SM_CODE_SIGNING_CERT_SHA1_HASH /tr http://timestamp.digicert.com /td SHA256 /fd SHA256 $exePath
      Write-Output "Verify signature"
      signtool.exe verify /v /pa $exePath
  }
}    Else    {
   Write-Output "Skipping verify signatures - no authorization to install certificates"
}

Write-Output "   ---"
Write-Output "electron-builder create installer"
npx electron-builder build --win --x64 --config.productName="LotteryCoin" --pd ".\dist\win-unpacked" --config ../../../build_scripts/electron-builder.json
Write-Output "   ---"

If ($env:HAS_SIGNING_SECRET) {
   Write-Output "   ---"
   Write-Output "Sign Final Installer App"
   signtool.exe sign /sha1 $env:SM_CODE_SIGNING_CERT_SHA1_HASH /tr http://timestamp.digicert.com /td SHA256 /fd SHA256 .\dist\LotterySetup-$packageVersion.exe
   Write-Output "   ---"
   Write-Output "Verify signature"
   Write-Output "   ---"
   signtool.exe verify /v /pa .\dist\LotterySetup-$packageVersion.exe
}   Else    {
   Write-Output "Skipping verify signatures - no authorization to install certificates"
}

Write-Output "   ---"
Write-Output "Moving final installers to expected location"
Write-Output "   ---"
Copy-Item ".\dist\win-unpacked" -Destination "$env:GITHUB_WORKSPACE\LotteryCoin-gui\LotteryCoin-win32-x64" -Recurse
mkdir "$env:GITHUB_WORKSPACE\LotteryCoin-gui\release-builds\windows-installer" -ea 0
Copy-Item ".\dist\LotterySetup-$packageVersion.exe" -Destination "$env:GITHUB_WORKSPACE\LotteryCoin-gui\release-builds\windows-installer"

Write-Output "   ---"
Write-Output "Windows Installer complete"
Write-Output "   ---"
