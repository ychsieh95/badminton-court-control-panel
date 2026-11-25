package io.github.ychsieh95.bccp.feature.courtform

import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.ime
import androidx.compose.foundation.layout.union
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.BottomAppBar
import androidx.compose.material3.BottomAppBarDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.repeatOnLifecycle
import kotlinx.coroutines.launch
import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.data.LocalFile
import io.github.ychsieh95.bccp.core.push.CourtNotifications
import io.github.ychsieh95.bccp.core.ui.component.Choice
import io.github.ychsieh95.bccp.core.ui.component.ConfirmDialog
import io.github.ychsieh95.bccp.core.ui.component.DateField
import io.github.ychsieh95.bccp.core.ui.component.DropdownField
import io.github.ychsieh95.bccp.core.ui.component.ErrorPane
import io.github.ychsieh95.bccp.core.ui.component.LoadingPane
import io.github.ychsieh95.bccp.core.ui.component.PrimaryActionButton
import io.github.ychsieh95.bccp.core.ui.component.SwitchRow
import io.github.ychsieh95.bccp.core.ui.component.TextInput
import io.github.ychsieh95.bccp.core.ui.component.TimeField
import io.github.ychsieh95.bccp.core.ui.format.levelLabel
import io.github.ychsieh95.bccp.core.ui.format.weekday
import io.github.ychsieh95.bccp.core.ui.text

@Composable
fun CourtFormScreen(onBack: () -> Unit, onSaved: (String, Boolean) -> Unit, viewModel: CourtFormViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    val context = LocalContext.current
    val lifecycle = LocalLifecycleOwner.current.lifecycle
    var confirmDiscard by rememberSaveable { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED) {
            viewModel.effects.collect { effect ->
                when (effect) {
                    is CourtFormEffect.Message -> launch { snackbar.showSnackbar(effect.message.resolve(context)) }
                    is CourtFormEffect.Saved -> onSaved(effect.guid, effect.created)
                }
            }
        }
    }
    // Organizer alerts need notification permission; ask once, then save either way.
    var askedPermission by rememberSaveable { mutableStateOf(false) }
    val permission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { viewModel.save() }
    val save = {
        val needsPermission = state.ownerNotificationsAvailable && state.ownerNotifications &&
            !CourtNotifications.canPost(context) && android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.TIRAMISU
        if (needsPermission && !askedPermission) {
            askedPermission = true
            permission.launch(android.Manifest.permission.POST_NOTIFICATIONS)
        } else {
            viewModel.save()
        }
    }
    val leave = { if (state.dirty) confirmDiscard = true else onBack() }
    BackHandler(enabled = state.dirty) { confirmDiscard = true }

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        topBar = {
            TopAppBar(
                title = { Text(stringResource(if (state.editing) R.string.edit_title else R.string.create_title)) },
                navigationIcon = { IconButton(onClick = leave) { Icon(Icons.AutoMirrored.Filled.ArrowBack, stringResource(R.string.back)) } },
            )
        },
        bottomBar = {
            if (!state.loading && state.loadError == null) {
                // Union, not sum: the IME inset already covers the navigation bar.
                BottomAppBar(windowInsets = BottomAppBarDefaults.windowInsets.union(WindowInsets.ime)) {
                    PrimaryActionButton(
                        text = stringResource(if (state.editing) R.string.save_changes else R.string.create_court),
                        onClick = save,
                        busy = state.saving,
                        modifier = Modifier.padding(horizontal = 16.dp),
                    )
                }
            }
        },
    ) { padding ->
        Box(Modifier.padding(padding).fillMaxSize()) {
            when {
                state.loadError != null -> ErrorPane(state.loadError!!.text(), viewModel::load)
                state.loading -> LoadingPane()
                else -> CourtForm(state, viewModel)
            }
        }
    }

    if (confirmDiscard) {
        ConfirmDialog(
            message = stringResource(R.string.unsaved_changes),
            confirmLabel = stringResource(R.string.discard),
            destructive = true,
            onConfirm = onBack,
            onDismiss = { confirmDiscard = false },
        )
    }
}

