/**
 * Student Assessment Form Handler
 * LocalStorage draft auto-save and completion progress tracking
 */

document.addEventListener('DOMContentLoaded', function () {
  const formElement = document.getElementById('student-assessment-form');
  if (!formElement) return;

  const formSlug = formElement.getAttribute('data-form-slug') || 'default_form';
  const STORAGE_KEY = `ssvs_draft_${formSlug}`;
  const progressBar = document.getElementById('form-progress-bar');
  const progressText = document.getElementById('form-progress-text');

  // Restore draft if exists
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const data = JSON.parse(saved);
      for (const [key, value] of Object.entries(data)) {
        const input = formElement.elements[key];
        if (input && value && input.type !== 'file') {
          input.value = value;
        }
      }
      showDraftRestoredToast();
    }
  } catch (e) {
    console.error('Error restoring draft:', e);
  }

  // Update progress and save draft on any input change
  formElement.addEventListener('input', function () {
    updateProgressAndSave();
  });

  function updateProgressAndSave() {
    const inputs = formElement.querySelectorAll('input:not([type="hidden"]):not([type="submit"]), select, textarea');
    let filled = 0;
    const draftData = {};

    inputs.forEach(input => {
      const name = input.name;
      const val = input.value.trim();
      if (val) {
        filled++;
        if (name && input.type !== 'file') {
          draftData[name] = val;
        }
      }
    });

    const percent = Math.round((filled / (inputs.length || 1)) * 100);
    if (progressBar) {
      progressBar.style.width = percent + '%';
      progressBar.setAttribute('aria-valuenow', percent);
    }
    if (progressText) {
      progressText.textContent = `${percent}% Completed`;
    }

    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(draftData));
    } catch (e) {}
  }

  // Initial progress update
  updateProgressAndSave();

  // Clear draft upon submission
  formElement.addEventListener('submit', function () {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch (e) {}
    
    const submitBtn = formElement.querySelector('button[type="submit"]');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Submitting & Analyzing Profiles...';
    }
  });

  function showDraftRestoredToast() {
    const banner = document.getElementById('draft-restored-banner');
    if (banner) {
      banner.classList.remove('d-none');
    }
  }
});
