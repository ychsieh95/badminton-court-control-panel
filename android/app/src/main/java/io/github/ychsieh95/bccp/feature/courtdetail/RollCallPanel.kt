package io.github.ychsieh95.bccp.feature.courtdetail

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Checkbox
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TriStateCheckbox
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.state.ToggleableState
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.model.Court
import io.github.ychsieh95.bccp.core.ui.component.PanelCard
import io.github.ychsieh95.bccp.core.ui.component.PrimaryActionButton
import io.github.ychsieh95.bccp.core.ui.component.SectionHeader
import io.github.ychsieh95.bccp.core.ui.component.StatusBadge

private data class RollRow(val key: String, val name: String, val source: String)

private val CHECK_COLUMN = 64.dp

@Composable
internal fun RollCallPanel(
    court: Court,
    draft: RollDraft,
    dirty: Boolean,
    busy: Boolean,
    actions: CourtDetailActions,
    modifier: Modifier,
) {
    val reservedLabel = stringResource(R.string.reserved)
    val onlineLabel = stringResource(R.string.joined_on_site)
    val unnamed = stringResource(R.string.unnamed_reserved_member)
    val rows = court.reservedMembers.mapNotNull { m ->
        m.id?.let { RollRow("r$it", m.nickname.ifBlank { "$unnamed ${m.position + 1}" }, reservedLabel) }
    } + court.participants.map { RollRow("p${it.id}", it.username, onlineLabel) }

    fun allState(values: Map<String, Boolean>): ToggleableState {
        val checked = rows.count { values[it.key] == true }
        return when {
            rows.isEmpty() || checked == 0 -> ToggleableState.Off
            checked == rows.size -> ToggleableState.On
            else -> ToggleableState.Indeterminate
        }
    }

    PanelCard(modifier) {
        SectionHeader(stringResource(R.string.roll_and_clearing), eyebrow = stringResource(R.string.read_only), trailing = { StatusBadge(court.status) })
        Text(stringResource(R.string.roll_and_clearing_body), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)

        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Text(stringResource(R.string.members), style = MaterialTheme.typography.labelLarge, modifier = Modifier.weight(1f))
            HeaderCheck(stringResource(R.string.roll_call), allState(draft.rollCalled)) { actions.setAll(rollCall = true, value = it) }
            HeaderCheck(stringResource(R.string.cleared), allState(draft.cleared)) { actions.setAll(rollCall = false, value = it) }
        }
        HorizontalDivider()
        rows.forEach { row ->
            Row(Modifier.fillMaxWidth().heightIn(min = 48.dp), verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text(row.name, style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.Medium)
                    Text(row.source, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                val rollLabel = "${stringResource(R.string.roll_call)} · ${row.name}"
                val clearedLabel = "${stringResource(R.string.cleared)} · ${row.name}"
                Checkbox(
                    checked = draft.rollCalled[row.key] == true,
                    onCheckedChange = { actions.toggleRoll(row.key, it) },
                    modifier = Modifier.width(CHECK_COLUMN).semantics { contentDescription = rollLabel },
                )
                Checkbox(
                    checked = draft.cleared[row.key] == true,
                    onCheckedChange = { actions.toggleCleared(row.key, it) },
                    modifier = Modifier.width(CHECK_COLUMN).semantics { contentDescription = clearedLabel },
                )
            }
        }
        PrimaryActionButton(
            text = stringResource(R.string.save_member_statuses),
            onClick = actions::saveRollClearing,
            enabled = dirty,
            busy = busy,
        )
    }
}

@Composable
private fun HeaderCheck(label: String, state: ToggleableState, onSet: (Boolean) -> Unit) {
    val description = "${stringResource(R.string.check_uncheck_all)} · $label"
    Column(Modifier.width(CHECK_COLUMN), horizontalAlignment = Alignment.CenterHorizontally) {
        Text(label, style = MaterialTheme.typography.labelMedium, textAlign = TextAlign.Center)
        TriStateCheckbox(
            state = state,
            onClick = { onSet(state != ToggleableState.On) },
            modifier = Modifier.semantics { contentDescription = description },
        )
    }
}
