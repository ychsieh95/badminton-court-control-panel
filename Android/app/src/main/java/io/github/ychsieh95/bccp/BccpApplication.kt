package io.github.ychsieh95.bccp

import android.app.Application
import coil3.ImageLoader
import coil3.PlatformContext
import coil3.SingletonImageLoader
import coil3.network.okhttp.OkHttpNetworkFetcherFactory
import coil3.request.crossfade
import dagger.hilt.android.HiltAndroidApp
import io.github.ychsieh95.bccp.core.push.CourtNotifications
import okhttp3.OkHttpClient
import javax.inject.Inject

@HiltAndroidApp
class BccpApplication : Application(), SingletonImageLoader.Factory {
    @Inject lateinit var okHttpClient: OkHttpClient

    override fun onCreate() {
        super.onCreate()
        CourtNotifications.createChannel(this)
    }

    override fun newImageLoader(context: PlatformContext): ImageLoader = ImageLoader.Builder(context)
        .components { add(OkHttpNetworkFetcherFactory(callFactory = { okHttpClient })) }
        .crossfade(true)
        .build()
}
