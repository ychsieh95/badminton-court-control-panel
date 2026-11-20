package io.github.ychsieh95.bccp.feature.courts

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.outlined.Add
import androidx.compose.material.icons.outlined.FilterList
import androidx.compose.material.icons.outlined.Link
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Badge
import androidx.compose.material3.BadgedBox
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExtendedFloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.nestedscroll.nestedScroll
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import io.github.ychsieh95.bccp.R
import io.github.ychsieh95.bccp.core.data.CourtFilters
import io.github.ychsieh95.bccp.core.data.CourtScope
import io.github.ychsieh95.bccp.core.ui.component.CourtCard
import io.github.ychsieh95.bccp.core.ui.component.ErrorPane
import io.github.ychsieh95.bccp.core.ui.component.LoadingPane
import io.github.ychsieh95.bccp.core.ui.component.MessagePane
import io.github.ychsieh95.bccp.core.ui.text
import io.github.ychsieh95.bccp.navigation.CourtLinks

@Composable
fun CourtListScreen(
    scope: CourtScope,
    onOpenCourt: (String) -> Unit,
    onNewCourt: () -> Unit,
    onBack: (() -> Unit)?,
    onSignIn: () -> Unit,
) {
    val viewModel = hiltViewModel<CourtListViewModel, CourtListViewModel.Factory>(key = scope.name) { it.create(scope) }
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    // Reload on every return so edits, joins, and deletes made elsewhere show up.
    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) { viewModel.refresh() }

    CourtListContent(
        state = state,
        onOpenCourt = onOpenCourt,
        onNewCourt = onNewCourt,
        onBack = onBack,
        onSignIn = onSignIn,
        onRefresh = viewModel::refresh,
        onLoadMore = viewModel::loadMore,
        onSearchTextChange = viewModel::onSearchTextChange,
        onSubmitSearch = viewModel::submitSearch,
        onApplyFilters = viewModel::applyFilters,
    )
}

@Composable
private fun CourtListContent(
    state: CourtListUiState,
    onOpenCourt: (String) -> Unit,
    onNewCourt: () -> Unit,
    onBack: (() -> Unit)?,
    onSignIn: () -> Unit,
    onRefresh: () -> Unit,
    onLoadMore: () -> Unit,
    onSearchTextChange: (String) -> Unit,
    onSubmitSearch: () -> Unit,
    onApplyFilters: (CourtFilters) -> Unit,
) {
    var showFilters by rememberSaveable { mutableStateOf(false) }
    var showLinkDialog by rememberSaveable { mutableStateOf(false) }
    val scrollBehavior = TopAppBarDefaults.pinnedScrollBehavior()
    val filterable = state.scope != CourtScope.Mine
    val title = stringResource(
        when (state.scope) {
            CourtScope.Public -> R.string.all_courts
            CourtScope.Mine -> R.string.my_courts
            CourtScope.Admin -> R.string.admin_courts
        },
    )

    Scaffold(
        modifier = Modifier.nestedScroll(scrollBehavior.nestedScrollConnection),
        topBar = {
            TopAppBar(
                title = { Text(title) },
                scrollBehavior = scrollBehavior,
                navigationIcon = {
                    if (onBack != null) IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, stringResource(R.string.back)) }
                },
                actions = {
                    if (state.scope == CourtScope.Public) {
                        IconButton(onClick = { showLinkDialog = true }) { Icon(Icons.Outlined.Link, stringResource(R.string.court_link_label)) }
                    }
                    if (filterable) {
                        IconButton(onClick = { showFilters = true }) {
                            BadgedBox(badge = { if (state.filters.activeCount > 0) Badge { Text("${state.filters.activeCount}") } }) {
                                Icon(Icons.Outlined.FilterList, stringResource(R.string.filters))
                            }
                        }
                    }
                },
            )
        },
        floatingActionButton = {
            val showFab = (state.scope == CourtScope.Mine && state.signedIn) || (state.scope == CourtScope.Public && state.signedIn)
            if (showFab) {
                ExtendedFloatingActionButton(
                    onClick = onNewCourt,
                    icon = { Icon(Icons.Outlined.Add, null) },
                    text = { Text(stringResource(R.string.new_court)) },
                )
            }
        },
    ) { padding ->
        Box(Modifier.padding(padding).fillMaxSize()) {
            when {
                state.needsSignIn -> MessagePane(
                    title = stringResource(R.string.sign_in_to_organize),
                    body = stringResource(R.string.sign_in_to_organize_body),
                    action = { Button(onClick = onSignIn) { Text(stringResource(R.string.sign_in)) } },
                )
                !state.loaded && state.error == null -> LoadingPane()
                state.courts.isEmpty() && state.error != null -> ErrorPane(state.error.text(), onRefresh)
                else -> PullToRefreshBox(isRefreshing = state.refreshing && state.loaded, onRefresh = onRefresh) {
                    CourtLazyList(state, onOpenCourt, onNewCourt, onLoadMore, onSearchTextChange, onSubmitSearch, filterable)
                }
            }
        }
    }

    if (showFilters) {
        CourtFilterSheet(state.scope, state.filters, onApply = { onApplyFilters(it); showFilters = false }, onDismiss = { showFilters = false })
    }
    if (showLinkDialog) {
        OpenLinkDialog(onOpen = { onOpenCourt(it); showLinkDialog = false }, onDismiss = { showLinkDialog = false })
    }
}

