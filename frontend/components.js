/**
 * Waiting The Longest™ - Components
 * ===================================
 * Reusable UI components
 */

// =============================================================================
// Animal Card Component
// =============================================================================

class AnimalCard {
  constructor(animal, options = {}) {
    this.animal = animal;
    this.options = {
      showStats: true,
      showActions: true,
      lazy: true,
      ...options,
    };
  }

  render() {
    const { animal, options } = this;
    const daysWaiting = this.calculateDaysWaiting(animal.intake_date);
    
    const card = document.createElement('article');
    card.className = 'animal-card';
    card.dataset.animalId = animal.id;
    
    card.innerHTML = `
      <div class="animal-card__image-container">
        ${this.renderImage()}
        ${this.renderBadges(daysWaiting)}
      </div>
      <div class="animal-card__content">
        <h3 class="animal-card__name">${this.escapeHtml(animal.name)}</h3>
        <p class="animal-card__breed">${this.escapeHtml(animal.breed || 'Unknown breed')}</p>
        ${options.showStats ? this.renderStats(daysWaiting) : ''}
        <p class="animal-card__shelter">${this.escapeHtml(animal.shelter_name || '')}</p>
        ${options.showActions ? this.renderActions() : ''}
      </div>
    `;
    
    // Add event listeners
    this.attachEventListeners(card);
    
    return card;
  }

  renderImage() {
    const { animal, options } = this;
    const src = animal.photo_url || '/images/placeholder-pet.svg';
    
    if (options.lazy) {
      return `
        <img 
          class="animal-card__image lazy-image" 
          data-src="${this.escapeHtml(src)}" 
          alt="Photo of ${this.escapeHtml(animal.name)}"
          loading="lazy"
        />
      `;
    }
    
    return `
      <img 
        class="animal-card__image" 
        src="${this.escapeHtml(src)}" 
        alt="Photo of ${this.escapeHtml(animal.name)}"
      />
    `;
  }

  renderBadges(daysWaiting) {
    const badges = [];
    
    if (daysWaiting >= 365) {
      badges.push('<span class="badge badge--urgent">1+ Year</span>');
    } else if (daysWaiting >= 180) {
      badges.push('<span class="badge badge--warning">6+ Months</span>');
    } else if (daysWaiting >= 90) {
      badges.push('<span class="badge badge--info">90+ Days</span>');
    }
    
    if (this.animal.species) {
      const icon = this.animal.species.toLowerCase() === 'dog' ? '🐕' : '🐈';
      badges.push(`<span class="badge badge--species">${icon}</span>`);
    }
    
    return `<div class="animal-card__badges">${badges.join('')}</div>`;
  }

  renderStats(daysWaiting) {
    return `
      <div class="animal-card__stats">
        <span class="stat">
          <span class="stat__value">${daysWaiting}</span>
          <span class="stat__label">days waiting</span>
        </span>
      </div>
    `;
  }

  renderActions() {
    return `
      <div class="animal-card__actions">
        <button class="btn btn--primary btn--small" data-action="view">
          View Profile
        </button>
        <button class="btn btn--icon" data-action="favorite" aria-label="Add to favorites">
          ❤️
        </button>
        <button class="btn btn--icon" data-action="share" aria-label="Share">
          📤
        </button>
      </div>
    `;
  }

  attachEventListeners(card) {
    card.querySelector('[data-action="view"]')?.addEventListener('click', () => {
      window.location.href = `/animals/${this.animal.id}`;
    });
    
    card.querySelector('[data-action="favorite"]')?.addEventListener('click', (e) => {
      e.stopPropagation();
      this.toggleFavorite();
    });
    
    card.querySelector('[data-action="share"]')?.addEventListener('click', (e) => {
      e.stopPropagation();
      this.share();
    });
  }

