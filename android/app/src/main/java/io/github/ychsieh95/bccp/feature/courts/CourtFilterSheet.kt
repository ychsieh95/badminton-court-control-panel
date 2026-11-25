package io.github.ychsieh95.bccp.feature.courts

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Female
import androidx.compose.material.icons.outlined.Male
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.data.CourtFilters
import io.github.ychsieh95.bccp.core.data.CourtScope
import io.github.ychsieh95.bccp.core.ui.component.Choice
import io.github.ychsieh95.bccp.core.ui.component.DateField
import io.github.ychsieh95.bccp.core.ui.component.DropdownField
import io.github.ychsieh95.bccp.core.ui.component.SwitchRow
import io.github.ychsieh95.bccp.core.ui.component.TextInput
import io.github.ychsieh95.bccp.core.ui.format.levelLabel

@Composable
fun CourtFilterSheet(
    scope: CourtScope,
    initial: CourtFilters,
    onApply: (CourtFilters) -> Unit,
    onDismiss: () -> Unit,
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    var draft by remember { mutableStateOf(initial) }
    ModalBottomSheet(onDismissRequest = onDismiss, sheetState = sheetState) {
        Column(
            Modifier.verticalScroll(rememberScrollState()).padding(horizontal = 24.dp).navigationBarsPadding(),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                stringResource(R.string.filter_courts),
                style = MaterialTheme.typography.titleLarge,
                modifier = Modifier.semantics { heading() },
            )
            TextInput(
                value = draft.query,
                onValueChange = { draft = draft.copy(query = it) },
                label = stringResource(R.string.search),
                placeholder = stringResource(R.string.filter_search),
                maxLength = 100,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
            )
            DateField(draft.dateFrom, { draft = draft.copy(dateFrom = it) }, stringResource(R.string.date_from), clearable = true)
            DateField(draft.dateTo, { draft = draft.copy(dateTo = it) }, stringResource(R.string.date_to), clearable = true)
            val levels = listOf(Choice<Int?>(null, stringResource(R.string.any_level))) +
                (1..18).map { Choice<Int?>(it, "$it · ${levelLabel(it)}") }
            DropdownField(stringResource(R.string.filter_level), levels, draft.level, { draft = draft.copy(level = it) })

            Text(stringResource(R.string.filter_gender), style = MaterialTheme.typography.labelLarge)
            val genders = listOf(
                Triple("both", R.string.both_genders, listOf(Icons.Outlined.Male, Icons.Outlined.Female)),
                Triple("male", R.string.male, listOf(Icons.Outlined.Male)),
                Triple("female", R.string.female, listOf(Icons.Outlined.Female)),
            )
            SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth()) {
                genders.forEachIndexed { index, (value, label, icons) ->
                    val description = stringResource(label)
                    SegmentedButton(
                        selected = draft.gender == value,
                        onClick = { draft = draft.copy(gender = value) },
                        shape = SegmentedButtonDefaults.itemShape(index, genders.size),
                        icon = {},
                        modifier = Modifier.semantics { contentDescription = description },
                    ) {
                        Row { icons.forEach { Icon(it, contentDescription = null) } }
                    }
                }
            }

            val statuses = buildList {
                add(Choice("", stringResource(R.string.any_status)))
                add(Choice("open", stringResource(R.string.open)))
                add(Choice("full", stringResource(R.string.full)))
                add(Choice("read_only", stringResource(R.string.read_only)))
                if (scope == CourtScope.Admin) add(Choice("archived", stringResource(R.string.archived)))
            }
            DropdownField(stringResource(R.string.filter_status), statuses, draft.status, { draft = draft.copy(status = it) })
            SwitchRow(stringResource(R.string.show_expired), draft.showExpired, { draft = draft.copy(showExpired = it) })

            Row(Modifier.padding(vertical = 8.dp), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedButton(onClick = { onApply(CourtFilters()) }, modifier = Modifier.weight(1f)) {
                    Text(stringResource(R.string.clear_filters))
                }
                Button(onClick = { onApply(draft) }, modifier = Modifier.weight(1f)) { Text(stringResource(R.string.apply_filters)) }
            }
        }
    }
}
