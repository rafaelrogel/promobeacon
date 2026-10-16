$shell = New-Object -ComObject Shell.Application
$drives = $shell.Namespace(17)
foreach ($item in $drives.Items()) {
    Write-Host "Device:" $item.Name "Path:" $item.Path
}
