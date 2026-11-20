package io.github.ychsieh95.bccp.core.network

import android.os.Build
import io.github.ychsieh95.bccp.BuildConfig
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.Interceptor
import okhttp3.Response
import java.util.Locale

/**
 * Points Retrofit's placeholder base URL at the server chosen in Settings, and adds
 * the bearer token and language. A rejected token signs the app out.
 */
class ApiInterceptor(
    private val serverUrl: () -> String,
    private val token: () -> String?,
    private val onTokenRejected: () -> Unit,
    private val userAgent: String = "BCCP-Android/${BuildConfig.VERSION_NAME} (Linux; Android ${Build.VERSION.RELEASE})",
) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val original = chain.request()
        val url = original.url
        if (url.host != PLACEHOLDER_HOST) return chain.proceed(original)

        val base = (serverUrl().trimEnd('/') + API_PATH).toHttpUrl()
        val target = base.newBuilder()
            .addEncodedPathSegments(url.encodedPath.removePrefix(API_PATH))
            .encodedQuery(url.encodedQuery)
            .build()

        val bearer = token()
        val request = original.newBuilder()
            .url(target)
            .header("Accept", "application/json")
            .header("Accept-Language", Locale.getDefault().toLanguageTag())
            // "Android" makes the server log this device type in join/leave history.
            .header("User-Agent", userAgent)
            .apply { if (bearer != null) header("Authorization", "Bearer $bearer") }
            .build()

        val response = chain.proceed(request)
        if (bearer != null && response.code == 401 &&
            response.header("WWW-Authenticate").orEmpty().contains("invalid_token") &&
            token() == bearer
        ) {
            onTokenRejected()
        }
        return response
    }

    companion object {
        const val PLACEHOLDER_HOST = "bccp.invalid"
        const val API_PATH = "/api/v1/"
        const val PLACEHOLDER_BASE_URL = "http://$PLACEHOLDER_HOST$API_PATH"
    }
}
