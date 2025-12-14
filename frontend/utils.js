/**
 * Waiting The Longest™ - Utility Functions
 * ==========================================
 * Shared JavaScript utilities for frontend
 */

/**
 * Format a number of days into human-readable text
 */
function formatDaysWaiting(days) {
  if (days === 0) return 'Just arrived';
  if (days === 1) return '1 day';
  if (days < 7) return `${days} days`;
  if (days < 14) return '1 week';
  if (days < 30) return `${Math.floor(days / 7)} weeks`;
  if (days < 60) return '1 month';
  if (days < 365) return `${Math.floor(days / 30)} months`;
  if (days < 730) return '1 year';
  return `${Math.floor(days / 365)} years`;
}

/**
 * Format a date relative to now
 */
function formatRelativeDate(date) {
  const now = new Date();
  const then = new Date(date);
  const diffMs = now - then;
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  
  return formatDaysWaiting(diffDays);
}

/**
 * Debounce a function
 */
function debounce(func, wait = 300) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func.apply(this, args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * Throttle a function
 */
function throttle(func, limit = 100) {
  let inThrottle;
  return function executedFunction(...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

/**
 * Parse query parameters from URL
 */
function getQueryParams() {
  const params = new URLSearchParams(window.location.search);
  const result = {};
  for (const [key, value] of params) {
    result[key] = value;
  }
  return result;
}

/**
 * Update URL query parameters without reload
 */
function updateQueryParams(params, replace = false) {
  const url = new URL(window.location);
  
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined || value === '') {
      url.searchParams.delete(key);
    } else {
      url.searchParams.set(key, value);
    }
  }
  
  if (replace) {
    window.history.replaceState({}, '', url);
  } else {
    window.history.pushState({}, '', url);
  }
}

/**
 * Truncate text with ellipsis
 */
function truncate(text, maxLength, suffix = '...') {
  if (!text || text.length <= maxLength) return text;
  return text.substring(0, maxLength - suffix.length).trim() + suffix;
}

/**
 * Capitalize first letter of each word
 */
function titleCase(str) {
  return str.toLowerCase().replace(/\b\w/g, char => char.toUpperCase());
}

/**
 * Generate a unique ID
 */
function generateId(prefix = 'id') {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Check if element is in viewport
 */
function isInViewport(element) {
  const rect = element.getBoundingClientRect();
  return (
    rect.top >= 0 &&
    rect.left >= 0 &&
    rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
    rect.right <= (window.innerWidth || document.documentElement.clientWidth)
  );
}

/**
 * Lazy load images with Intersection Observer
 */
function setupLazyImages() {
  const images = document.querySelectorAll('img[data-src]');
  
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target;
          img.src = img.dataset.src;
          img.classList.add('loaded');
          observer.unobserve(img);
        }
      });
    }, { rootMargin: '100px' });
    
    images.forEach(img => observer.observe(img));
  } else {
    // Fallback for older browsers
    images.forEach(img => {
      img.src = img.dataset.src;
    });
  }
}

/**
 * Copy text to clipboard
 */
async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (err) {
    // Fallback for older browsers
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    document.body.appendChild(textArea);
    textArea.select();
    
    try {
      document.execCommand('copy');
      return true;
    } finally {
      document.body.removeChild(textArea);
    }
  }
}

/**
 * Share content (Web Share API with fallback)
 */
async function share(data) {
  const { title, text, url } = data;
  
  if (navigator.share) {
    try {
      await navigator.share({ title, text, url });
      return true;
    } catch (err) {
      if (err.name !== 'AbortError') {
        console.error('Share failed:', err);
      }
    }
  }
  
  // Fallback: copy URL to clipboard
  await copyToClipboard(url);
  showToast('Link copied to clipboard!');
  return true;
}

/**
 * Show a toast notification
 */
function showToast(message, type = 'info', duration = 3000) {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  
  const container = document.getElementById('toast-container') || createToastContainer();
  container.appendChild(toast);
  
  // Trigger animation
  requestAnimationFrame(() => {
    toast.classList.add('show');
  });
  
  // Auto-dismiss
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

function createToastContainer() {
  const container = document.createElement('div');
  container.id = 'toast-container';
  container.style.cssText = `
    position: fixed;
    bottom: 20px;
    right: 20px;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    gap: 10px;
  `;
  document.body.appendChild(container);
  return container;
}

/**
 * Local storage wrapper with JSON support
 */
const storage = {
  get(key, defaultValue = null) {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue;
    } catch {
      return defaultValue;
    }
  },
  
  set(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch {
      return false;
    }
  },
  
  remove(key) {
    localStorage.removeItem(key);
  },
  
  clear() {
    localStorage.clear();
  }
};

/**
 * Session storage wrapper
 */
const session = {
  get(key, defaultValue = null) {
    try {
      const item = sessionStorage.getItem(key);
      return item ? JSON.parse(item) : defaultValue;
    } catch {
      return defaultValue;
    }
  },
  
  set(key, value) {
    try {
      sessionStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch {
      return false;
    }
  },
  
  remove(key) {
    sessionStorage.removeItem(key);
  }
};

/**
 * Check if user prefers reduced motion
 */
function prefersReducedMotion() {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Check if user prefers dark mode
 */
function prefersDarkMode() {
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

/**
 * Smooth scroll to element
 */
function scrollToElement(element, offset = 0) {
  const top = element.getBoundingClientRect().top + window.pageYOffset - offset;
  
  if (prefersReducedMotion()) {
    window.scrollTo(0, top);
  } else {
    window.scrollTo({ top, behavior: 'smooth' });
  }
}

/**
 * Format number with commas
 */
function formatNumber(num) {
  return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

/**
 * Validate email format
 */
function isValidEmail(email) {
  const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return pattern.test(email);
}

/**
 * Get contrast color (black or white) for a background
 */
function getContrastColor(hexColor) {
  const r = parseInt(hexColor.slice(1, 3), 16);
  const g = parseInt(hexColor.slice(3, 5), 16);
  const b = parseInt(hexColor.slice(5, 7), 16);
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.5 ? '#000000' : '#ffffff';
}

/**
 * Create element from HTML string
 */
function createElement(html) {
  const template = document.createElement('template');
  template.innerHTML = html.trim();
  return template.content.firstChild;
}

/**
 * Wait for DOM ready
 */
function domReady(callback) {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', callback);
  } else {
    callback();
  }
}

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    formatDaysWaiting,
    formatRelativeDate,
    debounce,
    throttle,
    getQueryParams,
    updateQueryParams,
    truncate,
    titleCase,
    generateId,
    isInViewport,
    setupLazyImages,
    copyToClipboard,
    share,
    showToast,
    storage,
    session,
    prefersReducedMotion,
    prefersDarkMode,
    scrollToElement,
    formatNumber,
    isValidEmail,
    getContrastColor,
    createElement,
    domReady,
  };
}

// Export to window
window.WTLUtils = {
  formatDaysWaiting,
  formatRelativeDate,
  debounce,
  throttle,
  getQueryParams,
  updateQueryParams,
  truncate,
  titleCase,
  generateId,
  isInViewport,
  setupLazyImages,
  copyToClipboard,
  share,
  showToast,
  storage,
  session,
  prefersReducedMotion,
  prefersDarkMode,
  scrollToElement,
  formatNumber,
  isValidEmail,
  getContrastColor,
  createElement,
  domReady,
};
