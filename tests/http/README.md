# HTTP API Test Suite

This directory contains HTTP request files for testing the Bwired API endpoints.

## Structure

```
tests/http/
├── README.md              # This file
├── 01_general_search.http    # Basic web search tests
├── 02_bang_syntax.http       # All bang type tests
├── 03_specialized_search.http # Category-specific searches
├── 04_bang_management.http   # GET endpoints for bangs/categories
├── 05_error_handling.http    # Error scenarios
├── 06_edge_cases.http        # Special query scenarios
└── 07_reference.http         # Bangs reference and SearXNG direct access
```

## Test Files

### 01_general_search.http
Basic web search tests for [`POST /web-search`](01_general_search.http:10)
- Minimal request
- Full parameter search
- Multi-language (EN, DE)
- Pagination

### 02_bang_syntax.http
All bang type tests for [`POST /web-search`](02_bang_syntax.http:10) with bang parameter
- Engine bangs: !gh, !so, !arxiv, !scholar, !r
- Category bangs: !images, !map, !news, !videos, !science, !it, !files, !social
- Combined language + bang

### 03_specialized_search.http
Specialized category searches for [`POST /web-search/specialized`](03_specialized_search.http:10)
- All 9 categories: general, it, science, social, files, images, map, videos, news
- With and without bang shortcuts

### 04_bang_management.http
GET endpoints:
- [`GET /web-search/bangs`](04_bang_management.http:10) - List all bangs
- [`GET /web-search/categories`](04_bang_management.http:15) - List categories
- [`GET /web-search/bangs/syntax`](04_bang_management.http:20) - Syntax help

### 05_error_handling.http
Error scenarios:
- Invalid bang (400)
- Invalid category
- Invalid time range
- Out-of-range pagination
- Per page limit exceeded

### 06_edge_cases.http
Special scenarios:
- Special characters
- Short/long queries
- Emoji in queries
- Empty queries

### 07_reference.http
Reference information:
- Available bangs list
- Language prefixes
- Time ranges
- Direct SearXNG access

## Running Tests

### Using VSCode REST Client

1. **Install REST Client extension:**
   - VSCode: Install "REST Client" by Huachao Mao

2. **Run individual requests:**
   - Click "Send Request" above any request block

3. **Run multiple requests:**
   - Select multiple requests and use "Send Request in Scope"

### Using curl (command line)

```bash
# Example: Run a basic web search
curl -X POST "http://localhost:8000/web-search" \
  -H "Content-Type: application/json" \
  -d '{"query": "test query"}'

# Example: Get available bangs
curl "http://localhost:8000/web-search/bangs"
```

## Prerequisites

1. **Start the server:**
   ```bash
   make r
   ```

2. **Start Docker services:**
   ```bash
   make up
   ```

3. **Verify services:**
   ```bash
   docker ps
   ```

4. **Check health:**
   ```bash
   curl http://localhost:8000/health
   ```

## Expected Responses

| Status Code | Meaning | Common Causes |
|-------------|---------|---------------|
| 200 | Success | Valid request, results returned |
| 400 | Bad Request | Invalid bang, invalid syntax |
| 503 | Service Unavailable | Server not initialized, SearXNG down |
| 504 | Gateway Timeout | SearXNG request timeout |

## Available Bangs Reference

### Engine-Specific Bangs
| Bang | Engine | Description |
|------|--------|-------------|
| `!gh` | GitHub | Code repositories |
| `!so` | Stack Overflow | Programming Q&A |
| `!aw` | ArchWiki | Linux documentation |
| `!arxiv` | arXiv | Scientific papers |
| `!scholar` | Google Scholar | Academic papers |
| `!r` | Reddit | Community discussions |
| `!g` | Google | Web search |
| `!b` | Bing | Web search |

### Category Bangs
| Bang | Category | Description |
|------|----------|-------------|
| `!images` | images | Image search |
| `!map` | map | Maps and locations |
| `!videos` | videos | Video platforms |
| `!science` | science | Scientific databases |
| `!it` | it | IT/programming |
| `!files` | files | Code repositories |
| `!social` | social | Social media |
| `!news` | news | News articles |
| `!general` | general | General web |

### Language Prefixes
`:en`, `:de`, `:fr`, `:es`, `:ja`, `:zh`, `:ru`, `:pt`, `:it`, `:nl`, `:pl`, `:ko`, `:ar`, `:hi`, `:tr`

### Time Ranges
`day`, `week`, `month`, `year`

## Related Files

- **API Implementation:** [`internal/api/web_search.py`](../../internal/api/web_search.py)
- **Bang Registry:** [`internal/searxng/bangs.py`](../../internal/searxng/bangs.py)
- **SearXNG Client:** [`internal/searxng/client.py`](../../internal/searxng/client.py)
- **Data Models:** [`internal/searxng/models.py`](../../internal/searxng/models.py)
- **Exceptions:** [`internal/searxng/exceptions.py`](../../internal/searxng/exceptions.py)

## Main API Reference

For quick reference, see the main [`api.http`](../../api.http) file in the project root.
