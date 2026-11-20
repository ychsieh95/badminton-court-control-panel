package io.github.ychsieh95.bccp

import io.github.ychsieh95.bccp.core.data.CourtFilters
import org.junit.Assert.assertEquals
import org.junit.Test

class CourtFiltersTest {
    @Test fun `default filters only page`() = assertEquals(mapOf("limit" to "30", "offset" to "0"), CourtFilters().toQuery(30, 0))

    @Test fun `all filters map to the web query names`() {
        val query = CourtFilters(
            query = " smash ", dateFrom = "2026-12-01", dateTo = "2026-12-31", level = 7,
            gender = "female", status = "open", showExpired = true,
        ).toQuery(30, 60)
        assertEquals(
            mapOf(
                "q" to "smash", "date_from" to "2026-12-01", "date_to" to "2026-12-31", "level" to "7",
                "gender" to "female", "status" to "open", "show_expired" to "1", "limit" to "30", "offset" to "60",
            ),
            query,
        )
    }
}
