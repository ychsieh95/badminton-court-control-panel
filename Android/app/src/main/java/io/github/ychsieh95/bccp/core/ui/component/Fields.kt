package io.github.ychsieh95.bccp.core.ui.component

import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.PressInteraction
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.CalendarMonth
import androidx.compose.material.icons.outlined.Close
import androidx.compose.material.icons.outlined.Schedule
import androidx.compose.material.icons.outlined.Visibility
import androidx.compose.material.icons.outlined.VisibilityOff
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.DatePicker
import androidx.compose.material3.DatePickerDialog
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.MenuAnchorType
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TimePicker
import androidx.compose.material3.rememberDatePickerState
import androidx.compose.material3.rememberTimePickerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.ui.format.Formats
import java.time.Instant
import java.time.LocalDate
import java.time.LocalTime
import java.time.ZoneOffset

@Composable
fun TextInput(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    modifier: Modifier = Modifier,
    error: String? = null,
    supporting: String? = null,
    placeholder: String? = null,
    singleLine: Boolean = true,
    minLines: Int = 1,
    maxLength: Int? = null,
    keyboardOptions: KeyboardOptions = KeyboardOptions.Default,
    enabled: Boolean = true,
) {
    OutlinedTextField(
        value = value,
        onValueChange = { if (maxLength == null || it.length <= maxLength) onValueChange(it) },
        label = { FieldLabel(label) },
        placeholder = placeholder?.let { { Text(it) } },
        isError = error != null,
        supportingText = (error ?: supporting)?.let { { Text(it) } },
        singleLine = singleLine,
        minLines = minLines,
        keyboardOptions = keyboardOptions,
        enabled = enabled,
        modifier = modifier.fillMaxWidth(),
    )
}

@Composable
fun SecretInput(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    modifier: Modifier = Modifier,
    error: String? = null,
    supporting: String? = null,
    numeric: Boolean = false,
) {
    var visible by rememberSaveable { mutableStateOf(false) }
    OutlinedTextField(
        value = value,
        onValueChange = { new ->
            if (!numeric) onValueChange(new) else if (new.length <= 6 && new.all(Char::isDigit)) onValueChange(new)
        },
        label = { FieldLabel(label) },
        isError = error != null,
        supportingText = (error ?: supporting)?.let { { Text(it) } },
        singleLine = true,
        visualTransformation = if (visible) VisualTransformation.None else PasswordVisualTransformation(),
        keyboardOptions = KeyboardOptions(keyboardType = if (numeric) KeyboardType.NumberPassword else KeyboardType.Password),
        trailingIcon = {
            val description = stringResource(
                when {
                    numeric && visible -> R.string.hide_pin
                    numeric -> R.string.show_pin
                    visible -> R.string.hide_password
                    else -> R.string.show_password
                },
            )
            IconButton(onClick = { visible = !visible }) {
                Icon(if (visible) Icons.Outlined.VisibilityOff else Icons.Outlined.Visibility, description)
            }
        },
        modifier = modifier.fillMaxWidth(),
    )
}

/** A label that never wraps: an empty field shows it in the body, where a second line would make it taller than its neighbours. */
@Composable
private fun FieldLabel(text: String) = Text(text, maxLines = 1, overflow = TextOverflow.Ellipsis)

/** [short] replaces [label] in the closed field when the full label is too long for it (the menu still shows [label]). */
data class Choice<T>(val value: T, val label: String, val short: String? = null)

@Composable
fun <T> DropdownField(
    label: String,
    choices: List<Choice<T>>,
    selected: T,
    onSelect: (T) -> Unit,
    modifier: Modifier = Modifier,
    error: String? = null,
    enabled: Boolean = true,
    supporting: String? = null,
) {
    var expanded by remember { mutableStateOf(false) }
    ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { if (enabled) expanded = it }, modifier = modifier) {
        OutlinedTextField(
            value = choices.firstOrNull { it.value == selected }?.let { it.short ?: it.label }.orEmpty(),
            onValueChange = {},
            readOnly = true,
            enabled = enabled,
            label = { FieldLabel(label) },
            isError = error != null,
            supportingText = (error ?: supporting)?.let { { Text(it) } },
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded) },
            // Read-only, so wrap a long choice instead of clipping it mid-word.
            singleLine = false,
            maxLines = 2,
            modifier = Modifier.menuAnchor(MenuAnchorType.PrimaryNotEditable, enabled).fillMaxWidth(),
        )
        ExposedDropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            choices.forEach { choice ->
                DropdownMenuItem(text = { Text(choice.label) }, onClick = {
                    onSelect(choice.value)
                    expanded = false
                })
            }
        }
    }
}

