package io.github.ychsieh95.bccp.feature.courtdetail

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.ui.component.Pill
import io.github.ychsieh95.bccp.core.ui.component.PrimaryActionButton
import io.github.ychsieh95.bccp.core.ui.component.SecretInput
import io.github.ychsieh95.bccp.core.ui.component.TextInput
import io.github.ychsieh95.bccp.core.ui.text
import io.github.ychsieh95.bccp.core.ui.theme.LocalExtraColors

/**
 * Writes a message or a reply. Players prove they joined with their nickname and PIN;
 * an organizer posts as [accountName] (the server decides, from the signed-in account).
 */
@Composable
internal fun MessageSheet(
    form: MessageForm,
    asOrganizer: Boolean,
    accountName: String?,
    showNotifyHint: Boolean,
    onNameChange: (String) -> Unit,
    onPinChange: (String) -> Unit,
    onMessageChange: (String) -> Unit,
    onSubmit: () -> Unit,
    onDismiss: () -> Unit,
) {
    val reply = form.replyTo
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)) {
        Column(
            Modifier
                .navigationBarsPadding()
                .imePadding()
                .verticalScroll(rememberScrollState())
                .padding(start = 24.dp, end = 24.dp, bottom = 24.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                if (reply != null) stringResource(R.string.court_message_reply_to, reply.authorName) else stringResource(R.string.message_write),
                style = MaterialTheme.typography.titleLarge,
            )
            if (reply != null) {
                // The message being answered, so the reply has context.
                Text(
                    reply.message,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 3,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            if (asOrganizer) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(
                        stringResource(R.string.court_message_posting_as, accountName.orEmpty()),
                        style = MaterialTheme.typography.bodyMedium,
                    )
                    val accent = LocalExtraColors.current
                    Pill(stringResource(R.string.court_message_organizer), accent.accent, accent.onAccent)
                }
            } else {
                Text(
                    stringResource(R.string.court_message_join_required),
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                if (showNotifyHint) {
                    Text(stringResource(R.string.court_message_notify_hint), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.primary)
                }
                TextInput(form.username, onNameChange, stringResource(R.string.username), maxLength = 40)
                SecretInput(form.pin, onPinChange, stringResource(R.string.pin), numeric = true)
            }
            TextInput(
                value = form.message,
                onValueChange = onMessageChange,
                label = stringResource(R.string.court_message_body),
                placeholder = stringResource(if (reply != null) R.string.court_message_reply_placeholder else R.string.court_message_placeholder),
                singleLine = false,
                minLines = 3,
                maxLength = MESSAGE_MAX_LENGTH,
                supporting = stringResource(R.string.message_length, form.message.length, MESSAGE_MAX_LENGTH),
                keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Sentences),
            )
            form.error?.let { Text(it.text(), color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodyMedium) }
            PrimaryActionButton(
                text = stringResource(if (reply != null) R.string.court_message_reply_submit else R.string.court_message_submit),
                onClick = onSubmit,
                enabled = form.canSubmit(asOrganizer),
                busy = form.submitting,
                modifier = Modifier.fillMaxWidth().padding(top = 4.dp),
            )
        }
    }
}
