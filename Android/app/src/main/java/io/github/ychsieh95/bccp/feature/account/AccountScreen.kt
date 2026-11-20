package io.github.ychsieh95.bccp.feature.account

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.KeyboardArrowRight
import androidx.compose.material.icons.automirrored.outlined.Logout
import androidx.compose.material.icons.outlined.Devices
import androidx.compose.material.icons.outlined.Lock
import androidx.compose.material.icons.outlined.Mail
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material3.Button
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.ListItem
import androidx.compose.material3.ListItemDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.model.Role
import io.github.ychsieh95.bccp.core.ui.component.PanelCard
import io.github.ychsieh95.bccp.core.ui.component.UserAvatar

@Composable
fun AccountScreen(
    onSignIn: () -> Unit,
    onSignUp: () -> Unit,
    onProfile: () -> Unit,
    onChangePassword: () -> Unit,
    onDevices: () -> Unit,
    onContact: () -> Unit,
    onSettings: () -> Unit,
    viewModel: AccountViewModel = hiltViewModel(),
) {
    val session by viewModel.session.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }
    val context = LocalContext.current
    LaunchedEffect(Unit) { viewModel.messages.collect { snackbar.showSnackbar(it.resolve(context)) } }
    val user = session.user

    Scaffold(
        snackbarHost = { SnackbarHost(snackbar) },
        topBar = { TopAppBar(title = { Text(stringResource(R.string.account)) }) },
    ) { padding ->
        Column(
            Modifier.padding(padding).fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            val width = Modifier.widthIn(max = 840.dp)
            PanelCard(width) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                    UserAvatar(user?.username ?: "?", Modifier.size(56.dp), url = user?.avatarUrl)
                    Column(Modifier.weight(1f)) {
                        Text(user?.username ?: stringResource(R.string.guest), style = MaterialTheme.typography.titleLarge)
                        Text(
                            if (user != null) stringResource(R.string.role_label, roleLabel(user.role)) else stringResource(R.string.guest_body),
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
                if (user == null) {
                    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        Button(onClick = onSignIn, modifier = Modifier.weight(1f)) { Text(stringResource(R.string.sign_in)) }
                        OutlinedButton(onClick = onSignUp, modifier = Modifier.weight(1f)) { Text(stringResource(R.string.sign_up)) }
                    }
                }
            }
            if (user != null) {
                LinkGroup(stringResource(R.string.account), width) {
                    LinkRow(Icons.Outlined.Person, stringResource(R.string.profile), stringResource(R.string.profile_body), onProfile)
                    LinkRow(Icons.Outlined.Lock, stringResource(R.string.change_password), stringResource(R.string.change_password_body), onChangePassword)
                    LinkRow(Icons.Outlined.Devices, stringResource(R.string.signed_in_devices), stringResource(R.string.signed_in_devices_body), onDevices)
                }
            }
            LinkGroup(stringResource(R.string.support), width) {
                LinkRow(Icons.Outlined.Mail, stringResource(R.string.contact_admin), stringResource(R.string.contact_body), onContact)
                LinkRow(Icons.Outlined.Settings, stringResource(R.string.app_settings), stringResource(R.string.preferences), onSettings)
            }
            if (user != null) {
                OutlinedButton(onClick = viewModel::signOut, modifier = width.fillMaxWidth()) {
                    Icon(Icons.AutoMirrored.Outlined.Logout, null, Modifier.padding(end = 8.dp))
                    Text(stringResource(R.string.sign_out))
                }
            }
        }
    }
}

@Composable
fun roleLabel(role: Role): String = stringResource(
    when (role) {
        Role.Member -> R.string.role_member
        Role.SubAdmin -> R.string.role_sub_admin
        Role.Admin -> R.string.role_admin
        Role.SuperAdmin -> R.string.role_super_admin
    },
)

@Composable
fun LinkGroup(title: String, modifier: Modifier = Modifier, content: @Composable () -> Unit) {
    Column(modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            title.uppercase(),
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.primary,
            modifier = Modifier.padding(start = 4.dp).semantics { heading() },
        )
        PanelCard(contentPadding = 0.dp) { content() }
    }
}

@Composable
fun LinkRow(icon: ImageVector, title: String, body: String?, onClick: () -> Unit, trailing: String? = null) {
    ListItem(
        modifier = Modifier.fillMaxWidth().clickable(role = androidx.compose.ui.semantics.Role.Button, onClick = onClick),
        headlineContent = { Text(title) },
        supportingContent = body?.let { { Text(it, maxLines = 2) } },
        leadingContent = { Icon(icon, null, tint = MaterialTheme.colorScheme.primary) },
        trailingContent = {
            Row(verticalAlignment = Alignment.CenterVertically) {
                if (trailing != null) Text(trailing, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.primary)
                Icon(Icons.AutoMirrored.Outlined.KeyboardArrowRight, null)
            }
        },
        colors = ListItemDefaults.colors(containerColor = MaterialTheme.colorScheme.surfaceContainerLowest),
    )
    HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))
}
