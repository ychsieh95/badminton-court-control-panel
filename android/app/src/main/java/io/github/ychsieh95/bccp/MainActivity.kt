package io.github.ychsieh95.bccp

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import dagger.hilt.android.AndroidEntryPoint
import io.github.ychsieh95.bccp.core.push.CourtNotifications
import io.github.ychsieh95.bccp.navigation.BccpApp
import io.github.ychsieh95.bccp.navigation.CourtDetailRoute
import io.github.ychsieh95.bccp.navigation.CourtLinks

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    private var sharedCourt by mutableStateOf<CourtDetailRoute?>(null)

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        if (savedInstanceState == null) sharedCourt = intent.sharedCourt()
        setContent {
            BccpApp(sharedCourt = sharedCourt, onSharedCourtHandled = { sharedCourt = null })
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        intent.sharedCourt()?.let { sharedCourt = it }
    }

    /** A court to open: shared as a link, or tapped in a court notification. */
    private fun Intent.sharedCourt(): CourtDetailRoute? {
        getStringExtra(CourtNotifications.EXTRA_COURT_GUID)?.let {
            return CourtDetailRoute(it, showMessages = getBooleanExtra(CourtNotifications.EXTRA_SHOW_MESSAGES, false))
        }
        if (action != Intent.ACTION_SEND) return null
        return getStringExtra(Intent.EXTRA_TEXT)?.let(CourtLinks::guidFrom)?.let { CourtDetailRoute(it) }
    }
}
