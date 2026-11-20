package io.github.ychsieh95.bccp.feature.courtdetail

import androidx.compose.foundation.layout.Box
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.MoreVert
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.res.stringResource
import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.model.Participant
import io.github.ychsieh95.bccp.core.ui.component.ConfirmDialog
import io.github.ychsieh95.bccp.core.ui.component.SecretInput
import io.github.ychsieh95.bccp.core.ui.component.TextInput

private enum class ParticipantDialog { Rename, Pin, Remove }

/** Admin-only player moderation, the web's `participant_admin_menu`. */
@Composable
internal fun ParticipantAdminMenu(participant: Participant, actions: CourtDetailActions) {
    var menuOpen by remember { mutableStateOf(false) }
    var dialog by rememberSaveable { mutableStateOf<ParticipantDialog?>(null) }
    Box {
        IconButton(onClick = { menuOpen = true }) {
            Icon(Icons.Outlined.MoreVert, stringResource(R.string.player_actions, participant.username))
        }
        DropdownMenu(expanded = menuOpen, onDismissRequest = { menuOpen = false }) {
            DropdownMenuItem(text = { Text(stringResource(R.string.rename_participant)) }, onClick = { menuOpen = false; dialog = ParticipantDialog.Rename })
            DropdownMenuItem(text = { Text(stringResource(R.string.reset_participant_pin)) }, onClick = { menuOpen = false; dialog = ParticipantDialog.Pin })
            DropdownMenuItem(
                text = { Text(stringResource(R.string.remove_participant), color = MaterialTheme.colorScheme.error) },
                onClick = { menuOpen = false; dialog = ParticipantDialog.Remove },
            )
        }
    }
    when (dialog) {
        ParticipantDialog.Rename -> InputDialog(
            title = stringResource(R.string.rename_participant),
            initial = participant.username,
            label = stringResource(R.string.participant_new_name),
            secret = false,
            valid = { it.trim().length in 2..40 },
            onConfirm = { actions.renameParticipant(participant.id, it) },
            onDismiss = { dialog = null },
        )
        ParticipantDialog.Pin -> InputDialog(
            title = stringResource(R.string.reset_participant_pin),
            initial = "",
            label = stringResource(R.string.pin),
            secret = true,
            valid = { it.length == 6 },
            onConfirm = { actions.resetParticipantPin(participant.id, it) },
            onDismiss = { dialog = null },
        )
        ParticipantDialog.Remove -> ConfirmDialog(
            title = participant.username,
            message = stringResource(R.string.remove_participant_confirm),
            confirmLabel = stringResource(R.string.remove_participant),
            destructive = true,
            onConfirm = { actions.removeParticipant(participant.id) },
            onDismiss = { dialog = null },
        )
        null -> Unit
    }
}

@Composable
internal fun InputDialog(
    title: String,
    initial: String,
    label: String,
    secret: Boolean,
    valid: (String) -> Boolean,
    onConfirm: (String) -> Unit,
    onDismiss: () -> Unit,
    numeric: Boolean = true,
    supporting: String? = null,
    confirmLabel: String = stringResource(R.string.save),
) {
    var value by rememberSaveable { mutableStateOf(initial) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title) },
        text = {
            if (secret) SecretInput(value, { value = it }, label, numeric = numeric, supporting = supporting)
            else TextInput(value, { value = it }, label, maxLength = 40, supporting = supporting)
        },
        confirmButton = {
            TextButton(onClick = { onConfirm(value); onDismiss() }, enabled = valid(value)) { Text(confirmLabel) }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) } },
    )
}
