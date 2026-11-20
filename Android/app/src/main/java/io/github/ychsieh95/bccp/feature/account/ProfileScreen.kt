package io.github.ychsieh95.bccp.feature.account

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.Place
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.ListItem
import androidx.compose.material3.ListItemDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
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
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.data.LocalFile
import io.github.ychsieh95.bccp.core.model.SavedLocation
import io.github.ychsieh95.bccp.core.ui.component.ConfirmDialog
import io.github.ychsieh95.bccp.core.ui.component.PanelCard
import io.github.ychsieh95.bccp.core.ui.component.SecretInput
import io.github.ychsieh95.bccp.core.ui.component.SectionHeader
import io.github.ychsieh95.bccp.core.ui.component.UserAvatar
import io.github.ychsieh95.bccp.core.ui.format.dateTime
import io.github.ychsieh95.bccp.core.ui.text

@Composable
fun ProfileScreen(onBack: () -> Unit, onAccountDeleted: () -> Unit, viewModel: ProfileViewModel = hiltViewModel()) {
    val session by viewModel.session.collectAsStateWithLifecycle()
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    val context = LocalContext.current
    LaunchedEffect(Unit) { viewModel.messages.collect { snackbar.showSnackbar(it.resolve(context)) } }
    LaunchedEffect(Unit) { viewModel.deleted.collect { onAccountDeleted() } }
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
        uri?.let { viewModel.uploadAvatar(LocalFile.from(context.contentResolver, it)) }
    }
    var confirmLocation by remember { mutableStateOf<SavedLocation?>(null) }
    var deleteOpen by rememberSaveable { mutableStateOf(false) }
    val user = session.user ?: return

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.profile_title)) },
                navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, stringResource(R.string.back)) } },
            )
        },
    ) { padding ->
        Box(Modifier.padding(padding).fillMaxSize()) {
            Column(
                Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                val width = Modifier.widthIn(max = 840.dp)
                PanelCard(width) {
                    SectionHeader(stringResource(R.string.profile_picture))
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                        UserAvatar(user.username, Modifier.size(72.dp), url = user.avatarUrl)
                        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            OutlinedButton(onClick = { picker.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)) }) {
                                Text(stringResource(if (user.avatarUrl == null) R.string.upload_picture else R.string.replace_picture))
                            }
                            if (user.avatarUrl != null) {
                                TextButton(onClick = viewModel::removeAvatar) { Text(stringResource(R.string.remove_picture), color = MaterialTheme.colorScheme.error) }
                            }
                        }
                    }
                    Text(stringResource(R.string.avatar_help), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Facts(
                        stringResource(R.string.username) to user.username,
                        stringResource(R.string.account_role) to roleLabel(user.role),
                        stringResource(R.string.member_since) to dateTime(user.createdAt),
                        stringResource(R.string.last_login) to (dateTime(user.lastLoginAt).ifBlank { stringResource(R.string.never) }),
                    )
                }
                PanelCard(width) {
                    SectionHeader(stringResource(R.string.datetime_format), eyebrow = stringResource(R.string.preferences))
                    Text(stringResource(R.string.datetime_format_help), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    val formats = listOf("24h" to R.string.time_format_24h, "12h" to R.string.time_format_12h)
                    SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth()) {
                        formats.forEachIndexed { i, (value, label) ->
                            SegmentedButton(
                                selected = user.timeFormat == value,
                                onClick = { if (user.timeFormat != value) viewModel.setTimeFormat(value) },
                                shape = SegmentedButtonDefaults.itemShape(i, formats.size),
                            ) { Text(stringResource(label)) }
                        }
                    }
                }
                PanelCard(width) {
                    SectionHeader(stringResource(R.string.saved_locations))
                    Text(stringResource(R.string.saved_locations_body), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    if (state.savedLocations.isEmpty()) Text(stringResource(R.string.no_saved_locations), color = MaterialTheme.colorScheme.onSurfaceVariant)
                    state.savedLocations.forEach { location ->
                        ListItem(
                            headlineContent = { Text(location.hallName) },
                            supportingContent = { Text(location.location) },
                            leadingContent = { Icon(Icons.Outlined.Place, null) },
                            trailingContent = {
                                IconButton(onClick = { confirmLocation = location }) {
                                    Icon(Icons.Outlined.Delete, stringResource(R.string.delete_saved_location), tint = MaterialTheme.colorScheme.error)
                                }
                            },
                            colors = ListItemDefaults.colors(containerColor = MaterialTheme.colorScheme.surfaceContainerLowest),
                        )
                    }
                }
                if (!user.isAdmin) {
                    PanelCard(width) {
                        SectionHeader(stringResource(R.string.delete_account_title))
                        Text(stringResource(R.string.delete_account_warning), style = MaterialTheme.typography.bodyMedium)
                        OutlinedButton(onClick = { deleteOpen = true }) { Text(stringResource(R.string.delete_account), color = MaterialTheme.colorScheme.error) }
                    }
                }
            }
            if (state.busy) LinearProgressIndicator(Modifier.fillMaxWidth().align(Alignment.TopCenter))
        }
    }

    confirmLocation?.let { location ->
        ConfirmDialog(
            title = location.hallName,
            message = stringResource(R.string.delete_saved_location_confirm),
            confirmLabel = stringResource(R.string.delete),
            destructive = true,
            onConfirm = { viewModel.deleteSavedLocation(location.id) },
            onDismiss = { confirmLocation = null },
        )
    }
    if (deleteOpen) {
        var password by rememberSaveable { mutableStateOf("") }
        AlertDialog(
            onDismissRequest = { deleteOpen = false; viewModel.clearDeleteError() },
            title = { Text(stringResource(R.string.delete_account_confirm)) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(stringResource(R.string.delete_account_warning))
                    SecretInput(password, { password = it }, stringResource(R.string.current_password), error = state.deleteError?.text())
                }
            },
            confirmButton = {
                TextButton(onClick = { viewModel.deleteAccount(password) }, enabled = password.isNotEmpty() && !state.busy) {
                    Text(stringResource(R.string.delete_account), color = MaterialTheme.colorScheme.error)
                }
            },
            dismissButton = { TextButton(onClick = { deleteOpen = false; viewModel.clearDeleteError() }) { Text(stringResource(R.string.cancel)) } },
        )
    }
}

@Composable
private fun Facts(vararg facts: Pair<String, String>) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        facts.forEach { (label, value) ->
            Row(Modifier.fillMaxWidth()) {
                Text(label, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.weight(1f))
                Text(value, style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}
