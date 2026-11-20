package io.github.ychsieh95.bccp.core.di

import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import io.github.ychsieh95.bccp.BuildConfig
import io.github.ychsieh95.bccp.core.data.SessionStore
import io.github.ychsieh95.bccp.core.data.SettingsStore
import io.github.ychsieh95.bccp.core.network.ApiInterceptor
import io.github.ychsieh95.bccp.core.network.BccpApi
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.serialization.ExperimentalSerializationApi
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonNamingStrategy
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.util.concurrent.TimeUnit
import javax.inject.Qualifier
import javax.inject.Singleton

@Qualifier annotation class ApiClient

@Module
@InstallIn(SingletonComponent::class)
object AppModule {
    @Provides @Singleton
    fun appScope(): CoroutineScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

    @OptIn(ExperimentalSerializationApi::class)
    @Provides @Singleton
    fun json(): Json = Json {
        ignoreUnknownKeys = true
        coerceInputValues = true
        explicitNulls = false
        namingStrategy = JsonNamingStrategy.SnakeCase
    }

    /** Shared by Coil; no API interceptor, since media URLs are absolute and public. */
    @Provides @Singleton
    fun okHttp(): OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .writeTimeout(120, TimeUnit.SECONDS) // media uploads go up to 50 MB
        .build()

    @Provides @Singleton
    fun apiInterceptor(settings: SettingsStore, session: SessionStore): ApiInterceptor = ApiInterceptor(
        serverUrl = { settings.current.serverUrl },
        token = { session.token },
        onTokenRejected = session::clear,
    )

    @Provides @Singleton @ApiClient
    fun apiOkHttp(base: OkHttpClient, interceptor: ApiInterceptor): OkHttpClient = base.newBuilder()
        .addInterceptor(interceptor)
        .apply {
            if (BuildConfig.DEBUG) {
                addInterceptor(HttpLoggingInterceptor().apply {
                    level = HttpLoggingInterceptor.Level.BASIC
                    redactHeader("Authorization")
                })
            }
        }
        .build()

    @Provides @Singleton
    fun api(@ApiClient client: OkHttpClient, json: Json): BccpApi = Retrofit.Builder()
        .baseUrl(ApiInterceptor.PLACEHOLDER_BASE_URL)
        .client(client)
        .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
        .build()
        .create(BccpApi::class.java)
}