/** Field errors are mostly localized messages; a few are codes the web translates with `t()`. */
@Composable
private fun CourtFormUiState.error(key: String): String? = fieldErrors[key]?.let { value ->
    when (value) {
        "nickname_too_long" -> stringResource(R.string.nickname_too_long)
        "media_invalid" -> stringResource(R.string.media_invalid)
        "media_too_large" -> stringResource(R.string.media_too_large)
        "media_too_many" -> stringResource(R.string.media_too_many)
        else -> value
    }
}

@Composable
private fun CourtForm(state: CourtFormUiState, vm: CourtFormViewModel) {
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        val section = Modifier.widthIn(max = 840.dp)
        Text(
            stringResource(if (state.editing) R.string.edit_body else R.string.create_body),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = section.fillMaxWidth(),
        )
        if (state.fieldErrors.isNotEmpty()) {
            Text(stringResource(R.string.fix_errors), color = MaterialTheme.colorScheme.error, modifier = section.fillMaxWidth())
        }
        EventSection(state, vm, section)
        HallSection(state, vm, section)
        MembersSection(state, vm, section)
        PriceSection(state, vm, section)
        LevelSection(state, vm, section)
        RemarkMediaSection(state, vm, section)
        if (state.ownerNotificationsAvailable) NotificationSection(state, vm, section)
    }
}

@Composable
private fun NotificationSection(state: CourtFormUiState, vm: CourtFormViewModel, modifier: Modifier) {
    val context = LocalContext.current
    FormSection("07", stringResource(R.string.owner_notifications_section), modifier = modifier) {
        SwitchRow(
            title = stringResource(R.string.owner_notifications_title),
            body = stringResource(R.string.owner_notifications_body),
            checked = state.ownerNotifications,
            onCheckedChange = vm::setOwnerNotifications,
        )
        val blocked = !CourtNotifications.canPost(context) && android.os.Build.VERSION.SDK_INT < android.os.Build.VERSION_CODES.TIRAMISU
        if (state.ownerNotifications && blocked) {
            Text(stringResource(R.string.push_notifications_blocked), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
        }
    }
}

@Composable
private fun EventSection(state: CourtFormUiState, vm: CourtFormViewModel, modifier: Modifier) {
    FormSection("01", stringResource(R.string.event_information), modifier = modifier) {
        TextInput(
            state[F.EVENT_NAME], { vm.set(F.EVENT_NAME, it) }, stringResource(R.string.event_name),
            placeholder = stringResource(R.string.event_name_placeholder), supporting = stringResource(R.string.optional),
            error = state.error(F.EVENT_NAME), maxLength = 160,
        )
        TextInput(
            state[F.BADMINTON_NAME], { vm.set(F.BADMINTON_NAME, it) }, stringResource(R.string.badminton_name),
            placeholder = stringResource(R.string.badminton_name_placeholder), supporting = stringResource(R.string.optional),
            error = state.error(F.BADMINTON_NAME), maxLength = 160,
        )
        DateField(state[F.DATE], { vm.set(F.DATE, it) }, stringResource(R.string.date), error = state.error(F.DATE), supporting = weekday(state[F.DATE]))
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            TimeField(state[F.START], { vm.set(F.START, it) }, stringResource(R.string.start_time), Modifier.weight(1f), error = state.error(F.START))
            TimeField(state[F.END], { vm.set(F.END, it) }, stringResource(R.string.end_time), Modifier.weight(1f), error = state.error(F.END))
        }
        SwitchRow(
            title = stringResource(R.string.leave_deadline_enable),
            body = stringResource(R.string.leave_deadline_help),
            checked = state[F.DEADLINE_ON] == "1",
            onCheckedChange = { vm.set(F.DEADLINE_ON, if (it) "1" else "0") },
        )
        if (state[F.DEADLINE_ON] == "1") {
            val at = state[F.DEADLINE_AT]
            val date = at.take(10).takeIf { it.length == 10 }.orEmpty()
            val time = at.drop(11).take(5)
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                // The date label is longer than "Time" and needs the room to stay on one line.
                DateField(date, { vm.setLeaveDeadline(it, time) }, stringResource(R.string.leave_deadline), Modifier.weight(3f), error = state.error(F.DEADLINE_AT))
                TimeField(time, { vm.setLeaveDeadline(date.ifBlank { state[F.DATE] }, it) }, stringResource(R.string.time), Modifier.weight(2f))
            }
            state.error(F.DEADLINE_ON)?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        }
    }
}

