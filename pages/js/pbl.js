/* ============================================
   PBL System JavaScript - SCNU LIKELION
   ============================================ */

const API_BASE = '/api';

// ---- API Helper ----
async function fetchAPI(endpoint, options = {}) {
  const token = localStorage.getItem('pbl_token');
  const headers = { ...(options.headers || {}) };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }
  const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
  if (res.status === 401) {
    localStorage.removeItem('pbl_token');
    localStorage.removeItem('pbl_user');
    window.location.href = 'login.html';
    throw new Error('Unauthorized');
  }
  const data = await res.json();
  if (!res.ok) throw new Error(data.message || 'API Error');
  return data;
}

// ---- Auth ----
function getUser() {
  try { return JSON.parse(localStorage.getItem('pbl_user')); } catch { return null; }
}

function isLoggedIn() {
  return !!localStorage.getItem('pbl_token');
}

function isAdmin() {
  const u = getUser();
  return u && u.role === 'admin';
}

function requireAuth() {
  if (!isLoggedIn()) {
    window.location.href = 'login.html';
  }
}

function requireAdmin() {
  requireAuth();
  if (!isAdmin()) {
    window.location.href = 'missions.html';
  }
}

function logout() {
  localStorage.removeItem('pbl_token');
  localStorage.removeItem('pbl_user');
  window.location.href = 'login.html';
}

// ---- Login / Register ----
async function handleLogin(e) {
  e.preventDefault();
  const form = e.target;
  const email = form.querySelector('[name="email"]').value.trim();
  const password = form.querySelector('[name="password"]').value;
  try {
    const data = await fetchAPI('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    localStorage.setItem('pbl_token', data.token);
    localStorage.setItem('pbl_user', JSON.stringify(data.user));
    showToast('success', '로그인 성공!');
    setTimeout(() => window.location.href = 'missions.html', 500);
  } catch (err) {
    showToast('error', err.message || '로그인 실패');
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const form = e.target;
  const payload = {
    email: form.querySelector('[name="email"]').value.trim(),
    password: form.querySelector('[name="password"]').value,
    name: form.querySelector('[name="name"]').value.trim(),
    track: form.querySelector('[name="track"]').value,
    team: parseInt(form.querySelector('[name="team"]').value, 10),
  };
  try {
    const data = await fetchAPI('/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    localStorage.setItem('pbl_token', data.token);
    localStorage.setItem('pbl_user', JSON.stringify(data.user));
    showToast('success', '회원가입 성공!');
    setTimeout(() => window.location.href = 'missions.html', 500);
  } catch (err) {
    showToast('error', err.message || '회원가입 실패');
  }
}

// ---- Missions ----
async function loadMissions(container) {
  const user = getUser();
  if (!user) return;
  try {
    const data = await fetchAPI(`/missions?track=${user.track}`);
    const missions = data.missions || [];
    container.innerHTML = missions.length === 0
      ? '<p class="text-muted text-center">등록된 미션이 없습니다.</p>'
      : missions.map(m => `
        <div class="pbl-card mission-card" onclick="location.href='submit.html?id=${m.id}'">
          <div class="mission-number">Mission ${String(m.number).padStart(2, '0')}</div>
          <div class="mission-title">${escapeHTML(m.title)}</div>
          <div class="mission-meta">
            <span>${m.estimated_time || '-'}</span>
            <span class="badge badge-${m.my_status || 'pending'}">${statusLabel(m.my_status)}</span>
          </div>
        </div>
      `).join('');
  } catch (err) {
    container.innerHTML = `<p class="text-muted">${escapeHTML(err.message)}</p>`;
  }
}

// ---- Submit ----
async function loadMissionDetail(missionId) {
  return fetchAPI(`/missions/${missionId}`);
}

async function submitAssignment(missionId, formEl) {
  const fd = new FormData(formEl);
  return fetchAPI(`/missions/${missionId}/submit`, {
    method: 'POST',
    body: fd,
  });
}

async function loadMySubmissions(missionId) {
  return fetchAPI(`/missions/${missionId}/my-submissions`);
}

// ---- My Page ----
async function loadAllMySubmissions() {
  return fetchAPI('/my/submissions');
}

// ---- Admin Dashboard ----
async function loadAdminStats() {
  return fetchAPI('/admin/stats');
}

async function loadAdminSubmissions(params = {}) {
  const qs = new URLSearchParams(params).toString();
  return fetchAPI(`/admin/submissions?${qs}`);
}

async function adminApprove(submissionId) {
  return fetchAPI(`/admin/submissions/${submissionId}/approve`, { method: 'POST' });
}

async function adminReject(submissionId, reason) {
  return fetchAPI(`/admin/submissions/${submissionId}/reject`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  });
}

// ---- UI Helpers ----
function escapeHTML(str) {
  const d = document.createElement('div');
  d.textContent = str || '';
  return d.innerHTML;
}

function statusLabel(status) {
  const map = { passed: '합격', rejected: '반려', pending: '대기', reviewing: '검토중' };
  return map[status] || '대기';
}

function showToast(type, message) {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => el.remove(), 3000);
}

// ---- Tab switching ----
function initTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const group = btn.closest('.tabs');
      const target = btn.dataset.tab;
      group.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const container = group.parentElement;
      container.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      const panel = container.querySelector(`#${target}`);
      if (panel) panel.classList.add('active');
    });
  });
}

