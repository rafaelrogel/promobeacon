package com.promobeacon.manager.di

import android.content.Context
import com.promobeacon.manager.data.ble.BleClient
import com.promobeacon.manager.data.repository.DeviceRepositoryImpl
import com.promobeacon.manager.domain.repository.DeviceRepository
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

/**
 * Application-level Hilt module
 */
@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    /**
     * Provide BleClient singleton
     */
    @Provides
    @Singleton
    fun provideBleClient(
        @ApplicationContext context: Context
    ): BleClient {
        val client = BleClient(context)
        client.initialize()
        return client
    }

    /**
     * Provide DeviceRepository implementation
     */
    @Provides
    @Singleton
    fun provideDeviceRepository(
        bleClient: BleClient,
        @ApplicationContext context: Context
    ): DeviceRepository {
        return DeviceRepositoryImpl(bleClient, context)
    }
}
