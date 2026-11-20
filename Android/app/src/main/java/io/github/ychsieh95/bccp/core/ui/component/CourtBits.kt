package io.github.ychsieh95.bccp.core.ui.component

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.ArrowForward
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material.icons.outlined.Place
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import coil3.compose.AsyncImage
import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.model.Court
import io.github.ychsieh95.bccp.core.model.CourtStatus
import io.github.ychsieh95.bccp.core.ui.format.Formats
import io.github.ychsieh95.bccp.core.ui.format.courtSchedule
import io.github.ychsieh95.bccp.core.ui.theme.LocalExtraColors

@Composable
fun StatusBadge(status: CourtStatus, modifier: Modifier = Modifier) {
    val scheme = MaterialTheme.colorScheme
    val extra = LocalExtraColors.current
    val (label, container, content) = when (status) {
        CourtStatus.Open -> Triple(R.string.open, scheme.primaryContainer, scheme.primary)
        CourtStatus.Full -> Triple(R.string.full, scheme.errorContainer, scheme.error)
        CourtStatus.ReadOnly -> Triple(R.string.read_only, scheme.surfaceContainerHigh, scheme.onSurface)
        CourtStatus.Expired -> Triple(R.string.expired, extra.warningContainer, extra.warning)
        CourtStatus.Archived -> Triple(R.string.archived, scheme.surfaceContainerHigh, scheme.onSurfaceVariant)
    }
    Pill(stringResource(label), container, content, modifier, dot = status == CourtStatus.Open)
}

@Composable
fun Pill(text: String, container: Color, content: Color, modifier: Modifier = Modifier, dot: Boolean = false) {
    Surface(shape = CircleShape, color = container, contentColor = content, modifier = modifier) {
        Row(
            Modifier.padding(horizontal = 10.dp, vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            if (dot) Box(Modifier.size(6.dp).clip(CircleShape).background(content))
            Text(text, style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.SemiBold)
        }
    }
}

@Composable
fun CountBadge(text: String, modifier: Modifier = Modifier) {
    Pill(text, MaterialTheme.colorScheme.surfaceContainerHigh, MaterialTheme.colorScheme.onSurface, modifier)
}

/** The web's month/day `.date-chip`. */
@Composable
fun DateChip(date: String, modifier: Modifier = Modifier) {
    Surface(
        modifier = modifier.clearAndSetSemantics { contentDescription = Formats.courtDate(date) },
        shape = MaterialTheme.shapes.small,
        color = LocalExtraColors.current.accent,
        contentColor = LocalExtraColors.current.onAccent,
    ) {
        Column(Modifier.padding(horizontal = 12.dp, vertical = 6.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Text(Formats.month(date), style = MaterialTheme.typography.labelSmall)
            Text(Formats.day(date), style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
fun IconLine(icon: androidx.compose.ui.graphics.vector.ImageVector, text: String, modifier: Modifier = Modifier) {
    Row(modifier, verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        Icon(icon, null, Modifier.size(16.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(
            text,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
fun CourtCard(court: Court, onClick: () -> Unit, modifier: Modifier = Modifier) {
    Card(
        onClick = onClick,
        modifier = modifier.fillMaxWidth(),
        shape = MaterialTheme.shapes.medium,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLowest),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
    ) {
        if (court.coverImageUrl != null) {
            AsyncImage(
                model = court.coverImageUrl,
                contentDescription = stringResource(R.string.court_media_alt, court.hallName),
                contentScale = ContentScale.Crop,
                modifier = Modifier.fillMaxWidth().aspectRatio(16f / 7f),
            )
        }
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                DateChip(court.courtDate)
                Box(Modifier.weight(1f))
                StatusBadge(court.status)
            }
            Text(
                courtSchedule(court.courtDate, court.startTime, court.endTime),
                style = MaterialTheme.typography.labelLarge,
                color = MaterialTheme.colorScheme.primary,
            )
            Text(court.title, style = MaterialTheme.typography.titleLarge, maxLines = 2, overflow = TextOverflow.Ellipsis)
            val context = listOfNotNull(
                court.hallName.takeIf { court.eventName.isNotBlank() },
                court.badmintonName.takeIf { it.isNotBlank() },
            )
            if (context.isNotEmpty()) {
                Text(context.joinToString(" · "), style = MaterialTheme.typography.bodyMedium)
            }
            IconLine(Icons.Outlined.Place, court.location)
            IconLine(
                Icons.Outlined.Person,
                "${stringResource(R.string.creator)} · ${court.creatorUsername.ifBlank { stringResource(R.string.admin_account) }}",
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                MetaValue(stringResource(R.string.court_id), court.courtId)
                MetaValue(stringResource(R.string.members), "${court.members.confirmedTotal}/${court.members.max}")
                if (court.members.waiting > 0) MetaValue(stringResource(R.string.waiting_list), court.members.waiting.toString())
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    "♂ ${court.levels.male.min}–${court.levels.male.max}   ♀ ${court.levels.female.min}–${court.levels.female.max}",
                    style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.weight(1f),
                )
                Text(stringResource(R.string.view_court), style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.primary)
                Icon(
                    Icons.AutoMirrored.Outlined.ArrowForward,
                    null,
                    Modifier.padding(start = 4.dp).size(16.dp),
                    tint = MaterialTheme.colorScheme.primary,
                )
            }
        }
    }
}

@Composable
private fun MetaValue(label: String, value: String) {
    Surface(shape = MaterialTheme.shapes.small, color = MaterialTheme.colorScheme.surfaceContainerHigh) {
        Text(
            "$label $value",
            style = MaterialTheme.typography.labelMedium,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
        )
    }
}

@Composable
fun UserAvatar(
    name: String,
    modifier: Modifier = Modifier,
    url: String? = null,
    container: Color = MaterialTheme.colorScheme.primaryContainer,
    content: Color = MaterialTheme.colorScheme.onPrimaryContainer,
) {
    Box(modifier.size(40.dp).clip(CircleShape).background(container), contentAlignment = Alignment.Center) {
        if (url != null) {
            AsyncImage(model = url, contentDescription = null, contentScale = ContentScale.Crop, modifier = Modifier.fillMaxSize())
        } else {
            Text(
                name.take(1).uppercase(),
                style = MaterialTheme.typography.titleMedium,
                color = content,
            )
        }
    }
}
