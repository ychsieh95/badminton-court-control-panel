package io.github.ychsieh95.bccp.feature.courtform

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.AddPhotoAlternate
import androidx.compose.material.icons.outlined.ArrowDownward
import androidx.compose.material.icons.outlined.ArrowUpward
import androidx.compose.material.icons.outlined.Close
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.Movie
import androidx.compose.material.icons.outlined.PersonAdd
import androidx.compose.material.icons.automirrored.outlined.Undo
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.ListItem
import androidx.compose.material3.ListItemDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import coil3.compose.AsyncImage
import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.model.CourtMedia
import io.github.ychsieh95.bccp.core.ui.component.Choice
import io.github.ychsieh95.bccp.core.ui.component.DropdownField
import io.github.ychsieh95.bccp.core.ui.component.PanelCard

/** The web form's numbered `form-section` panels. */
@Composable
internal fun FormSection(
    number: String,
    title: String,
    description: String? = null,
    modifier: Modifier = Modifier,
    content: @Composable ColumnScope.() -> Unit,
) {
    PanelCard(modifier) {
        // The description goes under the row, so a long one cannot push the badge away from the title.
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Surface(shape = MaterialTheme.shapes.small, color = MaterialTheme.colorScheme.primaryContainer) {
                Text(
                    number,
                    Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                    style = MaterialTheme.typography.labelLarge,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.Bold,
                )
            }
            Text(title, style = MaterialTheme.typography.titleLarge, modifier = Modifier.weight(1f).semantics { heading() })
        }
        if (description != null) {
            Text(description, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        content()
    }
}

@Composable
internal fun ReservedNicknameEditor(state: CourtFormUiState, vm: CourtFormViewModel, error: String?) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(stringResource(R.string.reserved_nicknames), style = MaterialTheme.typography.titleSmall)
        Text(stringResource(R.string.reserved_nicknames_help), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        DropdownField(
            stringResource(R.string.reserved_name_visibility),
            listOf(Choice("1", stringResource(R.string.show_reserved_names)), Choice("0", stringResource(R.string.hide_reserved_names))),
            state[F.NAMES_VISIBLE],
            { vm.set(F.NAMES_VISIBLE, it) },
        )
        val label = stringResource(R.string.reserved_nickname)
        state.nicknames.forEachIndexed { index, nickname ->
            Row(verticalAlignment = Alignment.CenterVertically) {
                OutlinedTextField(
                    value = nickname,
                    onValueChange = { vm.setNickname(index, it) },
                    label = { Text("$label ${index + 1}") },
                    placeholder = { Text(stringResource(R.string.reserved_nickname_placeholder)) },
                    singleLine = true,
                    modifier = Modifier.weight(1f),
                )
                // OutlinedTextField reserves 8.dp above its box for the floating label; match it so the icons centre on the box.
                Row(Modifier.padding(top = 8.dp)) {
                    IconButton(onClick = { vm.moveNickname(index, -1) }, enabled = index > 0) {
                        Icon(Icons.Outlined.ArrowUpward, "${stringResource(R.string.move_up)} $label ${index + 1}")
                    }
                    IconButton(onClick = { vm.moveNickname(index, 1) }, enabled = index < state.nicknames.lastIndex) {
                        Icon(Icons.Outlined.ArrowDownward, "${stringResource(R.string.move_down)} $label ${index + 1}")
                    }
                    IconButton(onClick = { vm.removeNickname(index) }) {
                        Icon(Icons.Outlined.Delete, "${stringResource(R.string.delete)} $label ${index + 1}", tint = MaterialTheme.colorScheme.error)
                    }
                }
            }
        }
        OutlinedButton(onClick = vm::addNickname) {
            Icon(Icons.Outlined.PersonAdd, null, Modifier.padding(end = 8.dp))
            Text(stringResource(R.string.add_reserved_nickname))
        }
        if (error != null) Text(error, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
internal fun MediaEditor(
    state: CourtFormUiState,
    error: String?,
    onPick: () -> Unit,
    onToggleExisting: (Int) -> Unit,
    onRemoveNew: (Int) -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(stringResource(R.string.event_media), style = MaterialTheme.typography.titleSmall)
        Text(stringResource(R.string.media_upload_help), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        if (state.existingMedia.isNotEmpty()) {
            Text(stringResource(R.string.current_media), style = MaterialTheme.typography.labelLarge)
            state.existingMedia.forEach { media ->
                val removed = media.id in state.removeMediaIds
                MediaRow(
                    media = media,
                    title = media.originalName.ifBlank { media.mimeType },
                    subtitle = if (removed) stringResource(R.string.media_marked_for_removal) else null,
                    struck = removed,
                    action = {
                        if (removed) {
                            TextButton(onClick = { onToggleExisting(media.id) }) {
                                Icon(Icons.AutoMirrored.Outlined.Undo, null, Modifier.padding(end = 4.dp))
                                Text(stringResource(R.string.keep_media))
                            }
                        } else {
                            IconButton(onClick = { onToggleExisting(media.id) }) {
                                Icon(Icons.Outlined.Delete, stringResource(R.string.remove_media), tint = MaterialTheme.colorScheme.error)
                            }
                        }
                    },
                )
            }
        }
        if (state.newFiles.isNotEmpty()) {
            Text(stringResource(R.string.selected_media), style = MaterialTheme.typography.labelLarge)
            state.newFiles.forEachIndexed { index, file ->
                ListItem(
                    headlineContent = { Text(file.name, maxLines = 1, overflow = TextOverflow.Ellipsis) },
                    supportingContent = { Text(file.size.takeIf { it >= 0 }?.let { "%.1f MB".format(it / 1_048_576.0) } ?: file.mimeType) },
                    leadingContent = {
                        Thumbnail(if (file.isVideo) null else file.uri, isVideo = file.isVideo)
                    },
                    trailingContent = {
                        IconButton(onClick = { onRemoveNew(index) }) { Icon(Icons.Outlined.Close, stringResource(R.string.remove_selected_file)) }
                    },
                    colors = ListItemDefaults.colors(containerColor = MaterialTheme.colorScheme.surfaceContainerLowest),
                )
            }
        }
        OutlinedButton(onClick = onPick, enabled = state.mediaSlotsLeft > 0, modifier = Modifier.fillMaxWidth()) {
            Icon(Icons.Outlined.AddPhotoAlternate, null, Modifier.padding(end = 8.dp))
            Text(stringResource(R.string.media_upload))
        }
        if (error != null) Text(error, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
private fun MediaRow(media: CourtMedia, title: String, subtitle: String?, struck: Boolean, action: @Composable () -> Unit) {
    ListItem(
        headlineContent = {
            Text(title, maxLines = 1, overflow = TextOverflow.Ellipsis, textDecoration = if (struck) TextDecoration.LineThrough else null)
        },
        supportingContent = subtitle?.let { { Text(it, color = MaterialTheme.colorScheme.error) } },
        leadingContent = { Thumbnail(if (media.isVideo) null else media.url, isVideo = media.isVideo) },
        trailingContent = action,
        colors = ListItemDefaults.colors(containerColor = MaterialTheme.colorScheme.surfaceContainerLowest),
    )
}

@Composable
private fun Thumbnail(model: Any?, isVideo: Boolean) {
    Box(
        Modifier.size(48.dp).clip(MaterialTheme.shapes.small),
        contentAlignment = Alignment.Center,
    ) {
        if (isVideo || model == null) {
            Surface(color = MaterialTheme.colorScheme.surfaceContainerHigh, modifier = Modifier.fillMaxSize(), border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)) {
                Box(contentAlignment = Alignment.Center) { Icon(Icons.Outlined.Movie, null) }
            }
        } else {
            AsyncImage(model = model, contentDescription = null, contentScale = ContentScale.Crop, modifier = Modifier.fillMaxSize())
        }
    }
}
