package io.github.ychsieh95.bccp.feature.courtdetail

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.navigation.toRoute
import dagger.hilt.android.lifecycle.HiltViewModel
import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.data.CourtRepository
import io.github.ychsieh95.bccp.core.data.DataError
import io.github.ychsieh95.bccp.core.data.PushRepository
import io.github.ychsieh95.bccp.core.data.RollStatus
import io.github.ychsieh95.bccp.core.data.SessionStore
import io.github.ychsieh95.bccp.core.data.SettingsStore
import io.github.ychsieh95.bccp.core.model.Court
import io.github.ychsieh95.bccp.core.model.CourtMessage
import io.github.ychsieh95.bccp.core.model.MessageBoard
import io.github.ychsieh95.bccp.core.push.CourtNotifications
import io.github.ychsieh95.bccp.core.ui.UiMessage
import io.github.ychsieh95.bccp.core.ui.toUiMessage
import io.github.ychsieh95.bccp.navigation.CourtDetailRoute
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.filter
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

enum class PlayerMode { Join, Leave }

data class PlayerForm(
    val mode: PlayerMode = PlayerMode.Join,
    val username: String = "",
    val pin: String = "",
    val error: UiMessage? = null,
    val submitting: Boolean = false,
) {
    val canSubmit: Boolean get() = username.trim().length in 2..40 && pin.length == 6 && !submitting
}

const val MESSAGE_MAX_LENGTH = 500

/** The message composer. [replyTo] is the thread being answered, or null for a new message. */
data class MessageForm(
    val open: Boolean = false,
    val replyTo: CourtMessage? = null,
    val username: String = "",
    val pin: String = "",
    val message: String = "",
    val error: UiMessage? = null,
    val submitting: Boolean = false,
) {
    /** Organizers post as their account, without a player's name and PIN. */
    fun canSubmit(asOrganizer: Boolean): Boolean =
        !submitting && message.isNotBlank() && message.length <= MESSAGE_MAX_LENGTH &&
            (asOrganizer || (username.trim().length in 2..40 && pin.length == 6))
}

/** Court-change notifications for this device. [available] when the server has FCM set up. */
data class PushUi(val available: Boolean = false, val subscribed: Boolean = false, val busy: Boolean = false)

/** After joining, offer to follow the court; after leaving, offer to stop. */
enum class NotificationPrompt { Enable, Disable }

/** Roll-call checkboxes keyed `p<id>` (online players) and `r<id>` (reserved members). */
data class RollDraft(val rollCalled: Map<String, Boolean> = emptyMap(), val cleared: Map<String, Boolean> = emptyMap())

data class CourtDetailUiState(
    val court: Court? = null,
    val loading: Boolean = true,
    val notFound: Boolean = false,
    val error: UiMessage? = null,
    val busy: Boolean = false,
    val playerForm: PlayerForm = PlayerForm(),
    val rollDraft: RollDraft = RollDraft(),
    val rollDirty: Boolean = false,
    val push: PushUi = PushUi(),
    val notificationPrompt: NotificationPrompt? = null,
    /** Null until the board first loads. */
    val board: MessageBoard? = null,
    val messageForm: MessageForm = MessageForm(),
    /** The signed-in account's name, shown as "Posting as" for organizers. */
    val accountName: String? = null,
)

@androidx.compose.runtime.Stable
interface CourtDetailActions {
    fun toggleRoll(key: String, value: Boolean)
    fun toggleCleared(key: String, value: Boolean)
    fun setAll(rollCall: Boolean, value: Boolean)
    fun saveRollClearing()
    fun renameParticipant(id: Int, name: String)
    fun resetParticipantPin(id: Int, pin: String)
    fun removeParticipant(id: Int)
    fun composeMessage(replyTo: CourtMessage?)
    fun deleteMessage(id: Int)
}

sealed interface CourtDetailEffect {
    data class Message(val message: UiMessage) : CourtDetailEffect
    data object PlayerSheetDone : CourtDetailEffect
    data object Deleted : CourtDetailEffect
}