/** A read-only field that opens a picker when tapped. */
@Composable
private fun PickerField(
    value: String,
    label: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    onOpen: () -> Unit,
    modifier: Modifier,
    error: String?,
    supporting: String?,
    onClear: (() -> Unit)?,
) {
    val interaction = remember { MutableInteractionSource() }
    LaunchedEffect(interaction) {
        interaction.interactions.collect { if (it is PressInteraction.Release) onOpen() }
    }
    OutlinedTextField(
        value = value,
        onValueChange = {},
        readOnly = true,
        label = { FieldLabel(label) },
        isError = error != null,
        supportingText = (error ?: supporting)?.let { { Text(it) } },
        leadingIcon = { Icon(icon, null) },
        trailingIcon = if (onClear != null && value.isNotEmpty()) {
            {
                IconButton(onClick = onClear) {
                    Icon(Icons.Outlined.Close, contentDescription = stringResource(R.string.clear))
                }
            }
        } else null,
        singleLine = true,
        interactionSource = interaction,
        modifier = modifier.fillMaxWidth().semantics { role = Role.Button },
    )
}

/** [value] is `YYYY-MM-DD` or empty. */
@Composable
fun DateField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    modifier: Modifier = Modifier,
    error: String? = null,
    supporting: String? = null,
    clearable: Boolean = false,
) {
    var open by remember { mutableStateOf(false) }
    PickerField(
        value = if (value.isEmpty()) "" else Formats.courtDate(value),
        label = label,
        icon = Icons.Outlined.CalendarMonth,
        onOpen = { open = true },
        modifier = modifier,
        error = error,
        supporting = supporting,
        onClear = if (clearable) ({ onValueChange("") }) else null,
    )
    if (open) {
        val initial = Formats.parseDate(value) ?: LocalDate.now()
        val state = rememberDatePickerState(initialSelectedDateMillis = initial.atStartOfDay(ZoneOffset.UTC).toInstant().toEpochMilli())
        DatePickerDialog(
            onDismissRequest = { open = false },
            confirmButton = {
                TextButton(onClick = {
                    state.selectedDateMillis?.let {
                        onValueChange(Instant.ofEpochMilli(it).atZone(ZoneOffset.UTC).toLocalDate().toString())
                    }
                    open = false
                }) { Text(stringResource(R.string.done)) }
            },
            dismissButton = { TextButton(onClick = { open = false }) { Text(stringResource(R.string.cancel)) } },
        ) { DatePicker(state) }
    }
}

/** [value] is 24-hour `HH:MM`, which is what the API stores. */
@Composable
fun TimeField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    modifier: Modifier = Modifier,
    error: String? = null,
    supporting: String? = null,
) {
    var open by remember { mutableStateOf(false) }
    PickerField(value, label, Icons.Outlined.Schedule, { open = true }, modifier, error, supporting, null)
    if (open) {
        val initial = Formats.parseTime(value) ?: LocalTime.of(19, 0)
        val state = rememberTimePickerState(initial.hour, initial.minute, is24Hour = true)
        AlertDialog(
            onDismissRequest = { open = false },
            title = { Text(label) },
            text = { TimePicker(state) },
            confirmButton = {
                TextButton(onClick = {
                    onValueChange("%02d:%02d".format(state.hour, state.minute))
                    open = false
                }) { Text(stringResource(R.string.done)) }
            },
            dismissButton = { TextButton(onClick = { open = false }) { Text(stringResource(R.string.cancel)) } },
        )
    }
}

@Composable
fun SwitchRow(
    title: String,
    checked: Boolean,
    onCheckedChange: (Boolean) -> Unit,
    modifier: Modifier = Modifier,
    body: String? = null,
    enabled: Boolean = true,
) {
    Row(
        modifier.fillMaxWidth().heightIn(min = 48.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Column(Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.bodyLarge)
            if (body != null) {
                Text(body, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        Switch(checked = checked, onCheckedChange = onCheckedChange, enabled = enabled)
    }
}

@Composable
fun ConfirmDialog(
    message: String,
    confirmLabel: String,
    onConfirm: () -> Unit,
    onDismiss: () -> Unit,
    title: String? = null,
    destructive: Boolean = false,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = title?.let { { Text(it) } },
        text = { Text(message) },
        confirmButton = {
            TextButton(onClick = { onConfirm(); onDismiss() }) {
                Text(confirmLabel, color = if (destructive) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary)
            }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) } },
    )
}
