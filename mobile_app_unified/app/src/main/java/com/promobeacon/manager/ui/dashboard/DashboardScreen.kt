package com.promobeacon.manager.ui.dashboard

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.DialogProperties
import androidx.hilt.navigation.compose.hiltViewModel
import com.promobeacon.manager.BuildConfig
import com.promobeacon.manager.data.ble.AuthenticationState
import com.promobeacon.manager.domain.model.ConnectionState
import com.promobeacon.manager.domain.model.GModeConfig
import com.promobeacon.manager.ui.components.*
import com.promobeacon.manager.ui.theme.*
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch
import javax.inject.Inject

/**
 * Device Console Screen
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(
    onNavigateBack: () -> Unit,
    viewModel: DashboardViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()

    // Return to scan screen when disconnected
    LaunchedEffect(uiState.connectionState) {
        if (uiState.connectionState == ConnectionState.DISCONNECTED) {
            onNavigateBack()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "Device Console",
                        fontWeight = FontWeight.Bold
                    )
                },
                navigationIcon = {
                    IconButton(onClick = {
                        viewModel.disconnect()
                    }) {
                        Icon(
                            imageVector = Icons.Default.ArrowBack,
                            contentDescription = "Back"
                        )
                    }
                },
                actions = {
                    // Authentication status indicator
                    if (uiState.authenticationState == AuthenticationState.AUTHENTICATED) {
                        Icon(
                            imageVector = Icons.Default.Verified,
                            contentDescription = "Authenticated",
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.padding(end = 8.dp)
                        )
                    }

                    // Disconnect button
                    TextButton(
                        onClick = {
                            viewModel.disconnect()
                        },
                        colors = ButtonDefaults.textButtonColors(
                            contentColor = MaterialTheme.colorScheme.error
                        )
                    ) {
                        Icon(
                            imageVector = Icons.Default.BluetoothDisabled,
                            contentDescription = null,
                            modifier = Modifier.size(20.dp)
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("Disconnect")
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
            if (uiState.isLoading) {
                LoadingIndicator(text = "Processing...")
            } else {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .verticalScroll(rememberScrollState())
                        .padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    // Connection status card
                    ConnectionStatusCard(
                        connectionState = uiState.connectionState,
                        deviceStatus = uiState.deviceStatus,
                        isAuthenticated = uiState.authenticationState == AuthenticationState.AUTHENTICATED
                    )

                    // Show lock overlay if not authenticated
                    if (uiState.authenticationState != AuthenticationState.AUTHENTICATED) {
                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { 
                                    // Manually trigger authentication dialog
                                    viewModel.triggerAuthentication()
                                },
                            colors = CardDefaults.cardColors(
                                containerColor = MaterialTheme.colorScheme.errorContainer
                            )
                        ) {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(16.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Lock,
                                    contentDescription = null,
                                    tint = MaterialTheme.colorScheme.error
                                )
                                Spacer(modifier = Modifier.width(12.dp))
                                Column {
                                    Text(
                                        text = "Authentication Required",
                                        style = MaterialTheme.typography.titleSmall,
                                        color = MaterialTheme.colorScheme.onErrorContainer
                                    )
                                    Text(
                                        text = "Please enter your authentication token to configure this device.",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onErrorContainer.copy(alpha = 0.7f)
                                    )
                                }
                            }
                        }
                    }

                    // G Mode configuration (only shown when authenticated)
                    if (uiState.authenticationState == AuthenticationState.AUTHENTICATED) {
                        GModeSettingsCard(
                            config = uiState.gModeConfig,
                            isSaving = uiState.isSaving,
                            onSaveConfig = { viewModel.updateGModeConfig(it) }
                        )

                        // Device actions
                        DeviceActionsCard(
                            onReboot = { viewModel.reboot() },
                            onResetDefaults = { viewModel.resetToDefaults() },
                            onExportStats = { ip -> viewModel.exportStatsCsv(ip) },
                            onUploadPortal = { viewModel.uploadPortalContent(it) }
                        )
                    }

                    // Upload progress indicator
                    if (uiState.isUploading) {
                        UploadProgressCard(
                            progress = uiState.uploadProgress,
                            totalBytes = uiState.uploadTotalBytes
                        )
                    }
                }
            }

            // Error and Success snackbars (Error takes priority)
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
            } ?: uiState.successMessage?.let { message ->
                Snackbar(
                    modifier = Modifier
                        .align(Alignment.BottomCenter)
                        .padding(16.dp),
                    containerColor = Success,
                    action = {
                        TextButton(onClick = { viewModel.clearSuccessMessage() }) {
                            Text("OK", color = androidx.compose.ui.graphics.Color.White)
                        }
                    }
                ) {
                    Text(message, color = androidx.compose.ui.graphics.Color.White)
                }
            }

            // Authentication Dialog (Compose Native)
            if (uiState.authenticationState != AuthenticationState.AUTHENTICATED && 
                uiState.authenticationState != AuthenticationState.NOT_AUTHENTICATED) {
                AdministratorAuthDialog(
                    authState = uiState.authenticationState,
                    onAuthenticate = { viewModel.authenticate(it) },
                    onDismiss = {
                        viewModel.disconnect()
                    }
                )
            }
        }
    }
}

/**
 * Administrator Authentication Dialog (Pure Compose)
 */
