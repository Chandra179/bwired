/**
 * Individual search result item component
 * @param {Object} props
 * @param {Object} props.result - Search result data
 * @param {string} props.result.title - Result title
 * @param {string} props.result.url - Result URL
 * @param {string} props.result.content - Result content snippet
 * @param {string} props.result.engine - Search engine name
 * @param {number} props.result.score - Relevance score
 */
function SearchItem(props) {
  const result = props.result;
  
  return (
    <article class="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-4 hover:shadow-md transition-shadow duration-200">
      {/* Title with link */}
      <h2 class="text-lg font-semibold mb-2">
        <a 
          href={result.url} 
          target="_blank" 
          rel="noopener noreferrer"
          class="text-blue-600 hover:text-blue-800 hover:underline"
        >
          {result.title}
        </a>
      </h2>
      
      {/* Content snippet */}
      <p class="text-gray-600 text-sm mb-3 line-clamp-3">
        {result.content}
      </p>
      
      {/* Footer with engine badge and score */}
      <div class="flex items-center justify-between text-xs">
        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full bg-blue-100 text-blue-800 font-medium">
          {result.engine}
        </span>
        <span class="text-gray-400">
          Score: {result.score.toFixed(2)}
        </span>
      </div>
    </article>
  );
}

export default SearchItem;
