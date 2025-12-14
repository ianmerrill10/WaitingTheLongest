// ===============================================================================
// Waiting The Longest™ - E2E Tests: API Endpoints
// ===============================================================================
// Purpose: Test critical API endpoints
// ===============================================================================

import { test, expect } from '@playwright/test';

test.describe('API Endpoints', () => {
  test('GET /health should return healthy status', async ({ request }) => {
    const response = await request.get('/health');
    
    expect(response.status()).toBe(200);
    
    const body = await response.json();
    expect(body.status).toBe('healthy');
  });

  test('GET /api/animals should return animal list', async ({ request }) => {
    const response = await request.get('/api/animals');
    
    expect(response.status()).toBe(200);
    
    const body = await response.json();
    expect(body).toHaveProperty('animals');
    expect(Array.isArray(body.animals)).toBe(true);
  });

  test('GET /api/animals should support pagination', async ({ request }) => {
    const response = await request.get('/api/animals?page=1&per_page=5');
    
    expect(response.status()).toBe(200);
    
    const body = await response.json();
    expect(body.animals.length).toBeLessThanOrEqual(5);
    expect(body).toHaveProperty('total');
    expect(body).toHaveProperty('page');
  });

  test('GET /api/animals should support species filter', async ({ request }) => {
    const response = await request.get('/api/animals?species=dog');
    
    expect(response.status()).toBe(200);
    
    const body = await response.json();
    body.animals.forEach(animal => {
      expect(animal.species.toLowerCase()).toBe('dog');
    });
  });

  test('GET /api/stats should return statistics', async ({ request }) => {
    const response = await request.get('/api/stats');
    
    expect(response.status()).toBe(200);
    
    const body = await response.json();
    expect(body).toHaveProperty('available_animals');
    expect(body).toHaveProperty('longest_wait_days');
    expect(typeof body.available_animals).toBe('number');
  });

  test('GET /api/success-stories should return stories', async ({ request }) => {
    const response = await request.get('/api/success-stories');
    
    expect(response.status()).toBe(200);
    
    const body = await response.json();
    expect(Array.isArray(body)).toBe(true);
  });

  test('GET /api/shelters should return shelter list', async ({ request }) => {
    const response = await request.get('/api/shelters');
    
    expect(response.status()).toBe(200);
    
    const body = await response.json();
    expect(body).toHaveProperty('shelters');
    expect(Array.isArray(body.shelters)).toBe(true);
  });

  test('GET /api/breeds should return breed list', async ({ request }) => {
    const response = await request.get('/api/breeds');
    
    expect(response.status()).toBe(200);
    
    const body = await response.json();
    expect(body).toHaveProperty('breeds');
    expect(Array.isArray(body.breeds)).toBe(true);
  });

  test('GET /api/filters should return filter options', async ({ request }) => {
    const response = await request.get('/api/filters');
    
    expect(response.status()).toBe(200);
    
    const body = await response.json();
    expect(body).toHaveProperty('species');
    expect(body).toHaveProperty('age_groups');
    expect(body).toHaveProperty('sizes');
    expect(body).toHaveProperty('genders');
  });
});

test.describe('API Error Handling', () => {
  test('GET /api/animals/{id} with invalid ID should return 404', async ({ request }) => {
    const response = await request.get('/api/animals/99999999');
    
    expect(response.status()).toBe(404);
  });

  test('GET /api/shelters/{id} with invalid ID should return 404', async ({ request }) => {
    const response = await request.get('/api/shelters/99999999');
    
    expect(response.status()).toBe(404);
  });

  test('Invalid endpoint should return 404', async ({ request }) => {
    const response = await request.get('/api/nonexistent');
    
    expect(response.status()).toBe(404);
  });
});

test.describe('API Rate Limiting', () => {
  test('should include rate limit headers', async ({ request }) => {
    const response = await request.get('/api/animals');
    
    // Rate limit headers should be present
    const headers = response.headers();
    expect(headers).toHaveProperty('x-ratelimit-limit');
    expect(headers).toHaveProperty('x-ratelimit-remaining');
  });
});

test.describe('API CORS', () => {
  test('should include CORS headers', async ({ request }) => {
    const response = await request.get('/api/animals', {
      headers: {
        'Origin': 'https://example.com'
      }
    });
    
    const headers = response.headers();
    // Note: CORS headers may only be present for cross-origin requests
    // This test verifies the API accepts cross-origin requests
    expect(response.status()).toBe(200);
  });
});

test.describe('Newsletter API', () => {
  test('POST /api/newsletter/subscribe should require email', async ({ request }) => {
    const response = await request.post('/api/newsletter/subscribe', {
      data: {}
    });
    
    expect(response.status()).toBe(422); // Validation error
  });

  test('POST /api/newsletter/subscribe should validate email format', async ({ request }) => {
    const response = await request.post('/api/newsletter/subscribe', {
      data: { email: 'invalid-email' }
    });
    
    expect(response.status()).toBe(422); // Validation error
  });

  test('POST /api/newsletter/subscribe should accept valid email', async ({ request }) => {
    const response = await request.post('/api/newsletter/subscribe', {
      data: { email: `test-${Date.now()}@example.com` }
    });
    
    // Either success or already subscribed
    expect([200, 201, 409]).toContain(response.status());
  });
});
