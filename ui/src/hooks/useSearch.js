import { createSignal, createEffect } from 'solid-js';
import { search, fetchCategories } from '../services/searchApi';

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
  const [hasNext, setHasNext] = createSignal(false);
  const [hasPrevious, setHasPrevious] = createSignal(false);
  const [categoryInfo, setCategoryInfo] = createSignal(null);
  
  // Filter state
  const [selectedCategory, setSelectedCategory] = createSignal('news');
  const [selectedEngines, setSelectedEngines] = createSignal([]);

  // Calculate total pages
  const totalPages = () => Math.ceil(totalResults() / PER_PAGE);

  // Fetch category info on mount
  createEffect(async () => {
    try {
      const data = await fetchCategories();
      if (data.categories && data.categories.news) {
        setCategoryInfo(data.categories.news);
      }
    } catch (err) {
      console.error('Failed to fetch categories:', err);
    }
  });

  /**
   * Perform search for a specific page
   * @param {string} searchQuery - The search query
   * @param {number} targetPage - Page number to fetch
   * @param {Object} filters - Optional filters to override current state
   */
  const performSearch = async (searchQuery, targetPage = 1, filters = null) => {
    if (!searchQuery.trim()) return;

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
      
      setResults(data.results || []);
      setTotalResults(data.number_of_results || 0);
      setHasNext(data.has_next || false);
      setHasPrevious(data.has_previous || false);
      setPage(targetPage);
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
    if (hasNext()) {
      goToPage(page() + 1);
    }
  };

  /**
   * Go to previous page
   */
  const goToPreviousPage = () => {
    if (hasPrevious()) {
      goToPage(page() - 1);
    }
  };

  /**
   * Handle search submission
   * @param {string} newQuery - The new search query
   */
  const handleSearch = (newQuery) => {
    setQuery(newQuery);
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
    
    // Update category info display
    fetchCategories().then((data) => {
      if (data.categories && data.categories[filters.category]) {
        setCategoryInfo(data.categories[filters.category]);
      }
    });
    
    // If there's an active query, re-search with new filters
    if (query()) {
      performSearch(query(), 1, filters);
    }
  };

  /**
   * Clear all filters and reset to defaults
   */
  const clearFilters = () => {
    setSelectedCategory('news');
    setSelectedEngines([]);
    
    // Reset category info to news
    fetchCategories().then((data) => {
      if (data.categories && data.categories.news) {
        setCategoryInfo(data.categories.news);
      }
    });
    
    // If there's an active query, re-search without filters
    if (query()) {
      performSearch(query(), 1, { category: 'news', engines: [] });
    }
  };

  /**
   * Remove a specific engine from the filter
   * @param {string} engineName - Engine to remove
   */
  const removeEngine = (engineName) => {
    const newEngines = selectedEngines().filter((e) => e !== engineName);
    setSelectedEngines(newEngines);
    
    // Re-search with updated filters
    if (query()) {
      performSearch(query(), 1, {
        category: selectedCategory(),
        engines: newEngines,
      });
    }
  };

  /**
   * Remove category filter (reset to news)
   */
  const removeCategory = () => {
    setSelectedCategory('news');
    setSelectedEngines([]);
    
    fetchCategories().then((data) => {
      if (data.categories && data.categories.news) {
        setCategoryInfo(data.categories.news);
      }
    });
    
    if (query()) {
      performSearch(query(), 1, { category: 'news', engines: [] });
    }
  };

  /**
   * Get visible page numbers for pagination
   * Shows pages around current page with ellipsis for gaps
   * @returns {Array} Array of page numbers and ellipsis markers
   */
  const getVisiblePages = () => {
    const current = page();
    const total = totalPages();
    const pages = [];
    
    if (total <= 7) {
      // Show all pages if 7 or fewer
      for (let i = 1; i <= total; i++) {
        pages.push(i);
      }
    } else {
      // Always show first page
      pages.push(1);
      
      if (current > 3) {
        pages.push('...');
      }
      
      // Show pages around current
      const start = Math.max(2, current - 1);
      const end = Math.min(total - 1, current + 1);
      
      for (let i = start; i <= end; i++) {
        if (i !== 1 && i !== total) {
          pages.push(i);
        }
      }
      
      if (current < total - 2) {
        pages.push('...');
      }
      
      // Always show last page
      pages.push(total);
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
    totalResults,
    totalPages,
    hasNext,
    hasPrevious,
    categoryInfo,
    selectedCategory,
    selectedEngines,
    
    // Computed
    getVisiblePages,
    getResultRange,
    
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
