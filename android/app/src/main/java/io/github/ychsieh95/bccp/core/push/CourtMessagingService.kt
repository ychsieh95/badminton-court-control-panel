package io.github.ychsieh95.bccp.core.push

import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import dagger.hilt.android.AndroidEntryPoint
import io.github.ychsieh95.bccp.core.data.PushRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.launch
import javax.inject.Inject

@AndroidEntryPoint
class CourtMessagingService : FirebaseMessagingService() {
    @Inject lateinit var push: PushRepository
    @Inject lateinit var appScope: CoroutineScope

    override fun onRegistered(token: String) {
        appScope.launch { push.onTokenRegistered(token) }
    }

    override fun onUnregistered(token: String) {
        appScope.launch { push.onTokenUnregistered() }
    }

    override fun onMessageReceived(message: RemoteMessage) {
        CourtNotifications.show(applicationContext, message.data)
    }
}