@Composable
private fun AdministratorAuthDialog(
    authState: AuthenticationState,
    onAuthenticate: (String) -> Unit,
    onDismiss: () -> Unit
) {
    var password by remember { mutableStateOf("") }
    val isAuthenticating = authState == AuthenticationState.AUTHENTICATING

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text(
                text = stringResource(com.promobeacon.manager.R.string.authentication_required),
                fontWeight = FontWeight.Bold
            )
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text(
                    text = stringResource(com.promobeacon.manager.R.string.enter_auth_token),
                    style = MaterialTheme.typography.bodyMedium
                )
                
                OutlinedTextField(
                    value = password,
                    onValueChange = { password = it },
                    label = { Text(stringResource(com.promobeacon.manager.R.string.auth_token)) },
                    placeholder = { Text(stringResource(com.promobeacon.manager.R.string.token_hint_format)) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    enabled = !isAuthenticating
                )

                if (authState == AuthenticationState.FAILED) {
                    Text(
                        text = stringResource(com.promobeacon.manager.R.string.authentication_failed),
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.bodySmall
                    )
                }

                if (authState == AuthenticationState.LOCKED) {
                    Text(
                        text = stringResource(com.promobeacon.manager.R.string.device_locked),
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.bodySmall
                    )
                }

                if (isAuthenticating) {
                    LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
                }
            }
        },
        confirmButton = {
            Button(
                onClick = { onAuthenticate(password) },
                enabled = password.length >= 4 && !isAuthenticating
            ) {
                Text(stringResource(com.promobeacon.manager.R.string.authenticate))
            }
        },
        dismissButton = {
            TextButton(
                onClick = onDismiss,
                enabled = !isAuthenticating
            ) {
                Text("Cancel")
            }
        },
        properties = DialogProperties(
            dismissOnBackPress = !isAuthenticating,
            dismissOnClickOutside = false
        )
    )
}

/**
 * Connection Status Card
 */
@Composable
private fun ConnectionStatusCard(
    connectionState: ConnectionState,
    deviceStatus: com.promobeacon.manager.domain.model.DeviceStatus,
    isAuthenticated: Boolean = false
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            // Title
            Text(
                text = "Connection Status",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )

            Spacer(modifier = Modifier.height(12.dp))

            // Status indicator
            ConnectionStatusIndicator(
                isConnected = connectionState == ConnectionState.CONNECTED,
                isAdvertising = deviceStatus.isAdvertising,
                isAuthenticated = isAuthenticated
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Status stats
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly
            ) {
                StatusCard(
                    title = "Uptime",
                    value = formatUptime(deviceStatus.uptimeMs),
                    icon = Icons.Default.Timer,
                    modifier = Modifier.weight(1f)
                )

                Spacer(modifier = Modifier.width(8.dp))

                StatusCard(
                    title = "Connected Clients",
                    value = deviceStatus.clientCount.toString(),
                    icon = Icons.Default.People,
                    modifier = Modifier.weight(1f)
                )

                Spacer(modifier = Modifier.width(8.dp))

                StatusCard(
                    title = "Signal Strength",
                    value = "${deviceStatus.rssi} dBm",
                    icon = Icons.Default.SignalWifi4Bar,
                    modifier = Modifier.weight(1f)
                )
            }
        }
    }
}

/**
 * G Mode Settings Card
 */
