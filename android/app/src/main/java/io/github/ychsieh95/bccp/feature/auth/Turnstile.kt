package io.github.ychsieh95.bccp.feature.auth

import android.annotation.SuppressLint
import android.os.Handler
import android.os.Looper
import android.webkit.JavascriptInterface
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import io.github.ychsieh95.bccp.R
import org.json.JSONObject

/** Receives widget callbacks from JavaScript (on a binder thread). */
class TurnstileBridge(
    private val onToken: (String) -> Unit,
    private val onError: () -> Unit,
    private val onHeight: (Float) -> Unit,
) {
    private val main = Handler(Looper.getMainLooper())
    @JavascriptInterface fun token(value: String) = main.post { onToken(value) }.let { }
    @JavascriptInterface fun error() = main.post { onError() }.let { }
    @JavascriptInterface fun height(cssPx: Float) = main.post { onHeight(cssPx) }.let { }
}

/**
 * Cloudflare Turnstile, rendered from the server's origin so the site key's hostname check
 * passes. [action] must match what the server verifies (`login`, `signup`, `contact_message`).
 * A token is single-use: bump [resetKey] after every submit to get a fresh one.
 */
@SuppressLint("SetJavaScriptEnabled")
@Composable
fun TurnstileWidget(siteKey: String, serverUrl: String, action: String, resetKey: Int, onToken: (String?) -> Unit, modifier: Modifier = Modifier) {
    val currentOnToken by rememberUpdatedState(onToken)
    var failed by remember(resetKey, action) { mutableStateOf(false) }
    // The widget is 65 CSS px tall; the page reports its real size once rendered.
    var height by remember { mutableStateOf(WIDGET_HEIGHT) }
    val dark = MaterialTheme.colorScheme.background.luminance() < 0.5f
    Column(modifier) {
        key(resetKey, action) {
            AndroidView(
                modifier = Modifier.fillMaxWidth().height(height),
                factory = { context ->
                    WebView(context).apply {
                        settings.javaScriptEnabled = true
                        settings.domStorageEnabled = true
                        // Keep the widget at its designed size regardless of the system font scale.
                        settings.textZoom = 100
                        isVerticalScrollBarEnabled = false
                        isHorizontalScrollBarEnabled = false
                        setBackgroundColor(android.graphics.Color.TRANSPARENT)
                        webViewClient = WebViewClient()
                        addJavascriptInterface(
                            TurnstileBridge(
                                onToken = { currentOnToken(it.ifBlank { null }) },
                                onError = { failed = true; currentOnToken(null) },
                                onHeight = { if (it > 0f) height = it.dp },
                            ),
                            "Bridge",
                        )
                        loadDataWithBaseURL("$serverUrl/", page(siteKey, action, dark), "text/html", "utf-8", null)
                    }
                },
                onRelease = { it.destroy() },
            )
        }
        if (failed) Text(stringResource(R.string.verification_failed), color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
    }
}

private fun androidx.compose.ui.graphics.Color.luminance(): Float = 0.2126f * red + 0.7152f * green + 0.0722f * blue

private val WIDGET_HEIGHT = 65.dp

private fun page(siteKey: String, action: String, dark: Boolean): String {
    val key = JSONObject.quote(siteKey)
    val actionJs = JSONObject.quote(action)
    val theme = if (dark) "dark" else "light"
    return """
        <!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
        <style>
          html,body{margin:0;padding:0;background:transparent;overflow:hidden}
          #widget{width:100%;line-height:0;transform-origin:0 0}
          #widget iframe{display:block;max-width:100%}
        </style>
        <script>
          function onTurnstileLoad() {
            turnstile.render('#widget', {
              sitekey: $key, action: $actionJs, theme: '$theme', size: 'flexible',
              callback: function (t) { Bridge.token(t); },
              'expired-callback': function () { Bridge.token(''); },
              'error-callback': function () { Bridge.error(); }
            });
            // The flexible widget is at least 300px wide; scale it down on narrower screens.
            var widget = document.getElementById('widget');
            var fit = function () {
              var w = document.documentElement.clientWidth;
              var s = Math.min(1, w / 300);
              widget.style.width = (w / s) + 'px';
              widget.style.transform = 'scale(' + s + ')';
              Bridge.height(Math.ceil(widget.getBoundingClientRect().height));
            };
            new ResizeObserver(fit).observe(widget);
            window.addEventListener('resize', fit);
          }
        </script>
        <script src="https://challenges.cloudflare.com/turnstile/v0/api.js?onload=onTurnstileLoad&render=explicit" async defer></script>
        </head><body><div id="widget" style="width:100%"></div></body></html>
    """.trimIndent()
}
