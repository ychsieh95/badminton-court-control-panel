package io.github.ychsieh95.bccp.feature.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.data.AccountRepository
import io.github.ychsieh95.bccp.core.data.SettingsStore
import io.github.ychsieh95.bccp.core.model.TurnstileConfig
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

data class AuthUiState(
    val signup: Boolean = false,
    val username: String = "",
    val password: String = "",
    val confirm: String = "",
    val turnstile: TurnstileConfig = TurnstileConfig(),
    val serverUrl: String = "",
    val turnstileToken: String? = null,
    val turnstileReset: Int = 0,
    val error: UiMessage? = null,
    val submitting: Boolean = false,
) {
    val canSubmit: Boolean get() = username.isNotBlank() &&
        password.length >= (if (signup) 8 else 1) &&
        (!signup || confirm.isNotEmpty()) &&
        (!turnstile.enabled || turnstileToken != null) &&
        !submitting
}

@HiltViewModel
class AuthViewModel @Inject constructor(
    private val account: AccountRepository,
    settings: SettingsStore,
) : ViewModel() {
    private val _uiState = MutableStateFlow(AuthUiState(serverUrl = settings.current.serverUrl))
    val uiState: StateFlow<AuthUiState> = _uiState.asStateFlow()
    private val _signedIn = Channel<Unit>(Channel.BUFFERED)
    val signedIn = _signedIn.receiveAsFlow()

    init {
        viewModelScope.launch {
            account.meta().onSuccess { meta -> _uiState.update { it.copy(turnstile = meta.turnstile) } }
        }
    }

    // The widget re-renders with the other action, so the old token no longer applies.
    fun setSignup(signup: Boolean) = _uiState.update { it.copy(signup = signup, error = null, turnstileToken = null) }
    fun setUsername(value: String) = _uiState.update { it.copy(username = value.take(40), error = null) }
    fun setPassword(value: String) = _uiState.update { it.copy(password = value, error = null) }
    fun setConfirm(value: String) = _uiState.update { it.copy(confirm = value, error = null) }
    fun setTurnstileToken(token: String?) = _uiState.update { it.copy(turnstileToken = token) }

    fun submit() {
        val state = _uiState.value
        if (!state.canSubmit) return
        if (state.signup && state.password != state.confirm) {
            _uiState.update { it.copy(error = UiMessage.Res(R.string.password_mismatch)) }
            return
        }
        _uiState.update { it.copy(submitting = true, error = null) }
        viewModelScope.launch {
            val result = if (state.signup) {
                account.signup(state.username, state.password, state.confirm, state.turnstileToken)
            } else {
                account.login(state.username, state.password, state.turnstileToken)
            }
            result
                .onSuccess { _signedIn.send(Unit) }
                .onFailure { e ->
                    _uiState.update {
                        it.copy(submitting = false, error = e.toUiMessage(), turnstileToken = null, turnstileReset = it.turnstileReset + 1)
                    }
                }
        }
    }
}
