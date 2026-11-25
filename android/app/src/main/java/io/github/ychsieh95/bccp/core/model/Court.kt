package io.github.ychsieh95.bccp.core.model

import kotlinx.serialization.Serializable

@Serializable
data class Court(
    val guid: String,
    val eventName: String = "",
    val badmintonName: String = "",
    val courtDate: String = "",
    val startTime: String = "",
    val endTime: String = "",
    val hallName: String = "",
    val location: String = "",
    val googlePlaceId: String = "",
    val latitude: Double? = null,
    val longitude: Double? = null,
    val courtId: String = "",
    val creatorUsername: String = "",
    val createdAt: String = "",
    val status: CourtStatus = CourtStatus.Open,
    val archived: Boolean = false,
    val expired: Boolean = false,
    val rollClearingLocked: Boolean = false,
    val leaveDeadline: LeaveDeadline = LeaveDeadline(),
    val members: Members = Members(),
    val levels: Levels = Levels(),
    val prices: Prices = Prices(),
    val shuttlecockInfo: String = "",
    val remark: String = "",
    val reservedNamesVisible: Boolean = true,
    val coverImageUrl: String? = null,
    val webUrl: String = "",
    val thumbnailUrl: String = "",
    // Detail-only fields (GET /courts/<guid>).
    val participants: List<Participant> = emptyList(),
    val waitingParticipants: List<Participant> = emptyList(),
    val reservedMembers: List<ReservedMember> = emptyList(),
    val media: List<CourtMedia> = emptyList(),
    val participationHistory: List<HistoryEvent> = emptyList(),
    val viewer: Viewer = Viewer(),
    val formValues: Map<String, String>? = null,
    /** Owner only: whether the organizer gets change notifications for this court. */
    val ownerNotifications: Boolean? = null,
    val reservedNicknames: List<String>? = null,
) {
    val title: String get() = eventName.ifBlank { hallName }
    val isFull: Boolean get() = members.confirmedTotal >= members.max
    val acceptsPlayers: Boolean get() = !expired && !rollClearingLocked && !archived
}

@Serializable
enum class CourtStatus {
    @kotlinx.serialization.SerialName("open") Open,
    @kotlinx.serialization.SerialName("full") Full,
    @kotlinx.serialization.SerialName("read_only") ReadOnly,
    @kotlinx.serialization.SerialName("expired") Expired,
    @kotlinx.serialization.SerialName("archived") Archived,
}

@Serializable
data class LeaveDeadline(val enabled: Boolean = false, val at: String? = null, val passed: Boolean = false)

@Serializable
data class Members(
    val min: Int = 0,
    val max: Int = 0,
    val reserved: Int = 0,
    val signedUp: Int = 0,
    val waiting: Int = 0,
    val confirmedTotal: Int = 0,
)

@Serializable
data class LevelRange(val min: Int = 1, val max: Int = 18)

@Serializable
data class Levels(val male: LevelRange = LevelRange(), val female: LevelRange = LevelRange())

@Serializable
data class Prices(val male: Int = 0, val female: Int = 0)

@Serializable
data class Participant(
    val id: Int,
    val username: String,
    val joinedAt: String = "",
    val rollCalled: Boolean = false,
    val cleared: Boolean = false,
)

@Serializable
data class ReservedMember(
    val id: Int? = null,
    val position: Int = 0,
    val nickname: String = "",
    val rollCalled: Boolean = false,
    val cleared: Boolean = false,
)

@Serializable
data class CourtMedia(
    val id: Int,
    val mediaType: String = "image",
    val mimeType: String = "",
    val originalName: String = "",
    val url: String,
) {
    val isVideo: Boolean get() = mediaType == "video"
}

@Serializable
data class HistoryEvent(
    val id: Int,
    val username: String,
    val eventType: String,
    val occurredAt: String,
    val ipAddress: String? = null,
    val deviceInformation: String? = null,
)

@Serializable
data class Viewer(val isOwner: Boolean = false, val isAdmin: Boolean = false, val canManage: Boolean = false)

@Serializable
data class Pagination(val total: Int = 0, val limit: Int = 100, val offset: Int = 0)
