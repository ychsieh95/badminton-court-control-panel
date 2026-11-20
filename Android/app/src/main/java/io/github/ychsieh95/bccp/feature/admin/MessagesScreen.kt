package io.github.ychsieh95.bccp.feature.admin

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.model.ContactMessage
import io.github.ychsieh95.bccp.core.ui.component.ErrorPane
import io.github.ychsieh95.bccp.core.ui.component.LoadingPane
import io.github.ychsieh95.bccp.core.ui.component.MessagePane
import io.github.ychsieh95.bccp.core.ui.component.PanelCard
import io.github.ychsieh95.bccp.core.ui.component.Pill
import io.github.ychsieh95.bccp.core.ui.format.dateTime
import io.github.ychsieh95.bccp.core.ui.text

@Composable
fun MessagesScreen(onBack: () -> Unit, viewModel: MessagesViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    val context = LocalContext.current
    LaunchedEffect(Unit) { viewModel.messages.collect { snackbar.showSnackbar(it.resolve(context)) } }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.contact_messages_title)) },
                navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, stringResource(R.string.back)) } },
            )
        },
    ) { padding ->
        Box(Modifier.padding(padding).fillMaxSize()) {
            LazyColumn(
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier.fillMaxSize(),
            ) {
                item {
                    Row(Modifier.widthIn(max = 840.dp).fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        listOf("all" to R.string.contact_filter_all, "unread" to R.string.contact_filter_unread, "read" to R.string.contact_filter_read)
                            .forEach { (value, label) ->
                                FilterChip(
                                    selected = state.status == value,
                                    onClick = { viewModel.setStatus(value) },
                                    label = {
                                        Text(stringResource(label) + if (value == "unread" && state.unreadCount > 0) " (${state.unreadCount})" else "")
                                    },
                                )
                            }
                    }
                }
                when {
                    state.loading && state.messages.isEmpty() -> item { LoadingPane(Modifier.padding(top = 48.dp)) }
                    state.error != null -> item { ErrorPane(state.error!!.text(), viewModel::load) }
                    state.messages.isEmpty() -> item { MessagePane(stringResource(R.string.contact_messages_empty), Modifier.padding(top = 48.dp)) }
                    else -> items(state.messages, key = { it.id }) { message ->
                        MessageCard(message, onToggleRead = { viewModel.setRead(message, !message.isRead) })
                    }
                }
                if (state.pageCount > 1) {
                    item {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            OutlinedButton(onClick = { viewModel.setPage(state.page - 1) }, enabled = state.page > 1) { Text(stringResource(R.string.previous_page)) }
                            Text(stringResource(R.string.page_of, state.page, state.pageCount))
                            OutlinedButton(onClick = { viewModel.setPage(state.page + 1) }, enabled = state.page < state.pageCount) { Text(stringResource(R.string.next_page)) }
                        }
                    }
                }
            }
            if (state.loading && state.messages.isNotEmpty()) LinearProgressIndicator(Modifier.fillMaxWidth().align(Alignment.TopCenter))
        }
    }
}

@Composable
private fun MessageCard(message: ContactMessage, onToggleRead: () -> Unit) {
    val scheme = MaterialTheme.colorScheme
    PanelCard(Modifier.widthIn(max = 840.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                message.subject,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = if (message.isRead) FontWeight.Normal else FontWeight.Bold,
                modifier = Modifier.weight(1f),
            )
            if (message.isRead) Pill(stringResource(R.string.contact_message_read), scheme.surfaceContainerHigh, scheme.onSurfaceVariant)
            else Pill(stringResource(R.string.contact_message_unread), scheme.primaryContainer, scheme.primary, dot = true)
        }
        Text(
            "${stringResource(R.string.contact_message_from)}: ${message.senderName}",
            style = MaterialTheme.typography.bodyMedium,
        )
        if (!message.replyContact.isNullOrBlank()) {
            SelectionContainer {
                Text("${stringResource(R.string.contact_message_reply)}: ${message.replyContact}", style = MaterialTheme.typography.bodyMedium)
            }
        }
        Text(
            "${stringResource(R.string.contact_message_submitted)}: ${dateTime(message.submittedAt)}",
            style = MaterialTheme.typography.bodySmall,
            color = scheme.onSurfaceVariant,
        )
        SelectionContainer { Text(message.message, style = MaterialTheme.typography.bodyLarge) }
        TextButton(onClick = onToggleRead) {
            Text(stringResource(if (message.isRead) R.string.contact_mark_unread else R.string.contact_mark_read))
        }
    }
}
