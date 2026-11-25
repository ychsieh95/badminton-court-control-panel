# kotlinx.serialization keeps generated serializers via its bundled rules.
# Retrofit 3 ships its own consumer rules.
-keepattributes Signature, InnerClasses, EnclosingMethod, *Annotation*
-keepclassmembers class io.github.ychsieh95.bccp.feature.auth.TurnstileBridge {
    @android.webkit.JavascriptInterface <methods>;
}
