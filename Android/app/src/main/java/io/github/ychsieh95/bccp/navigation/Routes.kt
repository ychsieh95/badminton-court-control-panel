package io.github.ychsieh95.bccp.navigation

import kotlinx.serialization.Serializable

@Serializable data object CourtsRoute
@Serializable data object OrganizeRoute
@Serializable data object AdminRoute
@Serializable data object AccountRoute

@Serializable data class CourtDetailRoute(val guid: String)

/** [guid] edits an existing court; [copyFrom] prefills a new one from another court's form values. */
@Serializable data class CourtFormRoute(val guid: String? = null, val copyFrom: String? = null)

@Serializable data class AuthRoute(val signup: Boolean = false)
@Serializable data object ProfileRoute
@Serializable data object ChangePasswordRoute
@Serializable data object DevicesRoute
@Serializable data object ContactRoute
@Serializable data object SettingsRoute
@Serializable data object AdminCourtsRoute
@Serializable data object AdminUsersRoute
@Serializable data object AdminMessagesRoute

object CourtLinks {
    private val GUID = Regex("[A-Za-z0-9_-]{8,}")

    /** A court page is `<server>/<guid>`; accept that URL, any text containing it, or a bare GUID. */
    fun guidFrom(text: String): String? {
        val candidate = text.trim().split(Regex("\\s+")).firstOrNull { it.contains("://") } ?: text.trim()
        val segment = candidate.substringBefore('?').substringBefore('#').trimEnd('/').substringAfterLast('/')
        return segment.takeIf { GUID.matches(it) }
    }
}