@Composable
private fun GModeSettingsCard(
    config: GModeConfig,
    isSaving: Boolean,
    onSaveConfig: (GModeConfig) -> Unit
) {
    var ssid by remember { mutableStateOf(config.ssid) }
    var promoText by remember { mutableStateOf(config.promoText) }
    var showPasswordField by remember { mutableStateOf(config.password.isNotEmpty()) }
    var password by remember { mutableStateOf(config.password) }
    var newAdminPassword by remember { mutableStateOf("") }

    LaunchedEffect(config) {
        ssid = config.ssid
        promoText = config.promoText
        showPasswordField = config.password.isNotEmpty()
        password = config.password
        newAdminPassword = config.newAdminPassword
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            Text(
                text = "Device Configuration",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Network name
            OutlinedTextField(
                value = ssid,
                onValueChange = { ssid = it },
                label = { Text("Network Name (SSID)") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                leadingIcon = {
                    Icon(Icons.Default.Wifi, contentDescription = null)
                }
            )

            Spacer(modifier = Modifier.height(12.dp))

            // Password toggle
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Switch(
                    checked = showPasswordField,
                    onCheckedChange = { showPasswordField = it }
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text("Set Password")
            }

            // Password field
            if (showPasswordField) {
                Spacer(modifier = Modifier.height(12.dp))
                OutlinedTextField(
                    value = password,
                    onValueChange = { password = it },
                    label = { Text("WiFi Password") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    leadingIcon = {
                        Icon(Icons.Default.Lock, contentDescription = null)
                    },
                    visualTransformation = androidx.compose.ui.text.input.PasswordVisualTransformation()
                )
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Default portal message (only shown when no custom HTML is uploaded)
            OutlinedTextField(
                value = promoText,
                onValueChange = { promoText = it },
                label = { Text("Default Portal Message") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                leadingIcon = {
                    Icon(Icons.Default.TextFields, contentDescription = null)
                },
                supportingText = {
                    Text(
                        "Only shown when no custom HTML portal is uploaded. Uploaded HTML replaces this text.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Admin password change
            Divider(modifier = Modifier.padding(vertical = 8.dp))
            Text(
                text = "Administrator Security",
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.primary
            )
            Spacer(modifier = Modifier.height(8.dp))
            OutlinedTextField(
                value = newAdminPassword,
                onValueChange = { newAdminPassword = it },
                label = { Text("New Administrator Password") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                leadingIcon = {
                    Icon(Icons.Default.Security, contentDescription = null)
                },
                supportingText = {
                    Text("Change the default 'admin123' password. Only applies if not empty.")
                },
                visualTransformation = androidx.compose.ui.text.input.PasswordVisualTransformation()
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Save button
            Button(
                onClick = {
                    onSaveConfig(
                        config.copy(
                            ssid = ssid,
                            promoText = promoText,
                            password = if (showPasswordField) password else "",
                            newAdminPassword = newAdminPassword
                        )
                    )
                },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isSaving
            ) {
                if (isSaving) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        strokeWidth = 2.dp,
                        color = MaterialTheme.colorScheme.onPrimary
                    )
                } else {
                    Icon(Icons.Default.Save, contentDescription = null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Save Config")
                }
            }
        }
    }
}

/**
 * Device Actions Card
 */
@Composable
private fun DeviceActionsCard(
    onReboot: () -> Unit,
    onResetDefaults: () -> Unit,
    onExportStats: (String) -> Unit,
    onUploadPortal: (String) -> Unit
) {
    var showRebootDialog by remember { mutableStateOf(false) }
    var showResetDialog by remember { mutableStateOf(false) }
    var showExportDialog by remember { mutableStateOf(false) }
    var showPortalUploadDialog by remember { mutableStateOf(false) }
    var deviceIp by remember { mutableStateOf("192.168.4.1") }

    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            Text(
                text = "Device Actions",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )

            Spacer(modifier = Modifier.height(12.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                // Reboot button
                OutlinedButton(
                    onClick = { showRebootDialog = true },
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.outlinedButtonColors(
                        contentColor = MaterialTheme.colorScheme.error
                    )
                ) {
                    Icon(Icons.Default.RestartAlt, contentDescription = null)
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Reboot")
                }

                // Factory reset button
                OutlinedButton(
                    onClick = { showResetDialog = true },
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.outlinedButtonColors(
                        contentColor = MaterialTheme.colorScheme.error
                    )
                ) {
                    Icon(Icons.Default.Restore, contentDescription = null)
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Reset")
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Export stats button
            OutlinedButton(
                onClick = { showExportDialog = true },
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.outlinedButtonColors(
                    contentColor = MaterialTheme.colorScheme.primary
                )
            ) {
                Icon(Icons.Default.FileDownload, contentDescription = null)
                Spacer(modifier = Modifier.width(8.dp))
                Text("Export Stats (CSV)")
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Upload portal button
            OutlinedButton(
                onClick = { showPortalUploadDialog = true },
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.outlinedButtonColors(
                    contentColor = MaterialTheme.colorScheme.tertiary
                )
            ) {
                Icon(Icons.Default.Upload, contentDescription = null)
                Spacer(modifier = Modifier.width(8.dp))
                Text("Upload Portal (HTML)")
            }
        }
    }

    // Reboot confirmation dialog
    if (showRebootDialog) {
        AlertDialog(
            onDismissRequest = { showRebootDialog = false },
            icon = { Icon(Icons.Default.RestartAlt, contentDescription = null) },
            title = { Text("Confirm Reboot") },
            text = { Text("Are you sure you want to reboot the device? This will disconnect the current connection.") },
            confirmButton = {
                TextButton(
                    onClick = {
                        showRebootDialog = false
                        onReboot()
                    }
                ) {
                    Text("Confirm")
                }
            },
            dismissButton = {
                TextButton(onClick = { showRebootDialog = false }) {
                    Text("Cancel")
                }
            }
        )
    }

    // Reset confirmation dialog
    if (showResetDialog) {
        AlertDialog(
            onDismissRequest = { showResetDialog = false },
            icon = { Icon(Icons.Default.Warning, contentDescription = null) },
            title = { Text("Confirm Reset") },
            text = {
                Text(
                    "Are you sure you want to factory reset? All configurations will be cleared.\n\nThis action cannot be undone!"
                )
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        showResetDialog = false
                        onResetDefaults()
                    },
                    colors = ButtonDefaults.textButtonColors(
                        contentColor = MaterialTheme.colorScheme.error
                    )
                ) {
                    Text("Confirm")
                }
            },
            dismissButton = {
                TextButton(onClick = { showResetDialog = false }) {
                    Text("Cancel")
                }
            }
        )
    }

    // Export stats dialog
    if (showExportDialog) {
        AlertDialog(
            onDismissRequest = { showExportDialog = false },
            icon = { Icon(Icons.Default.FileDownload, contentDescription = null) },
            title = { Text("Export Statistics") },
            text = {
                Column {
                    Text(
                        "Please enter the device IP address, ensuring your phone is connected to the device's WiFi network.",
                        style = MaterialTheme.typography.bodyMedium
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    OutlinedTextField(
                        value = deviceIp,
                        onValueChange = { deviceIp = it },
                        label = { Text("Device IP Address") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                        supportingText = {
                            Text("Default: 192.168.4.1")
                        }
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        "Tip: The device default IP address is 192.168.4.1",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )

                    Spacer(modifier = Modifier.height(8.dp))
                    
                    Text(
                        text = "App Version: v${BuildConfig.VERSION_NAME}",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f),
                        modifier = Modifier.align(Alignment.End)
                    )
                }
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        showExportDialog = false
                        onExportStats(deviceIp)
                    }
                ) {
                    Text("Export")
                }
            },
            dismissButton = {
                TextButton(onClick = { showExportDialog = false }) {
                    Text("Cancel")
                }
            }
        )
    }

    // Upload portal dialog
    if (showPortalUploadDialog) {
        PortalUploadDialog(
            onDismiss = { showPortalUploadDialog = false },
            onUpload = { htmlContent ->
                showPortalUploadDialog = false
                onUploadPortal(htmlContent)
            }
        )
    }
}

/**
 * Status Detail Component
 */
@Composable
private fun StatusCard(
    title: String,
    value: String,
    icon: ImageVector,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            modifier = Modifier.size(24.dp),
            tint = MaterialTheme.colorScheme.primary
        )
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = value,
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Bold
        )
        Text(
            text = title,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center
        )
    }
}

/**
 * Connection Status Indicator
 */
@Composable
private fun ConnectionStatusIndicator(
    isConnected: Boolean,
    isAdvertising: Boolean,
    isAuthenticated: Boolean
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(16.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        StatusDot(
            label = "Connected",
            isActive = isConnected,
            activeColor = MaterialTheme.colorScheme.primary
        )
        StatusDot(
            label = "Advertising",
            isActive = isAdvertising,
            activeColor = MaterialTheme.colorScheme.secondary
        )
        StatusDot(
            label = "Authenticated",
            isActive = isAuthenticated,
            activeColor = MaterialTheme.colorScheme.tertiary
        )
    }
}

@Composable
private fun StatusDot(
    label: String,
    isActive: Boolean,
    activeColor: androidx.compose.ui.graphics.Color
) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(
            modifier = Modifier
                .size(8.dp)
                .clip(CircleShape)
                .background(if (isActive) activeColor else MaterialTheme.colorScheme.outline.copy(alpha = 0.3f))
        )
        Spacer(modifier = Modifier.width(4.dp))
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall,
            color = if (isActive) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

/**
 * Portal Upload Dialog
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun PortalUploadDialog(
    onDismiss: () -> Unit,
    onUpload: (String) -> Unit
) {
    var htmlContent by remember { mutableStateOf("") }
    val context = LocalContext.current
    val launcher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument()
    ) { uri: Uri? ->
        uri?.let {
            val content = readHtmlFileFromUri(context, it)
            if (content != null) {
                htmlContent = content
            }
        }
    }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text(
                "Upload Custom Portal",
                fontWeight = FontWeight.Bold
            )
        },
        text = {
            Column {
                Text(
                    "Upload a custom HTML page to be displayed as the captive portal.",
                    style = MaterialTheme.typography.bodyMedium
                )
                
                Spacer(modifier = Modifier.height(16.dp))
                
                Button(
                    onClick = { launcher.launch(arrayOf("text/html")) },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Icon(Icons.Default.FileOpen, contentDescription = null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Select HTML File")
                }

                Spacer(modifier = Modifier.height(12.dp))

                OutlinedTextField(
                    value = htmlContent,
                    onValueChange = { htmlContent = it },
                    label = { Text("HTML Content Preview") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(min = 120.dp, max = 240.dp),
                    readOnly = true,
                    supportingText = {
                        Text(
                            "Size: ${formatBytes(htmlContent.toByteArray(Charsets.UTF_8).size)} / 16 KB",
                            color = if (htmlContent.toByteArray(Charsets.UTF_8).size > 16384) {
                                MaterialTheme.colorScheme.error
                            } else {
                                MaterialTheme.colorScheme.onSurfaceVariant
                            }
                        )
                    },
                    isError = htmlContent.toByteArray(Charsets.UTF_8).size > 16384
                )

                Spacer(modifier = Modifier.height(8.dp))

                Text(
                    "Tip: Supports standard HTML, max 32KB. The page will automatically display when users connect to the device WiFi.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        },
        confirmButton = {
            TextButton(
                onClick = { onUpload(htmlContent) },
                enabled = htmlContent.isNotBlank() &&
                         htmlContent.toByteArray(Charsets.UTF_8).size <= 16384
            ) {
                Text("Upload")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel")
            }
        }
    )
}

/**
 * Read HTML file content from URI
 */
private fun readHtmlFileFromUri(context: android.content.Context, uri: Uri): String? {
    return try {
        val inputStream = context.contentResolver.openInputStream(uri)
        inputStream?.bufferedReader()?.use { reader ->
            val content = reader.readText()
            if (content.toByteArray(Charsets.UTF_8).size > 16384) null else content
        }
    } catch (e: Exception) {
        e.printStackTrace()
        null
    }
}

/**
 * Upload Progress Card
 */
@Composable
private fun UploadProgressCard(
    progress: Int,
    totalBytes: Int
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.tertiaryContainer
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(
                imageVector = Icons.Default.CloudUpload,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onTertiaryContainer,
                modifier = Modifier.size(48.dp)
            )

            Spacer(modifier = Modifier.height(12.dp))

            Text(
                text = "Uploading portal page...",
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onTertiaryContainer
            )

            Spacer(modifier = Modifier.height(12.dp))

            LinearProgressIndicator(
                progress = progress / 100f,
                modifier = Modifier.fillMaxWidth(),
                color = MaterialTheme.colorScheme.tertiary,
                trackColor = MaterialTheme.colorScheme.tertiaryContainer
            )

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = "$progress% - ${formatBytes(totalBytes)}",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onTertiaryContainer
            )

            Text(
                text = "Please wait, transferring via Bluetooth...",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onTertiaryContainer.copy(alpha = 0.7f)
            )
        }
    }
}

/**
 * Format bytes
 */
private fun formatBytes(bytes: Int): String {
    return when {
        bytes < 1024 -> "$bytes B"
        bytes < 1024 * 1024 -> "${bytes / 1024} KB"
        else -> "${bytes / (1024 * 1024)} MB"
    }
}

/**
 * Format uptime
 */
private fun formatUptime(uptimeMs: Long): String {
    val seconds = uptimeMs / 1000
    val days = seconds / 86400
    val hours = (seconds % 86400) / 3600
    val minutes = (seconds % 3600) / 60
    val remainingSeconds = seconds % 60
    return when {
        days > 0 -> "${days}d ${hours}h ${minutes}m"
        hours > 0 -> "${hours}h ${minutes}m ${remainingSeconds}s"
        else -> "${minutes}m ${remainingSeconds}s"
    }
}
