# The ONE - API Documentation

## Internal API

"The ONE" uses a simple internal API to handle searches and retrieve results. This document outlines the endpoints and their usage.

### Search Endpoint

**URL**: `/search`
**Method**: `POST`
**Form Parameters**:
- `website`: The website to search (e.g., allrecipes.com)
- `query`: The search query
- `ranking_type`: The type of ranking to use (`relevance` or `ratings`)

**Response**: Redirects to `/results/<search_id>` with the search results

### Results Endpoint

**URL**: `/results/<search_id>`
**Method**: `GET`
**URL Parameters**:
- `search_id`: The unique ID for the search

**Response**: Renders the results page with the search results

## External API - Firecrawl

The application uses the Firecrawl API for web scraping and data extraction. Below are the main endpoints used:

### Search Endpoint

**URL**: `https://api.firecrawl.dev/v1/search`
**Method**: `POST`
**Headers**:
- `Authorization`: Bearer token with your API key
- `Content-Type`: application/json

**Body**:
```json
{
  "url": "https://example.com",
  "query": "search query"
}
```

**Response**: Returns search results for the specified website and query

### Extract Endpoint

**URL**: `https://api.firecrawl.dev/v1/extract`
**Method**: `POST`
**Headers**:
- `Authorization`: Bearer token with your API key
- `Content-Type`: application/json

**Body**:
```json
{
  "url": "https://example.com/specific-page",
  "include_comments": true,
  "summarize_comments": true
}
```

**Response**: Returns detailed information about the specified page, including comment summaries

For more information about the Firecrawl API, visit:
- [Firecrawl Documentation](https://docs.firecrawl.dev/)
- [API Introduction](https://docs.firecrawl.dev/introduction)