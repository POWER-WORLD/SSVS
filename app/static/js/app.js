/**
 * SSVS Global JavaScript Utilities
 * Theme Switcher, Accent Colors, Toasts, and UI Enhancements
 */

(function () {
  'use strict';

  // 1. Theme (Dark / Light) Management
  const THEME_KEY = 'ssvs_theme_mode';
  const ACCENT_KEY = 'ssvs_accent_color';

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    document.documentElement.setAttribute('data-bs-theme', theme);
    localStorage.setItem(THEME_KEY, theme);
    const themeIcon = document.getElementById('theme-toggle-icon');
    if (themeIcon) {
      themeIcon.className = theme === 'dark' ? 'bi bi-sun-fill text-warning' : 'bi bi-moon-stars-fill text-secondary';
    }
  }

  function applyAccent(accent) {
    document.documentElement.setAttribute('data-accent', accent);
    localStorage.setItem(ACCENT_KEY, accent);
  }

  // Initialize theme from storage or system preference
  const savedTheme = localStorage.getItem(THEME_KEY) || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  applyTheme(savedTheme);

  const savedAccent = localStorage.getItem(ACCENT_KEY) || 'indigo';
  applyAccent(savedAccent);

  document.addEventListener('DOMContentLoaded', function () {
    // Theme toggle button
    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    if (themeToggleBtn) {
      themeToggleBtn.addEventListener('click', function () {
        const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        applyTheme(newTheme);
      });
    }

    // Accent color picker
    document.querySelectorAll('[data-set-accent]').forEach(btn => {
      btn.addEventListener('click', function () {
        const accent = this.getAttribute('data-set-accent');
        applyAccent(accent);
      });
    });

    // Copy to clipboard helper
    document.querySelectorAll('[data-copy]').forEach(el => {
      el.addEventListener('click', function () {
        const text = this.getAttribute('data-copy');
        if (text) {
          navigator.clipboard.writeText(text).then(() => {
            const origHtml = this.innerHTML;
            this.innerHTML = '<i class="bi bi-check2"></i> Copied!';
            setTimeout(() => {
              this.innerHTML = origHtml;
            }, 2000);
          });
        }
      });
    });

    // Auto-dismiss alerts after 5 seconds
    setTimeout(function () {
      const alerts = document.querySelectorAll('.alert-dismissible');
      alerts.forEach(function (alert) {
        const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
        if (bsAlert) bsAlert.close();
      });
    }, 5000);
  });
})();
