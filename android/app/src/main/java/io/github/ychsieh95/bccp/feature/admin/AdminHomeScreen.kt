package io.github.ychsieh95.bccp.feature.admin

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Group
import androidx.compose.material.icons.outlined.Mail
import androidx.compose.material.icons.outlined.SportsTennis
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.ui.component.PanelCard
import io.github.ychsieh95.bccp.core.ui.component.PrimaryActionButton
import io.github.ychsieh95.bccp.core.ui.component.SectionHeader
import io.github.ychsieh95.bccp.core.ui.component.SwitchRow
import io.github.ychsieh95.bccp.core.ui.component.TextInput
import io.github.ychsieh95.bccp.core.ui.text
import io.github.ychsieh95.bccp.feature.account.LinkGroup
import io.github.ychsieh95.bccp.feature.account.LinkRow

@Composable
fun AdminHomeScreen(onCourts: () -> Unit, onUsers: () -> Unit, onMessages: () -> Unit, viewModel: AdminHomeViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    val context = LocalContext.current
    LaunchedEffect(Unit) { viewModel.messages.collect { snackbar.showSnackbar(it.resolve(context)) } }
    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) { viewModel.refresh() }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        topBar = { TopAppBar(title = { Text(stringResource(R.string.admin_console)) }) },
    ) { padding ->
        Column(
            Modifier.padding(padding).fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            val width = Modifier.widthIn(max = 840.dp)
            LinkGroup(stringResource(R.string.admin_tools), width) {
                LinkRow(Icons.Outlined.SportsTennis, stringResource(R.string.admin_courts), stringResource(R.string.admin_courts_body), onCourts)
                if (state.managesAccounts) {
                    LinkRow(Icons.Outlined.Group, stringResource(R.string.user_management), stringResource(R.string.admin_users_body), onUsers)
                    LinkRow(
                        Icons.Outlined.Mail,
                        stringResource(R.string.contact_messages_title),
                        stringResource(R.string.admin_messages_body),
                        onMessages,
                        trailing = state.unreadCount.takeIf { it > 0 }?.let { stringResource(R.string.unread_count, it) },
                    )
                }
            }
            if (state.managesAccounts) {
                state.error?.let { Text(it.text(), color = MaterialTheme.colorScheme.error) }
                PanelCard(width) {
                    SectionHeader(stringResource(R.string.homepage_settings))
                    Text(stringResource(R.string.homepage_settings_body), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    TextInput(
                        state.homepageLimit, viewModel::setLimit, stringResource(R.string.homepage_court_limit),
                        supporting = stringResource(R.string.homepage_court_limit_help),
                        error = if (state.homepageLimit.isNotEmpty() && !state.limitValid) stringResource(R.string.invalid_homepage_court_limit) else null,
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    )
                    SectionHeader(stringResource(R.string.contact_notification_settings))
                    Text(stringResource(R.string.contact_notification_settings_body), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    val channels = state.settings?.contactNotificationChannels
                    SwitchRow(
                        stringResource(R.string.contact_notification_enable),
                        state.notifications,
                        viewModel::setNotifications,
                        enabled = channels?.discordReady == true || state.notifications,
                    )
                    if (channels != null) {
                        Text(
                            stringResource(if (channels.discordReady) R.string.contact_notification_discord_ready else R.string.contact_notification_discord_missing),
                            style = MaterialTheme.typography.bodySmall,
                        )
                        Text(
                            stringResource(if (channels.telegramReady) R.string.contact_notification_telegram_ready else R.string.contact_notification_telegram_missing),
                            style = MaterialTheme.typography.bodySmall,
                        )
                    }
                    PrimaryActionButton(stringResource(R.string.save_settings), viewModel::save, enabled = state.limitValid && state.settings != null, busy = state.saving)
                }
            }
        }
    }
}
