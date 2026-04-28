package com.promobeacon.manager

import android.app.Application
import com.promobeacon.manager.data.ble.BleClient
import dagger.hilt.android.HiltAndroidApp
import javax.inject.Inject

/**
 * PromoBeacon管理應用程序類
 * 使用Hilt進行依賴注入
 */
@HiltAndroidApp
class PromoBeaconApp : Application() {

    override fun onCreate() {
        super.onCreate()
        // 應用程序初始化邏輯
    }
}
