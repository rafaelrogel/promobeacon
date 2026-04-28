package com.promobeacon.manager

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.padding
import androidx.compose.ui.unit.dp
import androidx.compose.material3.Text
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import com.promobeacon.manager.ui.theme.PromoBeaconManagerTheme
import com.promobeacon.manager.ui.navigation.Screen
import com.promobeacon.manager.ui.scan.ScanScreen
import com.promobeacon.manager.ui.dashboard.DashboardScreen
import dagger.hilt.android.AndroidEntryPoint

/**
 * Main Activity
 */
@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        setContent {
            PromoBeaconManagerTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = Color.White // Force white for diagnostic
                ) {
                    Column {
                        // Diagnostic marker
                        Text(
                            text = "APP OK - V2.0.3",
                            color = Color.Blue,
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(16.dp)
                        )
                        MainNavigation()
                    }
                }
            }
        }
    }
}

/**
 * Main Navigation System
 */
@Composable
fun MainNavigation(
    navController: NavHostController = rememberNavController()
) {
    NavHost(
        navController = navController,
        startDestination = Screen.Scanner.route
    ) {
        // Scanner page
        composable(Screen.Scanner.route) {
            ScanScreen(
                onNavigateToDashboard = {
                    navController.navigate(Screen.Dashboard.route) {
                        popUpTo(Screen.Scanner.route) { inclusive = true }
                    }
                }
            )
        }

        // Dashboard page
        composable(Screen.Dashboard.route) {
            DashboardScreen(
                onNavigateBack = {
                    navController.popBackStack()
                }
            )
        }
    }
}
