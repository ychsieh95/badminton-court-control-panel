package io.github.ychsieh95.bccp

import io.github.ychsieh95.bccp.navigation.CourtLinks
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class CourtLinksTest {
    private val guid = "84ca68c6-7348-49f0-a7fb-8c5bd18d03c8"

    @Test fun `extracts guid from a court url`() = assertEquals(guid, CourtLinks.guidFrom("https://courts.example.com/$guid"))
    @Test fun `ignores query, fragment and trailing slash`() = assertEquals(guid, CourtLinks.guidFrom("https://x.test/sub/$guid/?utm=1#top"))
    @Test fun `finds the url inside shared text`() = assertEquals(guid, CourtLinks.guidFrom("Friday games\nhttps://x.test/$guid"))
    @Test fun `accepts a bare guid`() = assertEquals(guid, CourtLinks.guidFrom("  $guid "))
    @Test fun `rejects text without a guid`() = assertNull(CourtLinks.guidFrom("see you at 7!"))
}
