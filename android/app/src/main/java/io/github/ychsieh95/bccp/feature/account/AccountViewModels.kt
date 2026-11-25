package io.github.ychsieh95.bccp.feature.account

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.data.AccountRepository
import io.github.ychsieh95.bccp.core.data.LocalFile
import io.github.ychsieh95.bccp.core.data.Session
import io.github.ychsieh95.bccp.core.data.SessionStore
import io.github.ychsieh95.bccp.core.model.DeviceToken
import io.github.ychsieh95.bccp.core.model.SavedLocation
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

@HiltViewModel
class AccountViewModel @Inject constructor(
    sessionStore: SessionStore,
    private val account: AccountRepository,
) : ViewModel() {
    val session: StateFlow<Session> = sessionStore.session
    private val _messages = Channel<UiMessage>(Channel.BUFFERED)
    val messages = _messages.receiveAsFlow()

    fun signOut() = viewModelScope.launch {
        account.logout()
        _messages.send(UiMessage.Res(R.string.signed_out))
    }
}

data class ProfileUiState(
    val savedLocations: List<SavedLocation> = emptyList(),
    val busy: Boolean = false,
    val deleteError: UiMessage? = null,
)

@HiltViewModel
class ProfileViewModel @Inject constructor(
    sessionStore: SessionStore,
    private val account: AccountRepository,
) : ViewModel() {
    val session: StateFlow<Session> = sessionStore.session
    private val _uiState = MutableStateFlow(ProfileUiState())
    val uiState: StateFlow<ProfileUiState> = _uiState.asStateFlow()
    private val _messages = Channel<UiMessage>(Channel.BUFFERED)
    val messages = _messages.receiveAsFlow()
    private val _deleted = Channel<Unit>(Channel.BUFFERED)
    val deleted = _deleted.receiveAsFlow()

    init {
        viewModelScope.launch {
            account.savedLocations().onSuccess { list -> _uiState.update { it.copy(savedLocations = list) } }
        }
    }

    fun setTimeFormat(format: String) = run(R.string.profile_preferences_saved) { account.setTimeFormat(format) }
    fun uploadAvatar(file: LocalFile) = run(R.string.avatar_updated) { account.uploadAvatar(file) }
    fun removeAvatar() = run(R.string.avatar_removed) { account.removeAvatar() }

    fun deleteSavedLocation(id: Int) = run(R.string.saved_location_deleted) {
        account.deleteSavedLocation(id).onSuccess {
            _uiState.update { s -> s.copy(savedLocations = s.savedLocations.filterNot { it.id == id }) }
        }
    }

    fun deleteAccount(password: String) {
        _uiState.update { it.copy(busy = true, deleteError = null) }
        viewModelScope.launch {
            account.deleteAccount(password)
                .onSuccess {
                    _messages.send(UiMessage.Res(R.string.account_deleted))
                    _deleted.send(Unit)
                }
                .onFailure { e -> _uiState.update { it.copy(busy = false, deleteError = e.toUiMessage()) } }
        }
    }

    fun clearDeleteError() = _uiState.update { it.copy(deleteError = null) }

    private fun run(success: Int, block: suspend () -> Result<*>) {
        _uiState.update { it.copy(busy = true) }
        viewModelScope.launch {
            val result = block()
            _uiState.update { it.copy(busy = false) }
            _messages.send(result.exceptionOrNull()?.toUiMessage() ?: UiMessage.Res(success))
        }
    }
}

data class ChangePasswordUiState(
    val current: String = "",
    val new: String = "",
    val confirm: String = "",
    val error: UiMessage? = null,
    val submitting: Boolean = false,
) {
    val canSubmit: Boolean get() = current.isNotEmpty() && new.length >= 8 && confirm.isNotEmpty() && !submitting
}

@HiltViewModel
class ChangePasswordViewModel @Inject constructor(
    sessionStore: SessionStore,
    private val account: AccountRepository,
) : ViewModel() {
    val session: StateFlow<Session> = sessionStore.session
    private val _uiState = MutableStateFlow(ChangePasswordUiState())
    val uiState: StateFlow<ChangePasswordUiState> = _uiState.asStateFlow()
    private val _done = Channel<Unit>(Channel.BUFFERED)
    val done = _done.receiveAsFlow()

    fun setCurrent(v: String) = _uiState.update { it.copy(current = v, error = null) }
    fun setNew(v: String) = _uiState.update { it.copy(new = v, error = null) }
    fun setConfirm(v: String) = _uiState.update { it.copy(confirm = v, error = null) }

    fun submit() {
        val s = _uiState.value
        if (!s.canSubmit) return
        if (s.new != s.confirm) {
            _uiState.update { it.copy(error = UiMessage.Res(R.string.password_mismatch)) }
            return
        }
        _uiState.update { it.copy(submitting = true) }
        viewModelScope.launch {
            account.changePassword(s.current, s.new, s.confirm)
                .onSuccess {
                    _uiState.value = ChangePasswordUiState()
                    _done.send(Unit)
                }
                .onFailure { e -> _uiState.update { it.copy(submitting = false, error = e.toUiMessage()) } }
        }
    }

    fun signOut() = viewModelScope.launch { account.logout() }
}

data class DevicesUiState(
    val devices: List<DeviceToken> = emptyList(),
    val loading: Boolean = true,
    val error: UiMessage? = null,
)

@HiltViewModel
class DevicesViewModel @Inject constructor(private val account: AccountRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(DevicesUiState())
    val uiState: StateFlow<DevicesUiState> = _uiState.asStateFlow()
    private val _messages = Channel<UiMessage>(Channel.BUFFERED)
    val messages = _messages.receiveAsFlow()

    init {
        refresh()
    }

    fun refresh() {
        _uiState.update { it.copy(loading = true, error = null) }
        viewModelScope.launch {
            account.devices()
                .onSuccess { list -> _uiState.update { it.copy(devices = list, loading = false) } }
                .onFailure { e -> _uiState.update { it.copy(loading = false, error = e.toUiMessage()) } }
        }
    }

    fun revoke(device: DeviceToken) = viewModelScope.launch {
        if (device.current) {
            account.logout()
            return@launch
        }
        account.revokeDevice(device.id)
            .onSuccess {
                _uiState.update { s -> s.copy(devices = s.devices.filterNot { it.id == device.id }) }
                _messages.send(UiMessage.Res(R.string.device_signed_out))
            }
            .onFailure { _messages.send(it.toUiMessage()) }
    }
}
