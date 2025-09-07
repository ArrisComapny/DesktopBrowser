Var strInstallerCustomVersionPreInstall

;!include NewTextReplace.nsh
;!include ReplaceInFileWithTextReplace.nsh

!macro CustomCodePreInstall
	ReadINIStr $strInstallerCustomVersionPreInstall "$INSTDIR\App\AppInfo\appinfo.ini" "Version" "PackageVersion"
	${If} ${FileExists} "$INSTDIR\Data\profile\*.*"
		${VersionCompare} $strInstallerCustomVersionPreInstall "20.0.0.0" $R0
		${If} $R0 == 2
			WriteINIStr "$INSTDIR\Data\settings\FirefoxPortableSettings.ini" "FirefoxPortableSettings" "SubmitCrashReport" "0"
		${Else}
			${VersionCompare} $strInstallerCustomVersionPreInstall "116.0.0.0" $R0
			${If} $R0 == 2
				ReadRegStr $0 HKLM "Software\Microsoft\Windows NT\CurrentVersion" "CurrentBuild"
				${If} $0 < 10000
					;Windows 7/8/8.1
					${GetParent} $INSTDIR $1
					${IfNot} ${FileExists} "$1\FirefoxPortableLegacy115\*.*"
						CreateDirectory "$1\FirefoxPortableLegacy115"
						CopyFiles /SILENT "$INSTDIR\*.*" "$1\FirefoxPortableLegacy115"
						WriteINIStr "$1\FirefoxPortableLegacy115\App\AppInfo\AppInfo.ini" "Details" "AppID" "FirefoxPortableLegacy115"
						WriteINIStr "$1\FirefoxPortableLegacy115\App\AppInfo\AppInfo.ini" "Details" "Name" "Firefox, Portable Edition (Legacy 115)"
						WriteINIStr "$1\FirefoxPortableLegacy115\App\AppInfo\AppInfo.ini" "Control" "BaseAppID" "FirefoxPortableLegacy115"
					${EndIf}
				${EndIf}	
			${EndIf}
		${EndIf}
	${EndIf}
!macroend

!macro CustomCodePostInstall
	${If} ${FileExists} "$INSTDIR\Data\profile\*.*"
		${VersionCompare} $strInstallerCustomVersionPreInstall "84.0.0.2" $R0
		${If} $R0 == 2
			Delete "$INSTDIR\Data\settings\update-config.json"
			CopyFiles /SILENT "$INSTDIR\App\DefaultData\settings\update-config.json" "$INSTDIR\Data\settings"
		${EndIf}
	${EndIf}
!macroend