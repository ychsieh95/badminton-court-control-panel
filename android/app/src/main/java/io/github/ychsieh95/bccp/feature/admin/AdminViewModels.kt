package io.github.ychsieh95.bccp.feature.admin

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.data.AdminRepository
import io.github.ychsieh95.bccp.core.data.SessionStore
import io.github.ychsieh95.bccp.core.data.UserAction
import io.github.ychsieh95.bccp.core.model.AdminSettings
import io.github.ychsieh95.bccp.core.model.AdminUser
import io.github.ychsieh95.bccp.core.model.ContactMessage
import io.github.ychsieh95.bccp.core.model.Role
import io.github.ychsieh95.bccp.core.ui.UiMessage
import io.github.ychsieh95.bccp.core.ui.toUiMessage
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.receiveAsFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AdminHomeUiState(
    val managesAccounts: Boolean = false,
    val settings: AdminSettings? = null,
    val homepageLimit: String = "",
    val notifications: Boolean = false,
    val unreadCount: Int = 0,
    val saving: Boolean = false,
    val error: UiMessage? = null,
) {
    val limitValid: Boolean get() = homepageLimit.toIntOrNull() in 1..100
}

@HiltViewModel
class AdminHomeViewModel @Inject constructor(
    session: SessionStore,
    private val admin: AdminRepository,
) : ViewModel() {
    private val _uiState = MutableStateFlow(AdminHomeUiState(managesAccounts = session.session.value.user?.role?.managesAccounts == true))
    val uiState: StateFlow<AdminHomeUiState> = _uiState.asStateFlow()
    private val _messages = Channel<UiMessage>(Channel.BUFFERED)
    val messages = _messages.receiveAsFlow()

    fun refresh() {
        if (!_uiState.value.managesAccounts) return
        viewModelScope.launch {
            admin.settings()
                .onSuccess { s -> _uiState.update { it.copy(settings = s, homepageLimit = s.homepageCourtLimit.toString(), notifications = s.contactNotificationsEnabled, error = null) } }
                .onFailure { e -> _uiState.update { it.copy(error = e.toUiMessage()) } }
            admin.messages("unread", 1).onSuccess { page -> _uiState.update { it.copy(unreadCount = page.unreadCount) } }
        }
    }

    fun setLimit(value: String) = _uiState.update { it.copy(homepageLimit = value.filter(Char::isDigit).take(3)) }
    fun setNotifications(value: Boolean) = _uiState.update { it.copy(notifications = value) }

    fun save() {
        val state = _uiState.value
        val limit = state.homepageLimit.toIntOrNull() ?: return
        _uiState.update { it.copy(saving = true) }
        viewModelScope.launch {
            admin.updateSettings(limit, state.notifications)
                .onSuccess { s ->
                    _uiState.update { it.copy(settings = s, saving = false, notifications = s.contactNotificationsEnabled) }
                    _messages.send(UiMessage.Res(R.string.settings_saved))
                }
                .onFailure { e ->
                    _uiState.update { it.copy(saving = false, notifications = it.settings?.contactNotificationsEnabled ?: false) }
                    _messages.send(e.toUiMessage())
                }
        }
    }
}

data class UsersUiState(
    val users: List<AdminUser> = emptyList(),
    val viewerId: Int? = null,
    val viewerRole: Role = Role.Member,
    val loading: Boolean = true,
    val busyUserId: Int? = null,
    val error: UiMessage? = null,
)

