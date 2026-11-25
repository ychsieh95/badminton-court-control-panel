package io.github.ychsieh95.bccp.core.data

import io.github.ychsieh95.bccp.core.model.AdminSettings
import io.github.ychsieh95.bccp.core.model.AdminUser
import io.github.ychsieh95.bccp.core.model.ContactMessage
import io.github.ychsieh95.bccp.core.model.Role
import io.github.ychsieh95.bccp.core.network.BccpApi
import io.github.ychsieh95.bccp.core.network.MessagesResponse
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import javax.inject.Inject
import javax.inject.Singleton

enum class UserAction(val path: String) {
    Archive("archive"), Restore("restore"), Ban("ban"), Unban("unban"), ResetLoginRetries("reset-login-retries")
}

@Singleton
class AdminRepository @Inject constructor(private val api: BccpApi, private val json: Json) {
    suspend fun users(): Result<List<AdminUser>> = apiCall(json) { api.adminUsers().users }
    suspend fun userAction(id: Int, action: UserAction): Result<AdminUser> = apiCall(json) { api.adminUserAction(id, action.path).user }
    suspend fun setTemporaryPassword(id: Int, password: String): Result<AdminUser> = apiCall(json) {
        api.adminTemporaryPassword(id, buildJsonObject { put("temporary_password", password) }).user
    }
    suspend fun setRole(id: Int, role: Role): Result<AdminUser> = apiCall(json) {
        api.adminSetRole(id, buildJsonObject { put("role", role.apiValue) }).user
    }
    suspend fun deleteUser(id: Int): Result<Unit> = apiCall(json) { api.adminDeleteUser(id).requireSuccess() }

    suspend fun messages(status: String, page: Int): Result<MessagesResponse> = apiCall(json) { api.adminMessages(status, page) }
    suspend fun setMessageRead(id: Int, read: Boolean): Result<ContactMessage> = apiCall(json) {
        api.adminUpdateMessage(id, buildJsonObject { put("read", read) }).message
    }

    suspend fun settings(): Result<AdminSettings> = apiCall(json) { api.adminSettings().settings }
    suspend fun updateSettings(homepageLimit: Int, notifications: Boolean): Result<AdminSettings> = apiCall(json) {
        api.adminUpdateSettings(buildJsonObject {
            put("homepage_court_limit", homepageLimit)
            put("contact_notifications_enabled", notifications)
        }).settings
    }
}
