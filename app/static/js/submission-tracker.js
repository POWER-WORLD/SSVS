/**
 * Live Background Status Poller for Student Submissions
 */

document.addEventListener('DOMContentLoaded', function () {
  const container = document.getElementById('status-tracker-container');
  if (!container) return;

  const uuid = container.getAttribute('data-submission-uuid');
  const initialStatus = container.getAttribute('data-status');

  if (initialStatus === 'completed' || initialStatus === 'failed') {
    return; // Already completed
  }

  let pollInterval = setInterval(checkStatus, 2500);

  async function checkStatus() {
    try {
      const resp = await fetch(`/api/submission/${uuid}/status`);
      if (!resp.ok) return;

      const data = await resp.json();
      updateSteps(data.status);

      if (data.status === 'completed') {
        clearInterval(pollInterval);
        // Reload page to display final scores, podium, and radar
        setTimeout(() => {
          window.location.reload();
        }, 1200);
      } else if (data.status === 'failed') {
        clearInterval(pollInterval);
        window.location.reload();
      }
    } catch (e) {
      console.warn('Status polling error:', e);
    }
  }

  function updateSteps(status) {
    const step1 = document.getElementById('step-validate');
    const step2 = document.getElementById('step-extract');
    const step3 = document.getElementById('step-score');
    const step4 = document.getElementById('step-rank');

    if (status === 'extracting') {
      if (step1) step1.className = 'status-step completed';
      if (step2) step2.className = 'status-step active';
    } else if (status === 'scoring') {
      if (step1) step1.className = 'status-step completed';
      if (step2) step2.className = 'status-step completed';
      if (step3) step3.className = 'status-step active';
    } else if (status === 'completed') {
      if (step1) step1.className = 'status-step completed';
      if (step2) step2.className = 'status-step completed';
      if (step3) step3.className = 'status-step completed';
      if (step4) step4.className = 'status-step completed';
    }
  }
});
