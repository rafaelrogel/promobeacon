param(
    [switch]$Erase
)

# PromoBeacon Universal Auto-Detect Flasher v2 (Hardcore Edition)
# Detects connected ESP32 hardware and uploads the correct environment.

$ErrorActionPreference = "Stop"
Write-Host "--- PromoBeacon Smart Flash ---" -ForegroundColor Cyan

# 1. Detect chip
Write-Host "Detecting hardware..." -NoNewline
try {
    $output = pio device list
    if ($output -match "303A:1001") {
        Write-Host " [Success]" -ForegroundColor Green
        Write-Host "Detected: ESP32-C3 (Hardware ID Match: 303A:1001)" -ForegroundColor Gray
        $envTarget = "esp32c3"
    } else {
        Write-Host " [Success]" -ForegroundColor Green
        Write-Host "Detected: Generic ESP32/Other (Using esp32dev environment)" -ForegroundColor Gray
        $envTarget = "esp32dev"
    }
} catch {
    Write-Host " [Error]" -ForegroundColor Red
    Write-Host "Failed to detect hardware. Is the device plugged in?" -ForegroundColor Red
    exit 1
}

# 2. Force Global Cleanup (The "Full Nuclear" Option)
Write-Host "`nOBLITERATING old build artifacts and caches..." -ForegroundColor Yellow
# Remove environment-specific sdkconfigs which are the hidden source of the 512-byte limit
Remove-Item -Path "sdkconfig.esp32c3" -ErrorAction SilentlyContinue
Remove-Item -Path "sdkconfig.esp32dev" -ErrorAction SilentlyContinue
Remove-Item -Path "sdkconfig" -ErrorAction SilentlyContinue

pio run -e $envTarget -t fullclean

# 3. Optional Erase
if ($Erase) {
    Write-Host "Erasing flash for environment: [$envTarget]..." -ForegroundColor Yellow
    pio run -e $envTarget -t erase
}

# 4. Execute Build & Upload
Write-Host "`nBuilding and uploading for environment: [$envTarget]..." -ForegroundColor Cyan
pio run -e $envTarget -t upload

if ($LastExitCode -ne 0) {
    Write-Host "`nERROR: Build or Upload failed!" -ForegroundColor Red
    exit $LastExitCode
}

# 5. POST-BUILD VERIFICATION (Security Check)
Write-Host "`nRunning Safety Verifications..." -ForegroundColor Cyan
$configHeader = ".pio\build\$envTarget\config\sdkconfig.h"
if (Test-Path $configHeader) {
    $hdrConfig = Select-String -Path $configHeader -Pattern "CONFIG_HTTPD_MAX_REQ_HDR_LEN"
    Write-Host "Detected Limit: $($hdrConfig.Line.Trim())" -ForegroundColor Gray
    
    if ($hdrConfig -match "512") {
        Write-Host "CRITICAL ERROR: Compiler ignored the 4096-byte limit and used 512!" -ForegroundColor Red
        Write-Host "Please run 'pio run -t fullclean' manually and try again." -ForegroundColor Red
        exit 1
    } else {
        Write-Host "Verification Success: 4096-byte limit is active!" -ForegroundColor Green
    }
}

Write-Host "`nMISSION ACCOMPLISHED!" -ForegroundColor Green
