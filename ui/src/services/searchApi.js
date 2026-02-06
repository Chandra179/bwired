const API_BASE_URL = 'http://localhost:8000';

/**
 * Search with optional filters
 * @param {string} query - Search query
 * @param {Object} filters - Search filters
 * @param {string} filters.category - Category to search (books, science, social_media, news)
 * @param {string[]} filters.engines - List of engines to use
 * @param {number} page - Page number (1-based)
 * @param {number} perPage - Results per page
 * @returns {Promise<Object>} Search response with results and metadata
 */
export async function search(query, filters = {}, page = 1, perPage = 10) {
  const requestBody = {
    query,
    page,
    per_page: perPage,
  };

  // Add optional filters
  if (filters.category) {
    requestBody.category = filters.category;
  }
  if (filters.engines && filters.engines.length > 0) {
    requestBody.engines = filters.engines;
  }

  const response = await fetch(`${API_BASE_URL}/search`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP error! status: ${response.status}`);
  }

  return response.json();
}

/**
 * Search for news articles (backward compatible)
 * @param {string} query - Search query
 * @param {number} page - Page number (1-based)
 * @param {number} perPage - Results per page
 * @returns {Promise<Object>} Search response with results and metadata
 */
export async function searchNews(query, page = 1, perPage = 10) {
  return search(query, { category: 'news' }, page, perPage);
}

/**
 * Fetch available search categories
 * @returns {Promise<Object>} Categories with their info
 */
export async function fetchCategories() {
  const response = await fetch(`${API_BASE_URL}/search/categories`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP error! status: ${response.status}`);
  }

  return response.json();
}

/**
 * Fetch available search engines grouped by category
 * @returns {Promise<Object>} Engines grouped by category
 */
export async function fetchEngines() {
  const response = await fetch(`${API_BASE_URL}/search/engines`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP error! status: ${response.status}`);
  }

  return response.json();
}
