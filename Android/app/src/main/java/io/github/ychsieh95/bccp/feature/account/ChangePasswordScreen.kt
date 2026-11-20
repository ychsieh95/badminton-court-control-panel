package io.github.ychsieh95.bccp.feature.account

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
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
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import io.github.ychsieh95.bccp.R
import kotlinx.coroutines.launch
import io.github.ychsieh95.bccp.core.ui.component.PanelCard
import io.github.ychsieh95.bccp.core.ui.component.PrimaryActionButton
import io.github.ychsieh95.bccp.core.ui.component.SecretInput
import io.github.ychsieh95.bccp.core.ui.text

/** [onBack] is null when the server requires replacing a temporary password before anything else. */
@Composable
fun ChangePasswordScreen(onBack: (() -> Unit)?, onDone: () -> Unit, viewModel: ChangePasswordViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    val session by viewModel.session.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    val context = LocalContext.current
    val forced = session.user?.mustChangePassword == true
    LaunchedEffect(Unit) {
        viewModel.done.collect {
            launch { snackbar.showSnackbar(context.getString(R.string.password_changed)) }
            onDone()
        }
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.change_password)) },
                navigationIcon = {
                    if (onBack != null) IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, stringResource(R.string.back)) }
                },
                actions = { if (forced) TextButton(onClick = viewModel::signOut) { Text(stringResource(R.string.sign_out)) } },
            )
        },
    ) { padding ->
        Column(
            Modifier.padding(padding).fillMaxSize().verticalScroll(rememberScrollState()).imePadding().padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            PanelCard(Modifier.widthIn(max = 480.dp)) {
                Text(stringResource(R.string.change_password_title), style = MaterialTheme.typography.headlineSmall)
                Text(
                    stringResource(if (forced) R.string.temporary_password_banner else R.string.change_password_body),
                    style = MaterialTheme.typography.bodyMedium,
                    color = if (forced) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant,
                )
                SecretInput(state.current, viewModel::setCurrent, stringResource(if (forced) R.string.temporary_password else R.string.current_password))
                SecretInput(state.new, viewModel::setNew, stringResource(R.string.new_password), supporting = stringResource(R.string.password_help))
                SecretInput(state.confirm, viewModel::setConfirm, stringResource(R.string.confirm_password))
                state.error?.let { Text(it.text(), color = MaterialTheme.colorScheme.error) }
                PrimaryActionButton(stringResource(R.string.change_password), viewModel::submit, enabled = state.canSubmit, busy = state.submitting)
            }
        }
    }
}
