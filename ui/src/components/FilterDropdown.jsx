import { createSignal, Show, For } from 'solid-js';

// Hardcoded engine data from searxng/settings.yml
const ENGINES_DATA = {
  news: [
    { name: 'duckduckgo news', bang: 'ddn', description: 'DuckDuckGo News search' },
    { name: 'presearch news', bang: 'psn', description: 'Presearch News search' },
  ],
  books: [
    { name: 'openlibrary', bang: 'ol', description: 'Open Library book search' },
    { name: 'annas archive', bang: 'aa', description: 'Anna\'s Archive book search' },
  ],
  science: [
    { name: 'arxiv', bang: 'arxiv', description: 'arXiv scientific papers' },
    { name: 'google scholar', bang: 'gos', description: 'Google Scholar academic search' },
  ],
  social_media: [
    { name: 'reddit', bang: 're', description: 'Reddit search' },
  ],
};

const CATEGORIES = [
  { id: 'news', label: 'News', icon: '📰' },
  { id: 'books', label: 'Books', icon: '📚' },
  { id: 'science', label: 'Science', icon: '🔬' },
  { id: 'social_media', label: 'Social', icon: '💬' },
];

/**
 * Filter dropdown component for selecting category and engines
 * Features:
 * - Category radio buttons (single select)
 * - Engine checkboxes within each category
 * - Apply and clear buttons
 * - Responsive design
 * 
 * @param {Object} props
 * @param {string} props.selectedCategory - Currently selected category
 * @param {string[]} props.selectedEngines - Currently selected engines
 * @param {Function} props.onApply - Called when filters are applied
 * @param {Function} props.onClear - Called when filters are cleared
 * @param {boolean} props.isOpen - Whether dropdown is open
 * @param {Function} props.onClose - Called when dropdown should close
 */
function FilterDropdown(props) {
  const [localCategory, setLocalCategory] = createSignal(props.selectedCategory || 'news');
  const [localEngines, setLocalEngines] = createSignal([...(props.selectedEngines || [])]);

  // Sync with parent props when they change
  const syncWithProps = () => {
    setLocalCategory(props.selectedCategory || 'news');
    setLocalEngines([...(props.selectedEngines || [])]);
  };

  // Watch for prop changes
  const propChanged = () => props.selectedCategory + props.selectedEngines?.join(',');
  
  // Solid's createEffect equivalent for watching prop changes
  // Using a simple effect pattern
  let prevProps = propChanged();
  const checkProps = () => {
    const current = propChanged();
    if (current !== prevProps) {
      prevProps = current;
      syncWithProps();
    }
  };

  // Check props on each render
  checkProps();

  const handleCategoryChange = (categoryId) => {
    setLocalCategory(categoryId);
    // Clear engines when switching category
    setLocalEngines([]);
  };

  const handleEngineToggle = (engineName) => {
    setLocalEngines((prev) => {
      if (prev.includes(engineName)) {
        return prev.filter((e) => e !== engineName);
      } else {
        return [...prev, engineName];
      }
    });
  };

  const handleApply = () => {
    props.onApply({
      category: localCategory(),
      engines: localEngines(),
    });
    props.onClose();
  };

  const handleClear = () => {
    setLocalCategory('news');
    setLocalEngines([]);
    props.onClear();
    props.onClose();
  };

  const getCurrentEngines = () => {
    return ENGINES_DATA[localCategory()] || [];
  };

  const hasActiveFilters = () => {
    return localCategory() !== 'news' || localEngines().length > 0;
  };

  return (
    <Show when={props.isOpen}>
      <>
        {/* Dropdown */}
        <div class="fixed sm:absolute sm:top-full sm:left-auto sm:right-0 sm:mt-2 bg-white rounded-lg shadow-xl border border-gray-200 z-50 overflow-hidden w-[calc(100vw-2rem)] sm:w-auto sm:min-w-[450px] max-w-[500px] left-4 right-4 top-20 sm:top-auto">
          {/* Header */}
          <div class="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
            <h3 class="font-semibold text-gray-900">Search Filters</h3>
            <button
              onClick={props.onClose}
              class="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg class="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
                <path
                  fill-rule="evenodd"
                  d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                  clip-rule="evenodd"
                />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div class="max-h-[60vh] sm:max-h-[400px] overflow-y-auto">
            {/* Category Section */}
            <div class="p-4 border-b border-gray-100">
              <h4 class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
                Category
              </h4>
              <div class="grid grid-cols-2 gap-3">
                <For each={CATEGORIES}>
                  {(category) => (
                    <label class="flex items-center gap-3 cursor-pointer group p-2 rounded-lg hover:bg-gray-50 transition-colors">
                      <input
                        type="radio"
                        name="category"
                        value={category.id}
                        checked={localCategory() === category.id}
                        onChange={() => handleCategoryChange(category.id)}
                        class="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                      />
                      <div class="flex items-center gap-2">
                        <span class="text-lg">{category.icon}</span>
                        <span class="text-sm font-medium text-gray-900 group-hover:text-blue-600 transition-colors">
                          {category.label}
                        </span>
                      </div>
                    </label>
                  )}
                </For>
              </div>
            </div>

            {/* Engine Section */}
            <div class="p-4">
              <h4 class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
                Search Engines
              </h4>
              <div class="space-y-3">
                <For each={getCurrentEngines()}>
                  {(engine) => (
                    <label class="flex items-start gap-3 cursor-pointer group p-2 rounded-lg hover:bg-gray-50 transition-colors">
                      <input
                        type="checkbox"
                        checked={localEngines().includes(engine.name)}
                        onChange={() => handleEngineToggle(engine.name)}
                        class="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 mt-0.5"
                      />
                      <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2">
                          <span class="text-sm font-medium text-gray-900 group-hover:text-blue-600 transition-colors">
                            {engine.name}
                          </span>
                          <span class="text-xs font-mono text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded flex-shrink-0">
                            !{engine.bang}
                          </span>
                        </div>
                        <div class="text-xs text-gray-500 mt-0.5">{engine.description}</div>
                      </div>
                    </label>
                  )}
                </For>
              </div>

              <Show when={getCurrentEngines().length === 0}>
                <div class="text-sm text-gray-500 text-center py-4">
                  No engines available for this category
                </div>
              </Show>
            </div>
          </div>

          {/* Footer */}
          <div class="px-4 py-3 border-t border-gray-100 bg-gray-50 flex justify-between items-center">
            <button
              onClick={handleClear}
              class={`text-sm font-medium transition-colors ${
                hasActiveFilters()
                  ? 'text-gray-600 hover:text-gray-900'
                  : 'text-gray-400 cursor-not-allowed'
              }`}
              disabled={!hasActiveFilters()}
            >
              Clear all
            </button>
            <button
              onClick={handleApply}
              class="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors"
            >
              Apply Filters
            </button>
          </div>
        </div>

      </>
    </Show>
  );
}

export default FilterDropdown;
