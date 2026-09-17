/**
 * LocalGPT Frontend Application Controller
 * Handles SSE real-time streaming, interactive permission gates, file browsing, and audit logging.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const feedContainer = document.getElementById('feedContainer');
  const goalForm = document.getElementById('goalForm');
  const goalInput = document.getElementById('goalInput');
  const submitGoalBtn = document.getElementById('submitGoalBtn');
  const workspaceFileList = document.getElementById('workspaceFileList');
  const refreshFilesBtn = document.getElementById('refreshFilesBtn');
  const ollamaModelName = document.getElementById('ollamaModelName');
  const stageRibbon = document.getElementById('stageRibbon');
  
  // Audit Drawer
  const auditDrawer = document.getElementById('auditDrawer');
  const auditToggleBtn = document.getElementById('auditToggleBtn');
  const closeAuditBtn = document.getElementById('closeAuditBtn');
  const refreshAuditBtn = document.getElementById('refreshAuditBtn');
  const auditFilterInput = document.getElementById('auditFilterInput');
  const auditStreamContainer = document.getElementById('auditStreamContainer');

  // File Modal
  const fileModal = document.getElementById('fileModal');
  const modalFileName = document.getElementById('modalFileName');
  const modalFilePath = document.getElementById('modalFilePath');
  const modalFileContent = document.getElementById('modalFileContent');
  const closeModalBtn = document.getElementById('closeModalBtn');

  // Presets
  const demoPreset1 = document.getElementById('demoPreset1');
  const demoPreset2 = document.getElementById('demoPreset2');
  const demoPreset3 = document.getElementById('demoPreset3');

  let currentEventSource = null;
  let allAuditEntries = [];

  // Initialize
  checkSystemHealth();
  fetchWorkspaceFiles();
  fetchAuditLogs();

  // Polling for health check
  setInterval(checkSystemHealth, 20000);

  // --- API Functions ---

  async function checkSystemHealth() {
    try {
      const res = await fetch('/api/health');
      if (res.ok) {
        const data = await res.json();
        if (data.ollama && data.ollama.target_model) {
          ollamaModelName.textContent = data.ollama.target_model;
        }
      }
    } catch (e) {
      console.warn('Health check error:', e);
    }
  }

  async function fetchWorkspaceFiles() {
    try {
      const res = await fetch('/api/workspace/files');
      if (res.ok) {
        const data = await res.json();
        renderFileList(data.items || []);
      }
    } catch (e) {
      workspaceFileList.innerHTML = `<div class="loading-state">Failed to load files</div>`;
    }
  }

  function renderFileList(items) {
    if (!items.length) {
      workspaceFileList.innerHTML = `<div class="loading-state">No files in workspace</div>`;
      return;
    }

    workspaceFileList.innerHTML = '';
    items.forEach(item => {
      const el = document.createElement('div');
      el.className = 'file-tree-item';
      
      const isDir = item.type === 'directory';
      const icon = isDir ? '📁' : (item.extension === '.pdf' ? '📕' : '📄');
      const sizeStr = item.size_bytes !== null ? `${(item.size_bytes / 1024).toFixed(1)} KB` : '';

      el.innerHTML = `
        <div class="file-info">
          <span>${icon}</span>
          <span class="file-name" title="${item.name}">${item.name}</span>
        </div>
        <span class="file-size">${sizeStr}</span>
      `;

      if (!isDir) {
        el.addEventListener('click', () => openFileModal(item.relative_path, item.name));
      }

      workspaceFileList.appendChild(el);
    });
  }

  async function openFileModal(relativePath, fileName) {
    modalFileName.textContent = fileName;
    modalFilePath.textContent = relativePath;
    modalFileContent.textContent = 'Loading content...';
    fileModal.style.display = 'flex';

    try {
      const res = await fetch(`/api/workspace/file?filepath=${encodeURIComponent(relativePath)}`);
      if (res.ok) {
        const data = await res.json();
        modalFileContent.textContent = data.content || '[Empty File]';
      } else {
        modalFileContent.textContent = 'Failed to load file content.';
      }
    } catch (e) {
      modalFileContent.textContent = `Error: ${e.message}`;
    }
  }

  // --- Visual Process Tracker Ribbon ---

  function setStageActive(stageName) {
    const nodes = stageRibbon.querySelectorAll('.stage-node');
    let reached = false;
    nodes.forEach(node => {
      const st = node.getAttribute('data-stage');
      if (st === stageName) {
        reached = true;
        node.className = 'stage-node active';
      } else if (!reached) {
        node.className = 'stage-node completed';
      } else {
        node.className = 'stage-node';
      }
    });
  }

  function resetStages() {
    const nodes = stageRibbon.querySelectorAll('.stage-node');
    nodes.forEach(n => n.className = 'stage-node');
  }

  // --- Run Agent Pipeline (SSE) ---

  async function startAgentRun(goalText) {
    if (!goalText.trim()) return;

    // Reset UI
    feedContainer.innerHTML = '';
    resetStages();
    setStageActive('understand');
    submitGoalBtn.disabled = true;

    try {
      const response = await fetch('/api/agent/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal: goalText })
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop(); // Keep incomplete chunk

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const rawJson = line.replace('data: ', '').trim();
            if (rawJson) {
              try {
                const eventData = JSON.parse(rawJson);
                handlePipelineEvent(eventData);
              } catch (err) {
                console.error('Error parsing SSE event:', err, rawJson);
              }
            }
          }
        }
      }

    } catch (e) {
      appendEventCard('error', 'Execution Error', e.message);
    } finally {
      submitGoalBtn.disabled = false;
      fetchWorkspaceFiles();
      fetchAuditLogs();
    }
  }

  // --- Event Stream Handler ---

  function handlePipelineEvent(event) {
    console.log('Pipeline Event:', event);

    switch (event.event) {
      case 'SESSION_STARTED':
        appendEventCard('session', 'Local Session Initialized', `Goal: <strong>${escapeHtml(event.goal)}</strong>`);
        break;

      case 'UNDERSTAND':
        setStageActive('understand');
        appendEventCard('understand', 'Intent Classification', `
          <div>Classified Intent: <span class="badge-tag">${event.classification}</span></div>
          <div style="font-size:0.8rem; color:var(--text-muted); margin-top:4px;">${event.message}</div>
        `);
        break;

      case 'KNOWLEDGE_RETRIEVED':
        setStageActive('rag');
        let sourcesHtml = '';
        if (event.sources && event.sources.length) {
          sourcesHtml = '<div class="sources-pill-row">' + event.sources.map(s => `
            <div class="source-chip" onclick="openFileModal('${escapeHtml(s.relative_path)}', '${escapeHtml(s.filename)}')">
              📄 ${escapeHtml(s.filename)} <span style="opacity:0.7">(${s.score})</span>
            </div>
          `).join('') + '</div>';
        }
        appendEventCard('rag', 'Local Knowledge Retrieved (RAG)', `
          <div>${event.message}</div>
          ${sourcesHtml}
        `);
        break;

      case 'PLAN_GENERATED':
        setStageActive('plan');
        const plan = event.plan;
        let stepsHtml = '<div class="plan-steps-list">';
        plan.steps.forEach(st => {
          const isHigh = st.risk_level === 'HIGH';
          stepsHtml += `
            <div class="plan-step-item ${isHigh ? 'high-risk' : ''}" id="step-row-${st.id}">
              <div class="step-details-left">
                <span class="step-num">#${st.id}</span>
                <span class="step-desc">${escapeHtml(st.description)}</span>
              </div>
              <div style="display:flex; align-items:center; gap:8px;">
                <span class="step-tool-badge">${st.tool}</span>
                <span class="badge-risk ${st.risk_level.toLowerCase()}">${st.risk_level}</span>
              </div>
            </div>
          `;
        });
        stepsHtml += '</div>';

        appendEventCard('plan', 'Structured Execution Plan', `
          <div style="font-size:0.84rem; color:#cbd5e1; margin-bottom:6px;">${escapeHtml(plan.summary)}</div>
          ${stepsHtml}
        `);
        break;

      case 'STEP_STARTED':
        // Highlight active step
        const stepRow = document.getElementById(`step-row-${event.step_id}`);
        if (stepRow) stepRow.style.borderColor = 'var(--accent-cyan)';
        break;

      case 'SYNTHESIZING_CONTENT':
        appendEventCard('synthesis', 'Synthesizing Content', `
          <div style="display:flex; align-items:center; gap:8px;">
            <span class="pulse-dot blue"></span>
            <span>${event.message}</span>
          </div>
        `);
        break;

      case 'PERMISSION_REQUIRED':
        setStageActive('permission');
        renderPermissionGateCard(event);
        break;

      case 'PERMISSION_RESOLVED':
        // Notification handled by card update
        break;

      case 'TOOL_EXECUTED':
        setStageActive('execute');
        appendEventCard('tool', `Executed Tool: ${event.tool}`, `
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span style="font-size:0.75rem; color:var(--text-dim);">Execution Time: ${event.execution_time_ms} ms</span>
            <span style="font-size:0.75rem; color:${event.success ? 'var(--accent-emerald)' : 'var(--accent-rose)'};">
              ${event.success ? '✓ SUCCESS' : '✗ ERROR'}
            </span>
          </div>
          <pre class="file-content-view" style="max-height:120px; overflow-y:auto; background:rgba(0,0,0,0.3); padding:8px; border-radius:4px; font-size:0.75rem;">${escapeHtml(JSON.stringify(event.output || event.error, null, 2))}</pre>
        `);
        break;

      case 'ACTION_VERIFIED':
        setStageActive('verify');
        let checksHtml = event.checks.map(c => `
          <div style="font-size:0.75rem; color:${c.passed ? '#6ee7b7' : '#fda4af'};">
            ${c.passed ? '✓' : '✗'} <strong>${escapeHtml(c.name)}</strong>: ${escapeHtml(c.details)}
          </div>
        `).join('');

        appendEventCard('verify', 'Post-Action Verification', `
          <div class="verification-badge">
            <span>🛡️</span>
            <strong>${escapeHtml(event.summary)}</strong>
          </div>
          <div style="margin-top:8px; display:flex; flex-direction:column; gap:4px;">
            ${checksHtml}
          </div>
        `);
        // Refresh files list
        fetchWorkspaceFiles();
        break;

      case 'FINAL_REPORT':
        setStageActive('audit');
        let finalSourcesHtml = '';
        if (event.sources && event.sources.length) {
          finalSourcesHtml = '<div class="sources-pill-row">' + event.sources.map(s => `
            <div class="source-chip">📄 Source: ${escapeHtml(s.filename)}</div>
          `).join('') + '</div>';
        }

        appendFinalReportCard(event.final_answer, finalSourcesHtml);
        fetchAuditLogs();
        break;

      case 'ERROR':
        appendEventCard('error', 'Execution Exception', event.message);
        break;
    }

    // Scroll to bottom
    feedContainer.scrollTop = feedContainer.scrollHeight;
  }

  // --- Render Helpers ---

  function appendEventCard(type, title, htmlContent) {
    const card = document.createElement('div');
    card.className = `event-card event-card-${type}`;
    card.innerHTML = `
      <div class="event-card-header">
        <div class="event-card-title">${title}</div>
      </div>
      <div class="event-card-body">${htmlContent}</div>
    `;
    feedContainer.appendChild(card);
  }

  function renderPermissionGateCard(req) {
    const gateCard = document.createElement('div');
    gateCard.className = 'permission-gate-card';
    gateCard.id = `gate-${req.request_id}`;

    gateCard.innerHTML = `
      <div class="permission-gate-header">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#f43f5e" stroke-width="2">
          <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
        </svg>
        <span class="gate-title">HUMAN PERMISSION CHECKPOINT REQUIRED</span>
      </div>
      <div style="font-size:0.84rem; margin-bottom:8px;">
        <strong>Action:</strong> <span class="step-tool-badge">${req.tool}</span> &bull; 
        <strong>Risk:</strong> <span class="badge-risk high">${req.risk_level}</span>
      </div>
      <div style="font-size:0.8rem; color:var(--text-muted); margin-bottom:10px;">
        <strong>Reasoning:</strong> ${escapeHtml(req.reasoning)}
      </div>
      <div class="permission-preview-box">${escapeHtml(req.preview || JSON.stringify(req.params, null, 2))}</div>
      <div class="permission-actions">
        <button class="btn-approve" id="approve-${req.request_id}">✓ Approve Action</button>
        <button class="btn-reject" id="reject-${req.request_id}">✗ Reject Action</button>
      </div>
    `;

    feedContainer.appendChild(gateCard);

    document.getElementById(`approve-${req.request_id}`).addEventListener('click', async () => {
      await sendPermissionDecision(req.request_id, 'APPROVE');
      gateCard.innerHTML = `
        <div style="color:var(--accent-emerald); font-size:0.85rem; font-weight:600;">
          ✓ Action Approved by User. Resuming deterministic execution...
        </div>
      `;
    });

    document.getElementById(`reject-${req.request_id}`).addEventListener('click', async () => {
      await sendPermissionDecision(req.request_id, 'REJECT');
      gateCard.innerHTML = `
        <div style="color:var(--accent-rose); font-size:0.85rem; font-weight:600;">
          ✗ Action Rejected by User. Step skipped safely.
        </div>
      `;
    });
  }

  async function sendPermissionDecision(requestId, decision) {
    try {
      await fetch('/api/permission/respond', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ request_id: requestId, decision: decision })
      });
    } catch (e) {
      console.error('Error sending permission decision:', e);
    }
  }

  function appendFinalReportCard(markdownText, sourcesHtml) {
    const card = document.createElement('div');
    card.className = 'final-report-card';
    card.innerHTML = `
      <div class="event-card-header">
        <div class="event-card-title" style="font-size:1.05rem; color:#a5b4fc;">
          ✨ LocalGPT Synthesized Workspace Report
        </div>
      </div>
      <div class="final-report-content">${renderSimpleMarkdown(markdownText)}</div>
      ${sourcesHtml}
    `;
    feedContainer.appendChild(card);
  }

  // --- Audit Trail Drawer Logic ---

  async function fetchAuditLogs() {
    try {
      const res = await fetch('/api/audit/logs?limit=50');
      if (res.ok) {
        const data = await res.json();
        allAuditEntries = data.entries || [];
        renderAuditStream(allAuditEntries);
      }
    } catch (e) {
      auditStreamContainer.innerHTML = `<div class="loading-state">Failed to load audit logs</div>`;
    }
  }

  function renderAuditStream(entries) {
    const filter = (auditFilterInput.value || '').toLowerCase();
    const filtered = entries.filter(e => {
      const str = JSON.stringify(e).toLowerCase();
      return str.includes(filter);
    });

    if (!filtered.length) {
      auditStreamContainer.innerHTML = `<div class="loading-state">No matching audit records</div>`;
      return;
    }

    auditStreamContainer.innerHTML = '';
    // Show newest first
    filtered.slice().reverse().forEach(entry => {
      const el = document.createElement('div');
      el.className = 'audit-entry-card';

      const time = entry.timestamp ? entry.timestamp.split('T')[1].replace('Z', '') : '';
      el.innerHTML = `
        <div class="audit-entry-head">
          <span>${entry.event_type}</span>
          <span style="color:var(--text-dim);">${time}</span>
        </div>
        <div class="audit-entry-body">
          ${escapeHtml(JSON.stringify(entry, null, 2))}
        </div>
      `;
      auditStreamContainer.appendChild(el);
    });
  }

  // --- Event Listeners ---

  goalForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const text = goalInput.value.trim();
    if (text) {
      startAgentRun(text);
      goalInput.value = '';
    }
  });

  // Enter to submit (Shift+Enter for newline)
  goalInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      goalForm.dispatchEvent(new Event('submit'));
    }
  });

  refreshFilesBtn.addEventListener('click', fetchWorkspaceFiles);

  auditToggleBtn.addEventListener('click', () => {
    auditDrawer.classList.toggle('open');
    if (auditDrawer.classList.contains('open')) fetchAuditLogs();
  });
  closeAuditBtn.addEventListener('click', () => auditDrawer.classList.remove('open'));
  refreshAuditBtn.addEventListener('click', fetchAuditLogs);
  auditFilterInput.addEventListener('input', () => renderAuditStream(allAuditEntries));

  closeModalBtn.addEventListener('click', () => { fileModal.style.display = 'none'; });
  fileModal.addEventListener('click', (e) => {
    if (e.target === fileModal) fileModal.style.display = 'none';
  });

  // Demo Presets
  demoPreset1.addEventListener('click', () => {
    const prompt = `Review my resume (Alex_Rivera_Resume.md) and the job description (Job_Description_AI_Research_Intern.md), analyze skill gaps, and create a customized cover letter and tailored project action plan in output/tailored_application.md.`;
    goalInput.value = prompt;
    startAgentRun(prompt);
  });

  demoPreset2.addEventListener('click', () => {
    const prompt = `Review Project_Alpha_Technical_Report.md and notes_q3_learnings.md, and synthesize the architectural principles of deterministic tool sandboxes and post-action verification.`;
    goalInput.value = prompt;
    startAgentRun(prompt);
  });

  demoPreset3.addEventListener('click', () => {
    const prompt = `Search my workspace documents for all mentions of Stanford education, inference benchmarks, and tool safety guarantees.`;
    goalInput.value = prompt;
    startAgentRun(prompt);
  });

  // --- Helpers ---

  function escapeHtml(str) {
    if (typeof str !== 'string') return '';
    return str.replace(/&/g, '&amp;')
              .replace(/</g, '&lt;')
              .replace(/>/g, '&gt;')
              .replace(/"/g, '&quot;');
  }

  function renderSimpleMarkdown(md) {
    if (!md) return '';
    let html = escapeHtml(md);
    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Headings
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
    // Bullet points
    html = html.replace(/^\* (.*$)/gim, '<li>$1</li>');
    html = html.replace(/^- (.*$)/gim, '<li>$1</li>');
    // Newlines
    html = html.replace(/\n\n/g, '<p></p>');
    html = html.replace(/\n/g, '<br>');
    return html;
  }
});
