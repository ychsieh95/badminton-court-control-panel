package io.github.ychsieh95.bccp.feature.admin

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.outlined.MoreVert
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.RadioButton
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
import io.github.ychsieh95.bccp.core.data.UserAction
import io.github.ychsieh95.bccp.core.model.AdminUser
import io.github.ychsieh95.bccp.core.model.Role
import io.github.ychsieh95.bccp.core.ui.component.ConfirmDialog
import io.github.ychsieh95.bccp.core.ui.component.ErrorPane
import io.github.ychsieh95.bccp.core.ui.component.LoadingPane
import io.github.ychsieh95.bccp.core.ui.component.MessagePane
import io.github.ychsieh95.bccp.core.ui.component.PanelCard
import io.github.ychsieh95.bccp.core.ui.component.Pill
import io.github.ychsieh95.bccp.core.ui.component.UserAvatar
import io.github.ychsieh95.bccp.core.ui.format.dateTime
import io.github.ychsieh95.bccp.core.ui.text
import io.github.ychsieh95.bccp.feature.account.roleLabel
import io.github.ychsieh95.bccp.feature.courtdetail.InputDialog

private sealed interface UserDialog {
    val user: AdminUser
    data class Confirm(override val user: AdminUser, val action: UserAction?) : UserDialog
    data class TempPassword(override val user: AdminUser) : UserDialog
    data class ChangeRole(override val user: AdminUser) : UserDialog
}

@Composable
fun UsersScreen(onBack: () -> Unit, viewModel: UsersViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    val context = LocalContext.current
    var dialog by remember { mutableStateOf<UserDialog?>(null) }
    LaunchedEffect(Unit) { viewModel.messages.collect { snackbar.showSnackbar(it.resolve(context)) } }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.user_management)) },
                navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, stringResource(R.string.back)) } },
            )
        },
    ) { padding ->
        Box(Modifier.padding(padding).fillMaxSize()) {
            when {
                state.loading && state.users.isEmpty() -> LoadingPane()
                state.error != null -> ErrorPane(state.error!!.text(), viewModel::refresh)
                state.users.isEmpty() -> MessagePane(stringResource(R.string.no_users))
                else -> LazyColumn(
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    item { Text(stringResource(R.string.user_management_body), color = MaterialTheme.colorScheme.onSurfaceVariant) }
                    items(state.users, key = { it.id }) { user ->
                        UserCard(
                            user = user,
                            busy = state.busyUserId == user.id,
                            canChangeRole = state.viewerRole == Role.SuperAdmin && user.id != state.viewerId,
                            onDialog = { dialog = it },
                            onAction = { viewModel.act(user, it) },
                        )
                    }
                }
            }
        }
    }

    when (val d = dialog) {
        is UserDialog.Confirm -> {
            val (message, label) = when (d.action) {
                UserAction.Archive -> R.string.archive_account_confirm to R.string.archive_account
                UserAction.Ban -> R.string.ban_account_confirm to R.string.ban_account
                UserAction.ResetLoginRetries -> R.string.reset_login_retries_confirm to R.string.reset_login_retries
                else -> R.string.delete_user_account_confirm to R.string.delete_user_account
            }
            ConfirmDialog(
                title = d.user.username,
                message = stringResource(message),
                confirmLabel = stringResource(label),
                destructive = d.action != UserAction.ResetLoginRetries,
                onConfirm = { if (d.action == null) viewModel.delete(d.user) else viewModel.act(d.user, d.action) },
                onDismiss = { dialog = null },
            )
        }
        is UserDialog.TempPassword -> InputDialog(
            title = stringResource(R.string.set_temporary_password),
            initial = "",
            label = stringResource(R.string.temporary_password),
            secret = true,
            numeric = false,
            supporting = stringResource(R.string.password_help),
            valid = { it.length >= 8 },
            onConfirm = { viewModel.setTemporaryPassword(d.user, it) },
            onDismiss = { dialog = null },
        )
        is UserDialog.ChangeRole -> RoleDialog(d.user, onPick = { viewModel.setRole(d.user, it) }, onDismiss = { dialog = null })
        null -> Unit
    }
}

