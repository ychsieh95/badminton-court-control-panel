package io.github.ychsieh95.bccp.core.ui.theme

import androidx.compose.ui.graphics.Color
import io.github.ychsieh95.bccp.core.data.Palette

/** The web stylesheet's CSS variables (`static/css/styles.css`), one set per palette and mode. */
internal data class WebTokens(
    val bg: Long, val surface: Long, val surfaceSoft: Long, val text: Long, val muted: Long,
    val border: Long, val borderStrong: Long, val primary: Long, val onPrimary: Long, val primarySoft: Long,
    val accent: Long, val accentText: Long, val danger: Long, val dangerSoft: Long, val warning: Long,
)

private const val LIGHT_DANGER = 0xFFBA3D49
private const val LIGHT_DANGER_SOFT = 0xFFFDEBED
private const val LIGHT_WARNING = 0xFFA66B14
private const val DARK_DANGER = 0xFFF07C85
private const val DARK_DANGER_SOFT = 0xFF3B2023
private const val DARK_WARNING = 0xFFE7B65E

internal fun webTokens(palette: Palette, dark: Boolean): WebTokens = when (palette) {
    Palette.Mono, Palette.Dynamic -> if (!dark) WebTokens(
        0xFFF6F6F7, 0xFFFFFFFF, 0xFFF0F0F2, 0xFF18181B, 0xFF6B6B73, 0xFFE1E1E5, 0xFFC9C9CF,
        0xFF18181B, 0xFFFFFFFF, 0xFFE9E9EC, 0xFFA1A1AA, 0xFF18181B, LIGHT_DANGER, LIGHT_DANGER_SOFT, LIGHT_WARNING,
    ) else WebTokens(
        0xFF09090B, 0xFF121214, 0xFF1D1D20, 0xFFFAFAFA, 0xFFA1A1AA, 0xFF29292D, 0xFF414147,
        0xFFF4F4F5, 0xFF09090B, 0xFF29292D, 0xFF71717A, 0xFFFAFAFA, DARK_DANGER, DARK_DANGER_SOFT, DARK_WARNING,
    )
    Palette.Green -> if (!dark) WebTokens(
        0xFFF5F7F2, 0xFFFFFFFF, 0xFFEEF2EB, 0xFF18201C, 0xFF69736D, 0xFFDCE3DC, 0xFFCBD5CC,
        0xFF126B45, 0xFFFFFFFF, 0xFFDFF1E7, 0xFFD7FF55, 0xFF17210D, LIGHT_DANGER, LIGHT_DANGER_SOFT, LIGHT_WARNING,
    ) else WebTokens(
        0xFF101411, 0xFF171D19, 0xFF202721, 0xFFEEF4EF, 0xFF9EA9A1, 0xFF2B352E, 0xFF3A473E,
        0xFF6FDAA2, 0xFF0B2417, 0xFF183B29, 0xFFC9F34E, 0xFF11190B, DARK_DANGER, DARK_DANGER_SOFT, DARK_WARNING,
    )
    Palette.Purple -> if (!dark) WebTokens(
        0xFFF8F6FB, 0xFFFFFFFF, 0xFFF0ECF5, 0xFF211A29, 0xFF746A7E, 0xFFE3DCEA, 0xFFCEC2DA,
        0xFF6D28D9, 0xFFFFFFFF, 0xFFEDE9FE, 0xFFD8B4FE, 0xFF2E1065, LIGHT_DANGER, LIGHT_DANGER_SOFT, LIGHT_WARNING,
    ) else WebTokens(
        0xFF100D14, 0xFF18131E, 0xFF251D2F, 0xFFFAF7FF, 0xFFB1A5BC, 0xFF33283F, 0xFF4B3A5D,
        0xFFC4B5FD, 0xFF1E1533, 0xFF302344, 0xFF8B5CF6, 0xFFF5F3FF, DARK_DANGER, DARK_DANGER_SOFT, DARK_WARNING,
    )
    Palette.Yellow -> if (!dark) WebTokens(
        0xFFFAF8F0, 0xFFFFFFFF, 0xFFF5F0DD, 0xFF262113, 0xFF776F5B, 0xFFE7DFC8, 0xFFD1C49E,
        0xFF946200, 0xFFFFFFFF, 0xFFFFF1B8, 0xFFFACC15, 0xFF2A2100, LIGHT_DANGER, LIGHT_DANGER_SOFT, LIGHT_WARNING,
    ) else WebTokens(
        0xFF121109, 0xFF1B190D, 0xFF292510, 0xFFFFFBEA, 0xFFB8AF8F, 0xFF393318, 0xFF544B23,
        0xFFFACC15, 0xFF1F1800, 0xFF3A3108, 0xFFF59E0B, 0xFF1F1800, DARK_DANGER, DARK_DANGER_SOFT, DARK_WARNING,
    )
}

internal fun Long.c() = Color(this)
