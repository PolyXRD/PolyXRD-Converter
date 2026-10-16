; ==============================================================================
; PolyXRD Converter —— Inno Setup 6 安装脚本 (Setup 安装版)
; ==============================================================================
; 编译 (build.bat 自动调用, 也可手工):
;   ISCC installer\PolyXRD-Converter.iss /DAPP_VERSION=1.5.0
;
; 输入: dist\PolyXRD-Converter-Setup\  (PyInstaller onedir 产物, 见
;        PolyXRDConverter-Setup.spec)
; 输出: dist\PolyXRD-Converter-Setup-v<版本>.exe
;
; 行为要点:
;   * 可指定安装位置 (DisableDirPage=no, 默认 Program Files\PolyXRD\Converter);
;   * 许可页展示中英双语许可 (license-bilingual.txt);
;   * 注册状态存 %APPDATA%\PolyXRD\Registration\PolyXRD_Converter.json,
;     卸载不清除 -> 重装/升级后注册仍然有效;
;   * CloseApplications=yes: 升级前自动关闭正在运行的转换器。
; ==============================================================================

#ifndef APP_VERSION
  #define APP_VERSION "0.0.0"
#endif

#define MyAppName "PolyXRD Converter"
#define MyAppPublisher "PolyXRD Team"
#define MyAppURL "https://github.com/PolyXRD/PolyXRD-Converter"
#define MyAppExeName "PolyXRD-Converter-Setup.exe"

[Setup]
; AppId 换新值会被安装程序视为另一款产品; 永久固定, 不要改
AppId={{5E37FB08-3567-4410-8752-1F95241F5FF1}
AppName={#MyAppName}
AppVersion={#APP_VERSION}
AppVerName={#MyAppName} v{#APP_VERSION}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL=mailto:sshztx@outlook.com
DefaultDirName={autopf}\PolyXRD\Converter
DisableDirPage=no
DisableProgramGroupPage=yes
LicenseFile=license-bilingual.txt
OutputDir=..\dist
OutputBaseFilename=PolyXRD-Converter-Setup-v{#APP_VERSION}
SetupIconFile=..\src\polyxrd_converter\resources\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
CloseApplications=yes
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
; 中文语言文件随仓库分发 (installer\ChineseSimplified.isl), 不依赖编译器安装了哪些语言
Name: "chinesesimplified"; MessagesFile: "ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; \
    GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\PolyXRD-Converter-Setup\*"; \
    DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; \
    Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; \
    Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&')}}"; \
    Flags: nowait postinstall skipifsilent
