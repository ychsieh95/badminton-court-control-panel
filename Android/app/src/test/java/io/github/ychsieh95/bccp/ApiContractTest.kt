package io.github.ychsieh95.bccp

import io.github.ychsieh95.bccp.core.data.DataError
import io.github.ychsieh95.bccp.core.data.apiCall
import io.github.ychsieh95.bccp.core.di.AppModule
import io.github.ychsieh95.bccp.core.model.CourtStatus
import io.github.ychsieh95.bccp.core.network.ApiInterceptor
import io.github.ychsieh95.bccp.core.network.BccpApi
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.put
import okhttp3.OkHttpClient
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

/** Runs the real Retrofit stack against responses captured from the Flask API. */
class ApiContractTest {
    private val server = MockWebServer()
    private var token: String? = "bccp_test"
    private var rejected = false
    private lateinit var api: BccpApi
    private val json = AppModule.json()

    private fun fixture(name: String) = javaClass.getResource("/fixtures/$name")!!.readText()

    @Before fun setUp() {
        server.start()
        val interceptor = ApiInterceptor(
            serverUrl = { server.url("/deploy/").toString() },
            token = { token },
            onTokenRejected = { rejected = true; token = null },
            userAgent = "BCCP-Android/test (Linux; Android 16)",
        )
        api = AppModule.api(OkHttpClient.Builder().addInterceptor(interceptor).build(), json)
    }

    @After fun tearDown() = server.shutdown()

    @Test fun `rewrites placeholder url onto configured server with sub-path`() = runTest {
        server.enqueue(MockResponse().setBody(fixture("court_list.json")))
        api.courts(mapOf("q" to "a b", "limit" to "30"))
        val request = server.takeRequest()
        assertEquals("/deploy/api/v1/courts?q=a%20b&limit=30", request.path)
        assertEquals("Bearer bccp_test", request.getHeader("Authorization"))
        assertTrue(request.getHeader("User-Agent")!!.contains("Android"))
    }

    @Test fun `parses court list`() = runTest {
        server.enqueue(MockResponse().setBody(fixture("court_list.json")))
        val page = api.courts(emptyMap())
        assertEquals(2, page.courts.size)
        assertEquals(2, page.pagination.total)
        val first = page.courts.first()
        assertEquals("Friday evening games", first.eventName)
        assertEquals(CourtStatus.Open, first.status)
        assertEquals(5, first.levels.male.min)
    }

    @Test fun `parses manager court detail`() = runTest {
        server.enqueue(MockResponse().setBody(fixture("court_detail_manager.json")))
        val court = api.court("x").court
        assertTrue(court.viewer.canManage)
        assertEquals(3, court.participants.size)
        assertEquals(2, court.reservedMembers.size)
        assertTrue(court.reservedMembers.all { it.id != null })
        assertTrue(court.leaveDeadline.enabled)
        assertEquals(listOf("Amy", ""), court.reservedNicknames)
        assertEquals("2", court.formValues!!["ordered_count"])
        assertEquals(false, court.ownerNotifications)
        assertFalse(court.participationHistory.isEmpty())
    }

    @Test fun `error envelope becomes DataError Api`() = runTest {
        server.enqueue(MockResponse().setResponseCode(409).setBody(fixture("error_duplicate.json")))
        val result = apiCall(json) { api.join("x", buildJsonObject { put("username", "Ben") }) }
        val error = result.exceptionOrNull() as DataError.Api
        assertEquals(409, error.status)
        assertEquals("duplicate_username", error.code)
        assertEquals("That username has already joined this court.", error.message)
    }

    @Test fun `invalid token signs out`() = runTest {
        server.enqueue(
            MockResponse().setResponseCode(401).setHeader("WWW-Authenticate", "Bearer error=\"invalid_token\"")
                .setBody("""{"error":{"code":"invalid_token","message":"Sign in again."}}"""),
        )
        apiCall(json) { api.me() }
        assertTrue(rejected)
        assertNull(token)
    }

    @Test fun `wrong password does not sign out`() = runTest {
        server.enqueue(MockResponse().setResponseCode(401).setBody("""{"error":{"code":"invalid_credentials","message":"x"}}"""))
        apiCall(json) { api.login(buildJsonObject { put("username", "a") }) }
        assertFalse(rejected)
    }

    @Test fun `no-content responses succeed`() = runTest {
        server.enqueue(MockResponse().setResponseCode(204))
        assertTrue(api.deleteCourt("x").isSuccessful)
    }
}
