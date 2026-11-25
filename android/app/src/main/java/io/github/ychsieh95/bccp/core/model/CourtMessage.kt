package io.github.ychsieh95.bccp.core.model

import kotlinx.serialization.Serializable

/** A message on a court's board. Top-level messages carry their [replies], oldest first. */
@Serializable
data class CourtMessage(
    val id: Int,
    val authorName: String,
    val authorKind: String = "participant",
    val message: String,
    val postedAt: String = "",
    /** Administrators only. */
    val ipAddress: String? = null,
    val replies: List<CourtMessage> = emptyList(),
) {
    val isOrganizer: Boolean get() = authorKind == "organizer"
}

/**
 * `GET/POST/DELETE /courts/<guid>/messages`. With an unchanged `version` the server sends
 * only `{changed: false, version}`, so [messages] is meaningful only when [changed].
 */
@Serializable
data class MessageBoard(
    val changed: Boolean = true,
    val messages: List<CourtMessage> = emptyList(),
    val count: Int = 0,
    val version: String = "",
    val messageId: Int? = null,
    val threadId: Int? = null,
)
