Unicode true
ManifestDPIAware true
RequestExecutionLevel user
SetCompressor zlib

!include "MUI2.nsh"
!include "x64.nsh"
!include "WinVer.nsh"

Name "Huntly"
OutFile "..\..\dist\Huntly-Setup.exe"
InstallDir "$LOCALAPPDATA\Programs\Huntly"
InstallDirRegKey HKCU "Software\Huntly" "InstallDir"
!define UninstallKey "Software\Microsoft\Windows\CurrentVersion\Uninstall\Huntly"
!define WebViewKey "Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"

VIProductVersion "${VERSION}.0"
VIAddVersionKey "ProductName" "Huntly"
VIAddVersionKey "FileDescription" "Huntly Windows Setup"
VIAddVersionKey "FileVersion" "${VERSION}"
VIAddVersionKey "ProductVersion" "${VERSION}"
VIAddVersionKey "LegalCopyright" "Copyright (C) 2026 Huntly and Sellbird contributors"

!define MUI_ICON "huntly.ico"
!define MUI_UNICON "huntly.ico"
!define MUI_ABORTWARNING
!define MUI_FINISHPAGE_RUN "$INSTDIR\Huntly.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Open Huntly"
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\..\LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Function .onInit
  ${IfNot} ${AtLeastWin10}
  ${OrIfNot} ${RunningX64}
    MessageBox MB_ICONSTOP "Huntly requires 64-bit Windows 10 or Windows 11." /SD IDOK
    SetErrorLevel 1
    Abort
  ${EndIf}
FunctionEnd

Section "Huntly"
  SetShellVarContext current

  ReadRegStr $0 HKLM "${WebViewKey}" "pv"
  ${If} $0 == ""
  ${OrIf} $0 == "0.0.0.0"
    ReadRegStr $0 HKCU "${WebViewKey}" "pv"
    ${If} $0 == ""
    ${OrIf} $0 == "0.0.0.0"
      InitPluginsDir
      File "/oname=$PLUGINSDIR\WebView2Setup.exe" "..\..\build\WebView2Setup.exe"
      DetailPrint "Installing Microsoft Edge WebView2 Runtime"
      ExecWait '"$PLUGINSDIR\WebView2Setup.exe" /silent /install' $0
      ${If} ${Errors}
      ${OrIf} $0 != 0
        MessageBox MB_ICONSTOP "WebView2 could not install. Check your internet connection and run Huntly Setup again." /SD IDOK
        SetErrorLevel 1
        Abort
      ${EndIf}
    ${EndIf}
  ${EndIf}

  SetOutPath "$INSTDIR"
  File /r "..\..\dist\Huntly\*"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  CreateShortcut "$SMPROGRAMS\Huntly.lnk" "$INSTDIR\Huntly.exe"
  WriteRegStr HKCU "Software\Huntly" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "${UninstallKey}" "DisplayName" "Huntly"
  WriteRegStr HKCU "${UninstallKey}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "${UninstallKey}" "DisplayIcon" "$INSTDIR\Huntly.exe"
  WriteRegStr HKCU "${UninstallKey}" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegDWORD HKCU "${UninstallKey}" "NoModify" 1
  WriteRegDWORD HKCU "${UninstallKey}" "NoRepair" 1
SectionEnd

Section "Uninstall"
  SetShellVarContext current
  Delete "$SMPROGRAMS\Huntly.lnk"
  Delete "$INSTDIR\Huntly.exe"
  Delete "$INSTDIR\HuntlyCLI.exe"
  Delete "$INSTDIR\LICENSE"
  Delete "$INSTDIR\NOTICE"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir /r "$INSTDIR\_internal"
  RMDir /r "$INSTDIR\third-party-licenses"
  RMDir "$INSTDIR"
  DeleteRegKey HKCU "${UninstallKey}"
  DeleteRegKey HKCU "Software\Huntly"
SectionEnd
