package io.github.ychsieh95.bccp.navigation

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AdminPanelSettings
import androidx.compose.material.icons.automirrored.filled.EventNote
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.SportsTennis
import androidx.compose.material.icons.outlined.AdminPanelSettings
import androidx.compose.material.icons.automirrored.outlined.EventNote
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material.icons.outlined.SportsTennis
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.State
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavDestination.Companion.hasRoute
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.toRoute
import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.data.CourtScope
import io.github.ychsieh95.bccp.core.ui.component.LoadingPane
import io.github.ychsieh95.bccp.core.ui.format.LocalUse12h
import io.github.ychsieh95.bccp.core.ui.theme.BccpTheme
import io.github.ychsieh95.bccp.feature.account.AccountScreen
import io.github.ychsieh95.bccp.feature.account.ChangePasswordScreen
import io.github.ychsieh95.bccp.feature.account.DevicesScreen
import io.github.ychsieh95.bccp.feature.account.ProfileScreen
import io.github.ychsieh95.bccp.feature.admin.AdminHomeScreen
import io.github.ychsieh95.bccp.feature.admin.MessagesScreen
import io.github.ychsieh95.bccp.feature.admin.UsersScreen
import io.github.ychsieh95.bccp.feature.auth.AuthScreen
import io.github.ychsieh95.bccp.feature.contact.ContactScreen
import io.github.ychsieh95.bccp.feature.courtdetail.CourtDetailScreen
import io.github.ychsieh95.bccp.feature.courtform.CourtFormScreen
import io.github.ychsieh95.bccp.feature.courts.CourtListScreen
import io.github.ychsieh95.bccp.feature.settings.SettingsScreen
import kotlin.reflect.KClass

private data class Tab(val route: Any, val routeClass: KClass<*>, val label: Int, val icon: ImageVector, val selectedIcon: ImageVector)

@Composable
fun BccpApp(sharedCourt: CourtDetailRoute?, onSharedCourtHandled: () -> Unit, viewModel: AppViewModel = hiltViewModel()) {
    val settings by viewModel.settings.collectAsStateWithLifecycle()
    val session by viewModel.session.collectAsStateWithLifecycle()

    BccpTheme(themeMode = settings.themeMode, palette = settings.palette) {
        CompositionLocalProvider(LocalUse12h provides (session.user?.timeFormat == "12h")) {
            Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                when {
                    !settings.loaded || !session.loaded -> LoadingPane()
                    // The API refuses everything else until a temporary password is replaced.
                    session.user?.mustChangePassword == true -> ChangePasswordScreen(onBack = null, onDone = {})
                    else -> MainScaffold(
                        isSignedIn = session.signedIn,
                        moderates = session.user?.role?.moderatesCourts == true,
                        sharedCourt = sharedCourt,
                        onSharedCourtHandled = onSharedCourtHandled,
                    )
                }
            }
        }
    }
}

@Composable
private fun MainScaffold(isSignedIn: Boolean, moderates: Boolean, sharedCourt: CourtDetailRoute?, onSharedCourtHandled: () -> Unit) {
    val nav = rememberNavController()
    val tabs = buildList {
        add(Tab(CourtsRoute, CourtsRoute::class, R.string.nav_courts, Icons.Outlined.SportsTennis, Icons.Filled.SportsTennis))
        add(Tab(OrganizeRoute, OrganizeRoute::class, R.string.nav_organize, Icons.AutoMirrored.Outlined.EventNote, Icons.AutoMirrored.Filled.EventNote))
        if (moderates) add(Tab(AdminRoute, AdminRoute::class, R.string.nav_admin, Icons.Outlined.AdminPanelSettings, Icons.Filled.AdminPanelSettings))
        add(Tab(AccountRoute, AccountRoute::class, R.string.nav_account, Icons.Outlined.Person, Icons.Filled.Person))
    }
    val backStack by nav.currentBackStackEntryAsState()
    val destination = backStack?.destination
    val onTab = tabs.any { tab -> destination?.hierarchy?.any { it.hasRoute(tab.routeClass) } == true }

    LaunchedEffect(sharedCourt) {
        if (sharedCourt != null) {
            nav.navigate(sharedCourt)
            onSharedCourtHandled()
        }
    }

    Scaffold(
        bottomBar = {
            if (onTab) {
                NavigationBar {
                    tabs.forEach { tab ->
                        val selected = destination?.hierarchy?.any { it.hasRoute(tab.routeClass) } == true
                        NavigationBarItem(
                            selected = selected,
                            onClick = { nav.switchTab(tab.route) },
                            icon = { Icon(if (selected) tab.selectedIcon else tab.icon, null) },
                            label = { Text(stringResource(tab.label)) },
                        )
                    }
                }
            }
        },
    ) { padding ->
        val signedIn = rememberUpdatedState(isSignedIn)
        Box(Modifier.padding(bottom = padding.calculateBottomPadding())) {
            AppNavHost(nav, signedIn)
        }
    }
}

