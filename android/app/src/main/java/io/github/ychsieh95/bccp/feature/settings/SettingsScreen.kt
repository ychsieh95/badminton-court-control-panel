package io.github.ychsieh95.bccp.feature.settings

import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import io.github.ychsieh95.bccp.BuildConfig
import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.data.Palette
import io.github.ychsieh95.bccp.core.data.ThemeMode
import io.github.ychsieh95.bccp.core.ui.component.PanelCard
import io.github.ychsieh95.bccp.core.ui.component.PrimaryActionButton
import io.github.ychsieh95.bccp.core.ui.component.SectionHeader
import io.github.ychsieh95.bccp.core.ui.component.TextInput
import io.github.ychsieh95.bccp.core.ui.text

@Composable
fun SettingsScreen(onBack: () -> Unit, viewModel: SettingsViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    val settings by viewModel.settings.collectAsStateWithLifecycle()
    val context = LocalContext.current

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.app_settings)) },
                navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, stringResource(R.string.back)) } },
            )
        },
    ) { padding ->
        Column(
            Modifier.padding(padding).fillMaxSize().verticalScroll(rememberScrollState()).imePadding().padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            val width = Modifier.widthIn(max = 840.dp)
            PanelCard(width) {
                SectionHeader(stringResource(R.string.server_url), eyebrow = stringResource(R.string.server))
                TextInput(
                    state.serverDraft, viewModel::setServerDraft, stringResource(R.string.server_url),
                    supporting = stringResource(R.string.server_url_help),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri, imeAction = ImeAction.Done),
                )
                if (state.signedIn && state.serverChanged) {
                    Text(stringResource(R.string.server_change_signs_out), color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                }
                state.status?.let { Text(it.text(), color = if (state.statusIsError) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary) }
                PrimaryActionButton(
                    stringResource(if (state.serverChanged) R.string.save else R.string.test_connection),
                    viewModel::saveAndTest,
                    busy = state.testing,
                )
            }
            PanelCard(width) {
                SectionHeader(stringResource(R.string.theme), eyebrow = stringResource(R.string.preferences))
                val modes = listOf(ThemeMode.System to R.string.theme_system, ThemeMode.Light to R.string.theme_light, ThemeMode.Dark to R.string.theme_dark)
                SingleChoiceSegmentedButtonRow(Modifier.fillMaxWidth()) {
                    modes.forEachIndexed { i, (mode, label) ->
                        SegmentedButton(
                            selected = settings.themeMode == mode,
                            onClick = { viewModel.setThemeMode(mode) },
                            shape = SegmentedButtonDefaults.itemShape(i, modes.size),
                        ) { Text(stringResource(label)) }
                    }
                }
                Text(stringResource(R.string.palette), style = MaterialTheme.typography.titleSmall)
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    val palettes = buildList {
                        add(Palette.Green to R.string.theme_green)
                        add(Palette.Mono to R.string.theme_mono)
                        add(Palette.Purple to R.string.theme_purple)
                        add(Palette.Yellow to R.string.theme_yellow)
                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) add(Palette.Dynamic to R.string.palette_dynamic)
                    }
                    palettes.forEach { (palette, label) ->
                        FilterChip(selected = settings.palette == palette, onClick = { viewModel.setPalette(palette) }, label = { Text(stringResource(label)) })
                    }
                }
            }
            PanelCard(width) {
                SectionHeader(stringResource(R.string.app_language))
                Text(stringResource(R.string.app_language_help), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                OutlinedButton(onClick = {
                    val intent = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                        Intent(Settings.ACTION_APP_LOCALE_SETTINGS, Uri.fromParts("package", context.packageName, null))
                    } else {
                        Intent(Settings.ACTION_LOCALE_SETTINGS)
                    }
                    runCatching { context.startActivity(intent) }
                }) { Text(stringResource(R.string.open_system_settings)) }
            }
            PanelCard(width) {
                SectionHeader(stringResource(R.string.about))
                Text(stringResource(R.string.brand), style = MaterialTheme.typography.titleMedium)
                Text(stringResource(R.string.version, BuildConfig.VERSION_NAME), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}
