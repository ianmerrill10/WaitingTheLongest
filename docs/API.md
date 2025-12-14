# Waiting The Longest™ - API Documentation

Complete reference for the Waiting The Longest™ REST API.

## Base URL

- **Production**: `https://waitingthelongest.com/api`
- **Local Development**: `http://localhost:8000/api`

## Authentication

Currently, all endpoints are public. Rate limiting is applied per IP address.

## Rate Limits

| Tier | Requests/Minute | Requests/Hour |
|------|-----------------|---------------|
| Default | 60 | 1000 |

Rate limit headers are included in all responses:
- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Reset`

---

## Endpoints

### Health & Info

#### `GET /health`

Health check endpoint for monitoring.

**Response:**
```json
{
  "status": "healthy",
  "database": "healthy",
  "timestamp": "2024-12-14T10:00:00",
  "version": "1.0.0"
}
```

---

### Animals

#### `GET /api/animals`

List animals with pagination and filtering. **Default sort is by days_waiting descending (longest waiting first).**

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `species` | string | - | Filter by species (`dog`, `cat`) |
| `status` | string | `available` | Filter by status |
| `breed` | string | - | Filter by breed (partial match) |
| `age_group` | string | - | Filter by age (`puppy`, `young`, `adult`, `senior`) |
| `size` | string | - | Filter by size (`small`, `medium`, `large`) |
| `gender` | string | - | Filter by gender (`male`, `female`) |
| `state` | string | - | Filter by state (e.g., `CA`, `TX`) |
| `sort_by` | string | `days_waiting` | Sort field |
| `sort_order` | string | `desc` | Sort direction (`asc`, `desc`) |
| `page` | int | `1` | Page number |
| `page_size` | int | `20` | Items per page (max: 100) |

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "species": "dog",
      "canonical_name": "Buddy",
      "breed_primary": "German Shepherd",
      "age_group": "adult",
      "size": "large",
      "gender": "male",
      "status": "available",
      "days_waiting": 500,
      "first_seen_at": "2023-08-01T00:00:00",
      "photo_url": "https://...",
      "city": "Austin",
      "state": "TX"
    }
  ],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "total_pages": 8,
  "has_next": true,
  "has_prev": false
}
```

#### `GET /api/animals/{id}`

Get detailed information about a specific animal.

**Response:**
```json
{
  "id": 1,
  "species": "dog",
  "canonical_name": "Buddy",
  "breed_primary": "German Shepherd",
  "breed_secondary": "Mix",
  "color_primary": "Black and Tan",
  "age_group": "adult",
  "size": "large",
  "gender": "male",
  "status": "available",
  "transfer_count": 0,
  "days_waiting": 500,
  "first_seen_at": "2023-08-01T00:00:00",
  "last_seen_at": "2024-12-14T00:00:00",
  "observations": [...],
  "photos": ["https://..."],
  "description": "Friendly dog...",
  "adoption_url": "https://...",
  "shelter_info": {...}
}
```

#### `GET /api/animals/{id}/similar`

Get animals similar to the specified animal.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | `6` | Max results (1-20) |

#### `GET /api/longest-waiting`

Get the animals who have waited the longest.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `species` | string | - | Filter by species |
| `limit` | int | `10` | Max results (1-50) |

---

### Shelters

#### `GET /api/shelters`

List all shelters and rescue organizations.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `state` | string | Filter by state |
| `page` | int | Page number |
| `page_size` | int | Items per page |

#### `GET /api/shelters/{id}`

Get detailed shelter information.

---

### Breeds & Filters

#### `GET /api/breeds`

Get list of unique breeds in the database.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `species` | string | Filter by species |

#### `GET /api/filters`

Get all available filter options with counts.

**Response:**
```json
{
  "species": [{"value": "dog", "count": 100}, {"value": "cat", "count": 50}],
  "age_groups": [...],
  "sizes": [...],
  "genders": [...],
  "states": [...]
}
```

---

### Success Stories

#### `GET /api/success-stories`

Get recent adoption success stories.

#### `POST /api/success-stories`

Submit a success story.

**Request Body:**
```json
{
  "pet_name": "Max",
  "adopter_name": "John Doe",
  "story_text": "After 500 days, Max finally found his forever home...",
  "days_waited": 500,
  "adoption_date": "2024-12-01",
  "photo_urls": ["https://..."],
  "contact_email": "john@example.com",
  "animal_id": 1
}
```

---

### Statistics

#### `GET /api/stats`

Get platform statistics.

**Response:**
```json
{
  "total_animals": 1000,
  "available_animals": 500,
  "average_wait_days": 45.5,
  "longest_wait_days": 500,
  "success_stories": 250,
  "mission": "Because Every Day Matters",
  "updated_at": "2024-12-14T10:00:00"
}
```

---

### Products & Affiliates

#### `GET /api/products/recommendations`

Get personalized product recommendations with affiliate links.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `pet_type` | string | Yes | `dog`, `cat`, or `both` |
| `pet_age` | string | No | `puppy`, `adult`, `senior` |
| `pet_size` | string | No | `small`, `medium`, `large` |
| `limit` | int | No | Max results (default: 5) |

#### `POST /api/affiliate/click`

Track affiliate link clicks.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `product_id` | string | Yes | Product identifier |
| `source_page` | string | No | Page where click originated |
| `animal_id` | int | No | Associated animal ID |

---

### Newsletter

#### `POST /api/newsletter/subscribe`

Subscribe to the weekly newsletter.

**Request Body:**
```json
{
  "email": "user@example.com",
  "name": "John Doe",
  "preferred_species": ["dog", "cat"],
  "location_state": "CA"
}
```

#### `POST /api/newsletter/unsubscribe`

Unsubscribe from marketing emails.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `email` | string | Email to unsubscribe |
| `token` | string | Verification token (optional) |

#### `GET /api/newsletter/verify`

Verify subscriber email address.

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message here"
}
```

### Common Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request - Invalid parameters |
| 404 | Not Found - Resource doesn't exist |
| 422 | Validation Error - Invalid request body |
| 429 | Too Many Requests - Rate limited |
| 500 | Internal Server Error |

---

## OpenAPI Documentation

Interactive API documentation is available at:
- **Swagger UI**: `/api/docs`
- **ReDoc**: `/api/redoc`

---

## SDKs & Libraries

Currently, we offer a REST API. Official SDKs are planned for:
- Python
- JavaScript/TypeScript
- Swift (iOS)
- Kotlin (Android)

---

## Support

For API issues or questions:
- Email: [hello@waitingthelongest.com](mailto:hello@waitingthelongest.com)
- GitHub Issues: [Report a bug](https://github.com/ianmerrill10/WaitingTheLongest/issues)
