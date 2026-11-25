package io.github.ychsieh95.bccp.feature.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.data.AccountRepository
import io.github.ychsieh95.bccp.core.data.AppSettings
import io.github.ychsieh95.bccp.core.data.Palette
import io.github.ychsieh95.bccp.core.data.SessionStore
import io.github.ychsieh95.bccp.core.data.SettingsStore
import io.github.ychsieh95.bccp.core.data.ThemeMode
import io.github.ychsieh95.bccp.core.ui.UiMessage
import io.github.ychsieh95.bccp.core.ui.toUiMessage
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SettingsUiState(
    val serverDraft: String,
    val savedServer: String,
    val signedIn: Boolean,
    val testing: Boolean = false,
    val status: UiMessage? = null,
    val statusIsError: Boolean = false,
) {
    val serverChanged: Boolean get() = SettingsStore.normalizeServerUrl(serverDraft) != savedServer
}

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val store: SettingsStore,
    private val session: SessionStore,
    private val account: AccountRepository,
) : ViewModel() {
    val settings: StateFlow<AppSettings> = store.settings
    private val _uiState = MutableStateFlow(
        SettingsUiState(store.current.serverUrl, store.current.serverUrl, session.session.value.signedIn),
    )
    val uiState: StateFlow<SettingsUiState> = _uiState.asStateFlow()

    fun setServerDraft(value: String) = _uiState.update { it.copy(serverDraft = value.trim(), status = null) }
    fun setThemeMode(mode: ThemeMode) = store.setThemeMode(mode)
    fun setPalette(palette: Palette) = store.setPalette(palette)

    fun saveAndTest() {
        val state = _uiState.value
        if (state.serverChanged) {
            // A token is only valid on the server that issued it.
            if (state.signedIn) session.clear()
            store.setServerUrl(state.serverDraft)
        }
        val saved = store.current.serverUrl
        _uiState.update { it.copy(serverDraft = saved, savedServer = saved, signedIn = session.session.value.signedIn, testing = true, status = null) }
        viewModelScope.launch {
            account.meta()
                .onSuccess { meta -> _uiState.update { it.copy(testing = false, status = UiMessage.Res(R.string.connection_ok, listOf(meta.apiVersion)), statusIsError = false) } }
                .onFailure { e -> _uiState.update { it.copy(testing = false, status = e.toUiMessage(), statusIsError = true) } }
        }
    }
}
