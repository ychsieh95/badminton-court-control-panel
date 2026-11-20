package io.github.ychsieh95.bccp.feature.courtform

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.navigation.toRoute
import dagger.hilt.android.lifecycle.HiltViewModel
import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.data.AccountRepository
import io.github.ychsieh95.bccp.core.data.CourtRepository
import io.github.ychsieh95.bccp.core.data.LocalFile
import io.github.ychsieh95.bccp.core.data.PushRepository
import io.github.ychsieh95.bccp.core.model.CourtMedia
import io.github.ychsieh95.bccp.core.model.Limits
import io.github.ychsieh95.bccp.core.model.SavedLocation
import io.github.ychsieh95.bccp.core.ui.UiMessage
import io.github.ychsieh95.bccp.core.ui.fieldErrors
import io.github.ychsieh95.bccp.core.ui.toUiMessage
import io.github.ychsieh95.bccp.navigation.CourtFormRoute
import kotlinx.coroutines.async
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import java.time.LocalDate
import javax.inject.Inject

/** Court fields exactly as `GET /meta` → `court_defaults` and `form_values` name them. */
object F {
    const val EVENT_NAME = "event_name"
    const val BADMINTON_NAME = "badminton_name"
    const val DATE = "court_date"
    const val START = "start_time"
    const val END = "end_time"
    const val HALL = "hall_name"
    const val LOCATION = "location"
    const val PLACE_ID = "google_place_id"
    const val LAT = "latitude"
    const val LNG = "longitude"
    const val COURT_ID = "court_id"
    const val REMARK = "remark"
    const val SHUTTLE = "shuttlecock_info"
    const val MALE_PRICE = "male_price"
    const val FEMALE_PRICE = "female_price"
    const val NAMES_VISIBLE = "reserved_names_visible"
    const val DEADLINE_ON = "leave_deadline_enabled"
    const val DEADLINE_AT = "leave_deadline_at"
    const val MEMBER_MIN = "member_min"
    const val MEMBER_MAX = "member_max"
    const val ORDERED = "ordered_count"
    const val MALE_MIN = "male_level_min"
    const val MALE_MAX = "male_level_max"
    const val FEMALE_MIN = "female_level_min"
    const val FEMALE_MAX = "female_level_max"
    const val NICKNAMES = "reserved_nicknames"
    const val MEDIA = "media"

    /** Mirrors `default_court_values()`, used until `/meta` answers. */
    fun defaults(): Map<String, String> = mapOf(
        EVENT_NAME to "", BADMINTON_NAME to "", DATE to LocalDate.now().toString(), START to "19:00", END to "21:00",
        HALL to "", LOCATION to "", PLACE_ID to "", LAT to "", LNG to "", REMARK to "", COURT_ID to "",
        MALE_PRICE to "0", FEMALE_PRICE to "0", SHUTTLE to "", NAMES_VISIBLE to "1", DEADLINE_ON to "0", DEADLINE_AT to "",
        MEMBER_MIN to "4", MEMBER_MAX to "8", ORDERED to "0",
        MALE_MIN to "1", MALE_MAX to "18", FEMALE_MIN to "1", FEMALE_MAX to "18",
    )
}

data class CourtFormUiState(
    val editingGuid: String? = null,
    val duplicating: Boolean = false,
    val values: Map<String, String> = F.defaults(),
    val nicknames: List<String> = emptyList(),
    val existingMedia: List<CourtMedia> = emptyList(),
    val removeMediaIds: Set<Int> = emptySet(),
    val newFiles: List<LocalFile> = emptyList(),
    val saveLocation: Boolean = false,
    /** Shown when the server sends FCM and this account owns (or is creating) the court. */
    val ownerNotificationsAvailable: Boolean = false,
    val ownerNotifications: Boolean = true,
    val savedLocations: List<SavedLocation> = emptyList(),
    val limits: Limits = Limits(),
    val fieldErrors: Map<String, String> = emptyMap(),
    val loading: Boolean = true,
    val loadError: UiMessage? = null,
    val saving: Boolean = false,
    val dirty: Boolean = false,
) {
    val editing: Boolean get() = editingGuid != null
    val mediaSlotsLeft: Int get() = limits.courtMediaFiles - (existingMedia.size - removeMediaIds.size) - newFiles.size
    operator fun get(key: String): String = values[key].orEmpty()
}

sealed interface CourtFormEffect {
    data class Message(val message: UiMessage) : CourtFormEffect
    data class Saved(val guid: String, val created: Boolean) : CourtFormEffect
}

