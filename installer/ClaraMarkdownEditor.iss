; ClaraMarkdownEditor 安装脚本（Inno Setup 6）
; 由 build_setup.ps1 调用：ISCC.exe /DAppVersion=x.y.z installer\ClaraMarkdownEditor.iss

#ifndef AppVersion
  #define AppVersion "1.6.6"
#endif

#define MyAppName "ClaraMarkdownEditor"
#define MyAppExeName "ClaraMarkdownEditor.exe"
#define MyAppPublisher "Clara"

[Setup]
AppId={{6D1F3A62-2A7B-4C4E-9A1D-7B0C5E3F8D21}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppVerName={#MyAppName} {#AppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
DisableWelcomePage=no
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ShowLanguageDialog=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
ChangesAssociations=yes
OutputDir=..\dist
OutputBaseFilename=ClaraMarkdownEditor_Setup_{#AppVersion}
SetupIconFile=..\clara\assets\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
WizardStyle=modern
WizardImageFile=assets\wizard.bmp
WizardSmallImageFile=assets\wizard_small.bmp
Compression=lzma2/max
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
VersionInfoVersion={#AppVersion}
VersionInfoDescription={#MyAppName} 安装程序
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#AppVersion}

[Languages]
Name: "chinesesimplified"; MessagesFile: "languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
chinesesimplified.TaskGroup=附加选项
chinesesimplified.TaskDesktop=创建桌面快捷方式(&D)
chinesesimplified.TaskStartMenu=在开始菜单中创建快捷方式(&S)
chinesesimplified.TaskAssoc=使用 {#MyAppName} 打开 .md 文件(&M)
chinesesimplified.TaskAssocHint=将 .md 文件的默认打开方式设为 {#MyAppName}
chinesesimplified.MarkdownDocType=Markdown 文档
chinesesimplified.LaunchApp=立即运行 {#MyAppName}
english.TaskGroup=Additional options
english.TaskDesktop=Create a desktop shortcut(&D)
english.TaskStartMenu=Create a Start menu shortcut(&S)
english.TaskAssoc=Open .md files with {#MyAppName}(&M)
english.TaskAssocHint=Set {#MyAppName} as the default app for .md files
english.MarkdownDocType=Markdown document
english.LaunchApp=Launch {#MyAppName}

[Messages]
chinesesimplified.WelcomeLabel2=此向导将把 [name/ver] 安装到您的电脑中。%n%nClaraMarkdownEditor 是一款仿 Word Ribbon 界面的 Markdown 编辑器，支持 Markdown、Word 与 PDF 三向互转，并提供源码、分屏与所见即所得三种编辑模式。%n%n请关闭其他应用程序后继续。
english.WelcomeLabel2=This wizard will install [name/ver] on your computer.%n%nClaraMarkdownEditor is a Ribbon-style Markdown editor with Markdown / Word / PDF conversion and source, split and WYSIWYG editing modes.%n%nPlease close other applications before continuing.

[Tasks]
Name: "mdassoc"; Description: "{cm:TaskAssoc}"; GroupDescription: "{cm:TaskGroup}"; Flags: checkablealone
Name: "desktopicon"; Description: "{cm:TaskDesktop}"; GroupDescription: "{cm:TaskGroup}"
Name: "startmenu"; Description: "{cm:TaskStartMenu}"; GroupDescription: "{cm:TaskGroup}"

[Files]
Source: "..\dist\{#MyAppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startmenu
Name: "{autoprograms}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"; Tasks: startmenu
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; 文件关联：ProgID + .md 默认打开方式 + “打开方式”列表
Root: HKA; Subkey: "Software\Classes\ClaraMarkdownEditor.md"; ValueType: string; ValueName: ""; ValueData: "{cm:MarkdownDocType}"; Flags: uninsdeletekey; Tasks: mdassoc
Root: HKA; Subkey: "Software\Classes\ClaraMarkdownEditor.md\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Tasks: mdassoc
Root: HKA; Subkey: "Software\Classes\ClaraMarkdownEditor.md\shell\open"; ValueType: string; ValueName: "FriendlyAppName"; ValueData: "{#MyAppName}"; Tasks: mdassoc
Root: HKA; Subkey: "Software\Classes\ClaraMarkdownEditor.md\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: mdassoc
Root: HKA; Subkey: "Software\Classes\.md"; ValueType: string; ValueName: ""; ValueData: "ClaraMarkdownEditor.md"; Flags: uninsdeletevalue; Tasks: mdassoc
Root: HKA; Subkey: "Software\Classes\.md\OpenWithProgids"; ValueType: string; ValueName: "ClaraMarkdownEditor.md"; ValueData: ""; Flags: uninsdeletevalue; Tasks: mdassoc
Root: HKA; Subkey: "Software\Classes\Applications\{#MyAppExeName}"; ValueType: string; ValueName: "FriendlyAppName"; ValueData: "{#MyAppName}"; Flags: uninsdeletekey; Tasks: mdassoc
Root: HKA; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".md"; ValueData: ""; Tasks: mdassoc
Root: HKA; Subkey: "Software\Classes\Applications\{#MyAppExeName}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Tasks: mdassoc

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchApp}"; Flags: nowait postinstall skipifsilent

[Code]
const
  MdClassesKey = 'Software\Classes\.md';
  AssocBackupKey = 'Software\Clara\ClaraMarkdownEditor';
  SHCNE_ASSOCCHANGED = $08000000;
  SHCNF_IDLIST = $0000;

procedure SHChangeNotify(wEventId: Integer; uFlags: Integer; dwItem1: Integer; dwItem2: Integer);
  external 'SHChangeNotify@shell32.dll stdcall';

procedure BackupMdAssociation;
var
  Previous: String;
begin
  if not WizardIsTaskSelected('mdassoc') then
    exit;
  if RegQueryStringValue(HKA, MdClassesKey, '', Previous) then
  begin
    RegWriteStringValue(HKA, AssocBackupKey, 'Previous', Previous);
    RegWriteDWordValue(HKA, AssocBackupKey, 'HadPrevious', 1);
  end
  else
    RegWriteDWordValue(HKA, AssocBackupKey, 'HadPrevious', 0);
end;

procedure RestoreMdAssociation;
var
  Previous: String;
  HadPrevious: Cardinal;
begin
  if not RegQueryDWordValue(HKA, AssocBackupKey, 'HadPrevious', HadPrevious) then
    exit;
  if HadPrevious = 1 then
  begin
    if RegQueryStringValue(HKA, AssocBackupKey, 'Previous', Previous) then
      RegWriteStringValue(HKA, MdClassesKey, '', Previous);
  end
  else
    RegDeleteValue(HKA, MdClassesKey, '');
  RegDeleteKeyIncludingSubkeys(HKA, AssocBackupKey);
  SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, 0, 0);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
    BackupMdAssociation;
  if CurStep = ssPostInstall then
    SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, 0, 0);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
    RestoreMdAssociation;
end;
