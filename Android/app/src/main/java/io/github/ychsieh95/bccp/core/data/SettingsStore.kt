package io.github.ychsieh95.bccp.core.data

import android.content.Context
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import io.github.ychsieh95.bccp.BuildConfig
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import javax.inject.Inject
import javax.inject.Singleton

internal val Context.dataStore by preferencesDataStore(name = "bccp")

enum class ThemeMode { System, Light, Dark }

/** Mirrors the web palettes (`data-palette`), plus the device's dynamic colors. */
enum class Palette { Mono, Green, Purple, Yellow, Dynamic }

data class AppSettings(
    val serverUrl: String = BuildConfig.DEFAULT_SERVER_URL,
    val themeMode: ThemeMode = ThemeMode.System,
    val palette: Palette = Palette.Green,
    val lastJoinName: String = "",
    val loaded: Boolean = false,
)

@Singleton
class SettingsStore @Inject constructor(
    @ApplicationContext private val context: Context,
    private val appScope: CoroutineScope,
) {
    private val _settings = MutableStateFlow(AppSettings())
    val settings: StateFlow<AppSettings> = _settings.asStateFlow()

    /** Read synchronously by the OkHttp interceptor. */
    val current: AppSettings get() = _settings.value

    init {
        appScope.launch {
            val prefs = context.dataStore.data.first()
            _settings.value = prefs.toSettings()
        }
    }

    fun setServerUrl(url: String) = update(SERVER_URL, normalizeServerUrl(url)) { copy(serverUrl = normalizeServerUrl(url)) }
    fun setThemeMode(mode: ThemeMode) = update(THEME, mode.name) { copy(themeMode = mode) }
    fun setPalette(palette: Palette) = update(PALETTE, palette.name) { copy(palette = palette) }
    fun setLastJoinName(name: String) = update(LAST_JOIN_NAME, name) { copy(lastJoinName = name) }

    private fun update(key: Preferences.Key<String>, value: String, change: AppSettings.() -> AppSettings) {
        _settings.value = _settings.value.change()
        appScope.launch { context.dataStore.edit { it[key] = value } }
    }

    private fun Preferences.toSettings() = AppSettings(
        serverUrl = this[SERVER_URL] ?: BuildConfig.DEFAULT_SERVER_URL,
        themeMode = this[THEME]?.let { runCatching { ThemeMode.valueOf(it) }.getOrNull() } ?: ThemeMode.System,
        palette = this[PALETTE]?.let { runCatching { Palette.valueOf(it) }.getOrNull() } ?: Palette.Green,
        lastJoinName = this[LAST_JOIN_NAME].orEmpty(),
        loaded = true,
    )

    companion object {
        private val SERVER_URL = stringPreferencesKey("server_url")
        private val THEME = stringPreferencesKey("theme_mode")
        private val PALETTE = stringPreferencesKey("palette")
        private val LAST_JOIN_NAME = stringPreferencesKey("last_join_name")

        fun normalizeServerUrl(raw: String): String {
            val trimmed = raw.trim().trimEnd('/')
            if (trimmed.isEmpty()) return BuildConfig.DEFAULT_SERVER_URL
            return if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) trimmed else "https://$trimmed"
        }
    }
}
