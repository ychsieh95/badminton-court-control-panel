package io.github.ychsieh95.bccp.core.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import dagger.hilt.android.qualifiers.ApplicationContext
import io.github.ychsieh95.bccp.core.model.User
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.serialization.json.Json
import javax.inject.Inject
import javax.inject.Singleton

data class Session(val token: String? = null, val user: User? = null, val loaded: Boolean = false) {
    val signedIn: Boolean get() = token != null && user != null
}

/**
 * The bearer token and the signed-in user. The token sits in app-private DataStore;
 * the server only keeps its SHA-256 hash.
 */
@Singleton
class SessionStore @Inject constructor(
    @ApplicationContext private val context: Context,
    private val appScope: CoroutineScope,
    private val json: Json,
) {
    private val _session = MutableStateFlow(Session())
    val session: StateFlow<Session> = _session.asStateFlow()

    /** Read synchronously by the OkHttp interceptor. */
    val token: String? get() = _session.value.token

    init {
        appScope.launch {
            val prefs = context.dataStore.data.first()
            val user = prefs[USER]?.let { runCatching { json.decodeFromString(User.serializer(), it) }.getOrNull() }
            val token = prefs[TOKEN]
            _session.value = Session(token = token.takeIf { user != null }, user = user.takeIf { token != null }, loaded = true)
        }
    }

    fun signIn(token: String, user: User) {
        _session.value = Session(token, user, loaded = true)
        appScope.launch {
            context.dataStore.edit {
                it[TOKEN] = token
                it[USER] = json.encodeToString(User.serializer(), user)
            }
        }
    }

    fun updateUser(user: User) {
        if (_session.value.token == null) return
        _session.update { it.copy(user = user) }
        appScope.launch { context.dataStore.edit { it[USER] = json.encodeToString(User.serializer(), user) } }
    }

    /** Called on sign-out, account deletion, or when the server answers `401 invalid_token`. */
    fun clear() {
        _session.value = Session(loaded = true)
        appScope.launch {
            context.dataStore.edit {
                it.remove(TOKEN)
                it.remove(USER)
            }
        }
    }

    private companion object {
        val TOKEN = stringPreferencesKey("api_token")
        val USER = stringPreferencesKey("api_user")
    }
}
