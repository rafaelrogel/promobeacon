package com.promobeacon.manager.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.promobeacon.manager.domain.model.DeviceMode
import com.promobeacon.manager.domain.repository.ScannedDevice
import com.promobeacon.manager.domain.repository.SignalLevel
import com.promobeacon.manager.ui.theme.*

/**
 * 設備掃描項目卡片
 */
@Composable
fun DeviceScanCard(
    device: ScannedDevice,
    isConnecting: Boolean,
    onConnect: () -> Unit,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // 設備圖標
            Box(
                modifier = Modifier
                    .size(48.dp)
                    .clip(CircleShape)
                    .background(MaterialTheme.colorScheme.primaryContainer),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.Bluetooth,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onPrimaryContainer
                )
            }

            Spacer(modifier = Modifier.width(16.dp))

            // 設備信息
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = device.name,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )

                Spacer(modifier = Modifier.height(4.dp))

                Text(
                    text = device.address,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                Spacer(modifier = Modifier.height(4.dp))

                Row(verticalAlignment = Alignment.CenterVertically) {
                    SignalStrengthIndicator(level = device.getSignalLevel())
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "${device.rssi} dBm",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            // Connect Button
            Button(
                onClick = onConnect,
                enabled = !isConnecting,
                modifier = Modifier.widthIn(min = 124.dp)
            ) {
                if (isConnecting) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        strokeWidth = 2.dp,
                        color = MaterialTheme.colorScheme.onPrimary
                    )
                } else {
                    Text("Connect")
                }
            }
        }
    }
}

/**
 * 信號強度指示器
 */
@Composable
fun SignalStrengthIndicator(
    level: SignalLevel,
    modifier: Modifier = Modifier
) {
    val color = when (level) {
        SignalLevel.EXCELLENT -> SignalExcellent
        SignalLevel.GOOD -> SignalGood
        SignalLevel.FAIR -> SignalFair
        SignalLevel.POOR -> SignalPoor
    }

    Row(modifier = modifier) {
        repeat(4) { index ->
            Box(
                modifier = Modifier
                    .size(width = 3.dp, height = ((index + 1) * 4).dp)
                    .padding(1.dp)
                    .background(
                        color = if (index <= (3 - level.ordinal)) color else color.copy(alpha = 0.3f),
                        shape = RoundedCornerShape(1.dp)
                    )
            )
        }
    }
}

/**
 * 模式切換卡片
 */
@Composable
fun ModeSwitchCard(
    currentMode: DeviceMode,
    onSwitchMode: () -> Unit,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = "Current Mode",
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Spacer(modifier = Modifier.height(16.dp))

            // 模式選擇器
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                // G模式按鈕
                ModeButton(
                    text = "G Mode",
                    icon = Icons.Default.Wifi,
                    isSelected = currentMode == DeviceMode.MODE_G,
                    color = ModeG,
                    modifier = Modifier.weight(1f)
                )

                // E模式按鈕
                ModeButton(
                    text = "E Mode",
                    icon = Icons.Default.Bluetooth,
                    isSelected = currentMode == DeviceMode.MODE_E,
                    color = ModeE,
                    modifier = Modifier.weight(1f)
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            // 切換按鈕
            OutlinedButton(
                onClick = onSwitchMode,
                modifier = Modifier.fillMaxWidth()
            ) {
                Icon(
                    imageVector = Icons.Default.SwapHoriz,
                    contentDescription = null,
                    modifier = Modifier.size(20.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text("Switch Mode")
            }
        }
    }
}

/**
 * 模式按鈕
 */
@Composable
private fun ModeButton(
    text: String,
    icon: ImageVector,
    isSelected: Boolean,
    color: Color,
    modifier: Modifier = Modifier
) {
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(12.dp),
        color = if (isSelected) color else color.copy(alpha = 0.1f),
        border = if (!isSelected) ButtonDefaults.outlinedButtonBorder else null
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = if (isSelected) Color.White else color,
                modifier = Modifier.size(24.dp)
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = text,
                color = if (isSelected) Color.White else color,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium
            )
        }
    }
}

/**
 * 狀態卡片
 */
@Composable
fun StatusCard(
    title: String,
    value: String,
    icon: ImageVector,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant
        )
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.primary,
                modifier = Modifier.size(28.dp)
            )

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = value,
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold
            )

            Text(
                text = title,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

/**
 * 連接狀態指示器
 */
@Composable
fun ConnectionStatusIndicator(
    isConnected: Boolean,
    isAdvertising: Boolean,
    isAuthenticated: Boolean = false,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier,
        verticalAlignment = Alignment.CenterVertically
    ) {
        // 連接狀態
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(8.dp)
                    .clip(CircleShape)
                    .background(if (isConnected) Connected else Disconnected)
            )
            Spacer(modifier = Modifier.width(4.dp))
            Text(
                text = if (isConnected) "Connected" else "Disconnected",
                style = MaterialTheme.typography.bodySmall,
                color = if (isConnected) Connected else Disconnected
            )
        }

        Spacer(modifier = Modifier.width(16.dp))

        // 廣播狀態
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(8.dp)
                    .clip(CircleShape)
                    .background(if (isAdvertising) Advertising else Disconnected)
            )
            Spacer(modifier = Modifier.width(4.dp))
            Text(
                text = if (isAdvertising) "Advertising" else "Stopped",
                style = MaterialTheme.typography.bodySmall,
                color = if (isAdvertising) Advertising else Disconnected
            )
        }

        if (isConnected) {
            Spacer(modifier = Modifier.width(16.dp))

            // 認證狀態
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(8.dp)
                        .clip(CircleShape)
                        .background(if (isAuthenticated) Success else Error)
                )
                Spacer(modifier = Modifier.width(4.dp))
                Text(
                    text = if (isAuthenticated) "Authenticated" else "Auth Required",
                    style = MaterialTheme.typography.bodySmall,
                    color = if (isAuthenticated) Success else Error
                )
            }
        }
    }
}

/**
 * 載入指示器
 */
@Composable
fun LoadingIndicator(
    text: String = "Loading...",
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier.fillMaxSize(),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        CircularProgressIndicator()
        Spacer(modifier = Modifier.height(16.dp))
        Text(
            text = text,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

/**
 * 錯誤提示
 */
@Composable
fun ErrorMessage(
    message: String,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier
) {
    Snackbar(
        modifier = modifier.padding(16.dp),
        action = {
            TextButton(onClick = onDismiss) {
                Text("OK")
            }
        },
        containerColor = Error,
        contentColor = Color.White,
        actionContentColor = Color.White
    ) {
        Text(message)
    }
}

/**
 * 成功提示
 */
@Composable
fun SuccessMessage(
    message: String,
    onDismiss: () -> Unit,
    modifier: Modifier = Modifier
) {
    Snackbar(
        modifier = modifier.padding(16.dp),
        action = {
            TextButton(onClick = onDismiss) {
                Text("OK")
            }
        },
        containerColor = Success,
        contentColor = Color.White,
        actionContentColor = Color.White
    ) {
        Text(message)
    }
}