private fun NavHostController.switchTab(route: Any) = navigate(route) {
    popUpTo(graph.findStartDestination().id) { saveState = true }
    launchSingleTop = true
    restoreState = true
}

@Composable
/**
 * [signedIn] is a State, not a value: a graph builder that captures a changing value is
 * rebuilt on sign-in/out, and a rebuilt graph resets the back stack to the start tab.
 */
private fun AppNavHost(nav: NavHostController, signedIn: State<Boolean>) {
    val openCourt: (String) -> Unit = { nav.navigate(CourtDetailRoute(it)) }
    val newCourt: () -> Unit = { nav.navigate(if (signedIn.value) CourtFormRoute() else AuthRoute()) }
    val back: () -> Unit = { nav.popBackStack() }

    NavHost(nav, startDestination = CourtsRoute) {
        composable<CourtsRoute> {
            CourtListScreen(
                scope = CourtScope.Public,
                onOpenCourt = openCourt,
                onNewCourt = newCourt,
                onBack = null,
                onSignIn = { nav.navigate(AuthRoute()) },
            )
        }
        composable<OrganizeRoute> {
            CourtListScreen(
                scope = CourtScope.Mine,
                onOpenCourt = openCourt,
                onNewCourt = newCourt,
                onBack = null,
                onSignIn = { nav.navigate(AuthRoute()) },
            )
        }
        composable<AdminRoute> {
            AdminHomeScreen(
                onCourts = { nav.navigate(AdminCourtsRoute) },
                onUsers = { nav.navigate(AdminUsersRoute) },
                onMessages = { nav.navigate(AdminMessagesRoute) },
            )
        }
        composable<AccountRoute> {
            AccountScreen(
                onSignIn = { nav.navigate(AuthRoute()) },
                onSignUp = { nav.navigate(AuthRoute(signup = true)) },
                onProfile = { nav.navigate(ProfileRoute) },
                onChangePassword = { nav.navigate(ChangePasswordRoute) },
                onDevices = { nav.navigate(DevicesRoute) },
                onContact = { nav.navigate(ContactRoute) },
                onSettings = { nav.navigate(SettingsRoute) },
            )
        }
        composable<CourtDetailRoute> { entry ->
            CourtDetailScreen(
                showMessages = entry.toRoute<CourtDetailRoute>().showMessages,
                onBack = back,
                onEdit = { guid -> nav.navigate(CourtFormRoute(guid = guid)) },
                onDuplicate = { guid -> nav.navigate(CourtFormRoute(copyFrom = guid)) },
            )
        }
        composable<CourtFormRoute> {
            CourtFormScreen(
                onBack = back,
                onSaved = { guid, created ->
                    if (created) {
                        nav.navigate(CourtDetailRoute(guid)) { popUpTo<CourtFormRoute> { inclusive = true } }
                    } else {
                        nav.popBackStack()
                    }
                },
            )
        }
        composable<AuthRoute> { entry ->
            AuthScreen(startWithSignup = entry.toRoute<AuthRoute>().signup, onBack = back, onSignedIn = back)
        }
        composable<ProfileRoute> { ProfileScreen(onBack = back, onAccountDeleted = back) }
        composable<ChangePasswordRoute> { ChangePasswordScreen(onBack = back, onDone = back) }
        composable<DevicesRoute> { DevicesScreen(onBack = back) }
        composable<ContactRoute> { ContactScreen(onBack = back) }
        composable<SettingsRoute> { SettingsScreen(onBack = back) }
        composable<AdminCourtsRoute> {
            CourtListScreen(
                scope = CourtScope.Admin,
                onOpenCourt = openCourt,
                onNewCourt = newCourt,
                onBack = back,
                onSignIn = { nav.navigate(AuthRoute()) },
            )
        }
        composable<AdminUsersRoute> { UsersScreen(onBack = back) }
        composable<AdminMessagesRoute> { MessagesScreen(onBack = back) }
    }
}
