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
import io.github.ychsieh95.bccp.navigation.CourtLinks

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    private var sharedGuid by mutableStateOf<String?>(null)

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        if (savedInstanceState == null) sharedGuid = intent.sharedCourtGuid()
        setContent {
            BccpApp(sharedGuid = sharedGuid, onSharedGuidHandled = { sharedGuid = null })
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        intent.sharedCourtGuid()?.let { sharedGuid = it }
    }

    /** A court to open: shared as a link, or tapped in a court notification. */
    private fun Intent.sharedCourtGuid(): String? =
        getStringExtra(CourtNotifications.EXTRA_COURT_GUID)
            ?: if (action == Intent.ACTION_SEND) getStringExtra(Intent.EXTRA_TEXT)?.let(CourtLinks::guidFrom) else null
}