@HiltViewModel
class CourtDetailViewModel @Inject constructor(
    savedStateHandle: SavedStateHandle,
    private val courts: CourtRepository,
    private val settings: SettingsStore,
    private val push: PushRepository,
    session: SessionStore,
) : ViewModel(), CourtDetailActions {
    val guid: String = savedStateHandle.toRoute<CourtDetailRoute>().guid

    private val _uiState = MutableStateFlow(
        CourtDetailUiState(
            playerForm = PlayerForm(username = settings.current.lastJoinName),
            messageForm = MessageForm(username = settings.current.lastJoinName),
            accountName = session.session.value.user?.username,
        ),
    )
    val uiState: StateFlow<CourtDetailUiState> = _uiState.asStateFlow()
    private val _effects = Channel<CourtDetailEffect>(Channel.BUFFERED)
    val effects = _effects.receiveAsFlow()

    init {
        // A push about this court (a new message, players joining…) while it is open.
        viewModelScope.launch {
            CourtNotifications.received.filter { it == guid }.collect { refresh() }
        }
        viewModelScope.launch {
            if (!push.available()) return@launch
            _uiState.update { it.copy(push = it.push.copy(available = true)) }
            push.isSubscribed(guid).onSuccess { subscribed -> updatePush { copy(subscribed = subscribed) } }
        }
    }

    // Notifications ------------------------------------------------------------------------

    /** The screen calls this only once notification permission is granted (when turning on). */
    fun setNotifications(enabled: Boolean) {
        if (_uiState.value.push.busy) return
        updatePush { copy(busy = true) }
        viewModelScope.launch {
            push.setSubscribed(guid, enabled)
                .onSuccess { subscribed ->
                    updatePush { copy(subscribed = subscribed, busy = false) }
                    val message = if (subscribed) R.string.push_notifications_enabled else R.string.push_notifications_disabled
                    _effects.send(CourtDetailEffect.Message(UiMessage.Res(message)))
                }
                .onFailure { e ->
                    updatePush { copy(busy = false) }
                    val message = if (e is DataError.Api) e.toUiMessage() else UiMessage.Res(R.string.push_notifications_error)
                    _effects.send(CourtDetailEffect.Message(message))
                }
        }
    }

    private fun updatePush(change: PushUi.() -> PushUi) = _uiState.update { it.copy(push = it.push.change()) }

    fun dismissNotificationPrompt() = _uiState.update { it.copy(notificationPrompt = null) }

    private fun promptAfter(mode: PlayerMode) = _uiState.update {
        val push = it.push
        val prompt = when {
            !push.available || push.busy -> null
            mode == PlayerMode.Join && !push.subscribed -> NotificationPrompt.Enable
            mode == PlayerMode.Leave && push.subscribed -> NotificationPrompt.Disable
            else -> null
        }
        it.copy(notificationPrompt = prompt)
    }

    fun refresh() {
        refreshMessages()
        _uiState.update { it.copy(loading = it.court == null, error = null) }
        viewModelScope.launch {
            courts.detail(guid)
                .onSuccess(::showCourt)
                .onFailure { e ->
                    val notFound = e is DataError.Api && e.status == 404
                    _uiState.update { it.copy(loading = false, notFound = notFound, error = if (notFound) null else e.toUiMessage()) }
                }
        }
    }

    private fun showCourt(court: Court) {
        _uiState.update {
            it.copy(
                court = court,
                loading = false,
                notFound = false,
                error = null,
                busy = false,
                rollDraft = if (it.rollDirty) it.rollDraft else court.rollDraft(),
            )
        }
    }

    // Message board ------------------------------------------------------------------------

    /** Cheap when nothing changed: the server answers just the version. */
    fun refreshMessages() {
        viewModelScope.launch {
            courts.messages(guid, _uiState.value.board?.version).onSuccess(::showBoard)
        }
    }

    private fun showBoard(board: MessageBoard) {
        if (board.changed) _uiState.update { it.copy(board = board) }
    }

    override fun composeMessage(replyTo: CourtMessage?) = updateMessageForm {
        // Keep an unsent draft when reopening the same composer.
        val sameTarget = this.replyTo?.id == replyTo?.id
        copy(open = true, replyTo = replyTo, message = if (sameTarget) message else "", error = null)
    }

    fun closeMessageSheet() = updateMessageForm { copy(open = false) }
    fun setMessageName(name: String) = updateMessageForm { copy(username = name.take(40), error = null) }
    fun setMessagePin(pin: String) = updateMessageForm { copy(pin = pin, error = null) }
    fun setMessageText(text: String) = updateMessageForm { copy(message = text.take(MESSAGE_MAX_LENGTH), error = null) }

    fun submitMessage() {
        val state = _uiState.value
        val form = state.messageForm
        val asOrganizer = state.court?.viewer?.canManage == true
        if (!form.canSubmit(asOrganizer)) return
        updateMessageForm { copy(submitting = true, error = null) }
        viewModelScope.launch {
            // Replies reach this device only if it follows the court; the server checks that too.
            val token = if (state.push.subscribed) push.knownToken() else null
            courts.postMessage(
                guid,
                username = if (asOrganizer) "" else form.username,
                pin = if (asOrganizer) "" else form.pin,
                message = form.message,
                parentId = form.replyTo?.id,
                fcmToken = token,
            )
                .onSuccess { board ->
                    if (!asOrganizer) settings.setLastJoinName(form.username.trim())
                    showBoard(board)
                    updateMessageForm { MessageForm(username = username) }
                    val posted = if (form.replyTo != null) R.string.court_message_reply_posted else R.string.court_message_posted
                    _effects.send(CourtDetailEffect.Message(UiMessage.Res(posted)))
                }
                .onFailure { e ->
                    val wrongCredentials = e is DataError.Api && e.status == 403
                    val gone = e is DataError.Api && e.code == "court_message_reply_missing"
                    updateMessageForm {
                        copy(
                            submitting = false,
                            error = e.toUiMessage(),
                            pin = if (wrongCredentials) "" else pin,
                            // The thread was deleted: keep the text as a new message instead.
                            replyTo = if (gone) null else replyTo,
                        )
                    }
                    if (gone) refreshMessages()
                }
        }
    }

    override fun deleteMessage(id: Int) {
        viewModelScope.launch {
            courts.deleteMessage(guid, id)
                .onSuccess {
                    showBoard(it)
                    _effects.send(CourtDetailEffect.Message(UiMessage.Res(R.string.court_message_deleted)))
                }
                .onFailure(::fail)
        }
    }

    private fun updateMessageForm(change: MessageForm.() -> MessageForm) =
        _uiState.update { it.copy(messageForm = it.messageForm.change()) }

    // Join / leave -----------------------------------------------------------------------

    fun setPlayerMode(mode: PlayerMode) = updateForm { copy(mode = mode, error = null) }
    fun setPlayerName(name: String) = updateForm { copy(username = name.take(40), error = null) }
    fun setPlayerPin(pin: String) = updateForm { copy(pin = pin, error = null) }

    fun submitPlayerForm() {
        val form = _uiState.value.playerForm
        if (!form.canSubmit) return
        updateForm { copy(submitting = true, error = null) }
        viewModelScope.launch {
            val result = if (form.mode == PlayerMode.Join) {
                courts.join(guid, form.username, form.pin).map { response ->
                    response.court to if (response.waitlisted) R.string.joined_waitlist_success else R.string.joined_success
                }
            } else {
                courts.leave(guid, form.username, form.pin).map { it to R.string.left_success }
            }
            result
                .onSuccess { (court, message) ->
                    settings.setLastJoinName(form.username.trim())
                    showCourt(court)
                    updateForm { copy(pin = "", submitting = false) }
                    _effects.send(CourtDetailEffect.PlayerSheetDone)
                    _effects.send(CourtDetailEffect.Message(UiMessage.Res(message)))
                    promptAfter(form.mode)
                }
                .onFailure { e -> updateForm { copy(submitting = false, error = e.toUiMessage()) } }
        }
    }

    private fun updateForm(change: PlayerForm.() -> PlayerForm) = _uiState.update { it.copy(playerForm = it.playerForm.change()) }

    // Organizer actions ------------------------------------------------------------------

    fun archive() = courtAction(R.string.court_archived) { courts.archive(guid) }
    fun restore() = courtAction(R.string.court_restored) { courts.restore(guid) }
    fun startRollClearing() = courtAction(R.string.roll_and_clearing_started) {
        _uiState.update { it.copy(rollDirty = false) }
        courts.startRollClearing(guid)
    }
    fun endRollClearing() = courtAction(R.string.editing_mode_restored) { courts.endRollClearing(guid) }

    fun delete() {
        _uiState.update { it.copy(busy = true) }
        viewModelScope.launch {
            courts.delete(guid)
                .onSuccess {
                    _effects.send(CourtDetailEffect.Message(UiMessage.Res(R.string.court_deleted)))
                    _effects.send(CourtDetailEffect.Deleted)
                }
                .onFailure(::fail)
        }
    }

    override fun toggleRoll(key: String, value: Boolean) = _uiState.update {
        it.copy(rollDraft = it.rollDraft.copy(rollCalled = it.rollDraft.rollCalled + (key to value)), rollDirty = true)
    }

    override fun toggleCleared(key: String, value: Boolean) = _uiState.update {
        it.copy(rollDraft = it.rollDraft.copy(cleared = it.rollDraft.cleared + (key to value)), rollDirty = true)
    }

    override fun setAll(rollCall: Boolean, value: Boolean) = _uiState.update { state ->
        val keys = state.court?.rollKeys().orEmpty()
        val draft = state.rollDraft
        val updated = keys.associateWith { value }
        state.copy(
            rollDraft = if (rollCall) draft.copy(rollCalled = draft.rollCalled + updated) else draft.copy(cleared = draft.cleared + updated),
            rollDirty = true,
        )
    }

    override fun saveRollClearing() {
        val state = _uiState.value
        val court = state.court ?: return
        val draft = state.rollDraft
        fun status(key: String, id: Int) = RollStatus(id, draft.rollCalled[key] == true, draft.cleared[key] == true)
        val participants = court.participants.map { status("p${it.id}", it.id) }
        val reserved = court.reservedMembers.mapNotNull { m -> m.id?.let { status("r$it", it) } }
        courtAction(R.string.member_statuses_saved) {
            _uiState.update { it.copy(rollDirty = false) }
            courts.saveRollClearing(guid, participants, reserved)
        }
    }

    // Admin player management -------------------------------------------------------------

    override fun renameParticipant(id: Int, name: String) = courtAction(R.string.participant_renamed) { courts.renameParticipant(guid, id, name.trim()) }
    override fun resetParticipantPin(id: Int, pin: String) = courtAction(R.string.participant_pin_reset) { courts.resetParticipantPin(guid, id, pin) }
    override fun removeParticipant(id: Int) = courtAction(R.string.participant_removed) { courts.removeParticipant(guid, id) }

    private fun courtAction(success: Int, block: suspend () -> Result<Court>) {
        _uiState.update { it.copy(busy = true) }
        viewModelScope.launch {
            block()
                .onSuccess {
                    showCourt(it)
                    _effects.send(CourtDetailEffect.Message(UiMessage.Res(success)))
                }
                .onFailure(::fail)
        }
    }

    private fun fail(e: Throwable) {
        _uiState.update { it.copy(busy = false) }
        viewModelScope.launch { _effects.send(CourtDetailEffect.Message(e.toUiMessage())) }
    }
}

private fun Court.rollKeys(): List<String> = participants.map { "p${it.id}" } + reservedMembers.mapNotNull { m -> m.id?.let { "r$it" } }

private fun Court.rollDraft() = RollDraft(
    rollCalled = participants.associate { "p${it.id}" to it.rollCalled } +
        reservedMembers.mapNotNull { m -> m.id?.let { "r$it" to m.rollCalled } },
    cleared = participants.associate { "p${it.id}" to it.cleared } +
        reservedMembers.mapNotNull { m -> m.id?.let { "r$it" to m.cleared } },
)