  async toggleFavorite() {
    const btn = document.querySelector(`[data-animal-id="${this.animal.id}"] [data-action="favorite"]`);
    const isFavorited = btn?.classList.toggle('is-favorited');
    
    // Store in local storage
    const favorites = JSON.parse(localStorage.getItem('favorites') || '[]');
    if (isFavorited) {
      favorites.push(this.animal.id);
    } else {
      const idx = favorites.indexOf(this.animal.id);
      if (idx > -1) favorites.splice(idx, 1);
    }
    localStorage.setItem('favorites', JSON.stringify(favorites));
  }

  async share() {
    const url = `${window.location.origin}/animals/${this.animal.id}`;
    const title = `Meet ${this.animal.name} - Waiting ${this.calculateDaysWaiting(this.animal.intake_date)} days for a home`;
    
    if (navigator.share) {
      try {
        await navigator.share({ title, url });
      } catch (err) {
        if (err.name !== 'AbortError') {
          this.copyToClipboard(url);
        }
      }
    } else {
      this.copyToClipboard(url);
    }
  }

  copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
      window.WTLUtils?.showToast('Link copied to clipboard!');
    });
  }

  calculateDaysWaiting(intakeDate) {
    if (!intakeDate) return 0;
    const intake = new Date(intakeDate);
    const now = new Date();
    return Math.floor((now - intake) / (1000 * 60 * 60 * 24));
  }

  escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }
}


// =============================================================================
// Modal Component
// =============================================================================

class Modal {
  constructor(options = {}) {
    this.options = {
      title: '',
      content: '',
      closable: true,
      size: 'medium', // small, medium, large, full
      onClose: null,
      ...options,
    };
    this.element = null;
    this.isOpen = false;
  }

  render() {
    const modal = document.createElement('div');
    modal.className = `modal modal--${this.options.size}`;
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    
    modal.innerHTML = `
      <div class="modal__overlay"></div>
      <div class="modal__container">
        <div class="modal__header">
          <h2 class="modal__title">${this.options.title}</h2>
          ${this.options.closable ? `
            <button class="modal__close" aria-label="Close modal">
              ✕
            </button>
          ` : ''}
        </div>
        <div class="modal__body">
          ${this.options.content}
        </div>
        <div class="modal__footer"></div>
      </div>
    `;
    
    this.element = modal;
    this.attachEventListeners();
    
    return modal;
  }

  attachEventListeners() {
    if (this.options.closable) {
      this.element.querySelector('.modal__overlay')?.addEventListener('click', () => this.close());
      this.element.querySelector('.modal__close')?.addEventListener('click', () => this.close());
    }
    
    // Escape key
    this.escapeHandler = (e) => {
      if (e.key === 'Escape' && this.options.closable) {
        this.close();
      }
    };
  }

  open() {
    if (this.isOpen) return;
    
    if (!this.element) {
      this.render();
    }
    
    document.body.appendChild(this.element);
    document.body.classList.add('modal-open');
    document.addEventListener('keydown', this.escapeHandler);
    
    // Trigger animation
    requestAnimationFrame(() => {
      this.element.classList.add('is-open');
    });
    
    this.isOpen = true;
    
    // Focus trap
    this.element.querySelector('.modal__close, button, input, a')?.focus();
  }

  close() {
    if (!this.isOpen) return;
    
    this.element.classList.remove('is-open');
    document.removeEventListener('keydown', this.escapeHandler);
    
    setTimeout(() => {
      this.element.remove();
      document.body.classList.remove('modal-open');
      this.isOpen = false;
      
      if (this.options.onClose) {
        this.options.onClose();
      }
    }, 300);
  }

  setContent(content) {
    if (this.element) {
      this.element.querySelector('.modal__body').innerHTML = content;
    }
    this.options.content = content;
  }

  addFooterButton(text, className, onClick) {
    if (!this.element) return;
    
    const footer = this.element.querySelector('.modal__footer');
    const button = document.createElement('button');
    button.className = `btn ${className}`;
    button.textContent = text;
    button.addEventListener('click', onClick);
    footer.appendChild(button);
  }
}


