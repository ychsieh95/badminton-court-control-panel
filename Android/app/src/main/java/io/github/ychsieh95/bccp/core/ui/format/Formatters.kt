package io.github.ychsieh95.bccp.core.ui.format

import androidx.annotation.StringRes
import androidx.compose.runtime.Composable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.res.stringResource
import io.github.ychsieh95.bccp.R
import java.time.DayOfWeek
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.LocalTime
import java.time.format.DateTimeFormatter

/** `true` when the signed-in member prefers 12-hour clocks (`time_format: "12h"`); the web's guest default is 24h. */
val LocalUse12h = staticCompositionLocalOf { false }

private val SLASH_DATE = DateTimeFormatter.ofPattern("yyyy/MM/dd")
private val CLOCK_24 = DateTimeFormatter.ofPattern("HH:mm")
private val CLOCK_12 = DateTimeFormatter.ofPattern("h:mm a", java.util.Locale.US)

object Formats {
    fun parseDate(value: String): LocalDate? = runCatching { LocalDate.parse(value.take(10)) }.getOrNull()
    fun parseTime(value: String): LocalTime? = runCatching { LocalTime.parse(value.take(5)) }.getOrNull()
    fun parseDateTime(value: String): LocalDateTime? = runCatching { LocalDateTime.parse(value) }.getOrNull()

    /** `2026-12-01` → `2026/12/01`, matching the web's `court_date` filter. */
    fun courtDate(value: String): String = parseDate(value)?.format(SLASH_DATE) ?: value

    fun clock(value: String, use12h: Boolean): String = parseTime(value)?.let { clock(it, use12h) } ?: value

    fun clock(time: LocalTime, use12h: Boolean): String = time.format(if (use12h) CLOCK_12 else CLOCK_24)

    fun dateTime(value: String?, use12h: Boolean): String {
        if (value.isNullOrBlank()) return ""
        val parsed = parseDateTime(value) ?: return value
        return "${parsed.toLocalDate().format(SLASH_DATE)} ${clock(parsed.toLocalTime(), use12h)}"
    }

    fun month(value: String): String = parseDate(value)?.monthValue?.toString()?.padStart(2, '0') ?: "--"
    fun day(value: String): String = parseDate(value)?.dayOfMonth?.toString()?.padStart(2, '0') ?: "--"

    @StringRes
    fun weekdayRes(day: DayOfWeek): Int = when (day) {
        DayOfWeek.MONDAY -> R.string.weekday_monday
        DayOfWeek.TUESDAY -> R.string.weekday_tuesday
        DayOfWeek.WEDNESDAY -> R.string.weekday_wednesday
        DayOfWeek.THURSDAY -> R.string.weekday_thursday
        DayOfWeek.FRIDAY -> R.string.weekday_friday
        DayOfWeek.SATURDAY -> R.string.weekday_saturday
        DayOfWeek.SUNDAY -> R.string.weekday_sunday
    }

    @StringRes
    fun levelLabelRes(level: Int): Int = when {
        level <= 3 -> R.string.level_beginner
        level <= 5 -> R.string.level_elementary
        level <= 7 -> R.string.level_preintermediate
        level <= 9 -> R.string.level_intermediate
        level <= 12 -> R.string.level_upperintermediate
        level <= 15 -> R.string.level_advanced
        else -> R.string.level_professional
    }
}

@Composable
fun weekday(date: String): String = Formats.parseDate(date)?.let { stringResource(Formats.weekdayRes(it.dayOfWeek)) }.orEmpty()

@Composable
fun clock(value: String): String = Formats.clock(value, LocalUse12h.current)

@Composable
fun dateTime(value: String?): String = Formats.dateTime(value, LocalUse12h.current)

@Composable
fun levelLabel(level: Int): String = stringResource(Formats.levelLabelRes(level))

/** `2026/12/01 · Tuesday · 19:00–21:00`, the web card's time line. */
@Composable
fun courtSchedule(date: String, start: String, end: String): String =
    "${Formats.courtDate(date)} · ${weekday(date)} · ${clock(start)}–${clock(end)}"
