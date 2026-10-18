/**
 * LocoPilot Frontend Application Controller
 * Handles SSE real-time streaming, session management, file uploads, 
 * interactive permission gates, file browsing, watchdog timers, and visual audit logging.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const feedContainer = document.getElementById('feedContainer');
  const goalForm = document.getElementById('goalForm');
  const goalInput = document.getElementById('goalInput');
  const submitGoalBtn = document.getElementById('submitGoalBtn');
  const attachedFilesContainer = document.getElementById('attachedFilesContainer');
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

  // Inline icons (presentation only)
  const svg = (size, body, extra = '') =>
    `<svg class="ico" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" ${extra}>${body}</svg>`;
  const ICON = {
    folder: svg(15, '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'),
    folderOpen: svg(15, '<path d="m6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.54 6a2 2 0 0 1-1.95 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H18a2 2 0 0 1 2 2v2"/>'),
    file: svg(15, '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>'),
    fileSm: svg(13, '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>'),
    pdf: svg(15, '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="8" y1="13" x2="16" y2="13"/><line x1="8" y1="17" x2="13" y2="17"/>'),
    check: svg(14, '<polyline points="20 6 9 17 4 12"/>'),
    x: svg(14, '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>'),
    shield: svg(16, '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/>'),
    alert: svg(18, '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>'),
    report: svg(15, '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>')
  };

  // Sprite icon helper (the icon sprite lives in index.html)
  const sp = (name, cls = '') => `<svg class="i ${cls}" aria-hidden="true"><use href="#i-${name}"/></svg>`;

  // UI-shell elements (layout, search, context panel, status bar)
  const appLayout = document.getElementById('appLayout');
  const sidebarPanel = document.getElementById('sidebarPanel');
  const contextPanel = document.getElementById('contextPanel');
  const sessionTitleEl = document.getElementById('sessionTitle');
  const sessionSavedLabel = document.getElementById('sessionSavedLabel');
  const sidebarSearchBtn = document.getElementById('sidebarSearchBtn');
  const sidebarSearchRow = document.getElementById('sidebarSearchRow');
  const sidebarSearchInput = document.getElementById('sidebarSearchInput');
  const sidebarSearchEmpty = document.getElementById('sidebarSearchEmpty');
  const viewAllSessionsBtn = document.getElementById('viewAllSessionsBtn');
  const uploadsCountBadge = document.getElementById('uploadsCountBadge');
  const uploadAddBtn = document.getElementById('uploadAddBtn');
  const attachBtn = document.getElementById('attachBtn');
  const attachMenu = document.getElementById('attachMenu');
  const latestRunBody = document.getElementById('latestRunBody');
  const scenarioDetail = document.getElementById('scenarioDetail');
  const scenarioDesc = document.getElementById('scenarioDesc');
  const scenarioPath = document.getElementById('scenarioPath');
  const statusWorkspace = document.getElementById('statusWorkspace');
  const statusSaved = document.getElementById('statusSaved');
  const statusAgent = document.getElementById('statusAgent');
  const SESSION_PREVIEW_LIMIT = 5;
  const DROPZONE_HTML = `
    <span class="dz-main">${sp('upload')}<span>Drop files or browse</span></span>
    <span class="dz-sub">Files stay on this device</span>
  `;

  // UI-shell state (presentation only)
  let uploadedCount = 0;          // files uploaded in this browser session
  let showAllSessions = false;
  let workspaceFilesFlat = [];    // non-folder workspace files, for the Attach menu
  let treeGeneration = 0;         // guards async folder loads against refreshes
  let agentHealth = 'unknown';    // 'ready' | 'offline' | 'unknown'
  let agentHealthLabel = 'Checking agent';
  let isRunning = false;
  let latestRun = null;           // summary of the most recent run, built from stream events
  let sessionTitleHint = '';

  // State
  let currentSessionId = generateSessionId();
  let chatHistory = [];
  let currentAssistantBubble = null;
  let allAuditEntries = [];
  let allSessions = [];
  let watchdogTimer = null;
  let attachedFiles = [];
  const WATCHDOG_TIMEOUT_MS = 300000; // 300s for local CPU inference

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
      sessionsCountBadge.textContent = String(sessions.length);
    }

    if (!sessions.length) {
      sessionsListContainer.innerHTML = `<div class="loading-state">No saved sessions yet</div>`;
      updateViewAllLink(0);
      updateSessionHeader();
      applySidebarFilter();
      return;
    }

    sessionsListContainer.innerHTML = '';
    sessions.forEach(sess => {
      const item = document.createElement('div');
      const isActive = sess.id === currentSessionId;
      item.className = `session-item ${isActive ? 'active' : ''}`;
      item.id = `session-card-${sess.id}`;

      const previewText = sess.preview || 'Empty session';
      const timeStr = formatRelative(sess.updated_at || sess.created_at);
      item.dataset.search = previewText.toLowerCase();
      item.title = `${sess.message_count || 0} msgs`;

      item.innerHTML = `
        <div class="session-item-left">
          ${sp('message')}
          <div class="session-item-preview" title="${escapeHtml(previewText)}">${escapeHtml(previewText)}</div>
        </div>
        <div class="session-item-time">${timeStr}</div>
        <button class="session-delete-btn" title="Delete Session" aria-label="Delete session" data-session-id="${sess.id}">
          ${sp('x')}
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

    updateViewAllLink(sessions.length);
    updateSessionHeader();
    applySidebarFilter();
  }

  async function loadSession(sessionId) {
    try {
      currentSessionId = sessionId;
      sessionTitleHint = '';
      resetLatestRun();
      selectScenario(null);
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
            appendChatBubble(msg.role, msg.content, msg.timestamp);
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
    sessionTitleHint = '';
    resetLatestRun();
    selectScenario(null);
    updateSessionHeader();
    fetchSessions();
    console.log('Started new chat session:', currentSessionId);
  }

  const WELCOME_HERO_HTML = `
    <div class="welcome-hero" id="welcomeHero">
      <h2>What should LocoPilot do in your workspace?</h2>
      <p>Describe a goal. LocoPilot reads your local files, shows its plan, and asks before it writes anything.</p>
      <div class="hero-features">
        <div class="feat-item"><strong>Runs on your machine</strong><span>Inference happens locally through Ollama.</span></div>
        <div class="feat-item"><strong>Five fixed tools</strong><span>No shell access and no generated code. It can list, read, search, create a file and create a folder.</span></div>
        <div class="feat-item"><strong>You approve every write</strong><span>Creating a file or folder always waits for your decision.</span></div>
        <div class="feat-item"><strong>Verified and logged</strong><span>Each change is checked on disk and recorded in the audit log.</span></div>
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
        if (data.ollama && data.ollama.online === false) {
          agentHealth = 'offline'; agentHealthLabel = 'Ollama offline';
        } else if (data.ollama && data.ollama.model_ready === false) {
          agentHealth = 'offline'; agentHealthLabel = 'Model not ready';
        } else {
          agentHealth = 'ready'; agentHealthLabel = 'Agent ready';
        }
        setAgentStatus();
        renderLatestRun();
      }
    } catch (e) {
      console.warn('Health check error:', e);
      agentHealth = 'offline'; agentHealthLabel = 'Backend unreachable';
      setAgentStatus();
    }
  }

  // --- Workspace File Management & Upload (Issue 1) ---

  async function fetchWorkspaceFiles() {
    try {
      const res = await fetch('/api/workspace/files');
      if (res.ok) {
        const data = await res.json();
        renderFileList(data.items || []);
        setWorkspaceStatus(true);
      } else {
        setWorkspaceStatus(false);
      }
    } catch (e) {
      workspaceFileList.innerHTML = `<div class="loading-state">Failed to load files</div>`;
      setWorkspaceStatus(false);
    }
  }

  function renderFileList(items) {
    treeGeneration++;
    workspaceFilesFlat = [];
    if (!items.length) {
      workspaceFileList.innerHTML = `<div class="loading-state">No files in workspace</div>`;
      applySidebarFilter();
      return;
    }

    workspaceFileList.innerHTML = '';
    let folderBudget = 12; // cap eager folder listings
    items.forEach(item => {
      if (item.type === 'directory') {
        workspaceFileList.appendChild(createDirGroup(item, 0, folderBudget-- > 0, treeGeneration));
      } else {
        workspaceFilesFlat.push(item);
        workspaceFileList.appendChild(createFileRow(item, 0));
      }
    });
    applySidebarFilter();
  }

  // Folder row + its (lazily loaded) children. Listing uses the existing ?subpath= endpoint.
  function createDirGroup(item, depth, loadChildren, generation) {
    const group = document.createElement('div');
    const startExpanded = depth === 0 && item.name === 'output';
    group.className = `tree-dir${startExpanded ? '' : ' collapsed'}`;

    const row = document.createElement('div');
    row.className = 'file-tree-item is-dir';
    row.style.setProperty('--depth', depth);
    row.dataset.name = String(item.name).toLowerCase();
    row.innerHTML = `
      <div class="file-info">
        ${startExpanded ? ICON.folderOpen : ICON.folder}
        <span class="file-name" title="${escapeHtml(item.name)}">${escapeHtml(item.name)}</span>
      </div>
      <div class="file-meta"><span class="dir-count"></span></div>
    `;

    const children = document.createElement('div');
    children.className = 'tree-children';

    row.addEventListener('click', () => {
      const collapsed = group.classList.toggle('collapsed');
      const icon = row.querySelector('.file-info svg');
      if (icon) icon.outerHTML = collapsed ? ICON.folder : ICON.folderOpen;
    });

    group.appendChild(row);
    group.appendChild(children);
    if (loadChildren && item.relative_path !== undefined) {
      loadDirChildren(item, children, row, depth + 1, generation);
    }
    return group;
  }

  async function loadDirChildren(dirItem, childrenEl, rowEl, depth, generation) {
    try {
      const res = await fetch(`/api/workspace/files?subpath=${encodeURIComponent(dirItem.relative_path)}`);
      if (!res.ok || generation !== treeGeneration) return;
      const data = await res.json();
      if (generation !== treeGeneration) return;
      const kids = data.items || [];
      const countEl = rowEl.querySelector('.dir-count');
      if (countEl) countEl.textContent = String(kids.length);
      childrenEl.innerHTML = '';
      kids.forEach(k => {
        if (k.type === 'directory') {
          childrenEl.appendChild(createDirGroup(k, depth, depth < 3, generation));
        } else {
          workspaceFilesFlat.push(k);
          childrenEl.appendChild(createFileRow(k, depth));
        }
      });
      applySidebarFilter();
    } catch (e) {
      // folder contents are optional detail; the folder row still renders
    }
  }

  function createFileRow(item, depth) {
      const el = document.createElement('div');
      el.className = 'file-tree-item';
      el.style.setProperty('--depth', depth);
      el.dataset.name = String(item.name).toLowerCase();

      const isDir = item.type === 'directory';
      const icon = isDir ? ICON.folder : (item.extension === '.pdf' ? ICON.pdf : ICON.file);
      const sizeStr = item.size_bytes !== null ? `${(item.size_bytes / 1024).toFixed(1)} KB` : '';
      if (sizeStr) el.title = sizeStr;

      let deleteHtml = '';
      if (!isDir) {
        deleteHtml = `
          <button class="file-delete-btn" title="Delete File" aria-label="Delete file" data-filepath="${escapeHtml(item.relative_path)}" data-filename="${escapeHtml(item.name)}">
            ${sp('trash')}
          </button>
        `;
      }

      el.innerHTML = `
        <div class="file-info">
          ${icon}
          <span class="file-name" title="${escapeHtml(item.name)}">${escapeHtml(item.name)}</span>
        </div>
        <div class="file-meta">
          <span class="file-size">${sizeStr}</span>
          ${deleteHtml}
        </div>
      `;

      if (!isDir) {
        el.draggable = true;
        el.addEventListener('dragstart', (e) => {
          e.dataTransfer.setData('application/x-locopilot-file', item.relative_path);
          e.dataTransfer.setData('text/plain', item.name);
          el.classList.add('dragging');
        });
        el.addEventListener('dragend', () => {
          el.classList.remove('dragging');
        });

        el.addEventListener('click', (e) => {
          if (e.target.closest('.file-delete-btn')) return;
          openFileModal(item.relative_path, item.name);
        });
        
        const delBtn = el.querySelector('.file-delete-btn');
        if (delBtn) {
          delBtn.addEventListener('click', async (e) => {
            e.stopPropagation();
            if (confirm(`Delete ${item.name}?`)) {
              try {
                const res = await fetch(`/api/workspace/files?filepath=${encodeURIComponent(item.relative_path)}`, { method: 'DELETE' });
                if (res.ok) {
                  const data = await res.json();
                  appendEventCard('understand', 'File deleted and index rebuilt', `
                    <div>Deleted <strong>${escapeHtml(item.name)}</strong> from the workspace.</div>
                    <div class="event-note">Knowledge index rebuilt automatically (${data.indexed_chunks} chunks).</div>
                  `);
                  fetchWorkspaceFiles();
                } else {
                  const err = await res.json();
                  alert('Delete failed: ' + (err.detail || 'Unknown error'));
                }
              } catch (err) {
                alert('Network error while deleting: ' + err.message);
              }
            }
          });
        }
      }

      return el;
  }

  async function handleFileUpload(files) {
    if (!files || files.length === 0) return;

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }
    if (currentSessionId) {
      formData.append('session_id', currentSessionId);
    }

    uploadFilesBtn.disabled = true;
    uploadFilesBtn.innerHTML = `<span class="dz-busy">Uploading...</span>`;

    try {
      const res = await fetch('/api/workspace/upload', {
        method: 'POST',
        body: formData
      });

      if (res.ok) {
        const data = await res.json();
        appendEventCard('understand', 'Files uploaded and index rebuilt', `
          <div>Imported <strong>${data.count}</strong> file(s) into the workspace:</div>
          <div class="event-list">
            ${(data.uploaded || []).map(f => `&bull; ${escapeHtml(f)}`).join('<br>')}
          </div>
          <div class="event-note">Knowledge index rebuilt automatically.</div>
        `);
        uploadedCount += Number(data.count) || 0;
        if (uploadsCountBadge) uploadsCountBadge.textContent = String(uploadedCount);
        fetchWorkspaceFiles();
      } else {
        const err = await res.json();
        alert('File upload failed: ' + (err.detail || 'Unknown error'));
      }
    } catch (e) {
      alert('File upload network error: ' + e.message);
    } finally {
      uploadFilesBtn.disabled = false;
      uploadFilesBtn.innerHTML = DROPZONE_HTML;
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
      <div class="event-card-body">
        Starting the on-device pipeline...
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
      appendEventCard('timeout', 'Response timed out', `
        <div>The local model took longer than ${WATCHDOG_TIMEOUT_MS / 1000} seconds to respond.</div>
        <div class="event-note">The stream was closed and the input is unlocked. Retry with a more specific request, or check that Ollama is running.</div>
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

    const requestAttachedFiles = [...attachedFiles];
    
    // Clear input box and attached files
    goalInput.value = '';
    attachedFiles = [];
    if (typeof renderAttachedFiles === 'function') renderAttachedFiles();

    // Remove welcome hero if present
    const hero = document.getElementById('welcomeHero');
    if (hero) hero.remove();

    // Reset current assistant bubble
    currentAssistantBubble = null;

    // Append user bubble
    appendChatBubble('user', goalText);

    // Header, status bar and "Latest run" panel (presentation only)
    if (!sessionTitleHint) sessionTitleHint = goalText.replace(/\s+/g, ' ').slice(0, 75);
    isRunning = true;
    latestRunStart();
    updateSessionHeader();
    setAgentStatus();

    // Show immediate progress card
    showThinkingIndicator('Processing workspace request...');

    // Reset UI stages
    resetStages();
    setStageActive('understand');
    submitGoalBtn.disabled = true;

    const abortController = new AbortController();
    resetWatchdog(abortController);

    try {
      let response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: goalText,
          history: chatHistory,
          session_id: currentSessionId,
          attached_files: requestAttachedFiles
        }),
        signal: abortController.signal
      });

      // If /api/chat/stream returned 404, fallback to /api/agent/run
      if (response.status === 404) {
        console.warn('/api/chat/stream returned 404. Falling back to /api/agent/run...');
        response = await fetch('/api/agent/run', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            goal: goalText,
            session_id: currentSessionId,
            attached_files: requestAttachedFiles
          }),
          signal: abortController.signal
        });
      }

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Server returned HTTP 404. The backend server needs to be restarted so the latest API endpoints are loaded. Please restart with: python run.py');
        }
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
                resetWatchdog(abortController); // Keep the connection alive for every SSE event
                handlePipelineEvent(eventData, (text, isFull) => {
                  if (isFull) {
                    currentAssistantMessage = text;
                  } else {
                    currentAssistantMessage += text;
                  }
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
        appendEventCard('error', 'Execution error', e.message);
      }
    } finally {
      clearWatchdog();
      removeThinkingIndicator();
      submitGoalBtn.disabled = false;
      isRunning = false;
      latestRunEnd();
      setAgentStatus();
      fetchWorkspaceFiles();
      fetchAuditLogs();
      fetchSessions();
    }
  }

  // --- Event Stream Handler ---

  function handlePipelineEvent(event, appendTextFn) {
    console.log('Pipeline Event:', event);
    try { trackRunEvent(event); } catch (e) { console.warn('Run tracking skipped:', e); }

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
        appendEventCard('session', 'Session started', `Goal: <strong>${escapeHtml(event.goal)}</strong>`);
        break;

      case 'UNDERSTAND':
        removeThinkingIndicator();
        setStageActive('understand');
        appendEventCard('understand', 'Intent', `
          <div>Classified Intent: <span class="badge-tag">${event.classification}</span></div>
          <div class="event-note">${event.message}</div>
        `);
        break;

      case 'KNOWLEDGE_RETRIEVED':
        setStageActive('rag');
        let sourcesHtml = '';
        if (event.sources && event.sources.length) {
          sourcesHtml = '<div class="sources-pill-row">' + event.sources.map(s => `
            <div class="source-chip" onclick="openFileModal('${escapeHtml(s.relative_path)}', '${escapeHtml(s.filename)}')">
              ${ICON.fileSm}${escapeHtml(s.filename)} <span class="score">${s.score}</span>
            </div>
          `).join('') + '</div>';
        }
        appendEventCard('rag', 'Local files searched', `
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
              <div>
                <span class="step-tool-badge">${st.tool}</span>
                <span class="badge-risk ${st.risk_level.toLowerCase()}">${st.risk_level}</span>
              </div>
            </div>
          `;
        });
        stepsHtml += '</div>';

        appendEventCard('plan', 'Plan', `
          <div class="plan-summary">${escapeHtml(plan.summary)}</div>
          ${stepsHtml}
        `);
        break;

      case 'STEP_STARTED':
        const stepRow = document.getElementById(`step-row-${event.step_id}`);
        if (stepRow) stepRow.classList.add('is-running');
        break;

      case 'SYNTHESIZING_CONTENT':
        appendEventCard('synthesis', 'Drafting content', `
          <div class="event-working">
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
        appendEventCard('tool', `Ran ${event.tool}`, `
          <div class="tool-meta">
            <span>Took ${event.execution_time_ms} ms</span>
            <span class="tool-status ${event.success ? 'ok' : 'fail'}">
              ${event.success ? ICON.check + 'Succeeded' : ICON.x + 'Failed'}
            </span>
          </div>
          <pre class="file-content-view tool-output">${escapeHtml(JSON.stringify(event.output || event.error, null, 2))}</pre>
        `);
        break;

      case 'ACTION_VERIFIED':
        setStageActive('verify');
        let checksHtml = event.checks.map(c => `
          <div class="check-row ${c.passed ? 'pass' : 'fail'}">
            ${c.passed ? ICON.check : ICON.x}<span><strong>${escapeHtml(c.name)}</strong>: ${escapeHtml(c.details)}</span>
          </div>
        `).join('');

        appendEventCard('verify', 'Verification', `
          <div class="verification-badge${event.checks.every(c => c.passed) ? '' : ' is-failed'}">
            ${ICON.shield}
            <strong>${escapeHtml(event.summary)}</strong>
          </div>
          <div class="check-list">
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
            <div class="source-chip">${ICON.fileSm}${escapeHtml(s.filename)}</div>
          `).join('') + '</div>';
        }

        appendFinalReportCard(event.final_answer, finalSourcesHtml);
        if (appendTextFn && event.final_answer) {
          appendTextFn(event.final_answer, true);
        }
        fetchAuditLogs();
        break;

      case 'ERROR':
        appendEventCard('error', 'Execution exception', event.message);
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
        ${ICON.alert}
        <span class="gate-title">Approval needed before this runs</span>
      </div>
      <div class="gate-meta">
        <span>Action <span class="step-tool-badge">${req.tool}</span></span>
        <span>Risk <span class="badge-risk high">${req.risk_level}</span></span>
      </div>
      <div class="gate-reason">
        <strong>Why:</strong> ${escapeHtml(req.reasoning)}
      </div>
      <div class="permission-preview-box">${escapeHtml(req.preview || JSON.stringify(req.params, null, 2))}</div>
      <div class="permission-actions">
        <button class="btn-approve" id="approve-${req.request_id}">Approve and run</button>
        <button class="btn-reject" id="reject-${req.request_id}">Reject</button>
      </div>
    `;

    feedContainer.appendChild(gateCard);

    document.getElementById(`approve-${req.request_id}`).addEventListener('click', async () => {
      await sendPermissionDecision(req.request_id, 'APPROVE');
      gateCard.classList.add('is-resolved');
      gateCard.innerHTML = `
        <div class="gate-resolved approved">
          ${ICON.check}Approved. Running the step...
        </div>
      `;
    });

    document.getElementById(`reject-${req.request_id}`).addEventListener('click', async () => {
      await sendPermissionDecision(req.request_id, 'REJECT');
      gateCard.classList.add('is-resolved');
      gateCard.innerHTML = `
        <div class="gate-resolved rejected">
          ${ICON.x}Rejected. The step was skipped.
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
    card.className = 'chat-bubble msg-assistant final-report-card';
    card.dataset.rawText = markdownText || '';
    const files = latestRun ? latestRun.files : [];
    const filesHtml = files.length
      ? `<div class="msg-files">${files.map(fileLinkChipHtml).join('')}</div>`
      : '';
    const warn = latestRun && latestRun.warnings.length ? latestRun.warnings[0] : null;
    const statusHtml = warn
      ? `<div class="msg-status">${sp('circle-alert')}<span>${escapeHtml(warn.title)} &middot; ${escapeHtml(warn.text)}</span></div>`
      : '';
    card.innerHTML = `
      <div class="msg-avatar" aria-hidden="true">${sp('command')}</div>
      <div class="msg-head"><span class="msg-name">LocoPilot</span><span class="msg-time">${formatClock()}</span></div>
      <div class="final-report-content">${renderMarkdown(markdownText)}</div>
      ${statusHtml}
      ${sourcesHtml}
      ${filesHtml}
      <div class="msg-actions"><button type="button" class="icon-btn" title="Copy message" aria-label="Copy message">${sp('copy')}</button></div>
    `;
    wireFileLinkChips(card);
    wireCopyButton(card);
    feedContainer.appendChild(card);
  }

  function appendChatBubble(role, content, timestamp) {
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble chat-bubble-${role}`;
    bubble.dataset.rawText = content || '';
    const isUser = role === 'user';
    const roleLabel = isUser ? 'You' : 'LocoPilot';
    const formattedHtml = isUser
      ? escapeHtml(content || '').replace(/\n/g, '<br>')
      : renderMarkdown(content || '');
    bubble.innerHTML = `
      <div class="msg-avatar" aria-hidden="true">${isUser ? 'Y' : sp('command')}</div>
      <div class="msg-head"><span class="msg-name">${roleLabel}</span><span class="msg-time">${formatClock(timestamp)}</span></div>
      <div class="bubble-content">${formattedHtml}</div>
      ${isUser ? '' : `<div class="msg-actions"><button type="button" class="icon-btn" title="Copy message" aria-label="Copy message">${sp('copy')}</button></div>`}
    `;
    wireCopyButton(bubble);
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
        summaryText = `LocoPilot system initialized`;
      } else {
        summaryText = escapeHtml(entry.action || entry.message || JSON.stringify(entry));
      }

      // Build meta pills
      let metaPills = '';
      if (entry.risk_level) {
        const isHigh = entry.risk_level === 'HIGH' || entry.risk_level === 'CRITICAL';
        metaPills += `<span class="audit-pill ${isHigh ? 'audit-pill-risk-high' : 'audit-pill-risk-low'}">${escapeHtml(String(entry.risk_level).charAt(0) + String(entry.risk_level).slice(1).toLowerCase())} risk</span>`;
      }
      if (entry.success !== undefined) {
        metaPills += `<span class="audit-pill ${entry.success ? 'audit-pill-success' : 'audit-pill-failure'}">${entry.success ? 'Succeeded' : 'Failed'}</span>`;
      }
      if (entry.execution_time_ms) {
        metaPills += `<span class="audit-pill">${entry.execution_time_ms} ms</span>`;
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
    a.download = `locopilot_audit_${Date.now()}.${format}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  // --- Event Listeners ---

  function renderAttachedFiles() {
    if (!attachedFilesContainer) return;
    attachedFilesContainer.innerHTML = '';
    if (attachedFiles.length === 0) {
      attachedFilesContainer.style.display = 'none';
      return;
    }
    attachedFilesContainer.style.display = 'flex';
    attachedFiles.forEach((file, idx) => {
      const chip = document.createElement('div');
      chip.className = 'attached-file-chip';
      const fileName = file.split('/').pop().split('\\').pop();
      chip.innerHTML = `
        <span class="attached-file-icon">${ICON.fileSm}</span>
        <span class="attached-file-name" title="${escapeHtml(file)}">${escapeHtml(fileName)}</span>
        <button type="button" class="remove-attached-file" title="Remove attachment">&times;</button>
      `;
      chip.querySelector('.remove-attached-file').addEventListener('click', () => {
        attachedFiles.splice(idx, 1);
        renderAttachedFiles();
      });
      attachedFilesContainer.appendChild(chip);
    });
  }

  goalForm.addEventListener('dragover', (e) => {
    e.preventDefault();
    if (e.dataTransfer.types.includes('application/x-locopilot-file')) {
      goalForm.classList.add('goal-form--drop-active');
    }
  });
  goalForm.addEventListener('dragleave', (e) => {
    e.preventDefault();
    goalForm.classList.remove('goal-form--drop-active');
  });
  goalForm.addEventListener('drop', (e) => {
    e.preventDefault();
    goalForm.classList.remove('goal-form--drop-active');
    const path = e.dataTransfer.getData('application/x-locopilot-file');
    if (path && !attachedFiles.includes(path)) {
      attachedFiles.push(path);
      renderAttachedFiles();
    }
  });

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
    selectScenario(demoPreset1);
    const prompt = `Review my resume (Alex_Rivera_Resume.md) and the job description (Job_Description_AI_Research_Intern.md), analyze skill gaps, and create a customized cover letter and tailored project action plan in output/tailored_application.md.`;
    goalInput.value = '';
    startAgentRun(prompt);
  });

  demoPreset2.addEventListener('click', () => {
    selectScenario(demoPreset2);
    const prompt = `Review Project_Alpha_Technical_Report.md and notes_q3_learnings.md, and synthesize the architectural principles of deterministic tool sandboxes and post-action verification.`;
    goalInput.value = '';
    startAgentRun(prompt);
  });

  demoPreset3.addEventListener('click', () => {
    selectScenario(demoPreset3);
    const prompt = `Search my workspace documents for all mentions of Stanford education, inference benchmarks, and tool safety guarantees.`;
    goalInput.value = '';
    startAgentRun(prompt);
  });

  // =====================================================================
  // UI shell: presentation-only helpers (layout, search, status bar,
  // "Latest run" panel, theme, drawers). Nothing here changes how the
  // agent, approvals, files or sessions work.
  // =====================================================================

  function formatRelative(isoStr) {
    if (!isoStr) return '';
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return '';
    const min = Math.floor((Date.now() - d.getTime()) / 60000);
    if (min < 1) return 'Now';
    if (min < 60) return `${min}m`;
    const h = Math.floor(min / 60);
    if (h < 24) return `${h}h`;
    const days = Math.floor(h / 24);
    if (days < 7) return `${days}d`;
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  }

  function formatClock(isoStr) {
    const d = isoStr ? new Date(isoStr) : new Date();
    if (isNaN(d.getTime())) return '';
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });
  }

  // --- Conversation header ---
  function updateSessionHeader() {
    if (!sessionTitleEl) return;
    const sess = allSessions.find(s => s.id === currentSessionId);
    const title = (sess && sess.preview) || sessionTitleHint || 'New chat';
    sessionTitleEl.textContent = title;
    sessionTitleEl.title = title;
    if (sessionSavedLabel) sessionSavedLabel.textContent = sess ? 'Saved locally' : '';
  }

  // --- Sidebar: "View all sessions" and search/filter ---
  function updateViewAllLink(total) {
    if (!viewAllSessionsBtn) return;
    viewAllSessionsBtn.hidden = total <= SESSION_PREVIEW_LIMIT;
    const label = viewAllSessionsBtn.querySelector('span');
    if (label) label.textContent = showAllSessions ? 'Show fewer sessions' : 'View all sessions';
  }

  if (viewAllSessionsBtn) {
    viewAllSessionsBtn.addEventListener('click', () => {
      showAllSessions = !showAllSessions;
      updateViewAllLink(allSessions.length);
      applySidebarFilter();
    });
  }

  function filterTreeNode(node, q, parentMatch) {
    if (node.classList.contains('tree-dir')) {
      const row = node.firstElementChild;
      const kids = node.lastElementChild;
      const selfMatch = parentMatch || !q || (row.dataset.name || '').includes(q);
      let anyChild = false;
      Array.from(kids.children).forEach(ch => { if (filterTreeNode(ch, q, selfMatch)) anyChild = true; });
      const visible = selfMatch || anyChild;
      node.hidden = !visible;
      return visible;
    }
    if (node.classList.contains('file-tree-item')) {
      const match = parentMatch || !q || (node.dataset.name || '').includes(q);
      node.hidden = !match;
      return match;
    }
    return false;
  }

  function applySidebarFilter() {
    const q = (sidebarSearchInput ? sidebarSearchInput.value : '').trim().toLowerCase();
    document.body.classList.toggle('is-searching', !!q);
    if (viewAllSessionsBtn) viewAllSessionsBtn.hidden = !!q || allSessions.length <= SESSION_PREVIEW_LIMIT;

    let sessionsVisible = 0;
    if (sessionsListContainer) {
      sessionsListContainer.querySelectorAll('.session-item').forEach((el, idx) => {
        const matches = !q || (el.dataset.search || '').includes(q);
        const overLimit = !q && !showAllSessions && idx >= SESSION_PREVIEW_LIMIT && !el.classList.contains('active');
        el.hidden = !matches || overLimit;
        if (!el.hidden) sessionsVisible++;
      });
    }

    let filesVisible = 0;
    if (workspaceFileList) {
      Array.from(workspaceFileList.children).forEach(node => {
        if (filterTreeNode(node, q, false)) filesVisible++;
      });
    }

    if (sidebarSearchEmpty) sidebarSearchEmpty.hidden = !(q && !sessionsVisible && !filesVisible);
  }

  // --- Status bar ---
  function setAgentStatus() {
    if (!statusAgent) return;
    let state = 'ready';
    let label = 'Agent ready';
    if (isRunning) { state = 'busy'; label = 'Agent working'; }
    else if (agentHealth === 'offline') { state = 'offline'; label = agentHealthLabel; }
    else if (agentHealth === 'unknown') { state = 'unknown'; label = agentHealthLabel; }
    statusAgent.dataset.state = state;
    statusAgent.textContent = label;
    if (statusSaved) statusSaved.hidden = isRunning;
  }

  function setWorkspaceStatus(ok) {
    if (!statusWorkspace) return;
    statusWorkspace.dataset.state = ok ? 'up' : 'down';
    const label = statusWorkspace.querySelector('span');
    if (label) label.textContent = ok ? 'Workspace connected' : 'Workspace unavailable';
  }

  // --- Saved-file links and copy ---
  function fileLinkChipHtml(path) {
    return `<button type="button" class="file-link-chip" data-path="${escapeHtml(path)}" title="Open ${escapeHtml(path)}">${sp('file')}<span>${escapeHtml(path)}</span>${sp('arrow-up-right', 'go')}</button>`;
  }

  function wireFileLinkChips(root) {
    root.querySelectorAll('.file-link-chip').forEach(chip => {
      chip.addEventListener('click', () => {
        const path = chip.dataset.path || '';
        openFileModal(path, path.split('/').pop());
      });
    });
  }

  async function copyText(text) {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
        return true;
      }
    } catch (e) { /* fall through to legacy path */ }
    try {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.cssText = 'position:fixed;opacity:0;';
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand('copy');
      ta.remove();
      return ok;
    } catch (e) { return false; }
  }

  function wireCopyButton(bubble) {
    const btn = bubble.querySelector('.msg-actions .icon-btn');
    if (!btn) return;
    btn.addEventListener('click', async () => {
      const ok = await copyText(bubble.dataset.rawText || '');
      if (!ok) return;
      btn.classList.add('is-done');
      btn.innerHTML = sp('check');
      setTimeout(() => { btn.classList.remove('is-done'); btn.innerHTML = sp('copy'); }, 1200);
    });
  }

  // --- Scenarios (right panel): selection highlight; clicking still runs the scenario ---
  function selectScenario(btn) {
    document.querySelectorAll('.scenario-item').forEach(b => b.classList.toggle('is-selected', b === btn));
    if (!scenarioDetail) return;
    if (!btn) { scenarioDetail.hidden = true; return; }
    if (scenarioDesc) scenarioDesc.textContent = btn.dataset.desc || '';
    if (scenarioPath) scenarioPath.innerHTML = escapeHtml(btn.dataset.path || 'No file requested').replace(/([/_])/g, '$1<wbr>');
    scenarioDetail.hidden = false;
  }

  document.querySelectorAll('[data-scenario-proxy]').forEach(btn => {
    btn.addEventListener('click', () => {
      const target = document.getElementById(btn.dataset.scenarioProxy);
      if (target) target.click();
    });
  });

  // --- "Latest run" panel, built from the real event stream ---
  function latestRunStart() {
    latestRun = { status: 'running', mode: 'agent', files: [], folders: [], warnings: [] };
    renderLatestRun();
  }

  function resetLatestRun() {
    latestRun = null;
    renderLatestRun();
  }

  function latestRunEnd() {
    if (latestRun && latestRun.status === 'running') {
      latestRun.status = 'stopped';
      renderLatestRun();
    }
  }

  function trackRunEvent(event) {
    if (!latestRun) return;
    switch (event.event) {
      case 'ROUTING':
        latestRun.mode = event.target === 'AGENT' ? 'agent' : 'chat';
        break;
      case 'KNOWLEDGE_RETRIEVED':
        if (Array.isArray(event.sources) && event.sources.length === 0) {
          latestRun.warnings.push({ title: 'No matching files', text: 'The search found nothing in your workspace for this request.' });
        }
        break;
      case 'TOOL_EXECUTED':
        if (event.success) {
          const out = event.output || {};
          if (event.tool === 'create_file' && out.filepath) latestRun.files.push(out.filepath);
          if (event.tool === 'create_folder' && out.folderpath) latestRun.folders.push(out.folderpath);
        } else {
          const why = typeof event.error === 'string' ? event.error : JSON.stringify(event.error || 'Unknown error');
          latestRun.warnings.push({ title: 'A step failed', text: `${event.tool}: ${why}` });
        }
        break;
      case 'ACTION_VERIFIED': {
        const failed = (event.checks || []).filter(c => !c.passed);
        if (failed.length) {
          latestRun.warnings.push({ title: 'Verification failed', text: failed.map(c => `${c.name}: ${c.details}`).join('; ') });
        }
        break;
      }
      case 'FINAL_REPORT':
      case 'CHAT_DONE':
        latestRun.status = 'complete';
        break;
      case 'ERROR':
        latestRun.status = 'failed';
        latestRun.warnings.push({ title: 'Run error', text: event.message || 'Unknown error' });
        break;
    }
    renderLatestRun();
  }

  function renderLatestRun() {
    if (!latestRunBody) return;
    if (!latestRun) {
      latestRunBody.innerHTML = `<div class="ctx-empty">No runs yet. Run a goal or pick a scenario and the result appears here.</div>`;
      return;
    }
    const r = latestRun;
    let cls = 'ok';
    let icon = sp('circle-check');
    let label;
    if (r.status === 'running') { cls = 'busy'; icon = '<span class="run-dot"></span>'; label = 'Running'; }
    else if (r.status === 'failed') { cls = 'fail'; icon = sp('circle-x'); label = 'Run failed'; }
    else if (r.status === 'stopped') { cls = 'fail'; icon = sp('circle-x'); label = 'Run stopped'; }
    else if (r.files.length) { label = 'Files saved'; }
    else if (r.mode === 'chat') { label = 'Reply ready'; }
    else { label = 'Run complete'; }

    const folderRow = r.folders.length
      ? `<div class="run-row"><span class="k">Folders created</span><span class="v">${r.folders.length}</span></div>`
      : '';
    const fileList = r.files.length
      ? `<div class="run-files">${r.files.map(fileLinkChipHtml).join('')}</div>`
      : '';
    const warnings = r.warnings.map(w => `
      <div class="run-warn">
        <div class="run-warn-title">${sp('circle-alert')}<span>${escapeHtml(w.title)}</span></div>
        <div class="run-warn-body">${escapeHtml(w.text)}</div>
      </div>`).join('');

    latestRunBody.innerHTML = `
      <div class="run-status ${cls}">${icon}<span>${label}</span></div>
      <div class="run-row"><span class="k">Model</span><span class="v">${escapeHtml(ollamaModelName ? ollamaModelName.textContent : '')}</span></div>
      <div class="run-row"><span class="k">Destination</span><span class="v">Local workspace</span></div>
      <div class="run-row"><span class="k">Files written</span><span class="v">${r.files.length}</span></div>
      ${folderRow}
      ${fileList}
      ${warnings}
    `;
    wireFileLinkChips(latestRunBody);
  }

  // --- Theme (light / dark), remembered in localStorage ---
  const themeLightBtn = document.getElementById('themeLightBtn');
  const themeDarkBtn = document.getElementById('themeDarkBtn');

  function applyTheme(theme, persist) {
    document.documentElement.setAttribute('data-theme', theme);
    if (themeLightBtn) themeLightBtn.setAttribute('aria-pressed', String(theme === 'light'));
    if (themeDarkBtn) themeDarkBtn.setAttribute('aria-pressed', String(theme === 'dark'));
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', theme === 'dark' ? '#1f2225' : '#ffffff');
    if (persist) {
      try { localStorage.setItem('locopilot-theme', theme); } catch (e) { /* storage unavailable */ }
    }
  }
  applyTheme(document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light', false);
  if (themeLightBtn) themeLightBtn.addEventListener('click', () => applyTheme('light', true));
  if (themeDarkBtn) themeDarkBtn.addEventListener('click', () => applyTheme('dark', true));

  // --- Collapsible sidebar / panel sections ---
  document.querySelectorAll('.side-section-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
      const section = btn.closest('.side-section');
      if (!section) return;
      const collapsed = section.classList.toggle('collapsed');
      btn.setAttribute('aria-expanded', String(!collapsed));
    });
  });

  // --- Sidebar search (client-side filter over sessions and files) ---
  if (sidebarSearchBtn && sidebarSearchRow && sidebarSearchInput) {
    sidebarSearchBtn.addEventListener('click', () => {
      const opening = sidebarSearchRow.hidden;
      sidebarSearchRow.hidden = !opening;
      sidebarSearchBtn.setAttribute('aria-expanded', String(opening));
      if (opening) {
        sidebarSearchInput.focus();
      } else {
        sidebarSearchInput.value = '';
        applySidebarFilter();
      }
    });
    sidebarSearchInput.addEventListener('input', applySidebarFilter);
    sidebarSearchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') { e.stopPropagation(); sidebarSearchBtn.click(); sidebarSearchBtn.focus(); }
    });
  }

  // --- Drawers: sidebar (<=900px) and session context (<=1180px); context collapses on desktop ---
  const sidebarToggleBtn = document.getElementById('sidebarToggleBtn');
  const contextToggleBtn = document.getElementById('contextToggleBtn');
  const closeContextBtn = document.getElementById('closeContextBtn');
  const layoutScrim = document.getElementById('layoutScrim');
  const mqCtx = window.matchMedia('(max-width: 1180px)');
  const mqSide = window.matchMedia('(max-width: 900px)');

  function ctxIsVisible() {
    return mqCtx.matches ? appLayout.classList.contains('ctx-open') : !appLayout.classList.contains('ctx-collapsed');
  }
  function setCtxVisible(show) {
    if (mqCtx.matches) appLayout.classList.toggle('ctx-open', show);
    else appLayout.classList.toggle('ctx-collapsed', !show);
    if (contextToggleBtn) contextToggleBtn.setAttribute('aria-expanded', String(show));
  }
  function setSidebarOpen(open) {
    appLayout.classList.toggle('sidebar-open', open);
    if (sidebarToggleBtn) sidebarToggleBtn.setAttribute('aria-expanded', String(open));
  }
  function closeDrawers() {
    appLayout.classList.remove('sidebar-open', 'ctx-open');
    if (sidebarToggleBtn) sidebarToggleBtn.setAttribute('aria-expanded', 'false');
    if (mqCtx.matches && contextToggleBtn) contextToggleBtn.setAttribute('aria-expanded', 'false');
  }

  if (contextToggleBtn) {
    contextToggleBtn.setAttribute('aria-expanded', String(ctxIsVisible()));
    contextToggleBtn.addEventListener('click', () => setCtxVisible(!ctxIsVisible()));
  }
  if (closeContextBtn) closeContextBtn.addEventListener('click', () => setCtxVisible(false));
  if (sidebarToggleBtn) sidebarToggleBtn.addEventListener('click', () => setSidebarOpen(!appLayout.classList.contains('sidebar-open')));
  if (layoutScrim) layoutScrim.addEventListener('click', closeDrawers);

  const onBreakpointChange = () => {
    closeDrawers();
    if (contextToggleBtn) contextToggleBtn.setAttribute('aria-expanded', String(ctxIsVisible()));
  };
  if (mqCtx.addEventListener) { mqCtx.addEventListener('change', onBreakpointChange); mqSide.addEventListener('change', onBreakpointChange); }

  if (sidebarPanel) {
    sidebarPanel.addEventListener('click', (e) => {
      if (mqSide.matches && e.target.closest('.session-item, .side-item, .file-tree-item:not(.is-dir)')) closeDrawers();
    });
  }
  if (contextPanel) {
    contextPanel.addEventListener('click', (e) => {
      if (mqCtx.matches && e.target.closest('.scenario-item')) closeDrawers();
    });
  }

  // --- Attach menu: attach an existing workspace file to the next goal ---
  function closeAttachMenu() {
    if (!attachMenu || attachMenu.hidden) return;
    attachMenu.hidden = true;
    if (attachBtn) attachBtn.setAttribute('aria-expanded', 'false');
  }

  function renderAttachMenu() {
    if (!workspaceFilesFlat.length) {
      attachMenu.innerHTML = `<div class="attach-empty">No workspace files to attach yet.</div>`;
      return;
    }
    attachMenu.innerHTML = workspaceFilesFlat.map(it => {
      const parts = String(it.relative_path).split('/');
      const dir = parts.length > 1 ? parts.slice(0, -1).join('/') : '';
      return `<button type="button" class="attach-item" role="menuitem" data-path="${escapeHtml(it.relative_path)}">${sp('file')}<span class="a-name">${escapeHtml(it.name)}</span>${dir ? `<span class="a-dir">${escapeHtml(dir)}</span>` : ''}</button>`;
    }).join('');
  }

  if (attachBtn && attachMenu) {
    attachBtn.addEventListener('click', () => {
      const opening = attachMenu.hidden;
      if (opening) renderAttachMenu();
      attachMenu.hidden = !opening;
      attachBtn.setAttribute('aria-expanded', String(opening));
    });
    attachMenu.addEventListener('click', (e) => {
      const item = e.target.closest('.attach-item');
      if (!item) return;
      const path = item.dataset.path;
      if (path && !attachedFiles.includes(path)) {
        attachedFiles.push(path);
        renderAttachedFiles();
      }
      closeAttachMenu();
      goalInput.focus();
    });
    document.addEventListener('click', (e) => {
      if (!attachMenu.hidden && !e.target.closest('.attach-wrap')) closeAttachMenu();
    });
  }

  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    closeAttachMenu();
    closeDrawers();
  });

  // --- Uploads: the "+" button and the drop zone use the existing upload handler ---
  if (uploadAddBtn && workspaceFileInput) {
    uploadAddBtn.addEventListener('click', () => workspaceFileInput.click());
  }
  if (uploadFilesBtn) {
    const dragHasFiles = (e) => e.dataTransfer && Array.from(e.dataTransfer.types || []).includes('Files');
    ['dragenter', 'dragover'].forEach(type => uploadFilesBtn.addEventListener(type, (e) => {
      if (dragHasFiles(e)) { e.preventDefault(); uploadFilesBtn.classList.add('drag-over'); }
    }));
    ['dragleave', 'drop'].forEach(type => uploadFilesBtn.addEventListener(type, () => uploadFilesBtn.classList.remove('drag-over')));
    uploadFilesBtn.addEventListener('drop', (e) => {
      if (dragHasFiles(e) && e.dataTransfer.files.length) {
        e.preventDefault();
        handleFileUpload(e.dataTransfer.files);
      }
    });
  }

  // Initial paint of shell state
  setAgentStatus();
  renderLatestRun();
  updateSessionHeader();

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