// =============================================================================
// Toast Component
// =============================================================================

class Toast {
  static container = null;

  static init() {
    if (!Toast.container) {
      Toast.container = document.createElement('div');
      Toast.container.className = 'toast-container';
      document.body.appendChild(Toast.container);
    }
  }

  static show(message, type = 'info', duration = 3000) {
    Toast.init();
    
    const toast = document.createElement('div');
    toast.className = `toast toast--${type}`;
    
    const icons = {
      info: 'ℹ️',
      success: '✅',
      warning: '⚠️',
      error: '❌',
    };
    
    toast.innerHTML = `
      <span class="toast__icon">${icons[type] || icons.info}</span>
      <span class="toast__message">${message}</span>
      <button class="toast__close" aria-label="Dismiss">✕</button>
    `;
    
    toast.querySelector('.toast__close').addEventListener('click', () => {
      Toast.dismiss(toast);
    });
    
    Toast.container.appendChild(toast);
    
    // Animate in
    requestAnimationFrame(() => {
      toast.classList.add('is-visible');
    });
    
    // Auto dismiss
    if (duration > 0) {
      setTimeout(() => Toast.dismiss(toast), duration);
    }
    
    return toast;
  }

  static dismiss(toast) {
    toast.classList.remove('is-visible');
    setTimeout(() => toast.remove(), 300);
  }

  static success(message, duration) {
    return Toast.show(message, 'success', duration);
  }

  static error(message, duration) {
    return Toast.show(message, 'error', duration);
  }

  static warning(message, duration) {
    return Toast.show(message, 'warning', duration);
  }

  static info(message, duration) {
    return Toast.show(message, 'info', duration);
  }
}


// =============================================================================
// Infinite Scroll Component
// =============================================================================

class InfiniteScroll {
  constructor(container, options = {}) {
    this.container = container;
    this.options = {
      threshold: 200,
      loadMore: async () => [],
      renderItem: (item) => item,
      noMoreText: 'No more items to load',
      loadingText: 'Loading...',
      ...options,
    };
    
    this.isLoading = false;
    this.hasMore = true;
    this.page = 1;
    
    this.init();
  }

  init() {
    this.sentinel = document.createElement('div');
    this.sentinel.className = 'infinite-scroll-sentinel';
    this.container.appendChild(this.sentinel);
    
    this.observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !this.isLoading && this.hasMore) {
          this.loadMore();
        }
      },
      { rootMargin: `${this.options.threshold}px` }
    );
    
    this.observer.observe(this.sentinel);
  }

  async loadMore() {
    this.isLoading = true;
    this.showLoading();
    
    try {
      const items = await this.options.loadMore(this.page);
      
      if (items.length === 0) {
        this.hasMore = false;
        this.showNoMore();
      } else {
        items.forEach(item => {
          const element = this.options.renderItem(item);
          this.container.insertBefore(element, this.sentinel);
        });
        this.page++;
      }
    } catch (error) {
      console.error('Failed to load more items:', error);
    } finally {
      this.isLoading = false;
      this.hideLoading();
    }
  }

  showLoading() {
    this.sentinel.innerHTML = `<div class="loading-indicator">${this.options.loadingText}</div>`;
  }

  hideLoading() {
    this.sentinel.innerHTML = '';
  }

  showNoMore() {
    this.sentinel.innerHTML = `<div class="no-more-items">${this.options.noMoreText}</div>`;
    this.observer.disconnect();
  }

  reset() {
    this.page = 1;
    this.hasMore = true;
    this.container.innerHTML = '';
    this.container.appendChild(this.sentinel);
    this.observer.observe(this.sentinel);
  }

  destroy() {
    this.observer.disconnect();
    this.sentinel.remove();
  }
}


// =============================================================================
// Export Components
// =============================================================================

window.WTLComponents = {
  AnimalCard,
  Modal,
  Toast,
  InfiniteScroll,
};
