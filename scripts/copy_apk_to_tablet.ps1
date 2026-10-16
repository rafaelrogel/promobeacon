$shell = New-Object -ComObject Shell.Application
$drives = $shell.Namespace(17)
$tablet = $drives.Items() | Where-Object { $_.Name -like "*Galaxy*" -or $_.Name -like "*Tab*" }

if ($tablet) {
    Write-Host "Found tablet:" $tablet.Name
    $tabletFolder = $tablet.GetFolder
    foreach ($storage in $tabletFolder.Items()) {
        Write-Host "Storage:" $storage.Name
        $storageFolder = $storage.GetFolder
        foreach ($folder in $storageFolder.Items()) {
            if ($folder.Name -match "Download") {
                Write-Host "Found Download folder! Copying APK..."
                $apkPath = "C:\Users\rafae\Documents\Vibecoding\PromoBeacon\mobile_app_unified\app\build\outputs\apk\debug\app-debug.apk"
                $downloadFolder = $folder.GetFolder
                $downloadFolder.CopyHere($apkPath, 16)
                Write-Host "APK SUCCESSFULLY COPIED TO TABLET DOWNLOAD FOLDER!"
            }
        }
    }
} else {
    Write-Host "Tablet not found"
}
