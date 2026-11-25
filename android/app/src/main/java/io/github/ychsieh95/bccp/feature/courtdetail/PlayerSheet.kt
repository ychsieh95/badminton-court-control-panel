package io.github.ychsieh95.bccp.feature.courtdetail

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.PrimaryTabRow
import androidx.compose.material3.Tab
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.model.Court
import io.github.ychsieh95.bccp.core.ui.component.PrimaryActionButton
import io.github.ychsieh95.bccp.core.ui.component.SecretInput
import io.github.ychsieh95.bccp.core.ui.component.TextInput
import io.github.ychsieh95.bccp.core.ui.format.dateTime
import io.github.ychsieh95.bccp.core.ui.text

@Composable
internal fun PlayerSheet(
    court: Court,
    form: PlayerForm,
    onModeChange: (PlayerMode) -> Unit,
    onNameChange: (String) -> Unit,
    onPinChange: (String) -> Unit,
    onSubmit: () -> Unit,
    onDismiss: () -> Unit,
) {
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)) {
        Column(Modifier.navigationBarsPadding().imePadding()) {
            PrimaryTabRow(selectedTabIndex = form.mode.ordinal) {
                Tab(form.mode == PlayerMode.Join, { onModeChange(PlayerMode.Join) }, text = { Text(stringResource(R.string.join)) })
                Tab(form.mode == PlayerMode.Leave, { onModeChange(PlayerMode.Leave) }, text = { Text(stringResource(R.string.leave)) })
            }
            Column(Modifier.padding(24.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                val deadline = court.leaveDeadline
                val leaveBlocked = form.mode == PlayerMode.Leave && deadline.passed
                val (title, body) = when {
                    form.mode == PlayerMode.Join && court.isFull -> R.string.join_waitlist to R.string.join_waitlist_body
                    form.mode == PlayerMode.Join -> R.string.join_title to R.string.join_body
                    leaveBlocked -> R.string.leave_deadline_passed_title to R.string.leave_deadline_passed_body
                    else -> R.string.leave_title to R.string.leave_body
                }
                Text(stringResource(title), style = MaterialTheme.typography.titleLarge)
                Text(stringResource(body), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                if (deadline.enabled && !leaveBlocked) {
                    Text(
                        if (deadline.passed) stringResource(R.string.leave_deadline_passed)
                        else stringResource(R.string.leave_deadline_notice, dateTime(deadline.at)),
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.primary,
                    )
                }
                if (!leaveBlocked) {
                    TextInput(form.username, onNameChange, stringResource(R.string.username), maxLength = 40)
                    SecretInput(form.pin, onPinChange, stringResource(R.string.pin), numeric = true, supporting = stringResource(R.string.remember_name))
                    form.error?.let { Text(it.text(), color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodyMedium) }
                    PrimaryActionButton(
                        text = stringResource(
                            when {
                                form.mode == PlayerMode.Leave -> R.string.leave
                                court.isFull -> R.string.join_waitlist
                                else -> R.string.join
                            },
                        ),
                        onClick = onSubmit,
                        enabled = form.canSubmit,
                        busy = form.submitting,
                        modifier = Modifier.fillMaxWidth().padding(top = 4.dp),
                    )
                }
            }
        }
    }
}
