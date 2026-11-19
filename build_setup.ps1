# 一键构建 ClaraMarkdownEditor 安装包
# 用法：powershell -ExecutionPolicy Bypass -File build_setup.ps1
# 产物：dist\ClaraMarkdownEditor_Setup_<版本号>.exe

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

$ver = (python -c "import clara; print(clara.__version__)").Trim()
if (-not $ver) { throw "无法读取 clara/__init__.py 中的版本号" }
Write-Host "==> 版本：$ver"

Write-Host "==> 生成图标与安装向导图片"
python installer\make_assets.py

Write-Host "==> PyInstaller 打包应用"
python -m PyInstaller --noconfirm --clean --windowed --name ClaraMarkdownEditor `
    --icon "clara\assets\app.ico" `
    --add-data "clara\assets;clara\assets" `
    app.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller 失败：$LASTEXITCODE" }

$iscc = @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "未找到 Inno Setup 的 ISCC.exe，请先安装 Inno Setup 6" }

Write-Host "==> 编译安装包"
& $iscc "/DAppVersion=$ver" "installer\ClaraMarkdownEditor.iss"
if ($LASTEXITCODE -ne 0) { throw "ISCC 编译失败：$LASTEXITCODE" }

$setup = Join-Path $root "dist\ClaraMarkdownEditor_Setup_$ver.exe"
if (-not (Test-Path $setup)) { throw "未生成安装包：$setup" }
Write-Host "==> 完成：$setup"
