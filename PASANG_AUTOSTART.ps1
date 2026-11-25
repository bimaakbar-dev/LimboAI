# Pasang Limbo HUD agar jalan otomatis saat PC hidup.
# Jalankan PowerShell di folder asisten-pc:
#   powershell -ExecutionPolicy Bypass -File PASANG_AUTOSTART.ps1
#
# Ini HANYAKAN membuat shortcut di folder Startup. Tidak mengubah sistem lain.

$startup = [Environment]::GetFolderPath('Startup')
$target = (Resolve-Path '.\JALANKAN_LIMBO_HUD.bat').Path
$workdir = (Get-Location).Path

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut((Join-Path $startup 'Limbo HUD.lnk'))
$shortcut.TargetPath = $target
$shortcut.WorkingDirectory = $workdir
$shortcut.Description = 'Limbo — asisten PC pribadi'
$shortcut.Save()

Write-Host "Auto-start terpasang: $startup\Limbo HUD.lnk"
Write-Host "Hapus shortcut itu dari Startup kalau tidak diinginkan."
