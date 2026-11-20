package io.github.ychsieh95.bccp.core.data

import android.content.Context
import dagger.hilt.android.qualifiers.ApplicationContext
import io.github.ychsieh95.bccp.core.model.DeviceToken
import io.github.ychsieh95.bccp.core.model.Meta
import io.github.ychsieh95.bccp.core.model.SavedLocation
import io.github.ychsieh95.bccp.core.model.User
import io.github.ychsieh95.bccp.core.network.BccpApi
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObjectBuilder
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import android.os.Build
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AccountRepository @Inject constructor(
    private val api: BccpApi,
    private val json: Json,
    private val session: SessionStore,
    @ApplicationContext private val context: Context,
) {
    suspend fun meta(): Result<Meta> = apiCall(json) { api.meta() }

    suspend fun login(username: String, password: String, turnstileToken: String?): Result<User> = apiCall(json) {
        api.login(buildJsonObject {
            put("username", username.trim())
            put("password", password)
            deviceAndTurnstile(turnstileToken)
        })
    }.onSuccess { session.signIn(it.token, it.user) }.map { it.user }

    suspend fun signup(username: String, password: String, confirm: String, turnstileToken: String?): Result<User> = apiCall(json) {
        api.signup(buildJsonObject {
            put("username", username.trim())
            put("password", password)
            put("confirm_password", confirm)
            deviceAndTurnstile(turnstileToken)
        })
    }.onSuccess { session.signIn(it.token, it.user) }.map { it.user }

    /** Signs out locally even when the server can't be reached; the token then expires on its own. */
    suspend fun logout() {
        apiCall(json) { api.logout().requireSuccess() }
        session.clear()
    }

    suspend fun refreshMe(): Result<User> = apiCall(json) { api.me().user }.onSuccess(session::updateUser)

    suspend fun setTimeFormat(format: String): Result<User> =
        apiCall(json) { api.updateMe(buildJsonObject { put("time_format", format) }).user }.onSuccess(session::updateUser)

    suspend fun changePassword(current: String, new: String, confirm: String): Result<User> = apiCall(json) {
        api.changePassword(buildJsonObject {
            put("current_password", current)
            put("new_password", new)
            put("confirm_password", confirm)
        }).user
    }.onSuccess(session::updateUser)

    suspend fun uploadAvatar(file: LocalFile): Result<User> =
        apiCall(json) { api.uploadAvatar(file.toPart(context.contentResolver, "avatar")).user }.onSuccess(session::updateUser)

    suspend fun removeAvatar(): Result<User> = apiCall(json) { api.deleteAvatar().user }.onSuccess(session::updateUser)

    suspend fun savedLocations(): Result<List<SavedLocation>> = apiCall(json) { api.savedLocations().savedLocations }
    suspend fun deleteSavedLocation(id: Int): Result<Unit> = apiCall(json) { api.deleteSavedLocation(id).requireSuccess() }

    suspend fun devices(): Result<List<DeviceToken>> = apiCall(json) { api.tokens().tokens }
    suspend fun revokeDevice(id: Int): Result<Unit> = apiCall(json) { api.revokeToken(id).requireSuccess() }

    suspend fun deleteAccount(currentPassword: String): Result<Unit> = apiCall(json) {
        api.deleteAccount(buildJsonObject { put("current_password", currentPassword) }).requireSuccess()
    }.onSuccess { session.clear() }

    suspend fun sendContact(name: String, reply: String, subject: String, message: String, turnstileToken: String?): Result<Unit> =
        apiCall(json) {
            api.contact(buildJsonObject {
                put("sender_name", name.trim())
                put("reply_contact", reply.trim())
                put("subject", subject.trim())
                put("message", message.trim())
                put("client", clientInfo())
                turnstileToken?.let { put("turnstile_token", it) }
            })
            Unit
        }

    /** App and device details the server adds to the contact report. */
    private fun clientInfo() = buildJsonObject {
        put("platform", "android")
        runCatching {
            val info = context.packageManager.getPackageInfo(context.packageName, 0)
            put("app_version", "${info.versionName} (${androidx.core.content.pm.PackageInfoCompat.getLongVersionCode(info)})")
        }
        put("os_version", "${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT})")
        put("device_model", "${Build.MANUFACTURER} ${Build.MODEL}".trim().take(60))
    }

    private fun JsonObjectBuilder.deviceAndTurnstile(turnstileToken: String?) {
        put("device_name", "${Build.MANUFACTURER} ${Build.MODEL}".trim().take(80))
        turnstileToken?.let { put("turnstile_token", it) }
    }
}
