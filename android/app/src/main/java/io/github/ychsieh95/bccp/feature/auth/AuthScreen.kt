package io.github.ychsieh95.bccp.feature.auth

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.ui.component.PanelCard
import io.github.ychsieh95.bccp.core.ui.component.PrimaryActionButton
import io.github.ychsieh95.bccp.core.ui.component.SecretInput
import io.github.ychsieh95.bccp.core.ui.component.TextInput
import io.github.ychsieh95.bccp.core.ui.text

@Composable
fun AuthScreen(startWithSignup: Boolean, onBack: () -> Unit, onSignedIn: () -> Unit, viewModel: AuthViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    LaunchedEffect(startWithSignup) { viewModel.setSignup(startWithSignup) }
    LaunchedEffect(Unit) { viewModel.signedIn.collect { onSignedIn() } }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.account)) },
                navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, stringResource(R.string.back)) } },
            )
        },
    ) { padding ->
        Column(
            Modifier.padding(padding).fillMaxSize().verticalScroll(rememberScrollState()).imePadding().padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            PanelCard(Modifier.widthIn(max = 480.dp)) {
                Text(
                    stringResource(if (state.signup) R.string.signup_title else R.string.member_login_title),
                    style = MaterialTheme.typography.headlineSmall,
                )
                Text(
                    stringResource(if (state.signup) R.string.signup_body else R.string.member_login_body),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                TextInput(
                    state.username, viewModel::setUsername, stringResource(R.string.username),
                    supporting = if (state.signup) stringResource(R.string.account_username_help) else null,
                )
                SecretInput(
                    state.password, viewModel::setPassword, stringResource(R.string.password),
                    supporting = if (state.signup) stringResource(R.string.password_help) else null,
                )
                if (state.signup) SecretInput(state.confirm, viewModel::setConfirm, stringResource(R.string.confirm_password))
                if (state.turnstile.enabled) {
                    TurnstileWidget(
                        state.turnstile.siteKey,
                        state.serverUrl,
                        action = if (state.signup) "signup" else "login",
                        resetKey = state.turnstileReset,
                        onToken = viewModel::setTurnstileToken,
                    )
                }
                state.error?.let { Text(it.text(), color = MaterialTheme.colorScheme.error) }
                PrimaryActionButton(
                    text = stringResource(if (state.signup) R.string.create_account else R.string.sign_in),
                    onClick = viewModel::submit,
                    enabled = state.canSubmit,
                    busy = state.submitting,
                )
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.Center) {
                    Text(
                        stringResource(if (state.signup) R.string.have_account else R.string.need_account),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.weight(1f, fill = false),
                    )
                    TextButton(onClick = { viewModel.setSignup(!state.signup) }) {
                        Text(stringResource(if (state.signup) R.string.sign_in else R.string.sign_up))
                    }
                }
            }
        }
    }
}
