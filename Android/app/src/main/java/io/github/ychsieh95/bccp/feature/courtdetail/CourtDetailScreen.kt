package io.github.ychsieh95.bccp.feature.courtdetail

import android.Manifest
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.outlined.FactCheck
import androidx.compose.material.icons.automirrored.outlined.Logout
import androidx.compose.material.icons.automirrored.outlined.OpenInNew
import androidx.compose.material.icons.outlined.Archive
import androidx.compose.material.icons.outlined.ContentCopy
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.Download
import androidx.compose.material.icons.outlined.Edit
import androidx.compose.material.icons.outlined.FileCopy
import androidx.compose.material.icons.outlined.MoreVert
import androidx.compose.material.icons.outlined.NotificationsActive
import androidx.compose.material.icons.outlined.NotificationsNone
import androidx.compose.material.icons.outlined.PersonAdd
import androidx.compose.material.icons.outlined.Share
import androidx.compose.material.icons.outlined.Unarchive
import androidx.compose.material3.BottomAppBar
import androidx.compose.material3.Button
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.repeatOnLifecycle
import kotlinx.coroutines.launch
import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.model.Court
import io.github.ychsieh95.bccp.core.ui.component.ConfirmDialog
import io.github.ychsieh95.bccp.core.ui.component.ErrorPane
import io.github.ychsieh95.bccp.core.ui.component.LoadingPane
import io.github.ychsieh95.bccp.core.ui.component.MessagePane
import io.github.ychsieh95.bccp.core.push.CourtNotifications
import io.github.ychsieh95.bccp.core.ui.UiMessage
import io.github.ychsieh95.bccp.core.ui.text
import kotlinx.coroutines.CoroutineScope

private enum class PendingConfirm { Archive, Delete, StartRoll, EndRoll }

@Composable
fun CourtDetailScreen(
    onBack: () -> Unit,
    onEdit: (String) -> Unit,
    onDuplicate: (String) -> Unit,
    viewModel: CourtDetailViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    val context = LocalContext.current
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    var playerSheetOpen by rememberSaveable { mutableStateOf(false) }
    var pendingConfirm by rememberSaveable { mutableStateOf<PendingConfirm?>(null) }
    val scope = rememberCoroutineScope()
    val blockedMessage = UiMessage.Res(R.string.push_notifications_blocked)
    val notificationPermission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted && CourtNotifications.canPost(context)) viewModel.setNotifications(true)
        else scope.showMessage(snackbar, blockedMessage.resolve(context))
    }
    val toggleNotifications = {
        when {
            state.push.subscribed -> viewModel.setNotifications(false)
            CourtNotifications.canPost(context) -> viewModel.setNotifications(true)
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU ->
                notificationPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
            else -> scope.showMessage(snackbar, blockedMessage.resolve(context))
        }
    }

    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) { viewModel.refresh() }
    LaunchedEffect(Unit) {
        lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED) {
            viewModel.effects.collect { effect ->
                when (effect) {
                    is CourtDetailEffect.Message -> launch { snackbar.showSnackbar(effect.message.resolve(context)) }
                    CourtDetailEffect.PlayerSheetDone -> playerSheetOpen = false
                    CourtDetailEffect.Deleted -> onBack()
                }
            }
        }
    }

    val court = state.court
    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        topBar = {
            TopAppBar(
                title = {},
                navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, stringResource(R.string.back)) } },
                actions = {
                    if (court != null) {
                        if (state.push.available) {
                            IconButton(onClick = toggleNotifications, enabled = !state.push.busy) {
                                if (state.push.subscribed) {
                                    Icon(Icons.Outlined.NotificationsActive, stringResource(R.string.push_notifications_turn_off), tint = MaterialTheme.colorScheme.primary)
                                } else {
                                    Icon(Icons.Outlined.NotificationsNone, stringResource(R.string.push_notifications_toggle))
                                }
                            }
                        }
                        IconButton(onClick = { CourtIntents.share(context, court) }) { Icon(Icons.Outlined.Share, stringResource(R.string.share)) }
                        CourtMenu(
                            court = court,
                            enabled = !state.busy,
                            onEdit = { onEdit(court.guid) },
                            onDuplicate = { onDuplicate(court.guid) },
                            onRestore = viewModel::restore,
                            onConfirm = { pending -> pendingConfirm = pending },
                        )
                    }
                },
            )
        },
        bottomBar = { if (court != null) PlayerBar(court, onOpen = { mode -> viewModel.setPlayerMode(mode); playerSheetOpen = true }) },
    ) { padding ->
        Box(Modifier.padding(padding).fillMaxSize()) {
            when {
                state.notFound -> MessagePane(
                    title = stringResource(R.string.court_not_found),
                    body = stringResource(R.string.court_not_found_body),
                    action = { OutlinedButton(onClick = onBack) { Text(stringResource(R.string.back_home)) } },
                )
                court == null && state.error != null -> ErrorPane(state.error!!.text(), viewModel::refresh)
                court == null -> LoadingPane()
                else -> CourtDetailContent(
                    court = court,
                    rollDraft = state.rollDraft,
                    rollDirty = state.rollDirty,
                    busy = state.busy,
                    actions = viewModel,
                )
            }
            if (state.busy) LinearProgressIndicator(Modifier.fillMaxWidth().align(Alignment.TopCenter))
        }
    }

    if (playerSheetOpen && court != null) {
        PlayerSheet(
            court = court,
            form = state.playerForm,
            onModeChange = viewModel::setPlayerMode,
            onNameChange = viewModel::setPlayerName,
            onPinChange = viewModel::setPlayerPin,
            onSubmit = viewModel::submitPlayerForm,
            onDismiss = { playerSheetOpen = false },
        )
    }

    state.notificationPrompt?.let { prompt ->
        val enable = prompt == NotificationPrompt.Enable
        ConfirmDialog(
            title = stringResource(if (enable) R.string.join_notify_prompt_title else R.string.leave_notify_prompt_title),
            message = stringResource(if (enable) R.string.join_notify_prompt_body else R.string.leave_notify_prompt_body),
            confirmLabel = stringResource(if (enable) R.string.join_notify_prompt_confirm else R.string.leave_notify_prompt_confirm),
            onDismiss = viewModel::dismissNotificationPrompt,
            onConfirm = {
                // Same path as the bell: turning on may need notification permission first.
                if (enable != state.push.subscribed) toggleNotifications()
            },
        )
    }

    pendingConfirm?.let { pending ->
        val (message, label, destructive) = when (pending) {
            PendingConfirm.Archive -> Triple(R.string.archive_confirm, R.string.archive, false)
            PendingConfirm.Delete -> Triple(R.string.delete_confirm, R.string.delete, true)
            PendingConfirm.StartRoll -> Triple(R.string.roll_and_clearing_confirm, R.string.start_roll_and_clearing, false)
            PendingConfirm.EndRoll -> Triple(R.string.end_roll_call_confirm, R.string.edit_from_roll_call, false)
        }
        ConfirmDialog(
            message = stringResource(message),
            confirmLabel = stringResource(label),
            destructive = destructive,
            onDismiss = { pendingConfirm = null },
            onConfirm = {
                when (pending) {
                    PendingConfirm.Archive -> viewModel.archive()
                    PendingConfirm.Delete -> viewModel.delete()
                    PendingConfirm.StartRoll -> viewModel.startRollClearing()
                    PendingConfirm.EndRoll -> viewModel.endRollClearing()
                }
            },
        )
    }
}