@HiltViewModel
class UsersViewModel @Inject constructor(
    session: SessionStore,
    private val admin: AdminRepository,
) : ViewModel() {
    private val _uiState = MutableStateFlow(
        UsersUiState(viewerId = session.session.value.user?.id, viewerRole = session.session.value.user?.role ?: Role.Member),
    )
    val uiState: StateFlow<UsersUiState> = _uiState.asStateFlow()
    private val _messages = Channel<UiMessage>(Channel.BUFFERED)
    val messages = _messages.receiveAsFlow()

    init {
        refresh()
    }

    fun refresh() {
        _uiState.update { it.copy(loading = true, error = null) }
        viewModelScope.launch {
            admin.users()
                .onSuccess { list -> _uiState.update { it.copy(users = list, loading = false) } }
                .onFailure { e -> _uiState.update { it.copy(loading = false, error = e.toUiMessage()) } }
        }
    }

    fun act(user: AdminUser, action: UserAction) {
        val message = when (action) {
            UserAction.Archive -> R.string.account_archived_success
            UserAction.Restore -> R.string.account_restored_success
            UserAction.Ban -> R.string.account_banned_success
            UserAction.Unban -> R.string.account_unbanned_success
            UserAction.ResetLoginRetries -> R.string.login_retries_reset
        }
        mutate(user.id, message) { admin.userAction(user.id, action) }
    }

    fun setTemporaryPassword(user: AdminUser, password: String) =
        mutate(user.id, R.string.temporary_password_set) { admin.setTemporaryPassword(user.id, password) }

    fun setRole(user: AdminUser, role: Role) = mutate(user.id, R.string.role_updated) { admin.setRole(user.id, role) }

    fun delete(user: AdminUser) {
        _uiState.update { it.copy(busyUserId = user.id) }
        viewModelScope.launch {
            admin.deleteUser(user.id)
                .onSuccess {
                    _uiState.update { s -> s.copy(users = s.users.filterNot { it.id == user.id }, busyUserId = null) }
                    _messages.send(UiMessage.Res(R.string.user_account_deleted))
                }
                .onFailure { e ->
                    _uiState.update { it.copy(busyUserId = null) }
                    _messages.send(e.toUiMessage())
                }
        }
    }

    private fun mutate(id: Int, success: Int, block: suspend () -> Result<AdminUser>) {
        _uiState.update { it.copy(busyUserId = id) }
        viewModelScope.launch {
            block()
                .onSuccess { updated ->
                    _uiState.update { s -> s.copy(users = s.users.map { if (it.id == updated.id) updated else it }, busyUserId = null) }
                    _messages.send(UiMessage.Res(success))
                }
                .onFailure { e ->
                    _uiState.update { it.copy(busyUserId = null) }
                    _messages.send(e.toUiMessage())
                }
        }
    }
}

data class MessagesUiState(
    val messages: List<ContactMessage> = emptyList(),
    val status: String = "all",
    val page: Int = 1,
    val pageCount: Int = 1,
    val totalCount: Int = 0,
    val unreadCount: Int = 0,
    val loading: Boolean = true,
    val error: UiMessage? = null,
)

@HiltViewModel
class MessagesViewModel @Inject constructor(private val admin: AdminRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(MessagesUiState())
    val uiState: StateFlow<MessagesUiState> = _uiState.asStateFlow()
    private val _messages = Channel<UiMessage>(Channel.BUFFERED)
    val messages = _messages.receiveAsFlow()

    init {
        load()
    }

    fun setStatus(status: String) {
        _uiState.update { it.copy(status = status, page = 1) }
        load()
    }

    fun setPage(page: Int) {
        _uiState.update { it.copy(page = page) }
        load()
    }

    fun load() {
        val state = _uiState.value
        _uiState.update { it.copy(loading = true, error = null) }
        viewModelScope.launch {
            admin.messages(state.status, state.page)
                .onSuccess { r ->
                    _uiState.update {
                        it.copy(
                            messages = r.messages, page = r.page, pageCount = r.pageCount,
                            totalCount = r.totalCount, unreadCount = r.unreadCount, loading = false,
                        )
                    }
                }
                .onFailure { e -> _uiState.update { it.copy(loading = false, error = e.toUiMessage()) } }
        }
    }

    fun setRead(message: ContactMessage, read: Boolean) = viewModelScope.launch {
        admin.setMessageRead(message.id, read)
            .onSuccess { updated ->
                _uiState.update { s ->
                    s.copy(
                        messages = s.messages.map { if (it.id == updated.id) updated else it },
                        unreadCount = (s.unreadCount + if (read) -1 else 1).coerceAtLeast(0),
                    )
                }
                _messages.send(UiMessage.Res(R.string.contact_message_status_updated))
            }
            .onFailure { _messages.send(it.toUiMessage()) }
    }
}
