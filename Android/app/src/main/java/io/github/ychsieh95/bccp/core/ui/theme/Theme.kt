package io.github.ychsieh95.bccp.core.ui.theme

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.ColorScheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.lerp
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import io.github.ychsieh95.bccp.core.data.Palette
import io.github.ychsieh95.bccp.core.data.ThemeMode

/** Roles M3 has no slot for: the web's `--warning` (expired) and `--accent` (lime highlight). */
@Immutable
data class ExtraColors(
    val warning: Color,
    val warningContainer: Color,
    val accent: Color,
    val onAccent: Color,
)

val LocalExtraColors = staticCompositionLocalOf {
    ExtraColors(Color(0xFFA66B14), Color(0x24A66B14), Color(0xFFD7FF55), Color(0xFF17210D))
}

private val AppShapes = Shapes(
    extraSmall = RoundedCornerShape(6.dp),
    small = RoundedCornerShape(10.dp),
    medium = RoundedCornerShape(18.dp),
    large = RoundedCornerShape(24.dp),
    extraLarge = RoundedCornerShape(28.dp),
)

private fun schemeFrom(t: WebTokens, dark: Boolean): ColorScheme {
    val surface = t.surface.c()
    val soft = t.surfaceSoft.c()
    val base = if (dark) darkColorScheme() else lightColorScheme()
    return base.copy(
        primary = t.primary.c(),
        onPrimary = t.onPrimary.c(),
        primaryContainer = t.primarySoft.c(),
        onPrimaryContainer = if (dark) t.text.c() else t.primary.c(),
        inversePrimary = t.primarySoft.c(),
        secondary = t.muted.c(),
        onSecondary = t.surface.c(),
        secondaryContainer = soft,
        onSecondaryContainer = t.text.c(),
        tertiary = t.accent.c(),
        onTertiary = t.accentText.c(),
        tertiaryContainer = t.accent.c(),
        onTertiaryContainer = t.accentText.c(),
        background = t.bg.c(),
        onBackground = t.text.c(),
        surface = t.bg.c(),
        onSurface = t.text.c(),
        surfaceVariant = soft,
        onSurfaceVariant = t.muted.c(),
        surfaceTint = t.primary.c(),
        surfaceBright = surface,
        surfaceDim = soft,
        surfaceContainerLowest = surface,
        surfaceContainerLow = lerp(surface, t.bg.c(), 0.5f),
        surfaceContainer = t.bg.c(),
        surfaceContainerHigh = soft,
        surfaceContainerHighest = lerp(soft, t.border.c(), 0.6f),
        outline = t.borderStrong.c(),
        outlineVariant = t.border.c(),
        error = t.danger.c(),
        onError = if (dark) t.bg.c() else Color.White,
        errorContainer = t.dangerSoft.c(),
        onErrorContainer = t.danger.c(),
    )
}

@Composable
fun BccpTheme(themeMode: ThemeMode, palette: Palette, content: @Composable () -> Unit) {
    val dark = when (themeMode) {
        ThemeMode.System -> isSystemInDarkTheme()
        ThemeMode.Light -> false
        ThemeMode.Dark -> true
    }
    val tokens = webTokens(palette, dark)
    val colorScheme = if (palette == Palette.Dynamic && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        val context = LocalContext.current
        if (dark) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
    } else {
        schemeFrom(tokens, dark)
    }
    val extra = ExtraColors(
        warning = tokens.warning.c(),
        warningContainer = tokens.warning.c().copy(alpha = 0.14f),
        accent = if (palette == Palette.Dynamic) colorScheme.tertiaryContainer else tokens.accent.c(),
        onAccent = if (palette == Palette.Dynamic) colorScheme.onTertiaryContainer else tokens.accentText.c(),
    )
    CompositionLocalProvider(LocalExtraColors provides extra) {
        MaterialTheme(colorScheme = colorScheme, shapes = AppShapes, content = content)
    }
}