@Composable
private fun CourtLazyList(
    state: CourtListUiState,
    onOpenCourt: (String) -> Unit,
    onNewCourt: () -> Unit,
    onLoadMore: () -> Unit,
    onSearchTextChange: (String) -> Unit,
    onSubmitSearch: () -> Unit,
    searchable: Boolean,
) {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(start = 16.dp, end = 16.dp, top = 8.dp, bottom = 96.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        item(key = "header") { ListHeader(state.scope) }
        if (searchable) {
            item(key = "search") {
                OutlinedTextField(
                    value = state.searchText,
                    onValueChange = onSearchTextChange,
                    leadingIcon = { Icon(Icons.Outlined.Search, null) },
                    placeholder = { Text(stringResource(R.string.filter_search), maxLines = 1) },
                    singleLine = true,
                    shape = MaterialTheme.shapes.extraLarge,
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
                    keyboardActions = KeyboardActions(onSearch = { onSubmitSearch() }),
                    modifier = Modifier.fillMaxWidth().widthIn(max = 840.dp),
                )
            }
        }
        if (state.courts.isEmpty()) {
            item(key = "empty") {
                val filtered = state.filters.activeCount > 0
                MessagePane(
                    title = stringResource(
                        when {
                            filtered -> R.string.no_results_filtered
                            state.scope == CourtScope.Mine -> R.string.empty_my_courts
                            else -> R.string.no_courts
                        },
                    ),
                    body = if (filtered) null else stringResource(if (state.scope == CourtScope.Mine) R.string.empty_my_courts_body else R.string.no_courts_body),
                    action = if (state.scope == CourtScope.Mine) {
                        { Button(onClick = onNewCourt) { Text(stringResource(R.string.new_court)) } }
                    } else null,
                    modifier = Modifier.padding(top = 32.dp),
                )
            }
        }
        items(state.courts, key = { it.guid }) { court ->
            CourtCard(court, onClick = { onOpenCourt(court.guid) }, modifier = Modifier.widthIn(max = 840.dp))
        }
        if (state.courts.size < state.total) {
            item(key = "more") {
                if (state.loadingMore) {
                    CircularProgressIndicator(Modifier.padding(16.dp))
                } else {
                    OutlinedButton(onClick = onLoadMore) { Text(stringResource(R.string.load_more)) }
                }
            }
        }
    }
}

@Composable
private fun ListHeader(scope: CourtScope) {
    val (eyebrow, title, body) = when (scope) {
        CourtScope.Public -> Triple(R.string.hero_eyebrow, R.string.hero_title, R.string.hero_body)
        CourtScope.Mine -> Triple(R.string.dashboard, R.string.my_courts_title, R.string.my_courts_body)
        CourtScope.Admin -> Triple(R.string.admin_console, R.string.dashboard_title, R.string.admin_courts_body)
    }
    Column(Modifier.fillMaxWidth().widthIn(max = 840.dp).padding(top = 8.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(stringResource(eyebrow).uppercase(), style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary)
        Text(stringResource(title), style = MaterialTheme.typography.headlineMedium)
        Text(stringResource(body), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun OpenLinkDialog(onOpen: (String) -> Unit, onDismiss: () -> Unit) {
    var text by rememberSaveable { mutableStateOf("") }
    val guid = CourtLinks.guidFrom(text)
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(stringResource(R.string.court_link_label)) },
        text = {
            OutlinedTextField(
                value = text,
                onValueChange = { text = it },
                singleLine = true,
                placeholder = { Text("https://…/<guid>") },
                modifier = Modifier.fillMaxWidth(),
            )
        },
        confirmButton = { TextButton(onClick = { guid?.let(onOpen) }, enabled = guid != null) { Text(stringResource(R.string.view_court)) } },
        dismissButton = { TextButton(onClick = onDismiss) { Text(stringResource(R.string.cancel)) } },
    )
}
