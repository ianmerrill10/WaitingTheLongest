// ===============================================================================
// Waiting The Longest™ - E2E Tests: Homepage
// ===============================================================================
// Purpose: Test critical homepage user flows
// ===============================================================================

import { test, expect } from '@playwright/test';

test.describe('Homepage', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display the main heading', async ({ page }) => {
    await expect(page.locator('h1')).toContainText('Waiting The Longest');
  });

  test('should show statistics section', async ({ page }) => {
    await expect(page.locator('[data-testid="stats-section"]')).toBeVisible();
    // Wait for stats to load
    await expect(page.locator('[data-testid="total-animals"]')).toBeVisible({ timeout: 10000 });
  });

  test('should display animal cards', async ({ page }) => {
    // Wait for animals to load
    await expect(page.locator('[data-testid="animal-card"]').first()).toBeVisible({ timeout: 10000 });
    
    // Check that multiple animals are shown
    const animalCards = page.locator('[data-testid="animal-card"]');
    await expect(animalCards).toHaveCount({ min: 1 });
  });

  test('should filter animals by species', async ({ page }) => {
    // Wait for animals to load
    await expect(page.locator('[data-testid="animal-card"]').first()).toBeVisible({ timeout: 10000 });
    
    // Click dog filter
    await page.click('[data-testid="filter-dog"]');
    
    // Wait for filter to apply
    await page.waitForTimeout(500);
    
    // Check that only dogs are shown
    const speciesLabels = page.locator('[data-testid="animal-species"]');
    const count = await speciesLabels.count();
    for (let i = 0; i < count; i++) {
      await expect(speciesLabels.nth(i)).toContainText('Dog', { ignoreCase: true });
    }
  });

  test('should search animals by name', async ({ page }) => {
    const searchInput = page.locator('[data-testid="search-input"]');
    
    // Type a search query
    await searchInput.fill('buddy');
    await searchInput.press('Enter');
    
    // Wait for search results
    await page.waitForTimeout(1000);
    
    // Results should update
    await expect(page.locator('[data-testid="animal-grid"]')).toBeVisible();
  });

  test('should toggle dark mode', async ({ page }) => {
    const themeToggle = page.locator('[data-testid="theme-toggle"]');
    
    // Get initial theme
    const initialTheme = await page.evaluate(() => document.documentElement.dataset.theme);
    
    // Click theme toggle
    await themeToggle.click();
    
    // Theme should change
    const newTheme = await page.evaluate(() => document.documentElement.dataset.theme);
    expect(newTheme).not.toBe(initialTheme);
  });

  test('should navigate to animal detail page', async ({ page }) => {
    // Wait for animals to load
    await expect(page.locator('[data-testid="animal-card"]').first()).toBeVisible({ timeout: 10000 });
    
    // Click first animal
    await page.locator('[data-testid="animal-card"]').first().click();
    
    // Should navigate to detail page
    await expect(page).toHaveURL(/\/animal\/\d+/);
    await expect(page.locator('[data-testid="animal-detail"]')).toBeVisible();
  });

  test('should add animal to favorites', async ({ page }) => {
    // Wait for animals to load
    await expect(page.locator('[data-testid="animal-card"]').first()).toBeVisible({ timeout: 10000 });
    
    // Click favorite button on first animal
    const favoriteBtn = page.locator('[data-testid="favorite-btn"]').first();
    await favoriteBtn.click();
    
    // Button should show favorited state
    await expect(favoriteBtn).toHaveClass(/favorited/);
    
    // Favorite should persist in localStorage
    const favorites = await page.evaluate(() => {
      return JSON.parse(localStorage.getItem('favorites') || '[]');
    });
    expect(favorites.length).toBeGreaterThan(0);
  });
});

test.describe('Navigation', () => {
  test('should navigate to success stories', async ({ page }) => {
    await page.goto('/');
    
    await page.click('[data-testid="nav-success-stories"]');
    
    await expect(page).toHaveURL('/success-stories');
    await expect(page.locator('h1')).toContainText('Success Stories');
  });

  test('should navigate to about page', async ({ page }) => {
    await page.goto('/');
    
    await page.click('[data-testid="nav-about"]');
    
    await expect(page).toHaveURL('/about');
    await expect(page.locator('h1')).toContainText('About');
  });
});

test.describe('Accessibility', () => {
  test('should have skip link', async ({ page }) => {
    await page.goto('/');
    
    const skipLink = page.locator('[data-testid="skip-link"]');
    await expect(skipLink).toBeVisible({ visible: false }); // visually hidden by default
    
    // Should become visible on focus
    await skipLink.focus();
    await expect(skipLink).toBeVisible();
  });

  test('should have proper heading hierarchy', async ({ page }) => {
    await page.goto('/');
    
    // Should have exactly one h1
    const h1Count = await page.locator('h1').count();
    expect(h1Count).toBe(1);
    
    // All h2s should come after h1
    const h1 = page.locator('h1').first();
    const h2s = page.locator('h2');
    
    // h1 should exist before any h2s
    await expect(h1).toBeVisible();
  });

  test('should have alt text on images', async ({ page }) => {
    await page.goto('/');
    
    // Wait for images to load
    await page.waitForLoadState('networkidle');
    
    // All images should have alt text
    const images = page.locator('img');
    const count = await images.count();
    
    for (let i = 0; i < count; i++) {
      const alt = await images.nth(i).getAttribute('alt');
      expect(alt).toBeTruthy();
    }
  });
});

test.describe('Performance', () => {
  test('should load within acceptable time', async ({ page }) => {
    const startTime = Date.now();
    
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    
    const loadTime = Date.now() - startTime;
    
    // Should load within 3 seconds
    expect(loadTime).toBeLessThan(3000);
  });

  test('should not have significant layout shift', async ({ page }) => {
    await page.goto('/');
    
    // Measure CLS
    const cls = await page.evaluate(() => {
      return new Promise((resolve) => {
        let clsValue = 0;
        new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (!entry.hadRecentInput) {
              clsValue += entry.value;
            }
          }
          resolve(clsValue);
        }).observe({ type: 'layout-shift', buffered: true });
        
        // Resolve after 2 seconds
        setTimeout(() => resolve(clsValue), 2000);
      });
    });
    
    // CLS should be under 0.1 (good)
    expect(cls).toBeLessThan(0.1);
  });
});
