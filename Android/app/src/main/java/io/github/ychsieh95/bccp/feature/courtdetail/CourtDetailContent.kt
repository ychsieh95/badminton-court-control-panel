package io.github.ychsieh95.bccp.feature.courtdetail

import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.CalendarMonth
import androidx.compose.material.icons.outlined.ExpandLess
import androidx.compose.material.icons.outlined.ExpandMore
import androidx.compose.material.icons.outlined.Groups
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material.icons.outlined.Place
import androidx.compose.material.icons.outlined.PlayCircle
import androidx.compose.material.icons.outlined.Schedule
import androidx.compose.material.icons.outlined.Stadium
import androidx.compose.material.icons.outlined.VisibilityOff
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import coil3.compose.AsyncImage
import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.model.Court
import io.github.ychsieh95.bccp.core.model.HistoryEvent
import io.github.ychsieh95.bccp.core.model.LevelRange
import io.github.ychsieh95.bccp.core.model.MessageBoard
import io.github.ychsieh95.bccp.core.ui.component.CountBadge
import io.github.ychsieh95.bccp.core.ui.component.IconLine
import io.github.ychsieh95.bccp.core.ui.component.PanelCard
import io.github.ychsieh95.bccp.core.ui.component.Pill
import io.github.ychsieh95.bccp.core.ui.component.SectionHeader
import io.github.ychsieh95.bccp.core.ui.component.StatusBadge
import io.github.ychsieh95.bccp.core.ui.component.UserAvatar
import io.github.ychsieh95.bccp.core.ui.format.Formats
import io.github.ychsieh95.bccp.core.ui.format.clock
import io.github.ychsieh95.bccp.core.ui.format.dateTime
import io.github.ychsieh95.bccp.core.ui.format.levelLabel
import io.github.ychsieh95.bccp.core.ui.format.weekday
import io.github.ychsieh95.bccp.core.ui.theme.LocalExtraColors

