/**
 * Dynamic Form Builder Engine
 * Drag & Drop, Palette, Inspector Drawer, and Live Canvas
 */

class FormBuilder {
  constructor(formId, initialFields = []) {
    this.formId = formId;
    this.fields = initialFields;
    this.selectedFieldIndex = null;
    this.canvas = document.getElementById('builder-canvas');
    this.inspector = document.getElementById('field-inspector');
    this.init();
  }

  init() {
    this.renderCanvas();
    this.setupPaletteClicks();
    this.setupSaveButton();
  }

  setupPaletteClicks() {
    document.querySelectorAll('[data-add-type]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const type = btn.getAttribute('data-add-type');
        const defaultLabel = btn.getAttribute('data-default-label') || 'New Field';
        const binding = btn.getAttribute('data-binding') || '';
        this.addField(type, defaultLabel, binding);
      });
    });
  }

  setupSaveButton() {
    const saveBtn = document.getElementById('save-builder-btn');
    if (saveBtn) {
      saveBtn.addEventListener('click', () => this.saveToServer());
    }
  }

  addField(type, label, binding = '') {
    const key = (binding || label.toLowerCase().replace(/[^a-z0-9]/g, '_')) + '_' + Date.now().toString().slice(-4);
    const newField = {
      id: null,
      field_key: key,
      label: label,
      field_type: type,
      placeholder: '',
      help_text: '',
      is_required: true,
      platform_metric_binding: binding,
      section_title: 'General Details',
      options: ['Option 1', 'Option 2', 'Option 3']
    };
    this.fields.push(newField);
    this.renderCanvas();
    this.selectField(this.fields.length - 1);
  }

  deleteField(index) {
    if (confirm('Are you sure you want to delete this field?')) {
      this.fields.splice(index, 1);
      this.selectedFieldIndex = null;
      this.renderCanvas();
      this.renderInspector();
    }
  }

  duplicateField(index) {
    const source = this.fields[index];
    const clone = JSON.parse(JSON.stringify(source));
    clone.id = null;
    clone.field_key = source.field_key + '_copy_' + Date.now().toString().slice(-3);
    clone.label = source.label + ' (Copy)';
    this.fields.splice(index + 1, 0, clone);
    this.renderCanvas();
    this.selectField(index + 1);
  }

  moveField(index, direction) {
    const target = index + direction;
    if (target < 0 || target >= this.fields.length) return;
    const temp = this.fields[index];
    this.fields[index] = this.fields[target];
    this.fields[target] = temp;
    this.selectedFieldIndex = target;
    this.renderCanvas();
  }

  selectField(index) {
    this.selectedFieldIndex = index;
    this.renderCanvas();
    this.renderInspector();
  }

  renderCanvas() {
    if (!this.canvas) return;
    this.canvas.innerHTML = '';

    if (this.fields.length === 0) {
      this.canvas.innerHTML = `
        <div class="text-center py-5 text-muted">
          <i class="bi bi-layout-text-window-reverse display-4 d-block mb-3 text-secondary"></i>
          <h5>Your Form Canvas is Empty</h5>
          <p class="small">Click any field from the palette on the left to start building your assessment form.</p>
        </div>
      `;
      return;
    }

    this.fields.forEach((f, idx) => {
      const isSelected = this.selectedFieldIndex === idx;
      const card = document.createElement('div');
      card.className = `canvas-field-card ${isSelected ? 'active' : ''}`;
      card.onclick = (e) => {
        if (!e.target.closest('.field-actions')) {
          this.selectField(idx);
        }
      };

      let inputPreview = '';
      if (f.field_type === 'textarea') {
        inputPreview = `<textarea class="form-control form-control-sm" rows="2" disabled placeholder="${f.placeholder || 'Text area response...'}"></textarea>`;
      } else if (f.field_type === 'dropdown') {
        inputPreview = `<select class="form-select form-select-sm" disabled><option>Select option...</option></select>`;
      } else if (f.field_type === 'section_divider') {
        inputPreview = `<hr class="my-2" /><div class="fw-bold text-primary">${f.label}</div>`;
      } else {
        inputPreview = `<input type="${f.field_type === 'number' || f.field_type === 'decimal' ? 'number' : 'text'}" class="form-control form-control-sm" disabled placeholder="${f.placeholder || 'Student response...'}">`;
      }

      card.innerHTML = `
        <div class="d-flex justify-content-between align-items-center mb-2">
          <div class="d-flex align-items-center gap-2">
            <span class="badge bg-secondary-subtle text-secondary font-monospace">#${idx + 1}</span>
            <span class="fw-bold">${f.label}</span>
            ${f.is_required ? '<span class="text-danger">*</span>' : ''}
            ${f.platform_metric_binding ? `<span class="badge bg-primary-subtle text-primary small"><i class="bi bi-link-45deg"></i> ${f.platform_metric_binding}</span>` : ''}
          </div>
          <div class="field-actions btn-group btn-group-sm">
            <button class="btn btn-outline-secondary btn-sm" onclick="builder.moveField(${idx}, -1)" title="Move Up"><i class="bi bi-arrow-up"></i></button>
            <button class="btn btn-outline-secondary btn-sm" onclick="builder.moveField(${idx}, 1)" title="Move Down"><i class="bi bi-arrow-down"></i></button>
            <button class="btn btn-outline-secondary btn-sm" onclick="builder.duplicateField(${idx})" title="Duplicate"><i class="bi bi-copy"></i></button>
            <button class="btn btn-outline-danger btn-sm" onclick="builder.deleteField(${idx})" title="Delete"><i class="bi bi-trash"></i></button>
          </div>
        </div>
        ${inputPreview}
        ${f.help_text ? `<div class="form-text small text-muted mt-1">${f.help_text}</div>` : ''}
      `;
      this.canvas.appendChild(card);
    });
  }

  renderInspector() {
    if (!this.inspector) return;
    if (this.selectedFieldIndex === null || !this.fields[this.selectedFieldIndex]) {
      this.inspector.innerHTML = `
        <div class="text-center py-5 text-muted">
          <i class="bi bi-sliders display-6 d-block mb-2"></i>
          <p class="small mb-0">Select a field on the canvas to configure its properties.</p>
        </div>
      `;
      return;
    }

    const f = this.fields[this.selectedFieldIndex];
    this.inspector.innerHTML = `
      <div class="p-3">
        <h6 class="fw-bold border-bottom pb-2 mb-3"><i class="bi bi-gear"></i> Field Settings</h6>
        
        <div class="mb-3">
          <label class="form-label small fw-bold">Field Label</label>
          <input type="text" class="form-control form-control-sm" id="prop-label" value="${f.label}">
        </div>

        <div class="mb-3">
          <label class="form-label small fw-bold">Field Key (Unique Identifier)</label>
          <input type="text" class="form-control form-control-sm font-monospace" id="prop-key" value="${f.field_key}">
        </div>

        <div class="mb-3">
          <label class="form-label small fw-bold">Section / Group Title</label>
          <input type="text" class="form-control form-control-sm" id="prop-section" value="${f.section_title || 'General'}">
        </div>

        <div class="mb-3">
          <label class="form-label small fw-bold">Placeholder Text</label>
          <input type="text" class="form-control form-control-sm" id="prop-placeholder" value="${f.placeholder || ''}">
        </div>

        <div class="mb-3">
          <label class="form-label small fw-bold">Help / Description Text</label>
          <input type="text" class="form-control form-control-sm" id="prop-help" value="${f.help_text || ''}">
        </div>

        <div class="mb-3">
          <label class="form-label small fw-bold">Platform Metric Binding</label>
          <select class="form-select form-select-sm" id="prop-binding">
            <option value="" ${!f.platform_metric_binding ? 'selected' : ''}>-- None (Custom Field) --</option>
            <option value="student_name" ${f.platform_metric_binding === 'student_name' ? 'selected' : ''}>Student Name</option>
            <option value="roll_number" ${f.platform_metric_binding === 'roll_number' ? 'selected' : ''}>Roll Number / ID</option>
            <option value="email" ${f.platform_metric_binding === 'email' ? 'selected' : ''}>Email Address</option>
            <option value="department" ${f.platform_metric_binding === 'department' ? 'selected' : ''}>Department</option>
            <option value="cgpa" ${f.platform_metric_binding === 'cgpa' ? 'selected' : ''}>Academic CGPA</option>
            <option value="backlogs" ${f.platform_metric_binding === 'backlogs' ? 'selected' : ''}>Backlog Count</option>
            <option value="leetcode_handle" ${f.platform_metric_binding === 'leetcode_handle' ? 'selected' : ''}>LeetCode URL / Handle</option>
            <option value="codechef_handle" ${f.platform_metric_binding === 'codechef_handle' ? 'selected' : ''}>CodeChef URL / Handle</option>
            <option value="codeforces_handle" ${f.platform_metric_binding === 'codeforces_handle' ? 'selected' : ''}>Codeforces Handle</option>
            <option value="github_handle" ${f.platform_metric_binding === 'github_handle' ? 'selected' : ''}>GitHub Profile URL / Handle</option>
            <option value="hackerrank_handle" ${f.platform_metric_binding === 'hackerrank_handle' ? 'selected' : ''}>HackerRank Profile URL</option>
            <option value="gfg_handle" ${f.platform_metric_binding === 'gfg_handle' ? 'selected' : ''}>GeeksforGeeks Profile URL</option>
            <option value="atcoder_handle" ${f.platform_metric_binding === 'atcoder_handle' ? 'selected' : ''}>AtCoder Profile URL</option>
            <option value="interviewbit_handle" ${f.platform_metric_binding === 'interviewbit_handle' ? 'selected' : ''}>InterviewBit Profile URL</option>
            <option value="kaggle_handle" ${f.platform_metric_binding === 'kaggle_handle' ? 'selected' : ''}>Kaggle Profile URL</option>
          </select>
          <div class="form-text small">Automatically binds this input to extraction and scoring engines.</div>
        </div>

        <div class="form-check form-switch mb-3">
          <input class="form-check-input" type="checkbox" id="prop-required" ${f.is_required ? 'checked' : ''}>
          <label class="form-check-label small fw-bold" for="prop-required">Required Field</label>
        </div>
      </div>
    `;

    // Bind inputs to field in memory
    document.getElementById('prop-label').oninput = (e) => { f.label = e.target.value; this.renderCanvas(); };
    document.getElementById('prop-key').oninput = (e) => { f.field_key = e.target.value; };
    document.getElementById('prop-section').oninput = (e) => { f.section_title = e.target.value; };
    document.getElementById('prop-placeholder').oninput = (e) => { f.placeholder = e.target.value; this.renderCanvas(); };
    document.getElementById('prop-help').oninput = (e) => { f.help_text = e.target.value; this.renderCanvas(); };
    document.getElementById('prop-binding').onchange = (e) => { f.platform_metric_binding = e.target.value; this.renderCanvas(); };
    document.getElementById('prop-required').onchange = (e) => { f.is_required = e.target.checked; this.renderCanvas(); };
  }

  async saveToServer() {
    const saveBtn = document.getElementById('save-builder-btn');
    if (saveBtn) {
      saveBtn.disabled = true;
      saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Saving...';
    }

    try {
      const resp = await fetch(`/api/form/${this.formId}/save-fields`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fields: this.fields })
      });
      const data = await resp.json();
      if (data.status === 'success') {
        alert('Form field layout saved successfully!');
      } else {
        alert('Error saving: ' + (data.message || 'Unknown error'));
      }
    } catch (err) {
      alert('Network error saving form: ' + err.message);
    } finally {
      if (saveBtn) {
        saveBtn.disabled = false;
        saveBtn.innerHTML = '<i class="bi bi-cloud-check me-1"></i> Save Form Changes';
      }
    }
  }
}
