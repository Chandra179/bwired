import { createSignal, For, Show } from 'solid-js';
import { useSearch } from '../hooks/useSearch';
import SearchItem from './SearchItem';
import SkeletonItem from './SkeletonItem';
import ErrorMessage from './ErrorMessage';
import FilterDropdown from './FilterDropdown';
import ActiveFilters from './ActiveFilters';

/**
 * Pagination component
 */
function Pagination(props) {
  const {
    page,
    hasNext,
    hasPrevious,
    visiblePages,
    onPageChange,
    onNext,
    onPrevious,
    resultsCount
  } = props;

  return (
    <div class="flex flex-col items-center gap-4 py-6">
      {/* Results count */}
      <Show when={resultsCount > 0}>
        <p class="text-sm text-gray-600">
          Showing {resultsCount} results
        </p>
      </Show>

      {/* Page navigation */}
      <div class="flex items-center gap-2">
        {/* Previous button */}
        <button
          onClick={onPrevious}
          disabled={!hasPrevious}
          class={`px-3 py-2 rounded-lg font-medium transition-colors ${hasPrevious
              ? 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 hover:border-gray-400'
              : 'bg-gray-100 border border-gray-200 text-gray-400 cursor-not-allowed'
            }`}
        >
          <span class="flex items-center gap-1">
            <svg class="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M12.79 5.23a.75.75 0 01-.02 1.06L8.832 10l3.938 3.71a.75.75 0 11-1.04 1.08l-4.5-4.25a.75.75 0 010-1.08l4.5-4.25a.75.75 0 011.06.02z" clip-rule="evenodd" />
            </svg>
            Previous
          </span>
        </button>

        {/* Page numbers */}
        <div class="flex items-center gap-1">
          <For each={visiblePages}>
            {(pageNum) => (
              <Show
                when={pageNum !== '...'}
                fallback={
                  <span class="px-3 py-2 text-gray-400">...</span>
                }
              >
                <button
                  onClick={() => onPageChange(pageNum)}
                  class={`min-w-[40px] px-3 py-2 rounded-lg font-medium transition-colors ${page === pageNum
                      ? 'bg-blue-600 text-white'
                      : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 hover:border-gray-400'
                    }`}
                >
                  {pageNum}
                </button>
              </Show>
            )}
          </For>
        </div>

        {/* Next button */}
        <button
          onClick={onNext}
          disabled={!hasNext}
          class={`px-3 py-2 rounded-lg font-medium transition-colors ${hasNext
              ? 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 hover:border-gray-400'
              : 'bg-gray-100 border border-gray-200 text-gray-400 cursor-not-allowed'
            }`}
        >
          <span class="flex items-center gap-1">
            Next
            <svg class="w-4 h-4" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clip-rule="evenodd" />
            </svg>
          </span>
        </button>
      </div>
    </div>
  );
}

/**
 * Main search list component with pagination and filters
 * Features:
 * - Search input for articles
 * - Filter button with category and engine selection
 * - Active filter chips with remove functionality
 * - Pagination with page number buttons
 * - Skeleton loaders during loading
 * - Inline error messages with retry
 * - Category info banner
 */
