/**
 * LocalGPT Frontend Application Controller
 * Handles SSE real-time streaming, session management, file uploads, 
 * interactive permission gates, file browsing, watchdog timers, and visual audit logging.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const feedContainer = document.getElementById('feedContainer');
  const goalForm = document.getElementById('goalForm');
  const goalInput = document.getElementById('goalInput');
  const submitGoalBtn = document.getElementById('submitGoalBtn');
  const workspaceFileList = document.getElementById('workspaceFileList');
  const refreshFilesBtn = document.getElementById('refreshFilesBtn');
  const uploadFilesBtn = document.getElementById('uploadFilesBtn');
  const workspaceFileInput = document.getElementById('workspaceFileInput');
  const ollamaModelName = document.getElementById('ollamaModelName');
  const stageRibbon = document.getElementById('stageRibbon');
  const clearChatBtn = document.getElementById('clearChatBtn');
  const newChatBtn = document.getElementById('newChatBtn');
  
  // Sessions Section
  const sessionsListContainer = document.getElementById('sessionsListContainer');
  const sessionsCountBadge = document.getElementById('sessionsCountBadge');

  // Audit Drawer
  const auditDrawer = document.getElementById('auditDrawer');
  const auditToggleBtn = document.getElementById('auditToggleBtn');
  const closeAuditBtn = document.getElementById('closeAuditBtn');
  const refreshAuditBtn = document.getElementById('refreshAuditBtn');
  const exportAuditCsvBtn = document.getElementById('exportAuditCsvBtn');
  const auditFilterInput = document.getElementById('auditFilterInput');
  const auditStreamContainer = document.getElementById('auditStreamContainer');

  // File Modal
  const fileModal = document.getElementById('fileModal');
  const modalFileName = document.getElementById('modalFileName');
  const modalFilePath = document.getElementById('modalFilePath');
  const modalFileContent = document.getElementById('modalFileContent');
  const closeModalBtn = document.getElementById('closeModalBtn');

  // Demo Presets
  const demoPreset1 = document.getElementById('demoPreset1');
  const demoPreset2 = document.getElementById('demoPreset2');
  const demoPreset3 = document.getElementById('demoPreset3');

  // State
  let currentSessionId = generateSessionId();
  let chatHistory = [];
  let currentAssistantBubble = null;
  let allAuditEntries = [];
  let allSessions = [];
  let watchdogTimer = null;
  const WATCHDOG_TIMEOUT_MS = 120000; // 120 seconds safety timeout (ample headroom for local CPU inference)

  function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7);
  }

  // Initialize
  checkSystemHealth();
  fetchWorkspaceFiles();
  fetchAuditLogs();
  fetchSessions();

  // Polling for health check
  setInterval(checkSystemHealth, 20000);

  // --- Session Management (Issue 5) ---

  async function fetchSessions() {
    try {
      const res = await fetch('/api/chat/sessions');
      if (res.ok) {
        const data = await res.json();
        allSessions = data.sessions || [];
        renderSessionsList(allSessions);
      }
    } catch (e) {
      console.warn('Failed to load sessions:', e);
      if (sessionsListContainer) {
        sessionsListContainer.innerHTML = `<div class="loading-state">No sessions found</div>`;
      }
    }
  }

  function renderSessionsList(sessions) {
    if (!sessionsListContainer) return;
    
    if (sessionsCountBadge) {
      sessionsCountBadge.textContent = `${sessions.length} session${sessions.length === 1 ? '' : 's'}`;
    }

    if (!sessions.length) {
      sessionsListContainer.innerHTML = `<div class="loading-state" style="padding:10px;">No saved sessions yet</div>`;
      return;
    }

    sessionsListContainer.innerHTML = '';
    sessions.forEach(sess => {
      const item = document.createElement('div');
      const isActive = sess.id === currentSessionId;
      item.className = `session-item ${isActive ? 'active' : ''}`;
      item.id = `session-card-${sess.id}`;

      const previewText = sess.preview || 'Empty session';
      const timeStr = formatTimestamp(sess.updated_at || sess.created_at);

      item.innerHTML = `
        <div class="session-item-left">
          <div class="session-item-preview" title="${escapeHtml(previewText)}">${escapeHtml(previewText)}</div>
          <div class="session-item-time">${timeStr} &bull; ${sess.message_count || 0} msgs</div>
        </div>
        <button class="session-delete-btn" title="Delete Session" data-session-id="${sess.id}">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      `;

      item.addEventListener('click', (e) => {
        if (e.target.closest('.session-delete-btn')) return;
        loadSession(sess.id);
      });

      const delBtn = item.querySelector('.session-delete-btn');
      delBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        deleteSession(sess.id);
      });

      sessionsListContainer.appendChild(item);
    });
  }

  async function loadSession(sessionId) {
    try {
      currentSessionId = sessionId;
      const res = await fetch(`/api/chat/sessions/${encodeURIComponent(sessionId)}`);
      if (res.ok) {
        const data = await res.json();
        chatHistory = data.messages || [];
        feedContainer.innerHTML = '';
        currentAssistantBubble = null;
        removeThinkingIndicator();

        if (chatHistory.length === 0) {
          feedContainer.innerHTML = WELCOME_HERO_HTML;
        } else {
          chatHistory.forEach(msg => {
            appendChatBubble(msg.role, msg.content);
          });
        }
        renderSessionsList(allSessions);
      }
    } catch (e) {
      console.error('Failed to load session details:', e);
    }
  }

  async function deleteSession(sessionId) {
    try {
      await fetch(`/api/chat/sessions/${encodeURIComponent(sessionId)}`, { method: 'DELETE' });
      allSessions = allSessions.filter(s => s.id !== sessionId);
      if (currentSessionId === sessionId) {
        startNewChatSession();
      } else {
        renderSessionsList(allSessions);
      }
    } catch (e) {
      console.error('Failed to delete session:', e);
    }
  }

  function startNewChatSession() {
    currentSessionId = generateSessionId();
    chatHistory = [];
    currentAssistantBubble = null;
    goalInput.value = '';
    removeThinkingIndicator();
    feedContainer.innerHTML = WELCOME_HERO_HTML;
    resetStages();
    fetchSessions();
    console.log('Started new chat session:', currentSessionId);
  }

  const WELCOME_HERO_HTML = `
    <div class="welcome-hero" id="welcomeHero">
      <div class="hero-icon">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
          <line x1="8" y1="21" x2="16" y2="21"></line>
          <line x1="12" y1="17" x2="12" y2="21"></line>
        </svg>
      </div>
      <h2>LocalGPT Workspace Agent</h2>
      <p>Your on-device, privacy-preserving digital assistant. LocalGPT gathers context from your local documents, plans safe deterministic actions, requests your explicit permission for writes, and verifies every disk change.</p>
      <div class="hero-features">
        <div class="feat-item">&check; 100% Local Inference (Qwen)</div>
        <div class="feat-item">&check; 5 Whitelisted Deterministic Tools</div>
        <div class="feat-item">&check; Human Permission Checkpoint</div>
        <div class="feat-item">&check; Post-Action Verification</div>
      </div>
    </div>
  `;

  async function clearCurrentChat() {
    if (currentSessionId) {
      try {
        await fetch(`/api/chat/sessions/${encodeURIComponent(currentSessionId)}`, { method: 'DELETE' });
      } catch (e) {
        console.warn('Session delete warning:', e);
      }
    }
    startNewChatSession();
    fetchAuditLogs();
  }

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

  // --- Workspace File Management & Upload (Issue 1) ---

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

  async function handleFileUpload(files) {
    if (!files || files.length === 0) return;

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }

    uploadFilesBtn.disabled = true;
    uploadFilesBtn.innerHTML = `<span>Uploading...</span>`;

    try {
      const res = await fetch('/api/workspace/upload', {
        method: 'POST',
        body: formData
      });

      if (res.ok) {
        const data = await res.json();
        appendEventCard('understand', 'Files Uploaded & Reindexed', `
          <div>Successfully imported <strong>${data.count}</strong> file(s) into workspace:</div>
          <div style="font-size:0.75rem; color:var(--accent-cyan); margin-top:4px;">
            ${(data.uploaded || []).map(f => `&bull; ${escapeHtml(f)}`).join('<br>')}
          </div>
          <div style="font-size:0.72rem; color:var(--text-muted); margin-top:4px;">Workspace knowledge index rebuilt automatically.</div>
        `);
        fetchWorkspaceFiles();
      } else {
        const err = await res.json();
        alert('File upload failed: ' + (err.detail || 'Unknown error'));
      }
    } catch (e) {
      alert('File upload network error: ' + e.message);
    } finally {
      uploadFilesBtn.disabled = false;
      uploadFilesBtn.innerHTML = `
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="17 8 12 3 7 8"></polyline>
          <line x1="12" y1="3" x2="12" y2="15"></line>
        </svg>
        <span>Upload</span>
      `;
      workspaceFileInput.value = '';
    }
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

  function removeThinkingIndicator() {
    const el = document.getElementById('activeThinkingCard');
    if (el) el.remove();
  }

  function showThinkingIndicator(msg) {
    removeThinkingIndicator();
    const card = document.createElement('div');
    card.id = 'activeThinkingCard';
    card.className = 'event-card event-card-session';
    card.innerHTML = `
      <div class="event-card-header">
        <div class="event-card-title">
          <span class="pulse-dot blue"></span>
          <span>${escapeHtml(msg || 'Processing Request...')}</span>
        </div>
      </div>
      <div class="event-card-body" style="font-size:0.83rem; color:var(--text-muted);">
        Initializing on-device pipeline and preparing local workspace response...
      </div>
    `;
    feedContainer.appendChild(card);
    feedContainer.scrollTop = feedContainer.scrollHeight;
  }

  // --- Watchdog Safety Timer (Issue 4) ---

  function resetWatchdog(abortController) {
    if (watchdogTimer) clearTimeout(watchdogTimer);
    watchdogTimer = setTimeout(() => {
      console.warn(`[Watchdog] No event received in ${WATCHDOG_TIMEOUT_MS / 1000}s. Triggering safety timeout.`);
      if (abortController) {
        try { abortController.abort(); } catch (e) {}
      }
      removeThinkingIndicator();
      if (currentAssistantBubble && (!currentAssistantBubble.dataset.rawText || !currentAssistantBubble.dataset.rawText.trim())) {
        currentAssistantBubble.remove();
        currentAssistantBubble = null;
      }
      submitGoalBtn.disabled = false;
      appendEventCard('timeout', 'Response Watchdog Timeout', `
        <div style="color: #fda4af; font-size: 0.84rem;">
          The local model or pipeline took longer than ${WATCHDOG_TIMEOUT_MS / 1000} seconds to yield a response token.
        </div>
        <div style="font-size: 0.76rem; color: var(--text-muted); margin-top: 4px;">
          The stream has been safely closed and your input box is unlocked. You can retry with a more specific query or verify Ollama is healthy.
        </div>
      `);
    }, WATCHDOG_TIMEOUT_MS);
  }

  function clearWatchdog() {
    if (watchdogTimer) {
      clearTimeout(watchdogTimer);
      watchdogTimer = null;
    }
  }

  // --- Run Agent Pipeline (SSE) ---

  async function startAgentRun(goalText) {
    if (!goalText.trim()) return;

    // Immediately clear input box
    goalInput.value = '';

    // Remove welcome hero if present
    const hero = document.getElementById('welcomeHero');
    if (hero) hero.remove();

    // Reset current assistant bubble
    currentAssistantBubble = null;

    // Append user bubble
    appendChatBubble('user', goalText);

    // Show immediate progress card
    showThinkingIndicator('Processing workspace request...');

    // Reset UI stages
    resetStages();
    setStageActive('understand');
    submitGoalBtn.disabled = true;

    const abortController = new AbortController();
    resetWatchdog(abortController);

    try {
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: goalText,
          history: chatHistory,
          session_id: currentSessionId
        }),
        signal: abortController.signal
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      chatHistory.push({ role: 'user', content: goalText });
      let currentAssistantMessage = "";

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        resetWatchdog(abortController); // Heartbeat on incoming chunk

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop(); // Keep incomplete chunk

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const rawJson = line.replace('data: ', '').trim();
            if (rawJson) {
              try {
                const eventData = JSON.parse(rawJson);
                handlePipelineEvent(eventData, (text) => {
                  currentAssistantMessage += text;
                });
              } catch (err) {
                console.error('Error parsing SSE event:', err, rawJson);
              }
            }
          }
        }
      }

      if (currentAssistantMessage) {
        chatHistory.push({ role: 'assistant', content: currentAssistantMessage });
      }

    } catch (e) {
      if (e.name !== 'AbortError') {
        removeThinkingIndicator();
        appendEventCard('error', 'Execution Error', e.message);
      }
    } finally {
      clearWatchdog();
      removeThinkingIndicator();
      submitGoalBtn.disabled = false;
      fetchWorkspaceFiles();
      fetchAuditLogs();
      fetchSessions();
    }
  }

  // --- Event Stream Handler ---

  function handlePipelineEvent(event, appendTextFn) {
    console.log('Pipeline Event:', event);

    switch (event.event) {
      case 'ROUTING':
        setStageActive('understand');
        if (event.target === 'AGENT') {
          showThinkingIndicator(event.message || 'Executing agent workspace workflow...');
        } else {
          showThinkingIndicator(event.message || 'Consulting local knowledge base...');
        }
        break;

      case 'CHAT_START':
        showThinkingIndicator('Generating response with local engine...');
        break;

      case 'CHAT_TOKEN':
        removeThinkingIndicator();
        if (!currentAssistantBubble) {
          currentAssistantBubble = appendChatBubble('assistant', '');
          currentAssistantBubble.dataset.rawText = '';
        }
        if (currentAssistantBubble) {
          const raw = (currentAssistantBubble.dataset.rawText || '') + event.token;
          currentAssistantBubble.dataset.rawText = raw;
          const contentDiv = currentAssistantBubble.querySelector('.bubble-content');
          contentDiv.innerHTML = renderMarkdown(raw);
          if (appendTextFn) appendTextFn(event.token);
          feedContainer.scrollTop = feedContainer.scrollHeight;
        }
        break;

      case 'CHAT_DONE':
        removeThinkingIndicator();
        if (currentAssistantBubble && currentAssistantBubble.dataset.rawText) {
          const contentDiv = currentAssistantBubble.querySelector('.bubble-content');
          contentDiv.innerHTML = renderMarkdown(currentAssistantBubble.dataset.rawText);
        } else if (currentAssistantBubble && (!currentAssistantBubble.dataset.rawText || !currentAssistantBubble.dataset.rawText.trim())) {
          currentAssistantBubble.remove();
          currentAssistantBubble = null;
        }
        break;

      case 'SESSION_STARTED':
        removeThinkingIndicator();
        appendEventCard('session', 'Local Session Initialized', `Goal: <strong>${escapeHtml(event.goal)}</strong>`);
        break;

      case 'UNDERSTAND':
        removeThinkingIndicator();
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
        // Handled by card update
        break;

      case 'TOOL_EXECUTED':
        setStageActive('execute');
        appendEventCard('tool', `Executed Tool: ${event.tool}`, `
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span style="font-size:0.75rem; color:var(--text-dim);">Execution Time: ${event.execution_time_ms} ms</span>
            <span style="font-size:0.75rem; color:${event.success ? 'var(--accent-emerald)' : 'var(--accent-rose)'}; font-weight:600;">
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
        if (appendTextFn && event.final_answer) {
          appendTextFn(event.final_answer);
        }
        fetchAuditLogs();
        break;

      case 'ERROR':
        appendEventCard('error', 'Execution Exception', event.message);
        break;
    }

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
      <div class="final-report-content">${renderMarkdown(markdownText)}</div>
      ${sourcesHtml}
    `;
    feedContainer.appendChild(card);
  }

  function appendChatBubble(role, content) {
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble chat-bubble-${role}`;
    bubble.dataset.rawText = content || '';
    const icon = role === 'user' ? '👤' : '🤖';
    const formattedHtml = role === 'user' 
      ? escapeHtml(content || '').replace(/\n/g, '<br>')
      : renderMarkdown(content || '');
    bubble.innerHTML = `
      <div class="bubble-icon">${icon}</div>
      <div class="bubble-content">${formattedHtml}</div>
    `;
    feedContainer.appendChild(bubble);
    feedContainer.scrollTop = feedContainer.scrollHeight;
    return bubble;
  }

  // --- Audit Trail Presentation & CSV Export (Issue 3) ---

  async function fetchAuditLogs() {
    try {
      const res = await fetch('/api/audit/logs?limit=80');
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
    // Show newest records first
    filtered.slice().reverse().forEach((entry, idx) => {
      const el = document.createElement('div');
      el.className = 'audit-entry-card';

      const timeStr = formatTimestamp(entry.timestamp);
      const eventType = entry.event_type || 'EVENT';
      
      // Determine badge class
      let badgeClass = 'audit-badge-default';
      if (eventType.includes('TOOL')) badgeClass = 'audit-badge-tool';
      else if (eventType.includes('PERMISSION')) badgeClass = 'audit-badge-permission';
      else if (eventType.includes('VERIF')) badgeClass = 'audit-badge-verify';
      else if (eventType.includes('SESSION')) badgeClass = 'audit-badge-session';
      else if (eventType.includes('ERROR')) badgeClass = 'audit-badge-error';

      // Build readable human summary
      let summaryText = '';
      if (eventType === 'TOOL_EXECUTION') {
        summaryText = `Executed tool <strong>${escapeHtml(entry.tool || 'unknown')}</strong>`;
      } else if (eventType === 'PERMISSION_REQUEST') {
        summaryText = `Requested permission for <strong>${escapeHtml(entry.tool || 'action')}</strong>`;
      } else if (eventType === 'PERMISSION_RESPONSE') {
        summaryText = `User decision: <strong>${escapeHtml(entry.decision || 'RESOLVED')}</strong> for ${escapeHtml(entry.tool || 'step')}`;
      } else if (eventType === 'VERIFICATION') {
        summaryText = escapeHtml(entry.summary || 'Post-action disk state verified');
      } else if (eventType === 'SESSION_START') {
        summaryText = `Session goal: <em>${escapeHtml(entry.goal || 'General request')}</em>`;
      } else if (eventType === 'SYSTEM_STARTUP') {
        summaryText = `LocalGPT system initialized`;
      } else {
        summaryText = escapeHtml(entry.action || entry.message || JSON.stringify(entry));
      }

      // Build meta pills
      let metaPills = '';
      if (entry.risk_level) {
        const isHigh = entry.risk_level === 'HIGH' || entry.risk_level === 'CRITICAL';
        metaPills += `<span class="audit-pill ${isHigh ? 'audit-pill-risk-high' : 'audit-pill-risk-low'}">${entry.risk_level} RISK</span>`;
      }
      if (entry.success !== undefined) {
        metaPills += `<span class="audit-pill ${entry.success ? 'audit-pill-success' : 'audit-pill-failure'}">${entry.success ? '✓ SUCCESS' : '✗ FAILED'}</span>`;
      }
      if (entry.execution_time_ms) {
        metaPills += `<span class="audit-pill" style="color:var(--text-dim);">${entry.execution_time_ms} ms</span>`;
      }

      const cardId = `audit-entry-${idx}`;
      el.innerHTML = `
        <div class="audit-card-head">
          <span class="audit-badge ${badgeClass}">${escapeHtml(eventType)}</span>
          <span class="audit-card-time">${timeStr}</span>
        </div>
        <div class="audit-card-summary">${summaryText}</div>
        <div class="audit-card-meta">
          ${metaPills}
          <button class="audit-details-toggle" data-target="${cardId}">View Raw</button>
        </div>
        <div class="audit-details-content" id="${cardId}" style="display:none;">${escapeHtml(JSON.stringify(entry, null, 2))}</div>
      `;

      const toggleBtn = el.querySelector('.audit-details-toggle');
      toggleBtn.addEventListener('click', () => {
        const content = el.querySelector(`#${cardId}`);
        const isHidden = content.style.display === 'none';
        content.style.display = isHidden ? 'block' : 'none';
        toggleBtn.textContent = isHidden ? 'Hide Raw' : 'View Raw';
      });

      auditStreamContainer.appendChild(el);
    });
  }

  function downloadAuditExport(format = 'csv') {
    const url = `/api/audit/export?format=${encodeURIComponent(format)}`;
    const a = document.createElement('a');
    a.href = url;
    a.download = `localgpt_audit_${Date.now()}.${format}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
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

  goalInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      goalForm.dispatchEvent(new Event('submit'));
    }
  });

  if (newChatBtn) {
    newChatBtn.addEventListener('click', startNewChatSession);
  }

  if (clearChatBtn) {
    clearChatBtn.addEventListener('click', clearCurrentChat);
  }

  if (uploadFilesBtn && workspaceFileInput) {
    uploadFilesBtn.addEventListener('click', () => workspaceFileInput.click());
    workspaceFileInput.addEventListener('change', (e) => {
      handleFileUpload(e.target.files);
    });
  }

  refreshFilesBtn.addEventListener('click', fetchWorkspaceFiles);

  auditToggleBtn.addEventListener('click', () => {
    auditDrawer.classList.toggle('open');
    if (auditDrawer.classList.contains('open')) fetchAuditLogs();
  });
  closeAuditBtn.addEventListener('click', () => auditDrawer.classList.remove('open'));
  refreshAuditBtn.addEventListener('click', fetchAuditLogs);
  auditFilterInput.addEventListener('input', () => renderAuditStream(allAuditEntries));

  if (exportAuditCsvBtn) {
    exportAuditCsvBtn.addEventListener('click', () => downloadAuditExport('csv'));
  }

  closeModalBtn.addEventListener('click', () => { fileModal.style.display = 'none'; });
  fileModal.addEventListener('click', (e) => {
    if (e.target === fileModal) fileModal.style.display = 'none';
  });

  // Demo Presets
  demoPreset1.addEventListener('click', () => {
    const prompt = `Review my resume (Alex_Rivera_Resume.md) and the job description (Job_Description_AI_Research_Intern.md), analyze skill gaps, and create a customized cover letter and tailored project action plan in output/tailored_application.md.`;
    goalInput.value = '';
    startAgentRun(prompt);
  });

  demoPreset2.addEventListener('click', () => {
    const prompt = `Review Project_Alpha_Technical_Report.md and notes_q3_learnings.md, and synthesize the architectural principles of deterministic tool sandboxes and post-action verification.`;
    goalInput.value = '';
    startAgentRun(prompt);
  });

  demoPreset3.addEventListener('click', () => {
    const prompt = `Search my workspace documents for all mentions of Stanford education, inference benchmarks, and tool safety guarantees.`;
    goalInput.value = '';
    startAgentRun(prompt);
  });

  // --- Helpers ---

  function formatTimestamp(isoStr) {
    if (!isoStr) return '';
    try {
      const d = new Date(isoStr);
      if (isNaN(d.getTime())) {
        return isoStr.includes('T') ? isoStr.split('T')[1].replace('Z', '') : isoStr;
      }
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch (e) {
      return isoStr;
    }
  }

  function escapeHtml(str) {
    if (typeof str !== 'string') return '';
    return str.replace(/&/g, '&amp;')
              .replace(/</g, '&lt;')
              .replace(/>/g, '&gt;')
              .replace(/"/g, '&quot;');
  }

  function renderMarkdown(md) {
    if (!md) return '';

    // 1. If marked.js is available from CDN
    if (typeof window.marked !== 'undefined' && typeof window.marked.parse === 'function') {
      try {
        return window.marked.parse(md, { breaks: true, gfm: true });
      } catch (err) {
        console.warn('marked.parse error, fallback to built-in parser:', err);
      }
    }

    // 2. Comprehensive offline Markdown parser
    let text = escapeHtml(md);

    // Code blocks with ```
    text = text.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
      return `<pre><code class="language-${lang}">${code}</code></pre>`;
    });

    // Inline code `code`
    text = text.replace(/`([^`\n]+)`/g, '<code>$1</code>');

    // Headings
    text = text.replace(/^#### (.*$)/gim, '<h4>$1</h4>');
    text = text.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    text = text.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    text = text.replace(/^# (.*$)/gim, '<h1>$1</h1>');

    // Bold & Italics
    text = text.replace(/\*\*\*(.*?)\*\*\*/g, '<strong><em>$1</em></strong>');
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    text = text.replace(/__([^_]+)__/g, '<strong>$1</strong>');
    text = text.replace(/\*([^\*\n]+)\*/g, '<em>$1</em>');

    // Blockquotes
    text = text.replace(/^>\s?(.*$)/gim, '<blockquote>$1</blockquote>');

    // Numbered lists
    text = text.replace(/^(\d+)\.\s+(.*$)/gim, '<div class="list-item-ordered"><span class="list-num">$1.</span> $2</div>');

    // Bullet lists
    text = text.replace(/^[\*\-]\s+(.*$)/gim, '<div class="list-item-bullet"><span class="bullet-dot">&bull;</span> $1</div>');

    // Paragraph breaks
    text = text.replace(/\n\n+/g, '<p></p>');
    text = text.replace(/\n/g, '<br>');

    return text;
  }
});