@HiltViewModel
class CourtFormViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    private val courts: CourtRepository,
    private val account: AccountRepository,
    private val push: PushRepository,
) : ViewModel() {
    private val route = savedStateHandle.toRoute<CourtFormRoute>()

    private val _uiState = MutableStateFlow(CourtFormUiState(editingGuid = route.guid, duplicating = route.copyFrom != null))
    val uiState: StateFlow<CourtFormUiState> = _uiState.asStateFlow()
    private val _effects = Channel<CourtFormEffect>(Channel.BUFFERED)
    val effects = _effects.receiveAsFlow()

    init {
        load()
    }

    fun load() {
        _uiState.update { it.copy(loading = true, loadError = null) }
        viewModelScope.launch {
            val meta = async { account.meta() }
            val locations = async { account.savedLocations() }
            val sourceGuid = route.guid ?: route.copyFrom
            val source = sourceGuid?.let { courts.detail(it) }

            val sourceCourt = source?.getOrElse { e ->
                _uiState.update { it.copy(loading = false, loadError = e.toUiMessage()) }
                return@launch
            }
            val metaValue = meta.await().getOrNull()
            // Editing: only the owner gets `owner_notifications`. Creating or copying: you'll own it.
            val ownerSetting = if (route.guid != null) sourceCourt?.ownerNotifications else sourceCourt?.ownerNotifications ?: true
            _uiState.update { state ->
                val base = metaValue?.courtDefaults?.takeIf { it.isNotEmpty() } ?: state.values
                val values = sourceCourt?.formValues ?: base
                state.copy(
                    values = F.defaults() + values,
                    nicknames = sourceCourt?.reservedNicknames.orEmpty(),
                    existingMedia = if (route.guid != null) sourceCourt?.media.orEmpty() else emptyList(),
                    limits = metaValue?.limits ?: state.limits,
                    ownerNotificationsAvailable = metaValue?.push?.fcm == true && ownerSetting != null,
                    ownerNotifications = ownerSetting ?: true,
                    savedLocations = locations.await().getOrDefault(emptyList()),
                    loading = false,
                )
            }
            if (route.copyFrom != null) _effects.send(CourtFormEffect.Message(UiMessage.Res(R.string.court_duplicated)))
        }
    }

    fun set(key: String, value: String) = _uiState.update {
        it.copy(values = it.values + (key to value), fieldErrors = it.fieldErrors - key, dirty = true)
    }

    fun setOrderedCount(count: Int) = _uiState.update {
        val names = it.nicknames.take(count) + List((count - it.nicknames.size).coerceAtLeast(0)) { "" }
        it.copy(values = it.values + (F.ORDERED to count.toString()), nicknames = names, dirty = true, fieldErrors = it.fieldErrors - F.ORDERED)
    }

    fun setNickname(index: Int, value: String) = updateNicknames { it.toMutableList().also { list -> list[index] = value.take(40) } }

    fun moveNickname(index: Int, delta: Int) = updateNicknames { list ->
        val target = index + delta
        if (target !in list.indices) list else list.toMutableList().also { java.util.Collections.swap(it, index, target) }
    }

    /** Like the web editor: removing a nickname also removes its pre-booked place. */
    fun removeNickname(index: Int) = updateNicknames { it.filterIndexed { i, _ -> i != index } }

    fun addNickname() = updateNicknames { if (it.size >= 99) it else it + "" }

    private fun updateNicknames(change: (List<String>) -> List<String>) = _uiState.update {
        val names = change(it.nicknames)
        it.copy(
            nicknames = names,
            values = it.values + (F.ORDERED to names.size.toString()),
            dirty = true,
            fieldErrors = it.fieldErrors - F.NICKNAMES,
        )
    }

    fun setLeaveDeadline(date: String, time: String) = set(F.DEADLINE_AT, if (date.isBlank()) "" else "${date}T${time.ifBlank { "00:00" }}")

    fun applySavedLocation(location: SavedLocation) = _uiState.update {
        it.copy(
            values = it.values + mapOf(
                F.HALL to location.hallName,
                F.LOCATION to location.location,
                F.PLACE_ID to location.googlePlaceId,
                F.LAT to (location.latitude?.toString() ?: ""),
                F.LNG to (location.longitude?.toString() ?: ""),
            ),
            fieldErrors = it.fieldErrors - F.HALL - F.LOCATION,
            dirty = true,
        )
    }

    fun setSaveLocation(save: Boolean) = _uiState.update { it.copy(saveLocation = save) }

    fun setOwnerNotifications(enabled: Boolean) = _uiState.update { it.copy(ownerNotifications = enabled, dirty = true) }

    fun toggleRemoveMedia(id: Int) = _uiState.update {
        it.copy(removeMediaIds = if (id in it.removeMediaIds) it.removeMediaIds - id else it.removeMediaIds + id, dirty = true)
    }

    fun addFiles(files: List<LocalFile>) = _uiState.update {
        it.copy(newFiles = it.newFiles + files.take(it.mediaSlotsLeft.coerceAtLeast(0)), dirty = true, fieldErrors = it.fieldErrors - F.MEDIA)
    }

    fun removeFile(index: Int) = _uiState.update { it.copy(newFiles = it.newFiles.filterIndexed { i, _ -> i != index }) }

    fun save() {
        val state = _uiState.value
        if (state.saving) return
        _uiState.update { it.copy(saving = true) }
        val body = buildJsonObject {
            state.values.forEach { (key, value) -> put(key, value.trim()) }
            if (state.values[F.DEADLINE_ON] != "1") put(F.DEADLINE_AT, "")
            put(F.NICKNAMES, JsonArray(state.nicknames.map { JsonPrimitive(it.trim()) }))
            if (state.ownerNotificationsAvailable) put("owner_notifications", state.ownerNotifications)
            if (state.editing) {
                put("remove_media_ids", JsonArray(state.removeMediaIds.map(::JsonPrimitive)))
            } else {
                put("save_location", state.saveLocation)
            }
        }
        viewModelScope.launch {
            courts.save(state.editingGuid, body, state.newFiles)
                .onSuccess { court ->
                    // Make sure this device is linked to the account that will get the alerts.
                    if (state.ownerNotificationsAvailable && state.ownerNotifications) launch { push.syncAccountToken() }
                    _uiState.update { it.copy(saving = false, dirty = false) }
                    _effects.send(CourtFormEffect.Saved(court.guid, created = !state.editing))
                }
                .onFailure { e ->
                    _uiState.update { it.copy(saving = false, fieldErrors = e.fieldErrors) }
                    _effects.send(CourtFormEffect.Message(e.toUiMessage()))
                }
        }
    }
}