@Composable
private fun CourtMenu(
    court: Court,
    enabled: Boolean,
    onEdit: () -> Unit,
    onDuplicate: () -> Unit,
    onRestore: () -> Unit,
    onConfirm: (PendingConfirm) -> Unit,
) {
    val context = LocalContext.current
    var open by remember { mutableStateOf(false) }
    IconButton(onClick = { open = true }) { Icon(Icons.Outlined.MoreVert, stringResource(R.string.more_options)) }
    DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
        @Composable
        fun item(label: Int, icon: ImageVector, destructive: Boolean = false, action: () -> Unit) = DropdownMenuItem(
            text = { Text(stringResource(label), color = if (destructive) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurface) },
            leadingIcon = { Icon(icon, null, tint = if (destructive) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant) },
            enabled = enabled || !destructive,
            onClick = { open = false; action() },
        )
        item(R.string.copy_link, Icons.Outlined.ContentCopy) { CourtIntents.copyLink(context, court) }
        item(R.string.open_in_browser, Icons.AutoMirrored.Outlined.OpenInNew) { CourtIntents.openUrl(context, court.webUrl) }
        item(R.string.download_thumbnail, Icons.Outlined.Download) { CourtIntents.downloadThumbnail(context, court) }
        if (court.viewer.canManage) {
            HorizontalDivider()
            if (court.rollClearingLocked) {
                item(R.string.edit_from_roll_call, Icons.Outlined.Edit) { onConfirm(PendingConfirm.EndRoll) }
            } else {
                item(R.string.edit, Icons.Outlined.Edit, action = onEdit)
            }
            item(R.string.duplicate, Icons.Outlined.FileCopy, action = onDuplicate)
            if (!court.rollClearingLocked) item(R.string.start_roll_and_clearing, Icons.AutoMirrored.Outlined.FactCheck) { onConfirm(PendingConfirm.StartRoll) }
            if (court.archived) {
                item(R.string.restore, Icons.Outlined.Unarchive, action = onRestore)
            } else {
                item(R.string.archive, Icons.Outlined.Archive) { onConfirm(PendingConfirm.Archive) }
            }
            item(R.string.delete, Icons.Outlined.Delete, destructive = true) { onConfirm(PendingConfirm.Delete) }
        }
    }
}

/** Join/leave lives in the thumb zone, like the web's mobile join button. */
@Composable
private fun PlayerBar(court: Court, onOpen: (PlayerMode) -> Unit) {
    if (!court.acceptsPlayers) return
    BottomAppBar(contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 16.dp)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            OutlinedButton(onClick = { onOpen(PlayerMode.Leave) }, modifier = Modifier.weight(1f)) {
                Icon(Icons.AutoMirrored.Outlined.Logout, null, Modifier.padding(end = 8.dp))
                Text(stringResource(R.string.leave), maxLines = 1)
            }
            Button(onClick = { onOpen(PlayerMode.Join) }, modifier = Modifier.weight(1.4f)) {
                Icon(Icons.Outlined.PersonAdd, null, Modifier.padding(end = 8.dp))
                Text(stringResource(if (court.isFull) R.string.join_waitlist else R.string.join), maxLines = 1)
            }
        }
    }
}

private fun CoroutineScope.showMessage(snackbar: SnackbarHostState, message: String) {
    launch { snackbar.showSnackbar(message) }
}
