package io.github.ychsieh95.bccp

import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.ui.format.Formats
import org.junit.Assert.assertEquals
import org.junit.Test

class FormatsTest {
    @Test fun `court date uses slashes like the web`() = assertEquals("2026/12/01", Formats.courtDate("2026-12-01"))
    @Test fun `unparseable dates pass through`() = assertEquals("soon", Formats.courtDate("soon"))
    @Test fun `24h clock`() = assertEquals("19:05", Formats.clock("19:05", use12h = false))
    @Test fun `12h clock`() = assertEquals("7:05 PM", Formats.clock("19:05", use12h = true))
    @Test fun `date time from iso`() = assertEquals("2026/11/20 08:30", Formats.dateTime("2026-11-20T08:30:00", use12h = false))
    @Test fun `leave deadline without seconds`() = assertEquals("2026/11/21 12:00", Formats.dateTime("2026-11-21T12:00", use12h = false))

    @Test fun `level labels follow the web bands`() {
        assertEquals(R.string.level_beginner, Formats.levelLabelRes(3))
        assertEquals(R.string.level_elementary, Formats.levelLabelRes(4))
        assertEquals(R.string.level_upperintermediate, Formats.levelLabelRes(12))
        assertEquals(R.string.level_professional, Formats.levelLabelRes(16))
    }
}
