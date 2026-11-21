package io.github.ychsieh95.bccp.core.push

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import io.github.ychsieh95.bccp.MainActivity
import io.github.ychsieh95.bccp.R
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow

/** Builds the court-change notifications the server sends as FCM data messages. */
object CourtNotifications {
    const val CHANNEL_ID = "court_updates"
    const val EXTRA_COURT_GUID = "io.github.ychsieh95.bccp.extra.COURT_GUID"
    const val EXTRA_SHOW_MESSAGES = "io.github.ychsieh95.bccp.extra.SHOW_MESSAGES"

    private val _received = MutableSharedFlow<String>(extraBufferCapacity = 16)

    /** GUIDs of courts a push just reported a change for, so an open court screen can reload. */
    val received: SharedFlow<String> = _received.asSharedFlow()

    fun createChannel(context: Context) {
        val channel = NotificationChannel(
            CHANNEL_ID,
            context.getString(R.string.notification_channel_courts),
            NotificationManager.IMPORTANCE_DEFAULT,
        ).apply { description = context.getString(R.string.notification_channel_courts_body) }
        context.getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
    }

    /** True when the app may post notifications (permission granted and not blocked). */
    fun canPost(context: Context): Boolean {
        val permitted = Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
            ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
        return permitted && NotificationManagerCompat.from(context).areNotificationsEnabled()
    }

    fun show(context: Context, data: Map<String, String>) {
        if (data["type"] != "court_changed") return
        val guid = data["guid"]?.takeIf { it.isNotBlank() } ?: return
        val title = data["title"].orEmpty()
        val body = data["body"].orEmpty()
        _received.tryEmit(guid)
        if (!canPost(context)) return

        // New messages and replies open the court at its message board.
        val messages = data["change"] == "message" || data["change"] == "reply"
        val tag = if (messages) "court-$guid-messages" else "court-$guid"
        val open = Intent(context, MainActivity::class.java)
            .putExtra(EXTRA_COURT_GUID, guid)
            .putExtra(EXTRA_SHOW_MESSAGES, messages)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP)
        val contentIntent = PendingIntent.getActivity(
            context,
            tag.hashCode(),
            open,
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_notification)
            .setColor(ContextCompat.getColor(context, R.color.notification_accent))
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setContentIntent(contentIntent)
            .setAutoCancel(true)
            .setCategory(NotificationCompat.CATEGORY_EVENT)
            .build()
        try {
            // One notification per court (and one for its board); a newer one replaces the older.
            NotificationManagerCompat.from(context).notify(tag, 0, notification)
        } catch (_: SecurityException) {
            // Permission revoked between the check and the post.
        }
    }
}
