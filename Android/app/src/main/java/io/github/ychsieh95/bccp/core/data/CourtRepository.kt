package io.github.ychsieh95.bccp.core.data

import android.content.Context
import dagger.hilt.android.qualifiers.ApplicationContext
import io.github.ychsieh95.bccp.core.model.Court
import io.github.ychsieh95.bccp.core.model.MessageBoard
import io.github.ychsieh95.bccp.core.network.BccpApi
import io.github.ychsieh95.bccp.core.network.CourtListResponse
import io.github.ychsieh95.bccp.core.network.CourtResponse
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.buildJsonArray
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import javax.inject.Inject
import javax.inject.Singleton

data class CourtFilters(
    val query: String = "",
    val dateFrom: String = "",
    val dateTo: String = "",
    val level: Int? = null,
    val gender: String = "both",
    val status: String = "",
    val showExpired: Boolean = false,
) {
    val activeCount: Int get() = listOf(
        query.isNotBlank(), dateFrom.isNotBlank(), dateTo.isNotBlank(), level != null,
        status.isNotBlank(), showExpired,
    ).count { it }

    fun toQuery(limit: Int, offset: Int): Map<String, String> = buildMap {
        if (query.isNotBlank()) put("q", query.trim())
        if (dateFrom.isNotBlank()) put("date_from", dateFrom)
        if (dateTo.isNotBlank()) put("date_to", dateTo)
        level?.let { put("level", it.toString()) }
        if (gender != "both") put("gender", gender)
        if (status.isNotBlank()) put("status", status)
        if (showExpired) put("show_expired", "1")
        put("limit", limit.toString())
        put("offset", offset.toString())
    }
}

enum class CourtScope { Public, Mine, Admin }

data class RollStatus(val id: Int, val rollCalled: Boolean, val cleared: Boolean)

@Singleton
class CourtRepository @Inject constructor(
    private val api: BccpApi,
    private val json: Json,
    @ApplicationContext private val context: Context,
) {
    suspend fun list(scope: CourtScope, filters: CourtFilters, limit: Int, offset: Int): Result<CourtListResponse> = apiCall(json) {
        when (scope) {
            CourtScope.Public -> api.courts(filters.toQuery(limit, offset))
            CourtScope.Admin -> api.adminCourts(filters.toQuery(limit, offset))
            CourtScope.Mine -> api.myCourts(limit, offset)
        }
    }

    suspend fun detail(guid: String): Result<Court> = apiCall(json) { api.court(guid).court }

    suspend fun join(guid: String, username: String, pin: String): Result<CourtResponse> = apiCall(json) {
        api.join(guid, credentials(username, pin))
    }

    suspend fun leave(guid: String, username: String, pin: String): Result<Court> = apiCall(json) {
        api.leave(guid, credentials(username, pin)).court
    }

    /**
     * [body] is the court JSON (`POST /courts` / `PATCH /courts/<guid>`); with [uploads]
     * it goes as multipart, the JSON in a `court` part and each file as `media`.
     */
    suspend fun save(guid: String?, body: JsonObject, uploads: List<LocalFile>): Result<Court> = apiCall(json) {
        if (uploads.isEmpty()) {
            if (guid == null) api.createCourt(body).court else api.updateCourt(guid, body).court
        } else {
            val courtPart = body.toString().toRequestBody("application/json".toMediaType())
            val parts = uploads.map { it.toPart(context.contentResolver, "media") }
            if (guid == null) api.createCourt(courtPart, parts).court else api.updateCourt(guid, courtPart, parts).court
        }
    }

    suspend fun delete(guid: String): Result<Unit> = apiCall(json) { api.deleteCourt(guid).requireSuccess() }
    suspend fun archive(guid: String): Result<Court> = apiCall(json) { api.archiveCourt(guid).court }
    suspend fun restore(guid: String): Result<Court> = apiCall(json) { api.restoreCourt(guid).court }
    suspend fun startRollClearing(guid: String): Result<Court> = apiCall(json) { api.startRollClearing(guid).court }
    suspend fun endRollClearing(guid: String): Result<Court> = apiCall(json) { api.endRollClearing(guid).court }

    suspend fun saveRollClearing(guid: String, participants: List<RollStatus>, reserved: List<RollStatus>): Result<Court> =
        apiCall(json) {
            api.updateRollClearing(guid, buildJsonObject {
                put("participants", participants.toJson())
                put("reserved_members", reserved.toJson())
            }).court
        }

    suspend fun renameParticipant(guid: String, id: Int, username: String): Result<Court> = apiCall(json) {
        api.updateParticipant(guid, id, buildJsonObject { put("username", username) }).court
    }

    suspend fun resetParticipantPin(guid: String, id: Int, pin: String): Result<Court> = apiCall(json) {
        api.updateParticipant(guid, id, buildJsonObject { put("pin", pin) }).court
    }

    suspend fun removeParticipant(guid: String, id: Int): Result<Court> = apiCall(json) { api.deleteParticipant(guid, id).court }

    /** [version] is the board the caller already shows; an unchanged board answers `changed = false`. */
    suspend fun messages(guid: String, version: String? = null): Result<MessageBoard> = apiCall(json) {
        api.messages(guid, version?.takeIf { it.isNotEmpty() })
    }

    /**
     * Players send the [username] and [pin] they joined with; an organizer's account needs neither.
     * [fcmToken] lets replies reach this device when it follows the court.
     */
    suspend fun postMessage(
        guid: String,
        username: String,
        pin: String,
        message: String,
        parentId: Int?,
        fcmToken: String?,
    ): Result<MessageBoard> = apiCall(json) {
        api.postMessage(guid, buildJsonObject {
            put("username", username.trim())
            put("pin", pin)
            put("message", message.trim())
            parentId?.let { put("parent_id", it) }
            fcmToken?.let { put("fcm_token", it) }
        })
    }

    suspend fun deleteMessage(guid: String, id: Int): Result<MessageBoard> = apiCall(json) { api.deleteMessage(guid, id) }

    private fun credentials(username: String, pin: String) = buildJsonObject {
        put("username", username.trim())
        put("pin", pin)
    }

    private fun List<RollStatus>.toJson() = buildJsonArray {
        forEach { s ->
            add(buildJsonObject {
                put("id", s.id)
                put("roll_called", s.rollCalled)
                put("cleared", s.cleared)
            })
        }
    }
}
