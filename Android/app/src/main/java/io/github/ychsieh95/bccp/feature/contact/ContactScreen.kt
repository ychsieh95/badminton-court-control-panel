package io.github.ychsieh95.bccp.feature.contact

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.outlined.MarkEmailRead
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.ui.component.MessagePane
import io.github.ychsieh95.bccp.core.ui.component.PanelCard
import io.github.ychsieh95.bccp.core.ui.component.PrimaryActionButton
import io.github.ychsieh95.bccp.core.ui.component.SectionHeader
import io.github.ychsieh95.bccp.core.ui.component.TextInput
import io.github.ychsieh95.bccp.core.ui.text
import io.github.ychsieh95.bccp.feature.auth.TurnstileWidget

@Composable
fun ContactScreen(onBack: () -> Unit, viewModel: ContactViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.contact_admin)) },
                navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, stringResource(R.string.back)) } },
            )
        },
    ) { padding ->
        if (state.sent) {
            MessagePane(
                title = stringResource(R.string.message_sent_title),
                body = stringResource(R.string.contact_message_sent),
                icon = Icons.Outlined.MarkEmailRead,
                action = { OutlinedButton(onClick = viewModel::reset) { Text(stringResource(R.string.send_another)) } },
                modifier = Modifier.padding(padding),
            )
            return@Scaffold
        }
        Column(
            Modifier.padding(padding).fillMaxSize().verticalScroll(rememberScrollState()).imePadding().padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            val width = Modifier.widthIn(max = 840.dp)
            PanelCard(width) {
                SectionHeader(stringResource(R.string.contact_help_title), eyebrow = stringResource(R.string.contact_eyebrow))
                listOf(
                    R.string.contact_account_title to R.string.contact_account_body,
                    R.string.contact_technical_title to R.string.contact_technical_body,
                    R.string.contact_privacy_title to R.string.contact_privacy_body,
                    R.string.contact_event_title to R.string.contact_event_body,
                    R.string.contact_security_title to R.string.contact_security_body,
                ).forEach { (title, body) ->
                    Column {
                        Text(stringResource(title), style = MaterialTheme.typography.titleSmall)
                        Text(stringResource(body), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
            PanelCard(width) {
                SectionHeader(stringResource(R.string.contact_form_title))
                Text(stringResource(R.string.contact_form_body), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                @Composable
                fun err(field: String) = state.fieldErrors[field]?.let { contactError(it) }
                TextInput(
                    state.name, { viewModel.set("sender_name", it) }, stringResource(R.string.contact_sender_name),
                    placeholder = stringResource(R.string.contact_sender_name_placeholder), error = err("sender_name"), maxLength = 100,
                )
                TextInput(
                    state.reply, { viewModel.set("reply_contact", it) }, stringResource(R.string.contact_reply),
                    placeholder = stringResource(R.string.contact_reply_placeholder), supporting = stringResource(R.string.contact_reply_help),
                    error = err("reply_contact"), maxLength = 200,
                )
                TextInput(
                    state.subject, { viewModel.set("subject", it) }, stringResource(R.string.contact_subject),
                    placeholder = stringResource(R.string.contact_subject_placeholder), error = err("subject"), maxLength = 150,
                )
                TextInput(
                    state.message, { viewModel.set("message", it) }, stringResource(R.string.contact_message_label),
                    placeholder = stringResource(R.string.contact_message_placeholder), error = err("message"),
                    singleLine = false, minLines = 5, maxLength = 4000,
                )
                if (state.turnstile.enabled) {
                    TurnstileWidget(
                        state.turnstile.siteKey,
                        state.serverUrl,
                        action = "contact_message",
                        resetKey = state.turnstileReset,
                        onToken = viewModel::setTurnstileToken,
                    )
                }
                Text(stringResource(R.string.contact_form_privacy), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                state.error?.let { Text(it.text(), color = MaterialTheme.colorScheme.error) }
                PrimaryActionButton(stringResource(R.string.contact_submit), viewModel::submit, enabled = state.canSubmit, busy = state.submitting)
            }
        }
    }
}

@Composable
private fun contactError(code: String): String = when (code) {
    "contact_form_required" -> stringResource(R.string.contact_form_required)
    "contact_name_too_long" -> stringResource(R.string.contact_name_too_long)
    "contact_reply_too_long" -> stringResource(R.string.contact_reply_too_long)
    "contact_subject_too_long" -> stringResource(R.string.contact_subject_too_long)
    "contact_message_too_long" -> stringResource(R.string.contact_message_too_long)
    "contact_form_invalid" -> stringResource(R.string.contact_form_invalid)
    else -> code
}