@Composable
private fun HallSection(state: CourtFormUiState, vm: CourtFormViewModel, modifier: Modifier) {
    val context = LocalContext.current
    FormSection("02", stringResource(R.string.hall), modifier = modifier) {
        if (!state.editing) {
            val choices = listOf(Choice<Int?>(null, stringResource(if (state.savedLocations.isEmpty()) R.string.no_saved_locations else R.string.choose_saved_location))) +
                state.savedLocations.map { Choice<Int?>(it.id, "${it.hallName} · ${it.location}") }
            DropdownField(
                label = stringResource(R.string.use_saved_location),
                choices = choices,
                selected = null,
                onSelect = { id -> state.savedLocations.firstOrNull { it.id == id }?.let(vm::applySavedLocation) },
                enabled = state.savedLocations.isNotEmpty(),
            )
        }
        TextInput(
            state[F.HALL], { vm.set(F.HALL, it) }, stringResource(R.string.hall_name),
            placeholder = stringResource(R.string.hall_placeholder), error = state.error(F.HALL), maxLength = 160,
        )
        TextInput(
            state[F.LOCATION], { vm.set(F.LOCATION, it) }, stringResource(R.string.location),
            placeholder = stringResource(R.string.location_placeholder), error = state.error(F.LOCATION), maxLength = 160,
        )
        androidx.compose.material3.TextButton(onClick = {
            val query = android.net.Uri.encode(listOf(state[F.HALL], state[F.LOCATION]).filter(String::isNotBlank).joinToString(" "))
            runCatching {
                context.startActivity(android.content.Intent(android.content.Intent.ACTION_VIEW, android.net.Uri.parse("https://www.google.com/maps/search/?api=1&query=$query")))
            }
        }) { Text(stringResource(R.string.search_maps) + " ↗") }
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            val decimal = KeyboardOptions(keyboardType = KeyboardType.Decimal)
            TextInput(state[F.LAT], { vm.set(F.LAT, it) }, stringResource(R.string.latitude), Modifier.weight(1f), error = state.error(F.LAT), keyboardOptions = decimal)
            TextInput(state[F.LNG], { vm.set(F.LNG, it) }, stringResource(R.string.longitude), Modifier.weight(1f), error = state.error(F.LNG), keyboardOptions = decimal)
        }
        Text(stringResource(R.string.optional_coordinates_help), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        if (!state.editing) {
            SwitchRow(stringResource(R.string.save_this_location), state.saveLocation, vm::setSaveLocation, body = stringResource(R.string.save_location_help))
        }
        TextInput(state[F.COURT_ID], { vm.set(F.COURT_ID, it) }, stringResource(R.string.court_id), placeholder = "A1", error = state.error(F.COURT_ID), maxLength = 160)
    }
}

@Composable
private fun MembersSection(state: CourtFormUiState, vm: CourtFormViewModel, modifier: Modifier) {
    val counts = (1..99).map { Choice(it.toString(), it.toString()) }
    FormSection("03", stringResource(R.string.members), stringResource(R.string.ordered_help), modifier) {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            DropdownField(stringResource(R.string.member_min), counts, state[F.MEMBER_MIN], { vm.set(F.MEMBER_MIN, it) }, Modifier.weight(1f), state.error(F.MEMBER_MIN))
            DropdownField(stringResource(R.string.member_max), counts, state[F.MEMBER_MAX], { vm.set(F.MEMBER_MAX, it) }, Modifier.weight(1f), state.error(F.MEMBER_MAX))
        }
        DropdownField(
            stringResource(R.string.ordered_count),
            (0..99).map { Choice(it, it.toString()) },
            state[F.ORDERED].toIntOrNull() ?: 0,
            vm::setOrderedCount,
            error = state.error(F.ORDERED),
        )
        ReservedNicknameEditor(state, vm, state.error(F.NICKNAMES))
    }
}

