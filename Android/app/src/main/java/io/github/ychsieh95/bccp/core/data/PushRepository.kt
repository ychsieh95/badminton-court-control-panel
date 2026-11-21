package io.github.ychsieh95.bccp.core.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import com.google.android.gms.tasks.Task
import com.google.firebase.messaging.FirebaseMessaging
import dagger.hilt.android.qualifiers.ApplicationContext
import io.github.ychsieh95.bccp.core.network.BccpApi
import kotlinx.coroutines.flow.filterNotNull
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.TimeoutCancellationException
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withTimeout
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

/**
 * Per-court push notifications through Firebase Cloud Messaging. The server keys
 * subscriptions by this device's FCM token, so no account is needed.
 *
 * FCM hands the token to [io.github.ychsieh95.bccp.core.push.CourtMessagingService.onRegistered]
 * (on first registration and on every refresh), which stores it here.
 */
@Singleton
class PushRepository @Inject constructor(
    private val api: BccpApi,
    private val json: Json,
    private val session: SessionStore,
    @ApplicationContext private val context: Context,
) {
    /** Whether the current server sends FCM notifications. */
    suspend fun available(): Boolean = apiCall(json) { api.meta().push.fcm }.getOrDefault(false)

    suspend fun isSubscribed(guid: String): Result<Boolean> = apiCall(json) {
        api.pushStatus(guid, tokenBody(currentToken())).subscribed
    }

    suspend fun setSubscribed(guid: String, subscribed: Boolean): Result<Boolean> = apiCall(json) {
        val body = tokenBody(currentToken())
        if (subscribed) api.subscribePush(guid, body).subscribed else api.unsubscribePush(guid, body).subscribed
    }

    /** This device's FCM token if it already has one; never registers. */
    suspend fun knownToken(): String? = storedToken()

    /** FCM issued a token. If it replaces an older one, move this device's court subscriptions to it. */
    suspend fun onTokenRegistered(token: String) {
        val previous = storedToken()
        storeToken(token)
        if (previous != null && previous != token) {
            apiCall(json) {
                api.replacePushToken(buildJsonObject {
                    put("previous_token", previous)
                    put("token", token)
                })
            }
        }
        if (previous != token && session.token != null) syncAccountToken()
    }

    /**
     * Link this device's token to the signed-in account, so the organizer hears about
     * changes others make to their courts. Signing out drops the link on the server.
     */
    suspend fun syncAccountToken(): Result<Unit> {
        if (session.token == null || !available()) return Result.success(Unit)
        return try {
            apiCall(json) {
                api.registerAccountPushToken(tokenBody(currentToken()))
                Unit
            }
        } catch (e: TimeoutCancellationException) {
            // FCM never delivered a token; don't let the timeout cancel the caller.
            Result.failure(DataError.Unexpected(e))
        }
    }

    suspend fun onTokenUnregistered() {
        context.dataStore.edit { it.remove(FCM_TOKEN) }
    }

    /** The stored token, or register with FCM and wait for [onTokenRegistered] to deliver one. */
    private suspend fun currentToken(): String {
        storedToken()?.let { return it }
        FirebaseMessaging.getInstance().register().await()
        return withTimeout(REGISTER_TIMEOUT_MS) {
            context.dataStore.data.map { it[FCM_TOKEN] }.filterNotNull().first()
        }
    }

    private fun tokenBody(token: String) = buildJsonObject { put("token", token) }

    private suspend fun storedToken(): String? = context.dataStore.data.first()[FCM_TOKEN]

    private suspend fun storeToken(token: String) {
        context.dataStore.edit { it[FCM_TOKEN] = token }
    }

    private companion object {
        val FCM_TOKEN = stringPreferencesKey("fcm_token")
        const val REGISTER_TIMEOUT_MS = 20_000L
    }
}

private suspend fun <T> Task<T>.await(): T = suspendCancellableCoroutine { continuation ->
    addOnCompleteListener { task ->
        val error = task.exception
        when {
            error != null -> continuation.resumeWithException(error)
            task.isCanceled -> continuation.cancel()
            else -> continuation.resume(task.result)
        }
    }
}
