package io.github.ychsieh95.bccp.feature.contact

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import io.github.ychsieh95.bccp.core.data.AccountRepository
import io.github.ychsieh95.bccp.core.data.SettingsStore
import io.github.ychsieh95.bccp.core.model.TurnstileConfig
import io.github.ychsieh95.bccp.core.ui.UiMessage
import io.github.ychsieh95.bccp.core.ui.fieldErrors
import io.github.ychsieh95.bccp.core.ui.toUiMessage
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ContactUiState(
    val name: String = "",
    val reply: String = "",
    val subject: String = "",
    val message: String = "",
    val turnstile: TurnstileConfig = TurnstileConfig(),
    val serverUrl: String = "",
    val turnstileToken: String? = null,
    val turnstileReset: Int = 0,
    val fieldErrors: Map<String, String> = emptyMap(),
    val error: UiMessage? = null,
    val submitting: Boolean = false,
    val sent: Boolean = false,
) {
    val canSubmit: Boolean get() = name.isNotBlank() && subject.isNotBlank() && message.isNotBlank() &&
        (!turnstile.enabled || turnstileToken != null) && !submitting
}

@HiltViewModel
class ContactViewModel @Inject constructor(
    private val account: AccountRepository,
    settings: SettingsStore,
) : ViewModel() {
    private val _uiState = MutableStateFlow(ContactUiState(serverUrl = settings.current.serverUrl))
    val uiState: StateFlow<ContactUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch { account.meta().onSuccess { m -> _uiState.update { it.copy(turnstile = m.turnstile) } } }
    }

    fun set(field: String, value: String) = _uiState.update {
        val errors = it.fieldErrors - field
        when (field) {
            "sender_name" -> it.copy(name = value, fieldErrors = errors)
            "reply_contact" -> it.copy(reply = value, fieldErrors = errors)
            "subject" -> it.copy(subject = value, fieldErrors = errors)
            else -> it.copy(message = value, fieldErrors = errors)
        }
    }

    fun setTurnstileToken(token: String?) = _uiState.update { it.copy(turnstileToken = token) }

    fun submit() {
        val s = _uiState.value
        if (!s.canSubmit) return
        _uiState.update { it.copy(submitting = true, error = null) }
        viewModelScope.launch {
            account.sendContact(s.name, s.reply, s.subject, s.message, s.turnstileToken)
                .onSuccess { _uiState.update { it.copy(submitting = false, sent = true) } }
                .onFailure { e ->
                    _uiState.update {
                        it.copy(
                            submitting = false, error = e.toUiMessage(), fieldErrors = e.fieldErrors,
                            turnstileToken = null, turnstileReset = it.turnstileReset + 1,
                        )
                    }
                }
        }
    }

    fun reset() = _uiState.update {
        ContactUiState(turnstile = it.turnstile, serverUrl = it.serverUrl, name = it.name, reply = it.reply, turnstileReset = it.turnstileReset + 1)
    }
}
