/**
 * Inline error message component with retry button
 * @param {Object} props
 * @param {string} props.message - Error message to display
 * @param {Function} props.onRetry - Callback when retry button is clicked
 */
function ErrorMessage(props) {
  return (
    <div class="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
      <div class="flex items-start gap-3">
        <div class="flex-shrink-0">
          <svg 
            class="h-5 w-5 text-red-400" 
            viewBox="0 0 20 20" 
            fill="currentColor"
          >
            <path 
              fill-rule="evenodd" 
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" 
              clip-rule="evenodd" 
            />
          </svg>
        </div>
        <div class="flex-1">
          <h3 class="text-sm font-medium text-red-800">
            Error loading results
          </h3>
          <p class="mt-1 text-sm text-red-700">
            {props.message}
          </p>
        </div>
        <button
          onClick={props.onRetry}
          class="flex-shrink-0 rounded-md bg-red-50 px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
        >
          Retry
        </button>
      </div>
    </div>
  );
}

export default ErrorMessage;
