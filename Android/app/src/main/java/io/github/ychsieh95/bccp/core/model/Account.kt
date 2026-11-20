package io.github.ychsieh95.bccp.core.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
enum class Role {
    @SerialName("member") Member,
    @SerialName("sub_admin") SubAdmin,
    @SerialName("admin") Admin,
    @SerialName("super_admin") SuperAdmin;

    val moderatesCourts: Boolean get() = this != Member
    val managesAccounts: Boolean get() = this == Admin || this == SuperAdmin
    val apiValue: String get() = when (this) {
        Member -> "member"
        SubAdmin -> "sub_admin"
        Admin -> "admin"
        SuperAdmin -> "super_admin"
    }
}

@Serializable
data class User(
    val id: Int,
    val username: String,
    val role: Role = Role.Member,
    val avatarUrl: String? = null,
    val createdAt: String = "",
    val timeFormat: String = "24h",
    val lastLoginAt: String? = null,
    val mustChangePassword: Boolean = false,
    val isAdmin: Boolean = false,
)

@Serializable
data class DeviceToken(
    val id: Int,
    val name: String = "",
    val createdAt: String = "",
    val lastUsedAt: String? = null,
    val expiresAt: String = "",
    val current: Boolean = false,
)

@Serializable
data class SavedLocation(
    val id: Int,
    val hallName: String = "",
    val location: String = "",
    val googlePlaceId: String = "",
    val latitude: Double? = null,
    val longitude: Double? = null,
)

@Serializable
data class AdminUser(
    val id: Int,
    val username: String,
    val role: Role = Role.Member,
    val archived: Boolean = false,
    val banned: Boolean = false,
    val mustChangePassword: Boolean = false,
    val createdAt: String = "",
    val lastLoginAt: String? = null,
    val lastLoginIp: String? = null,
    val courtCount: Int = 0,
    val failedLoginAttempts: Int = 0,
)

@Serializable
data class ContactMessage(
    val id: Int,
    val senderName: String = "",
    val replyContact: String? = null,
    val subject: String = "",
    val message: String = "",
    val language: String = "",
    val submittedAt: String = "",
    val readAt: String? = null,
) {
    val isRead: Boolean get() = readAt != null
}

@Serializable
data class AdminSettings(
    val homepageCourtLimit: Int = 12,
    val contactNotificationsEnabled: Boolean = false,
    val contactNotificationChannels: NotificationChannels = NotificationChannels(),
)

@Serializable
data class NotificationChannels(val discordReady: Boolean = false, val telegramReady: Boolean = false)

@Serializable
data class Meta(
    val apiVersion: Int = 1,
    val language: String = "",
    val turnstile: TurnstileConfig = TurnstileConfig(),
    val push: PushConfig = PushConfig(),
    val limits: Limits = Limits(),
    val courtDefaults: Map<String, String> = emptyMap(),
)

/** `fcm`: the server can send this app court notifications through Firebase Cloud Messaging. */
@Serializable
data class PushConfig(val fcm: Boolean = false)

@Serializable
data class TurnstileConfig(val enabled: Boolean = false, val siteKey: String = "")

@Serializable
data class Limits(
    val courtMediaFiles: Int = 12,
    val courtImageBytes: Long = 8L * 1024 * 1024,
    val courtVideoBytes: Long = 50L * 1024 * 1024,
    val avatarBytes: Long = 2L * 1024 * 1024,
)
