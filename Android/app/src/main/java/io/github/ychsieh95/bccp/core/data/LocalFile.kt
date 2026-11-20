package io.github.ychsieh95.bccp.core.data

import android.content.ContentResolver
import android.net.Uri
import android.provider.OpenableColumns
import okhttp3.MediaType
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okio.BufferedSink
import okio.source

/** A file the user picked, streamed from its content URI on upload. */
data class LocalFile(val uri: Uri, val name: String, val mimeType: String, val size: Long) {
    val isVideo: Boolean get() = mimeType.startsWith("video/")

    companion object {
        fun from(resolver: ContentResolver, uri: Uri): LocalFile {
            var name = uri.lastPathSegment ?: "file"
            var size = -1L
            resolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE), null, null, null)?.use { c ->
                if (c.moveToFirst()) {
                    c.getColumnIndex(OpenableColumns.DISPLAY_NAME).takeIf { it >= 0 }?.let { name = c.getString(it) ?: name }
                    c.getColumnIndex(OpenableColumns.SIZE).takeIf { it >= 0 && !c.isNull(it) }?.let { size = c.getLong(it) }
                }
            }
            return LocalFile(uri, name, resolver.getType(uri) ?: "application/octet-stream", size)
        }
    }
}

internal fun LocalFile.toPart(resolver: ContentResolver, field: String): MultipartBody.Part {
    val file = this
    val body = object : RequestBody() {
        override fun contentType(): MediaType? = file.mimeType.toMediaTypeOrNull()
        override fun contentLength(): Long = file.size
        override fun writeTo(sink: BufferedSink) {
            val stream = resolver.openInputStream(file.uri) ?: throw java.io.FileNotFoundException(file.uri.toString())
            stream.source().use { sink.writeAll(it) }
        }
    }
    return MultipartBody.Part.createFormData(field, file.name, body)
}