function SearchList() {
  const [searchInput, setSearchInput] = createSignal('');
  const [isFilterOpen, setIsFilterOpen] = createSignal(false);

  const {
    results,
    page,
    loading,
    error,

    selectedCategory,
    selectedEngines,
    handleSearch,
    goToPage,
    goToNextPage,
    goToPreviousPage,
    retry,
    applyFilters,
    clearFilters,
    removeEngine,
    removeCategory,
    getVisiblePages,
    emptyPageDetected,
  } = useSearch();

  // Handle form submission
  const onSubmit = (e) => {
    e.preventDefault();
    const query = searchInput().trim();
    if (query) {
      handleSearch(query);
    }
  };

  // Handle filter apply
  const onFilterApply = (filters) => {
    applyFilters(filters);
  };

  // Handle filter clear
  const onFilterClear = () => {
    clearFilters();
  };

  // Compute pagination state from results
  const hasNext = () => !emptyPageDetected();
  const hasPrevious = () => page() > 1;

  // Render skeleton items
  const renderSkeletons = () => {
    return Array.from({ length: 3 }, (_, i) => <SkeletonItem />);
  };

  const categoryLabels = {
    news: 'News',
    books: 'Books',
    science: 'Science',
  };

  const getCategoryLabel = () => {
    return selectedCategory() ? categoryLabels[selectedCategory()] : 'General';
  };

  return (
    <div class="min-h-screen bg-gray-50">
      <div class="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <header class="mb-8">
          <h1 class="text-3xl font-bold text-gray-900 mb-2">
            {getCategoryLabel()} Search
          </h1>
          <p class="text-gray-600">
            Search for {selectedCategory() === null
              ? 'content across all sources'
              : selectedCategory() === 'news'
                ? 'news articles and current events'
                : `${selectedCategory()} content`
            }
          </p>
        </header>

        {/* Search Form with Filter Button */}
        <form onSubmit={onSubmit} class="mb-4">
          <div class="flex gap-2">
            <div class="flex-1 relative">
              <input
                type="text"
                value={searchInput()}
                onInput={(e) => setSearchInput(e.target.value)}
                placeholder={selectedCategory() ? `Search ${categoryLabels[selectedCategory()]?.toLowerCase()}...` : 'Search...'}
                class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
                disabled={loading()}
              />
              <Show when={searchInput()}>
                <button
                  type="button"
                  onClick={() => setSearchInput('')}
                  class="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <svg class="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clip-rule="evenodd" />
                  </svg>
                </button>
              </Show>
            </div>

            {/* Filter Button */}
            <div class="relative">
              <button
                type="button"
                onClick={() => setIsFilterOpen(!isFilterOpen())}
                class={`px-4 py-3 border rounded-lg font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-all flex items-center gap-2 ${isFilterOpen() || selectedCategory() !== null
                    ? 'border-blue-500 text-blue-600 bg-blue-50'
                    : 'border-gray-300 text-gray-700 hover:bg-gray-50'
                  }`}
              >
                <svg class="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M3 3a1 1 0 011-1h12a1 1 0 011 1v3a1 1 0 01-.293.707L12 11.414V15a1 1 0 01-.293.707l-2 2A1 1 0 018 17v-5.586L3.293 6.707A1 1 0 013 6V3z" clip-rule="evenodd" />
                </svg>
                <span>Filter</span>
              </button>

              {/* Filter Dropdown */}
              <FilterDropdown
                isOpen={isFilterOpen()}
                onClose={() => setIsFilterOpen(false)}
                selectedCategory={selectedCategory()}
                selectedEngines={selectedEngines()}
                onApply={onFilterApply}
                onClear={onFilterClear}
              />
            </div>

            <button
              type="submit"
              disabled={!searchInput().trim() || loading()}
              class="px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Show
                when={!loading()}
                fallback={
                  <span class="flex items-center gap-2">
                    <svg class="animate-spin h-4 w-4" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Searching...
                  </span>
                }
              >
                Search
              </Show>
            </button>
          </div>
        </form>

        {/* Active Filters */}
        <ActiveFilters
          category={selectedCategory()}
          engines={selectedEngines()}
          onRemoveCategory={removeCategory}
          onRemoveEngine={removeEngine}
          onClearAll={clearFilters}
        />

        {/* Error Message */}
        <Show when={error()}>
          <ErrorMessage message={error()} onRetry={retry} />
        </Show>

        {/* Results List */}
        <div class="space-y-0">
          {/* Loading skeletons */}
          <Show when={loading()}>
            {renderSkeletons()}
          </Show>

          {/* Results */}
          <Show when={!loading()}>
            <For each={results()}>
              {(result) => <SearchItem result={result} />}
            </For>
          </Show>

          {/* Empty state */}
          <Show when={!loading() && results().length === 0 && !error()}>
            <div class="text-center py-12">
              <svg
                class="mx-auto h-12 w-12 text-gray-400 mb-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  stroke-width={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
              <h3 class="text-lg font-medium text-gray-900 mb-1">
                No results yet
              </h3>
              <p class="text-gray-500">
                Enter a search query to find {selectedCategory() === null ? 'content across all sources' : selectedCategory() === 'news' ? 'news articles' : 'content'}
              </p>
            </div>
          </Show>

          {/* Pagination */}
          <Show when={!loading() && results().length > 0}>
            <Pagination
              page={page()}
              hasNext={hasNext()}
              hasPrevious={hasPrevious()}
              visiblePages={getVisiblePages()}
              onPageChange={goToPage}
              onNext={goToNextPage}
              onPrevious={goToPreviousPage}
              resultsCount={results().length}
            />
          </Show>
        </div>
      </div>
    </div>
  );
}

export default SearchList;