@Composable
internal fun CourtDetailContent(
    court: Court,
    rollDraft: RollDraft,
    rollDirty: Boolean,
    busy: Boolean,
    board: MessageBoard?,
    actions: CourtDetailActions,
    listState: LazyListState = rememberLazyListState(),
) {
    LazyColumn(
        state = listState,
        contentPadding = PaddingValues(start = 16.dp, end = 16.dp, bottom = 32.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier.fillMaxSize(),
    ) {
        val section = Modifier.widthIn(max = 840.dp)
        item(key = "hero") { Hero(court, section) }
        item(key = "info") { InfoGrid(court, section) }
        if (court.media.isNotEmpty()) item(key = "gallery") { Gallery(court, section) }
        item(key = "capacity") { Capacity(court, section) }
        if (!court.acceptsPlayers) item(key = "closed") { ClosedNotice(court, section) }
        if (court.rollClearingLocked && court.viewer.canManage) {
            item(key = "roll") { RollCallPanel(court, rollDraft, rollDirty, busy, actions, section) }
        }
        item(key = "price") { PriceSection(court, section) }
        item(key = "level") { LevelSection(court, section) }
        if (court.remark.isNotBlank()) {
            item(key = "remark") {
                PanelCard(section) {
                    SectionHeader(stringResource(R.string.remark))
                    Text(court.remark, style = MaterialTheme.typography.bodyLarge)
                }
            }
        }
        if (court.reservedMembers.isNotEmpty()) item(key = "reserved") { ReservedSection(court, section) }
        item(key = "players") { PlayersSection(court, waiting = false, actions = actions, modifier = section) }
        if (court.waitingParticipants.isNotEmpty()) {
            item(key = "waiting") { PlayersSection(court, waiting = true, actions = actions, modifier = section) }
        }
        if (board != null) item(key = "messages") { MessagesSection(court, board, actions, section) }
        item(key = "history") { HistorySection(court, section) }
    }
}

@Composable
private fun Hero(court: Court, modifier: Modifier) {
    val context = LocalContext.current
    Column(modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        StatusBadge(court.status)
        Text(court.title, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.SemiBold)
        if (court.eventName.isNotBlank()) Text(court.hallName, style = MaterialTheme.typography.titleMedium)
        if (court.badmintonName.isNotBlank()) {
            Text(court.badmintonName, style = MaterialTheme.typography.bodyLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Row(
            Modifier
                .heightIn(min = 48.dp)
                .clip(MaterialTheme.shapes.small)
                .clickable(role = Role.Button, onClickLabel = stringResource(R.string.open_in_maps)) { CourtIntents.openMaps(context, court) },
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Icon(Icons.Outlined.Place, null, Modifier.size(18.dp), tint = MaterialTheme.colorScheme.primary)
            Text(court.location, style = MaterialTheme.typography.bodyLarge, color = MaterialTheme.colorScheme.primary)
        }
        IconLine(
            Icons.Outlined.Person,
            "${stringResource(R.string.creator)} · ${court.creatorUsername.ifBlank { stringResource(R.string.admin_account) }}",
        )
    }
}

@Composable
private fun InfoGrid(court: Court, modifier: Modifier) {
    val tiles = listOf(
        InfoTileData(Icons.Outlined.CalendarMonth, stringResource(R.string.date), Formats.courtDate(court.courtDate), weekday(court.courtDate)),
        InfoTileData(Icons.Outlined.Schedule, stringResource(R.string.time), "${clock(court.startTime)}–${clock(court.endTime)}", null),
        InfoTileData(Icons.Outlined.Stadium, stringResource(R.string.court_id), court.courtId, null),
        InfoTileData(Icons.Outlined.Groups, stringResource(R.string.member_range), "${court.members.min}–${court.members.max}", null),
    )
    Column(modifier, verticalArrangement = Arrangement.spacedBy(12.dp)) {
        tiles.chunked(2).forEach { row ->
            Row(Modifier.height(IntrinsicSize.Min), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                row.forEach { InfoTile(it, Modifier.weight(1f).fillMaxHeight()) }
            }
        }
    }
}

private data class InfoTileData(val icon: ImageVector, val label: String, val value: String, val extra: String?)

@Composable
private fun InfoTile(data: InfoTileData, modifier: Modifier) {
    PanelCard(modifier.semantics(mergeDescendants = true) {}) {
        Surface(shape = MaterialTheme.shapes.small, color = MaterialTheme.colorScheme.primaryContainer) {
            Icon(data.icon, null, Modifier.padding(8.dp).size(20.dp), tint = MaterialTheme.colorScheme.primary)
        }
        Column {
            Text(data.label, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(data.value, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            if (data.extra != null) Text(data.extra, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun Gallery(court: Court, modifier: Modifier) {
    val context = LocalContext.current
    val pager = rememberPagerState { court.media.size }
    PanelCard(modifier) {
        SectionHeader(stringResource(R.string.event_gallery), eyebrow = stringResource(R.string.event_media))
        HorizontalPager(pager, pageSpacing = 12.dp) { page ->
            val media = court.media[page]
            val description = stringResource(R.string.gallery_item, page + 1, court.media.size)
            Box(
                Modifier
                    .fillMaxWidth()
                    .aspectRatio(4f / 3f)
                    .clip(MaterialTheme.shapes.small)
                    .background(MaterialTheme.colorScheme.surfaceContainerHigh)
                    .clickable(role = Role.Button) { CourtIntents.openMedia(context, media) }
                    .semantics { contentDescription = media.originalName.ifBlank { description } },
                contentAlignment = Alignment.Center,
            ) {
                if (media.isVideo) {
                    Icon(Icons.Outlined.PlayCircle, stringResource(R.string.play_video), Modifier.size(56.dp))
                } else {
                    AsyncImage(
                        model = media.url,
                        contentDescription = stringResource(R.string.court_media_alt, court.hallName),
                        contentScale = ContentScale.Crop,
                        modifier = Modifier.fillMaxSize(),
                    )
                }
            }
        }
        if (court.media.size > 1) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center) {
                repeat(court.media.size) { index ->
                    val selected = pager.currentPage == index
                    Box(
                        Modifier
                            .padding(3.dp)
                            .size(if (selected) 8.dp else 6.dp)
                            .clip(CircleShape)
                            .background(if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outlineVariant),
                    )
                }
            }
        }
    }
}

@Composable
private fun Capacity(court: Court, modifier: Modifier) {
    val members = court.members
    PanelCard(modifier) {
        SectionHeader(
            title = "${members.confirmedTotal} / ${members.max}",
            eyebrow = stringResource(R.string.members),
            trailing = {
                if (!court.isFull) {
                    Text(
                        stringResource(R.string.spots_left_count, members.max - members.confirmedTotal),
                        style = MaterialTheme.typography.titleSmall,
                        color = MaterialTheme.colorScheme.primary,
                    )
                } else {
                    Pill(stringResource(R.string.full), MaterialTheme.colorScheme.errorContainer, MaterialTheme.colorScheme.error)
                }
            },
        )
        LinearProgressIndicator(
            progress = { if (members.max == 0) 0f else (members.confirmedTotal.toFloat() / members.max).coerceIn(0f, 1f) },
            modifier = Modifier.fillMaxWidth().height(10.dp).clip(CircleShape),
            strokeCap = StrokeCap.Round,
            gapSize = 0.dp,
            drawStopIndicator = {},
        )
        FlowRow(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            LegendDot(LocalExtraColors.current.accent, "${members.reserved} ${stringResource(R.string.reserved)}")
            LegendDot(MaterialTheme.colorScheme.primary, "${members.signedUp} ${stringResource(R.string.joined_on_site)}")
            if (members.waiting > 0) LegendDot(LocalExtraColors.current.warning, "${members.waiting} ${stringResource(R.string.waiting)}")
        }
    }
}

@Composable
private fun LegendDot(color: Color, label: String) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        Box(Modifier.size(10.dp).clip(CircleShape).background(color))
        Text(label, style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
private fun ClosedNotice(court: Court, modifier: Modifier) {
    val (title, body) = when {
        court.expired -> R.string.court_expired to R.string.court_expired_body
        court.rollClearingLocked -> R.string.court_read_only to R.string.court_read_only_body
        else -> R.string.archived to R.string.court_closed
    }
    PanelCard(modifier) {
        StatusBadge(court.status)
        Text(stringResource(title), style = MaterialTheme.typography.titleMedium)
        Text(stringResource(body), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun PriceSection(court: Court, modifier: Modifier) {
    PanelCard(modifier) {
        SectionHeader(stringResource(R.string.price_and_shuttlecock))
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            GenderValue("♂", stringResource(R.string.male_price), price(court.prices.male), Modifier.weight(1f))
            GenderValue("♀", stringResource(R.string.female_price), price(court.prices.female), Modifier.weight(1f))
        }
        Column {
            Text(stringResource(R.string.shuttlecock), style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(court.shuttlecockInfo.ifBlank { "—" }, style = MaterialTheme.typography.bodyLarge)
        }
    }
}

@Composable
private fun price(value: Int): String = if (value == 0) stringResource(R.string.free) else stringResource(R.string.price_value, value)

@Composable
private fun GenderValue(symbol: String, label: String, value: String, modifier: Modifier, detail: String? = null) {
    Row(modifier.semantics(mergeDescendants = true) {}, horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
        Surface(shape = CircleShape, color = MaterialTheme.colorScheme.secondaryContainer, modifier = Modifier.size(44.dp)) {
            Box(contentAlignment = Alignment.Center) { Text(symbol, style = MaterialTheme.typography.titleMedium) }
        }
        Column {
            Text(label, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(value, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            if (detail != null) Text(detail, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun LevelSection(court: Court, modifier: Modifier) {
    var chartOpen by rememberSaveable { mutableStateOf(false) }
    @Composable
    fun detail(range: LevelRange) = "${levelLabel(range.min)} – ${levelLabel(range.max)}"
    PanelCard(modifier) {
        SectionHeader(stringResource(R.string.level_guide), eyebrow = stringResource(R.string.level))
        GenderValue("♂", stringResource(R.string.male), "${court.levels.male.min}–${court.levels.male.max}", Modifier, detail(court.levels.male))
        GenderValue("♀", stringResource(R.string.female), "${court.levels.female.min}–${court.levels.female.max}", Modifier, detail(court.levels.female))
        Text(stringResource(R.string.level_guide_text), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        TextButton(onClick = { chartOpen = true }) { Text(stringResource(R.string.show_grading_chart)) }
    }
    if (chartOpen) {
        Dialog(onDismissRequest = { chartOpen = false }, properties = DialogProperties(usePlatformDefaultWidth = false)) {
            Surface(Modifier.padding(16.dp), shape = MaterialTheme.shapes.medium) {
                Column(Modifier.verticalScroll(rememberScrollState()).padding(12.dp)) {
                    Text(stringResource(R.string.grading_chart_caption), style = MaterialTheme.typography.titleSmall)
                    Image(
                        painterResource(R.drawable.grading_chart),
                        contentDescription = stringResource(R.string.grading_chart_alt),
                        contentScale = ContentScale.FillWidth,
                        modifier = Modifier.fillMaxWidth().padding(vertical = 12.dp),
                    )
                    TextButton(onClick = { chartOpen = false }, modifier = Modifier.align(Alignment.End)) { Text(stringResource(R.string.close)) }
                }
            }
        }
    }
}

@Composable
private fun ReservedSection(court: Court, modifier: Modifier) {
    val named = court.reservedMembers.filter { it.nickname.isNotBlank() }
    if (named.isEmpty() && !court.viewer.canManage) return
    PanelCard(modifier) {
        SectionHeader(
            stringResource(R.string.reserved_players),
            eyebrow = stringResource(R.string.reserved),
            trailing = { CountBadge("${named.size} / ${court.members.reserved}") },
        )
        if (!court.reservedNamesVisible) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                Icon(Icons.Outlined.VisibilityOff, null, Modifier.size(16.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
                Text(stringResource(R.string.hidden_from_viewers), style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        named.forEach { member ->
            PersonRow(
                member.nickname,
                stringResource(R.string.reserved),
                avatarColor = LocalExtraColors.current.accent,
                avatarContent = LocalExtraColors.current.onAccent,
            )
        }
    }
}

@Composable
private fun PlayersSection(court: Court, waiting: Boolean, actions: CourtDetailActions, modifier: Modifier) {
    val people = if (waiting) court.waitingParticipants else court.participants
    val canModerate = court.viewer.isAdmin && !court.rollClearingLocked
    PanelCard(modifier) {
        SectionHeader(
            stringResource(if (waiting) R.string.waiting_list else R.string.participants),
            eyebrow = stringResource(if (waiting) R.string.waitlisted else R.string.joined_on_site),
            trailing = { CountBadge(people.size.toString()) },
        )
        if (people.isEmpty()) {
            Text(stringResource(R.string.no_participants), color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        people.forEachIndexed { index, person ->
            PersonRow(
                name = person.username,
                status = if (waiting) stringResource(R.string.waitlisted) else dateTime(person.joinedAt).takeIf { it.isNotEmpty() }?.let { stringResource(R.string.joined_at, it) },
                avatarText = if (waiting) "${index + 1}" else null,
                avatarColor = if (waiting) LocalExtraColors.current.warningContainer else MaterialTheme.colorScheme.primaryContainer,
                avatarContent = if (waiting) LocalExtraColors.current.warning else MaterialTheme.colorScheme.onPrimaryContainer,
                trailing = if (canModerate) ({ ParticipantAdminMenu(person, actions) }) else null,
            )
        }
    }
}

@Composable
private fun PersonRow(
    name: String,
    status: String?,
    avatarText: String? = null,
    avatarColor: Color = MaterialTheme.colorScheme.primaryContainer,
    avatarContent: Color = MaterialTheme.colorScheme.onPrimaryContainer,
    trailing: (@Composable () -> Unit)? = null,
) {
    Row(
        Modifier.fillMaxWidth().heightIn(min = 48.dp).semantics(mergeDescendants = true) {},
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        UserAvatar(avatarText ?: name, container = avatarColor, content = avatarContent)
        Column(Modifier.weight(1f)) {
            Text(name, style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.Medium)
            if (status != null) Text(status, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        trailing?.invoke()
    }
}

@Composable
private fun HistorySection(court: Court, modifier: Modifier) {
    var expanded by rememberSaveable { mutableStateOf(false) }
    PanelCard(modifier) {
        SectionHeader(
            stringResource(R.string.participation_history),
            eyebrow = stringResource(R.string.participation_history_eyebrow),
            trailing = {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    CountBadge(court.participationHistory.size.toString())
                    IconButton(onClick = { expanded = !expanded }) {
                        Icon(if (expanded) Icons.Outlined.ExpandLess else Icons.Outlined.ExpandMore, stringResource(R.string.participation_history))
                    }
                }
            },
        )
        if (expanded) {
            if (court.participationHistory.isEmpty()) {
                Text(stringResource(R.string.no_participation_history), color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            court.participationHistory.forEach { HistoryRow(it, court.viewer.isAdmin) }
        }
    }
}

@Composable
private fun HistoryRow(event: HistoryEvent, showAudit: Boolean) {
    val joined = event.eventType == "join"
    Column(Modifier.fillMaxWidth().semantics(mergeDescendants = true) {}.padding(vertical = 4.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(event.username, style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.Medium, modifier = Modifier.weight(1f))
            Pill(
                stringResource(if (joined) R.string.history_joined else R.string.history_left),
                if (joined) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.errorContainer,
                if (joined) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,
            )
        }
        Text(dateTime(event.occurredAt), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        if (showAudit) {
            val device = when (event.deviceInformation) {
                "ios" -> stringResource(R.string.device_ios)
                "android" -> stringResource(R.string.device_android)
                "mobile" -> stringResource(R.string.device_mobile)
                "web" -> stringResource(R.string.device_web)
                else -> event.deviceInformation
            }
            val audit = listOfNotNull(event.ipAddress?.takeIf { it.isNotBlank() }, device?.takeIf { it.isNotBlank() })
            if (audit.isNotEmpty()) {
                Text(audit.joinToString(" · "), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}
