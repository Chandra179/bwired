import { createSignal } from 'solid-js';
import { search } from '../services/searchApi';

const PER_PAGE = 10;

/**
 * Custom hook for paginated search with filter support
 * @returns {Object} Search state and handlers
 */
export function useSearch() {
  const [query, setQuery] = createSignal('');
  const [results, setResults] = createSignal([]);
  const [page, setPage] = createSignal(1);
  const [loading, setLoading] = createSignal(false);
  const [error, setError] = createSignal(null);
  const [totalResults, setTotalResults] = createSignal(0);
  // Pagination computed from results, not API response
  const [emptyPageDetected, setEmptyPageDetected] = createSignal(false);
  const [lastScrollPosition, setLastScrollPosition] = createSignal(0);

  // Filter state - null means general search (no category filter)
  const [selectedCategory, setSelectedCategory] = createSignal(null);
  const [selectedEngines, setSelectedEngines] = createSignal([]);

  // Calculate total pages (this is now just for display, not logic)
  const totalPages = () => Math.ceil(totalResults() / PER_PAGE) || 1;

  /**
   * Perform search for a specific page
   * @param {string} searchQuery - The search query
   * @param {number} targetPage - Page number to fetch
   * @param {Object} filters - Optional filters to override current state
   */
  const performSearch = async (searchQuery, targetPage = 1, filters = null) => {
    if (!searchQuery.trim()) return;

    // Save current scroll position before loading
    setLastScrollPosition(window.scrollY);

    // Use provided filters or current state
    const category = filters?.category ?? selectedCategory();
    const engines = filters?.engines ?? selectedEngines();

    setLoading(true);
    setError(null);

    try {
      const data = await search(
        searchQuery,
        { category, engines },
        targetPage,
        PER_PAGE
      );

      const newResults = data.results || [];
      setResults(newResults);
      setTotalResults(data.number_of_results || 0);
      setPage(targetPage);

      // Detect empty page - this means no next page available
      if (newResults.length === 0) {
        setEmptyPageDetected(true);
      } else {
        // Reset empty page detection if we got results
        setEmptyPageDetected(false);
      }

      // Restore scroll position after a short delay to ensure DOM is updated
      setTimeout(() => {
        window.scrollTo(0, lastScrollPosition());
      }, 0);
    } catch (err) {
      setError(err.message || 'Failed to fetch results');
    } finally {
      setLoading(false);
    }
  };

  /**
   * Navigate to a specific page
   * @param {number} targetPage - Page number to navigate to
   */
  const goToPage = (targetPage) => {
    const newPage = Math.max(1, targetPage);
    if (newPage !== page() && query()) {
      performSearch(query(), newPage);
    }
  };

  /**
   * Go to next page
   */
  const goToNextPage = () => {
    goToPage(page() + 1);
  };

  /**
   * Go to previous page
   */
  const goToPreviousPage = () => {
    if (page() > 1) {
      goToPage(page() - 1);
    }
  };

  /**
   * Handle search submission
   * @param {string} newQuery - The new search query
   */
  const handleSearch = (newQuery) => {
    setQuery(newQuery);
    setEmptyPageDetected(false);
    performSearch(newQuery, 1);
  };

  /**
   * Retry the last failed request
   */
  const retry = () => {
    setError(null);
    performSearch(query(), page());
  };

  /**
   * Apply new filters and trigger a search
   * @param {Object} filters - Filter values { category, engines }
   */
  const applyFilters = (filters) => {
    setSelectedCategory(filters.category);
    setSelectedEngines(filters.engines);
    setEmptyPageDetected(false);

    // If there's an active query, re-search with new filters
    if (query()) {
      performSearch(query(), 1, filters);
    }
  };

  /**
   * Clear all filters and reset to defaults (general search)
   */
  const clearFilters = () => {
    setSelectedCategory(null);
    setSelectedEngines([]);
    setEmptyPageDetected(false);

    // Clear results and reset state without fetching
    setResults([]);
    setQuery('');
    setPage(1);
    setTotalResults(0);
    setError(null);
  };

  /**
   * Remove a specific engine from the filter
   * @param {string} engineName - Engine to remove
   */
  const removeEngine = (engineName) => {
    const newEngines = selectedEngines().filter((e) => e !== engineName);
    setSelectedEngines(newEngines);
    setEmptyPageDetected(false);

    // Clear results and reset state without fetching
    setResults([]);
    setQuery('');
    setPage(1);
    setTotalResults(0);
    setError(null);
  };

  /**
   * Remove category filter (reset to general search)
   */
  const removeCategory = () => {
    setSelectedCategory(null);
    setSelectedEngines([]);
    setEmptyPageDetected(false);

    // Clear results and reset state without fetching
    setResults([]);
    setQuery('');
    setPage(1);
    setTotalResults(0);
    setError(null);
  };

  /**
   * Get visible page numbers for pagination
   * Shows exactly 3 pages as a sliding window
   * Pages 1-3: show 1, 2, 3
   * Page 4+: slide window showing current-1, current, current+1
   * @returns {Array} Array of page numbers (always 3 pages)
   */
  const getVisiblePages = () => {
    const current = page();
    const pages = [];

    if (current <= 2) {
      // Pages 1-2: show 1, 2, 3
      pages.push(1, 2, 3);
    } else {
      // Page 3+: show sliding window (current-1, current, current+1)
      pages.push(current - 1, current, current + 1);
    }

    return pages;
  };

  /**
   * Calculate result range for display
   * @returns {Object} { start, end } result indices
   */
  const getResultRange = () => {
    const start = (page() - 1) * PER_PAGE + 1;
    const end = Math.min(page() * PER_PAGE, totalResults());
    return { start, end };
  };

  return {
    // State
    query,
    results,
    page,
    loading,
    error,
    selectedCategory,
    selectedEngines,
    emptyPageDetected,

    // Computed
    getVisiblePages,

    // Actions
    handleSearch,
    goToPage,
    goToNextPage,
    goToPreviousPage,
    retry,
    applyFilters,
    clearFilters,
    removeEngine,
    removeCategory,
  };
}
