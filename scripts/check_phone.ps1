$shell = New-Object -ComObject Shell.Application
$drives = $shell.Namespace(17) # ssfDRIVES
$device = $drives.Items() | Where-Object { $_.Name -like "*moto*" }
if ($device) {
    Write-Host "Found device:" $device.Name
    $deviceFolder = $device.GetFolder
    foreach ($item in $deviceFolder.Items()) {
        Write-Host " Storage:" $item.Name
        $internal = $item.GetFolder
        foreach ($sub in $internal.Items()) {
            if ($sub.Name -match "Download") {
                Write-Host "  Found Download folder:" $sub.Name
                $apkPath = "C:\Users\rafae\Documents\Vibecoding\PromoBeacon\mobile_app_unified\app\build\outputs\apk\debug\app-debug.apk"
                if (Test-Path $apkPath) {
                    Write-Host "  Copying APK to Download folder..."
                    $sub.GetFolder.CopyHere($apkPath, 16) # 16 = Respond Yes to all
                    Write-Host "  COPY_SUCCESS"
                }
            }
        }
    }
} else {
    Write-Host "Device not found in Shell drives"
}