@Composable
private fun UserCard(user: AdminUser, busy: Boolean, canChangeRole: Boolean, onDialog: (UserDialog) -> Unit, onAction: (UserAction) -> Unit) {
    var menu by remember { mutableStateOf(false) }
    PanelCard(Modifier.widthIn(max = 840.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            UserAvatar(user.username)
            Column(Modifier.weight(1f)) {
                Text(user.username, style = MaterialTheme.typography.titleMedium)
                Text(roleLabel(user.role), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Box {
                IconButton(onClick = { menu = true }, enabled = !busy) { Icon(Icons.Outlined.MoreVert, stringResource(R.string.actions)) }
                DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                    @Composable
                    fun item(label: Int, destructive: Boolean = false, onClick: () -> Unit) = DropdownMenuItem(
                        text = { Text(stringResource(label), color = if (destructive) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurface) },
                        onClick = { menu = false; onClick() },
                    )
                    if (canChangeRole) item(R.string.change_role) { onDialog(UserDialog.ChangeRole(user)) }
                    item(R.string.set_temporary_password) { onDialog(UserDialog.TempPassword(user)) }
                    item(R.string.reset_login_retries) { onDialog(UserDialog.Confirm(user, UserAction.ResetLoginRetries)) }
                    if (user.banned) item(R.string.unban_account) { onAction(UserAction.Unban) }
                    else item(R.string.ban_account, destructive = true) { onDialog(UserDialog.Confirm(user, UserAction.Ban)) }
                    if (user.archived) {
                        item(R.string.restore_account) { onAction(UserAction.Restore) }
                        item(R.string.delete_user_account, destructive = true) { onDialog(UserDialog.Confirm(user, null)) }
                    } else {
                        item(R.string.archive_account, destructive = true) { onDialog(UserDialog.Confirm(user, UserAction.Archive)) }
                    }
                }
            }
        }
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            val scheme = MaterialTheme.colorScheme
            when {
                user.banned -> Pill(stringResource(R.string.banned), scheme.errorContainer, scheme.error)
                user.archived -> Pill(stringResource(R.string.archived), scheme.surfaceContainerHigh, scheme.onSurfaceVariant)
                else -> Pill(stringResource(R.string.active_account), scheme.primaryContainer, scheme.primary, dot = true)
            }
            if (user.mustChangePassword) Pill(stringResource(R.string.must_change_password), scheme.surfaceContainerHigh, scheme.onSurface)
        }
        Text(stringResource(R.string.user_meta, user.courtCount, user.failedLoginAttempts), style = MaterialTheme.typography.bodySmall)
        Text(
            "${stringResource(R.string.created)} ${dateTime(user.createdAt)}",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Text(
            "${stringResource(R.string.last_login)} ${dateTime(user.lastLoginAt).ifBlank { stringResource(R.string.never) }}" +
                (user.lastLoginIp?.takeIf { it.isNotBlank() }?.let { " · $it" } ?: ""),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        if (busy) LinearProgressIndicator(Modifier.fillMaxWidth())
    }
}

@Composable
private fun RoleDialog(user: AdminUser, onPick: (Role) -> Unit, onDismiss: () -> Unit) {
    var selected by remember { mutableStateOf(user.role) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.change_role)) },
        text = {
            Column {
                Role.entries.forEach { role ->
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        RadioButton(selected = selected == role, onClick = { selected = role })
                        Text(roleLabel(role))
                    }
                }
            }
        },
        confirmButton = { TextButton(onClick = { onPick(selected); onDismiss() }, enabled = selected != user.role) { Text(stringResource(R.string.save)) } },
        dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) } },
    )
}