@Composable
private fun PriceSection(state: CourtFormUiState, vm: CourtFormViewModel, modifier: Modifier) {
    val number = KeyboardOptions(keyboardType = KeyboardType.Number)
    FormSection("04", stringResource(R.string.price_and_shuttlecock), modifier = modifier) {
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            TextInput(
                state[F.MALE_PRICE], { v -> vm.set(F.MALE_PRICE, v.filter(Char::isDigit)) }, stringResource(R.string.male_price), Modifier.weight(1f),
                supporting = stringResource(R.string.price_hint), error = state.error(F.MALE_PRICE), keyboardOptions = number,
            )
            TextInput(
                state[F.FEMALE_PRICE], { v -> vm.set(F.FEMALE_PRICE, v.filter(Char::isDigit)) }, stringResource(R.string.female_price), Modifier.weight(1f),
                supporting = stringResource(R.string.price_hint), error = state.error(F.FEMALE_PRICE), keyboardOptions = number,
            )
        }
        TextInput(
            state[F.SHUTTLE], { vm.set(F.SHUTTLE, it) }, stringResource(R.string.shuttlecock),
            placeholder = stringResource(R.string.shuttlecock_placeholder), error = state.error(F.SHUTTLE),
            singleLine = false, minLines = 2, maxLength = 500,
        )
    }
}

@Composable
private fun LevelSection(state: CourtFormUiState, vm: CourtFormViewModel, modifier: Modifier) {
    // "18 · Professional" does not fit a half-width field: show the number, with the name below it.
    val levels = (1..18).map { Choice(it.toString(), "$it · ${levelLabel(it)}", short = it.toString()) }
    @Composable
    fun LevelField(label: Int, key: String, modifier: Modifier) = DropdownField(
        stringResource(label), levels, state[key], { vm.set(key, it) }, modifier, state.error(key),
        supporting = state[key].toIntOrNull()?.let { levelLabel(it) },
    )
    FormSection("05", stringResource(R.string.level), stringResource(R.string.level_guide_text), modifier) {
        Text("♂ " + stringResource(R.string.male), style = MaterialTheme.typography.titleSmall)
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            LevelField(R.string.male_min, F.MALE_MIN, Modifier.weight(1f))
            LevelField(R.string.male_max, F.MALE_MAX, Modifier.weight(1f))
        }
        Text("♀ " + stringResource(R.string.female), style = MaterialTheme.typography.titleSmall)
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            LevelField(R.string.female_min, F.FEMALE_MIN, Modifier.weight(1f))
            LevelField(R.string.female_max, F.FEMALE_MAX, Modifier.weight(1f))
        }
    }
}

@Composable
private fun RemarkMediaSection(state: CourtFormUiState, vm: CourtFormViewModel, modifier: Modifier) {
    val context = LocalContext.current
    val maxPick = state.mediaSlotsLeft.coerceIn(2, 12)
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.PickMultipleVisualMedia(maxPick)) { uris ->
        vm.addFiles(uris.map { LocalFile.from(context.contentResolver, it) })
    }
    FormSection("06", stringResource(R.string.remark), modifier = modifier) {
        TextInput(
            state[F.REMARK], { vm.set(F.REMARK, it) }, stringResource(R.string.remark),
            placeholder = stringResource(R.string.remark_placeholder), error = state.error(F.REMARK),
            singleLine = false, minLines = 3, maxLength = 2000,
        )
        MediaEditor(
            state = state,
            error = state.error(F.MEDIA),
            onPick = { picker.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageAndVideo)) },
            onToggleExisting = vm::toggleRemoveMedia,
            onRemoveNew = vm::removeFile,
        )
    }
}

