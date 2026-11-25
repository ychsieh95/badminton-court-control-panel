package io.github.ychsieh95.bccp.feature.courtdetail

import android.app.DownloadManager
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.widget.Toast
import androidx.core.content.getSystemService
import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.model.Court
import io.github.ychsieh95.bccp.core.model.CourtMedia

internal object CourtIntents {
    fun share(context: Context, court: Court) {
        val send = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_SUBJECT, court.title)
            putExtra(Intent.EXTRA_TEXT, "${court.title}\n${court.webUrl}")
        }
        context.startActivity(Intent.createChooser(send, context.getString(R.string.share_court)))
    }

    fun copyLink(context: Context, court: Court) {
        context.getSystemService<ClipboardManager>()?.setPrimaryClip(ClipData.newPlainText(court.title, court.webUrl))
        // Android 13+ shows its own clipboard confirmation.
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) {
            Toast.makeText(context, R.string.link_copied, Toast.LENGTH_SHORT).show()
        }
    }

    fun openUrl(context: Context, url: String, mimeType: String? = null) {
        val intent = Intent(Intent.ACTION_VIEW).apply {
            if (mimeType != null) setDataAndType(Uri.parse(url), mimeType) else data = Uri.parse(url)
        }
        runCatching { context.startActivity(intent) }
    }

    fun openMaps(context: Context, court: Court) {
        val query = Uri.encode(listOf(court.hallName, court.location).filter(String::isNotBlank).joinToString(" "))
        val url = buildString {
            append("https://www.google.com/maps/search/?api=1&query=")
            if (court.latitude != null && court.longitude != null) append("${court.latitude},${court.longitude}") else append(query)
            if (court.googlePlaceId.isNotBlank()) append("&query_place_id=").append(Uri.encode(court.googlePlaceId))
        }
        openUrl(context, url)
    }

    fun openMedia(context: Context, media: CourtMedia) = openUrl(context, media.url, media.mimeType.ifBlank { null })

    /** Saves the server-rendered share thumbnail to Downloads (no storage permission needed on 10+). */
    fun downloadThumbnail(context: Context, court: Court) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q) {
            openUrl(context, court.thumbnailUrl)
            return
        }
        val name = "${court.courtDate}_${court.startTime.replace(":", "")}_${court.title}"
            .replace(Regex("[\\\\/:*?\"<>|\\p{Cntrl}]+"), "_").take(100) + ".jpg"
        val request = DownloadManager.Request(Uri.parse(court.thumbnailUrl))
            .setTitle(name)
            .setMimeType("image/jpeg")
            .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
            .setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, name)
        context.getSystemService<DownloadManager>()?.enqueue(request)
        Toast.makeText(context, R.string.thumbnail_downloading, Toast.LENGTH_SHORT).show()
    }
}
