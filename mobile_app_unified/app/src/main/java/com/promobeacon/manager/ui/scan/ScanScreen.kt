package com.promobeacon.manager.ui.scan

import android.Manifest
import android.os.Build
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.BluetoothSearching
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.promobeacon.manager.domain.repository.ScannedDevice
import com.promobeacon.manager.ui.components.DeviceScanCard
import com.promobeacon.manager.ui.components.LoadingIndicator
import com.google.accompanist.permissions.ExperimentalPermissionsApi
import com.google.accompanist.permissions.MultiplePermissionsState
import com.google.accompanist.permissions.rememberMultiplePermissionsState

/**
 * Device Scan Page
 */
@OptIn(ExperimentalMaterial3Api::class, ExperimentalPermissionsApi::class)
@Composable
fun ScanScreen(
    onNavigateToDashboard: () -> Unit,
    viewModel: ScanViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()

    // Permission request
    val permissions = rememberMultiplePermissionsState(
        permissions = listOf(
            Manifest.permission.BLUETOOTH_SCAN,
            Manifest.permission.BLUETOOTH_CONNECT,
        ).let { 
            if (Build.VERSION.SDK_INT <= Build.VERSION_CODES.R) {
                it + Manifest.permission.ACCESS_FINE_LOCATION
            } else it
        }
    )

    // Monitor navigation events
    LaunchedEffect(Unit) {
        viewModel.navigationEvent.collect { event ->
            when (event) {
                is NavigationEvent.NavigateToDashboard -> onNavigateToDashboard()
            }
        }
    }

    // Check permissions and start scanning
    LaunchedEffect(permissions.allPermissionsGranted) {
        if (permissions.allPermissionsGranted && uiState.devices.isEmpty()) {
            viewModel.startScan()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "Scan Devices",
                        fontWeight = FontWeight.Bold
                    )
                },
                actions = {
                    IconButton(
                        onClick = { viewModel.startScan() },
                        enabled = !uiState.isScanning && permissions.allPermissionsGranted
                    ) {
                        Icon(
                            imageVector = Icons.Default.Refresh,
                            contentDescription = "Refresh"
                        )
                    }
                }
            )
        }
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            when {
                // Permissions not granted
                !permissions.allPermissionsGranted -> {
                    PermissionRequest(
                        onRequestPermission = { permissions.launchMultiplePermissionRequest() }
                    )
                }

                // Scanning with no devices
                uiState.isScanning && uiState.devices.isEmpty() -> {
                    LoadingIndicator(text = "Scanning...")
                }

                // No devices
                uiState.devices.isEmpty() -> {
                    EmptyDeviceList(
                        onRetry = { viewModel.startScan() }
                    )
                }

                // Has device list
                else -> {
                    DeviceList(
                        devices = uiState.devices,
                        connectingDevice = uiState.connectingDevice,
                        onConnect = { viewModel.connectDevice(it) }
                    )
                }
            }

            // Error snackbar
            uiState.error?.let { error ->
                Snackbar(
                    modifier = Modifier
                        .align(Alignment.BottomCenter)
                        .padding(16.dp),
                    action = {
                        TextButton(onClick = { viewModel.clearError() }) {
                            Text("OK")
                        }
                    }
                ) {
                    Text(error)
                }
            }
        }
    }
}

/**
 * Permission Request
 */
@Composable
private fun PermissionRequest(
    onRequestPermission: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Icon(
            imageVector = Icons.Default.BluetoothSearching,
            contentDescription = null,
            modifier = Modifier.size(64.dp),
            tint = MaterialTheme.colorScheme.primary
        )

        Spacer(modifier = Modifier.height(24.dp))

        Text(
            text = "Permission Required",
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Bold
        )

        Spacer(modifier = Modifier.height(16.dp))

        Text(
            text = "This app requires Bluetooth and Location permissions to scan for nearby PromoBeacon devices.",
            style = MaterialTheme.typography.bodyMedium,
            textAlign = TextAlign.Center,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(modifier = Modifier.height(24.dp))

        Button(onClick = onRequestPermission) {
            Text("Grant Permission")
        }
    }
}

/**
 * Device List
 */
@Composable
private fun DeviceList(
    devices: List<ScannedDevice>,
    connectingDevice: ScannedDevice?,
    onConnect: (ScannedDevice) -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp)
    ) {
        Text(
            text = "Found ${devices.size} devices",
            style = MaterialTheme.typography.titleSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(vertical = 8.dp)
        )

        LazyColumn(
            verticalArrangement = Arrangement.spacedBy(12.dp),
            modifier = Modifier.padding(bottom = 16.dp)
        ) {
            items(devices, key = { it.address }) { device ->
                DeviceScanCard(
                    device = device,
                    isConnecting = connectingDevice?.address == device.address &&
                            device == connectingDevice,
                    onConnect = { onConnect(device) }
                )
            }
        }
    }
}

/**
 * Empty Device List
 */
@Composable
private fun EmptyDeviceList(
    onRetry: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Icon(
            imageVector = Icons.Default.BluetoothSearching,
            contentDescription = null,
            modifier = Modifier.size(64.dp),
            tint = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(modifier = Modifier.height(24.dp))

        Text(
            text = "No Devices Found",
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Bold
        )

        Spacer(modifier = Modifier.height(16.dp))

        Text(
            text = "Please ensure the PromoBeacon device is powered on and nearby.",
            style = MaterialTheme.typography.bodyMedium,
            textAlign = TextAlign.Center,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Spacer(modifier = Modifier.height(24.dp))

        OutlinedButton(onClick = onRetry) {
            Icon(
                imageVector = Icons.Default.Refresh,
                contentDescription = null,
                modifier = Modifier.size(20.dp)
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text("Scan Again")
        }
    }
}

/**
 * Multiple Permission Request
 */
@OptIn(com.google.accompanist.permissions.ExperimentalPermissionsApi::class)
@Composable
fun rememberMultiplePermissions(): MultiplePermissionsState {
    return rememberMultiplePermissionsState(
        permissions = buildList {
            add(Manifest.permission.BLUETOOTH_SCAN)
            add(Manifest.permission.BLUETOOTH_CONNECT)
            if (Build.VERSION.SDK_INT <= Build.VERSION_CODES.R) {
                add(Manifest.permission.ACCESS_FINE_LOCATION)
            }
        }
    )
}
