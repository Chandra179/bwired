import { Show } from 'solid-js';

/**
 * Active filters component displaying selected category as removable chip
 * 
 * @param {Object} props
 * @param {string} props.category - Selected category
 * @param {string[]} props.engines - Selected engines (kept for compatibility)
 * @param {Function} props.onRemoveCategory - Called when category chip is removed
 * @param {Function} props.onRemoveEngine - Called when an engine chip is removed (kept for compatibility)
 * @param {Function} props.onClearAll - Called when "Clear all" is clicked
 */
function ActiveFilters(props) {
  const categoryLabels = {
    news: 'News',
    books: 'Books',
    science: 'Science',
    social_media: 'Social Media',
  };

  const categoryIcons = {
    news: '📰',
    books: '📚',
    science: '🔬',
    social_media: '💬',
  };

  const hasActiveFilters = () => {
    // Show filters whenever a category is selected (including news)
    return !!props.category;
  };

  return (
    <Show when={hasActiveFilters()}>
      <div class="flex flex-wrap items-center gap-2 mb-4">
        {/* Category chip - show for all categories */}
        <div class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
          <span>{categoryIcons[props.category] || '📁'}</span>
          <span>{categoryLabels[props.category] || props.category}</span>
          <button
            onClick={props.onRemoveCategory}
            class="ml-1 hover:bg-blue-200 rounded-full p-0.5 transition-colors"
            aria-label="Remove category filter"
          >
            <svg class="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor">
              <path
                fill-rule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clip-rule="evenodd"
              />
            </svg>
          </button>
        </div>

        {/* Clear all button */}
        <button
          onClick={props.onClearAll}
          class="text-sm text-gray-500 hover:text-gray-700 underline ml-2"
        >
          Clear all
        </button>
      </div>
    </Show>
  );
}

export default ActiveFilters;
