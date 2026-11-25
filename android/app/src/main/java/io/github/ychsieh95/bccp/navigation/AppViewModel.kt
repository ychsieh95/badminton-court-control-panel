package io.github.ychsieh95.bccp.navigation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import io.github.ychsieh95.bccp.core.data.AccountRepository
import io.github.ychsieh95.bccp.core.data.AppSettings
import io.github.ychsieh95.bccp.core.data.PushRepository
import io.github.ychsieh95.bccp.core.data.Session
import io.github.ychsieh95.bccp.core.data.SessionStore
import io.github.ychsieh95.bccp.core.data.SettingsStore
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.distinctUntilChangedBy
import kotlinx.coroutines.flow.filter
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class AppViewModel @Inject constructor(
    settingsStore: SettingsStore,
    sessionStore: SessionStore,
    private val account: AccountRepository,
    private val push: PushRepository,
) : ViewModel() {
    val settings: StateFlow<AppSettings> = settingsStore.settings
    val session: StateFlow<Session> = sessionStore.session

    init {
        // Refresh the cached user once per launch so role changes and forced password
        // resets made on the website take effect.
        viewModelScope.launch {
            settings.filter { it.loaded }.first()
            session.filter { it.loaded }.distinctUntilChangedBy { it.token }.collect {
                if (it.token != null) {
                    account.refreshMe()
                    // Organizer notifications reach the devices the account is signed in on.
                    push.syncAccountToken()
                }
            }
        }
    }
}
