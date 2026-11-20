package io.github.ychsieh95.bccp.core.ui

import android.content.Context
import androidx.annotation.StringRes
import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext
import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.data.DataError

/** Text a ViewModel hands to the UI without holding a Context. */
sealed interface UiMessage {
    data class Res(@StringRes val id: Int, val args: List<Any> = emptyList()) : UiMessage
    data class Text(val text: String) : UiMessage

    fun resolve(context: Context): String = when (this) {
        is Res -> context.getString(id, *args.toTypedArray())
        is Text -> text
    }
}

@Composable
fun UiMessage.text(): String = resolve(LocalContext.current)

fun Throwable.toUiMessage(): UiMessage = when (this) {
    is DataError.Api -> UiMessage.Text(message.orEmpty())
    is DataError.Network -> UiMessage.Res(R.string.error_network)
    else -> UiMessage.Res(R.string.error_unexpected)
}

val Throwable.fieldErrors: Map<String, String> get() = (this as? DataError.Api)?.fields.orEmpty()
