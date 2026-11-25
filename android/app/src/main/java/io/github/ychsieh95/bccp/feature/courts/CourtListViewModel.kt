package io.github.ychsieh95.bccp.feature.courts

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.assisted.Assisted
import dagger.assisted.AssistedFactory
import dagger.assisted.AssistedInject
import dagger.hilt.android.lifecycle.HiltViewModel
import io.github.ychsieh95.bccp.core.data.CourtFilters
import io.github.ychsieh95.bccp.core.data.CourtRepository
import io.github.ychsieh95.bccp.core.data.CourtScope
import io.github.ychsieh95.bccp.core.data.SessionStore
import io.github.ychsieh95.bccp.core.model.Court
import io.github.ychsieh95.bccp.core.ui.UiMessage
import io.github.ychsieh95.bccp.core.ui.toUiMessage
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.distinctUntilChangedBy
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class CourtListUiState(
    val scope: CourtScope,
    val courts: List<Court> = emptyList(),
    val total: Int = 0,
    val filters: CourtFilters = CourtFilters(),
    val searchText: String = "",
    val signedIn: Boolean = false,
    val loaded: Boolean = false,
    val refreshing: Boolean = false,
    val loadingMore: Boolean = false,
    val error: UiMessage? = null,
) {
    val canLoadMore: Boolean get() = courts.size < total && !loadingMore
    val needsSignIn: Boolean get() = scope == CourtScope.Mine && !signedIn
}

@HiltViewModel(assistedFactory = CourtListViewModel.Factory::class)
class CourtListViewModel @AssistedInject constructor(
    @Assisted scope: CourtScope,
    private val courts: CourtRepository,
    session: SessionStore,
) : ViewModel() {
    @AssistedFactory
    interface Factory {
        fun create(scope: CourtScope): CourtListViewModel
    }

    private val _uiState = MutableStateFlow(CourtListUiState(scope, signedIn = session.session.value.signedIn))
    val uiState: StateFlow<CourtListUiState> = _uiState.asStateFlow()
    private var loadJob: Job? = null

    init {
        viewModelScope.launch {
            session.session.distinctUntilChangedBy { it.token }.collect { s ->
                _uiState.update { it.copy(signedIn = s.signedIn, courts = if (s.signedIn) it.courts else emptyList()) }
            }
        }
    }

    fun refresh() {
        val state = _uiState.value
        if (state.needsSignIn) return
        loadJob?.cancel()
        _uiState.update { it.copy(refreshing = true, error = null) }
        loadJob = viewModelScope.launch {
            courts.list(state.scope, state.filters, PAGE_SIZE, 0)
                .onSuccess { page -> _uiState.update { it.copy(courts = page.courts, total = page.pagination.total, loaded = true, refreshing = false) } }
                .onFailure { e -> _uiState.update { it.copy(error = e.toUiMessage(), loaded = true, refreshing = false) } }
        }
    }

    fun loadMore() {
        val state = _uiState.value
        if (!state.canLoadMore || state.refreshing) return
        _uiState.update { it.copy(loadingMore = true) }
        viewModelScope.launch {
            courts.list(state.scope, state.filters, PAGE_SIZE, state.courts.size)
                .onSuccess { page ->
                    _uiState.update {
                        it.copy(courts = (it.courts + page.courts).distinctBy(Court::guid), total = page.pagination.total, loadingMore = false)
                    }
                }
                .onFailure { e -> _uiState.update { it.copy(loadingMore = false, error = e.toUiMessage()) } }
        }
    }

    fun onSearchTextChange(text: String) = _uiState.update { it.copy(searchText = text) }

    fun submitSearch() = applyFilters(_uiState.value.filters.copy(query = _uiState.value.searchText))

    fun applyFilters(filters: CourtFilters) {
        _uiState.update { it.copy(filters = filters, searchText = filters.query, courts = emptyList(), loaded = false) }
        refresh()
    }

    private companion object {
        const val PAGE_SIZE = 30
    }
}
