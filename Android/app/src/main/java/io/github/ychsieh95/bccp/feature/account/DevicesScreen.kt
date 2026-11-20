package io.github.ychsieh95.bccp.feature.account

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.outlined.PhoneAndroid
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
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.model.DeviceToken
import io.github.ychsieh95.bccp.core.ui.component.ConfirmDialog
import io.github.ychsieh95.bccp.core.ui.component.ErrorPane
import io.github.ychsieh95.bccp.core.ui.component.LoadingPane
import io.github.ychsieh95.bccp.core.ui.component.PanelCard
import io.github.ychsieh95.bccp.core.ui.component.Pill
import io.github.ychsieh95.bccp.core.ui.format.dateTime
import io.github.ychsieh95.bccp.core.ui.text

@Composable
fun DevicesScreen(onBack: () -> Unit, viewModel: DevicesViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    val context = LocalContext.current
    var confirm by remember { mutableStateOf<DeviceToken?>(null) }
    LaunchedEffect(Unit) { viewModel.messages.collect { snackbar.showSnackbar(it.resolve(context)) } }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.signed_in_devices)) },
                navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, stringResource(R.string.back)) } },
            )
        },
    ) { padding ->
        when {
            state.loading && state.devices.isEmpty() -> LoadingPane(Modifier.padding(padding))
            state.error != null -> ErrorPane(state.error!!.text(), viewModel::refresh, Modifier.padding(padding))
            else -> LazyColumn(
                Modifier.padding(padding).fillMaxSize(),
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                item { Text(stringResource(R.string.signed_in_devices_body), color = MaterialTheme.colorScheme.onSurfaceVariant) }
                items(state.devices, key = { it.id }) { device ->
                    PanelCard(Modifier.widthIn(max = 840.dp)) {
                        androidx.compose.foundation.layout.Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Outlined.PhoneAndroid, null, tint = MaterialTheme.colorScheme.primary)
                            Text(device.name.ifBlank { "—" }, style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(start = 12.dp).weight(1f))
                            if (device.current) Pill(stringResource(R.string.this_device), MaterialTheme.colorScheme.primaryContainer, MaterialTheme.colorScheme.primary)
                        }
                        Text(stringResource(R.string.last_used, dateTime(device.lastUsedAt)), style = MaterialTheme.typography.bodySmall)
                        Text(stringResource(R.string.expires, dateTime(device.expiresAt)), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        TextButton(onClick = { confirm = device }) {
                            Text(stringResource(if (device.current) R.string.sign_out else R.string.sign_out_device), color = MaterialTheme.colorScheme.error)
                        }
                    }
                }
            }
        }
    }
    confirm?.let { device ->
        ConfirmDialog(
            title = device.name,
            message = stringResource(if (device.current) R.string.sign_out else R.string.sign_out_device) + "?",
            confirmLabel = stringResource(R.string.sign_out),
            destructive = true,
            onConfirm = { viewModel.revoke(device) },
            onDismiss = { confirm = null },
        )
    }
}
