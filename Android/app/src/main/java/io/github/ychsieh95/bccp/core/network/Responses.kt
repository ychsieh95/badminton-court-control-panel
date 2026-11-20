package io.github.ychsieh95.bccp.core.network

import io.github.ychsieh95.bccp.core.model.AdminSettings
import io.github.ychsieh95.bccp.core.model.AdminUser
import io.github.ychsieh95.bccp.core.model.ContactMessage
import io.github.ychsieh95.bccp.core.model.Court
import io.github.ychsieh95.bccp.core.model.DeviceToken
import io.github.ychsieh95.bccp.core.model.Pagination
import io.github.ychsieh95.bccp.core.model.SavedLocation
import io.github.ychsieh95.bccp.core.model.User
import kotlinx.serialization.Serializable

@Serializable
data class CourtListResponse(val courts: List<Court>, val pagination: Pagination = Pagination())

@Serializable
data class CourtResponse(val court: Court, val waitlisted: Boolean = false)

@Serializable
data class AuthResponse(val token: String, val expiresAt: String = "", val user: User)

@Serializable
data class UserResponse(val user: User)

@Serializable
data class TokensResponse(val tokens: List<DeviceToken>)

@Serializable
data class SavedLocationsResponse(val savedLocations: List<SavedLocation>)

@Serializable
data class AdminUsersResponse(val users: List<AdminUser>)

@Serializable
data class AdminUserResponse(val user: AdminUser)

@Serializable
data class MessagesResponse(
    val messages: List<ContactMessage>,
    val status: String = "all",
    val page: Int = 1,
    val pageCount: Int = 1,
    val totalCount: Int = 0,
    val unreadCount: Int = 0,
)

@Serializable
data class MessageResponse(val message: ContactMessage)

@Serializable
data class SettingsResponse(val settings: AdminSettings)

@Serializable
data class ErrorEnvelope(val error: ErrorBody)

@Serializable
data class ErrorBody(val code: String = "error", val message: String = "", val fields: Map<String, String> = emptyMap())

@Serializable
data class PushStatusResponse(val subscribed: Boolean)
