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

/** Builds the court-change notifications the server sends as FCM data messages. */
object CourtNotifications {
    const val CHANNEL_ID = "court_updates"
    const val EXTRA_COURT_GUID = "io.github.ychsieh95.bccp.extra.COURT_GUID"

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
        if (!canPost(context)) return

        val open = Intent(context, MainActivity::class.java)
            .putExtra(EXTRA_COURT_GUID, guid)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP)
        val contentIntent = PendingIntent.getActivity(
            context,
            guid.hashCode(),
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
            // One notification per court; a newer change replaces the older one.
            NotificationManagerCompat.from(context).notify("court-$guid", 0, notification)
        } catch (_: SecurityException) {
            // Permission revoked between the check and the post.
        }
    }
}
