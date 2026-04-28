package com.promobeacon.manager.ui.navigation

/**
 * 導航路由定義
 */
sealed class Screen(val route: String) {
    object Scanner : Screen("scanner")
    object Dashboard : Screen("dashboard")
    object Settings : Screen("settings")
}

/**
 * 導航參數
 */
object NavArgs {
    const val DEVICE_ADDRESS = "device_address"
    const val DEVICE_NAME = "device_name"
}
