package io.github.ychsieh95.bccp.feature.courtdetail

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.background
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.Reply
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.EditNote
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.model.Court
import io.github.ychsieh95.bccp.core.model.CourtMessage
import io.github.ychsieh95.bccp.core.model.MessageBoard
import io.github.ychsieh95.bccp.core.ui.component.ConfirmDialog
import io.github.ychsieh95.bccp.core.ui.component.CountBadge
import io.github.ychsieh95.bccp.core.ui.component.PanelCard
import io.github.ychsieh95.bccp.core.ui.component.Pill
import io.github.ychsieh95.bccp.core.ui.component.SectionHeader
import io.github.ychsieh95.bccp.core.ui.component.UserAvatar
import io.github.ychsieh95.bccp.core.ui.format.dateTime
import io.github.ychsieh95.bccp.core.ui.theme.LocalExtraColors

/** The court's message board: threads newest first, each with its replies underneath. */
@Composable
internal fun MessagesSection(court: Court, board: MessageBoard, actions: CourtDetailActions, modifier: Modifier) {
    var pendingDelete by rememberSaveable { mutableStateOf<Int?>(null) }
    var pendingDeleteHasReplies by rememberSaveable { mutableStateOf(false) }
    val canManage = court.viewer.canManage
    PanelCard(modifier) {
        SectionHeader(
            stringResource(R.string.court_messages),
            eyebrow = stringResource(R.string.court_messages_eyebrow),
            trailing = { CountBadge(board.count.toString()) },
        )
        if (court.archived) {
            Text(stringResource(R.string.court_message_closed), color = MaterialTheme.colorScheme.onSurfaceVariant)
        } else {
            OutlinedButton(onClick = { actions.composeMessage(null) }, modifier = Modifier.fillMaxWidth()) {
                Icon(Icons.Outlined.EditNote, null, Modifier.padding(end = 8.dp))
                Text(stringResource(R.string.message_write))
            }
        }
        if (board.messages.isEmpty() && !court.archived) {
            Text(stringResource(R.string.court_messages_empty), color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        board.messages.forEachIndexed { index, thread ->
            if (index > 0) HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                MessageRow(
                    thread,
                    showAudit = court.viewer.isAdmin,
                    onDelete = if (canManage) ({
                        pendingDelete = thread.id
                        pendingDeleteHasReplies = thread.replies.isNotEmpty()
                    }) else null,
                )
                if (thread.replies.isNotEmpty()) {
                    // A rule down the left marks the replies as one thread.
                    Row(Modifier.height(IntrinsicSize.Min).padding(start = 18.dp)) {
                        Box(Modifier.width(2.dp).fillMaxHeight().background(MaterialTheme.colorScheme.outlineVariant))
                        Column(Modifier.padding(start = 14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            thread.replies.forEach { reply ->
                                MessageRow(
                                    reply,
                                    showAudit = court.viewer.isAdmin,
                                    compact = true,
                                    onDelete = if (canManage) ({
                                        pendingDelete = reply.id
                                        pendingDeleteHasReplies = false
                                    }) else null,
                                )
                            }
                        }
                    }
                }
                if (!court.archived) {
                    TextButton(onClick = { actions.composeMessage(thread) }, modifier = Modifier.padding(start = 44.dp)) {
                        Icon(Icons.AutoMirrored.Outlined.Reply, null, Modifier.padding(end = 6.dp).size(18.dp))
                        Text(stringResource(R.string.court_message_reply))
                    }
                }
            }
        }
    }
    pendingDelete?.let { id ->
        ConfirmDialog(
            message = stringResource(if (pendingDeleteHasReplies) R.string.court_message_delete_thread_confirm else R.string.court_message_delete_confirm),
            confirmLabel = stringResource(R.string.delete),
            destructive = true,
            onDismiss = { pendingDelete = null },
            onConfirm = { actions.deleteMessage(id) },
        )
    }
}

@Composable
private fun MessageRow(message: CourtMessage, showAudit: Boolean, onDelete: (() -> Unit)?, compact: Boolean = false) {
    val accent = LocalExtraColors.current
    Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.Top) {
        UserAvatar(
            message.authorName,
            modifier = if (compact) Modifier.size(32.dp) else Modifier,
            container = if (message.isOrganizer) accent.accent else MaterialTheme.colorScheme.primaryContainer,
            content = if (message.isOrganizer) accent.onAccent else MaterialTheme.colorScheme.onPrimaryContainer,
        )
        Column(Modifier.weight(1f).semantics(mergeDescendants = true) {}, verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                Text(message.authorName, style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.SemiBold)
                if (message.isOrganizer) {
                    Pill(stringResource(R.string.court_message_organizer), accent.accent, accent.onAccent)
                }
            }
            val meta = listOfNotNull(dateTime(message.postedAt), message.ipAddress?.takeIf { showAudit && it.isNotBlank() })
            Text(meta.joinToString(" · "), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(message.message, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.padding(top = 4.dp))
        }
        if (onDelete != null) {
            IconButton(onClick = onDelete) {
                Icon(Icons.Outlined.Delete, stringResource(R.string.court_message_delete), tint = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}