// ---- Mobile hamburger ----
function initHamburger() {
  const btn = document.querySelector('.pbl-hamburger');
  const menu = document.querySelector('.pbl-nav-menu');
  if (btn && menu) {
    btn.addEventListener('click', () => menu.classList.toggle('open'));
  }
}

// ---- Nav auth state ----
function updateNav() {
  const user = getUser();
  const authArea = document.querySelector('.pbl-nav-actions');
  if (!authArea) return;
  if (user) {
    authArea.innerHTML = `
      <span style="font-size:.85rem;color:var(--text-muted)">${escapeHTML(user.name)}</span>
      <button class="btn btn-sm btn-outline" onclick="logout()">로그아웃</button>
    `;
    // Show admin link
    if (user.role === 'admin') {
      const menu = document.querySelector('.pbl-nav-menu');
      if (menu && !menu.querySelector('.admin-link')) {
        const li = document.createElement('li');
        li.innerHTML = '<a href="admin/dashboard.html" class="admin-link">운영진</a>';
        menu.appendChild(li);
      }
    }
  } else {
    authArea.innerHTML = '<a href="login.html" class="btn btn-sm btn-primary">로그인</a>';
  }
}

// ---- File upload helper ----
function initFileUpload() {
  document.querySelectorAll('.file-upload').forEach(area => {
    const input = area.querySelector('input[type="file"]');
    if (!input) return;
    area.addEventListener('click', () => input.click());
    area.addEventListener('dragover', e => { e.preventDefault(); area.style.borderColor = 'var(--primary)'; });
    area.addEventListener('dragleave', () => { area.style.borderColor = ''; });
    area.addEventListener('drop', e => {
      e.preventDefault();
      area.style.borderColor = '';
      input.files = e.dataTransfer.files;
      area.querySelector('p').textContent = e.dataTransfer.files[0]?.name || '파일 선택';
    });
    input.addEventListener('change', () => {
      area.querySelector('p').textContent = input.files[0]?.name || '파일 선택';
    });
  });
}

// ---- Modal helper ----
function openModal(id) {
  document.getElementById(id)?.classList.add('open');
}
function closeModal(id) {
  document.getElementById(id)?.classList.remove('open');
}

// ---- Render submission fields by track ----
function renderSubmitFields(track, container) {
  const fields = {
    frontend: `
      <div class="form-group"><label class="form-label">GitHub URL</label>
      <input type="url" name="github_url" class="form-input" placeholder="https://github.com/..." required></div>
      <div class="form-group"><label class="form-label">배포 URL</label>
      <input type="url" name="deploy_url" class="form-input" placeholder="https://..."></div>`,
    backend: `
      <div class="form-group"><label class="form-label">GitHub URL</label>
      <input type="url" name="github_url" class="form-input" placeholder="https://github.com/..." required></div>
      <div class="form-group"><label class="form-label">배포 URL</label>
      <input type="url" name="deploy_url" class="form-input" placeholder="https://..."></div>`,
    design: `
      <div class="form-group"><label class="form-label">Figma URL</label>
      <input type="url" name="figma_url" class="form-input" placeholder="https://figma.com/..." required></div>
      <div class="form-group"><label class="form-label">스크린샷</label>
      <div class="file-upload"><input type="file" name="screenshot" accept="image/*"><p>클릭 또는 드래그하여 업로드</p></div></div>`,
    planning: `
      <div class="form-group"><label class="form-label">설명</label>
      <textarea name="description" class="form-textarea" placeholder="과제 설명을 입력하세요..." required></textarea></div>
      <div class="form-group"><label class="form-label">스크린샷 (선택)</label>
      <div class="file-upload"><input type="file" name="screenshot" accept="image/*"><p>클릭 또는 드래그하여 업로드</p></div></div>`,
  };
  container.innerHTML = fields[track] || fields.planning;
  initFileUpload();
}

// ---- Init on DOMContentLoaded ----
document.addEventListener('DOMContentLoaded', () => {
  initHamburger();
  initTabs();
  updateNav();
  initFileUpload();
});
