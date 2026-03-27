/* Admin Dashboard JS - External file for CSP compatibility */
requireAdmin();

document.getElementById('filterBtn').addEventListener('click', function() { applyFilters(); });
document.getElementById('modalCloseBtn').addEventListener('click', function() { closeModal('detailModal'); });

var TRACK_LABELS = {planning:'기획', design:'디자인', frontend:'프론트엔드', backend:'백엔드'};
var ROLE_LABELS = {admin: '운영진', baby_lion: '아기사자', tester: '테스터'};
var ROLE_COLORS = {admin: '#FF7710', baby_lion: '#888', tester: '#4ade80'};

// ---- Pending Users ----
function loadPendingUsers() {
  fetchAPI('/admin/pending-users').then(function(users) {
    var section = document.getElementById('pendingUsersSection');
    var list = document.getElementById('pendingUsersList');
    document.getElementById('pendingUserCount').textContent = users.length;
    if (users.length === 0) { section.style.display = 'none'; return; }
    section.style.display = 'block';
    list.innerHTML = users.map(function(u) {
      return '<div class="card" style="padding:16px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;">'
        +'<div><strong style="color:#fff;">'+escapeHTML(u.name)+'</strong>'
        +'<span class="badge" style="margin-left:8px;">'+u.generation+'기</span><br>'
        +'<span style="color:#888;font-size:13px;">'+escapeHTML(u.email)+' · '+(TRACK_LABELS[u.track]||u.track)+' · '+(u.team?u.team+'팀':'미정')+'</span></div>'
        +'<div style="display:flex;gap:8px;">'
        +'<button type="button" class="btn btn-primary btn-sm btn-approve" data-uid="'+u.id+'" data-name="'+escapeHTML(u.name)+'">승인</button>'
        +'<button type="button" class="btn btn-outline btn-sm btn-reject-user" style="color:#ff4444;border-color:#ff4444;" data-uid="'+u.id+'" data-name="'+escapeHTML(u.name)+'">거절</button>'
        +'</div></div>';
    }).join('');
  }).catch(function(err) { console.error('Pending users error:', err); });
}

// Pending users - event delegation
document.getElementById('pendingUsersList').addEventListener('click', function(e) {
  var approveBtn = e.target.closest('.btn-approve');
  var rejectBtn = e.target.closest('.btn-reject-user');
  if (approveBtn) {
    fetchAPI('/admin/users/' + approveBtn.dataset.uid + '/approve', { method: 'PATCH' }).then(function() {
      showToast('success', approveBtn.dataset.name + '님이 승인되었습니다.');
      loadPendingUsers(); loadWarnings(); loadMatrix('');
    }).catch(function(err) { showToast('error', err.message); });
  }
  if (rejectBtn) {
    fetchAPI('/admin/users/' + rejectBtn.dataset.uid + '/reject', { method: 'PATCH' }).then(function() {
      showToast('success', rejectBtn.dataset.name + '님의 가입이 거절되었습니다.');
      loadPendingUsers();
    }).catch(function(err) { showToast('error', err.message); });
  }
});

loadPendingUsers();

// ---- User Management ----
function loadUserManagement() {
  fetchAPI('/admin/users').then(function(users) {
    var container = document.getElementById('userManagementList');
    if (!users || users.length === 0) {
      container.innerHTML = '<p style="color:#888;">승인된 사용자가 없습니다.</p>';
      return;
    }
    container.innerHTML = users.map(function(u) {
      var roleLabel = '<span style="color:'+ROLE_COLORS[u.role]+';font-weight:600;">'+(ROLE_LABELS[u.role]||u.role)+'</span>';
      var selectHtml = '<select class="form-select role-select" data-uid="'+u.id+'" data-uname="'+escapeHTML(u.name)+'" style="font-size:.8rem;width:auto;padding:4px 8px;background:#111;color:#fff;border:1px solid #333;border-radius:6px;">'
        +'<option value="baby_lion"'+(u.role==='baby_lion'?' selected':'')+'>아기사자</option>'
        +'<option value="tester"'+(u.role==='tester'?' selected':'')+'>테스터</option>'
        +'<option value="admin"'+(u.role==='admin'?' selected':'')+'>운영진</option>'
        +'</select>';
      var deleteBtn = u.role !== 'admin'
        ? '<button type="button" class="btn-delete" data-uid="'+u.id+'" data-uname="'+escapeHTML(u.name)+'" style="font-size:.75rem;color:#f87171;border:1px solid #f87171;background:transparent;padding:6px 12px;border-radius:6px;margin-left:8px;cursor:pointer;">삭제</button>'
        : '';
      return '<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 16px;background:#1a1a1a;border-radius:8px;">'
        +'<div><strong style="color:#fff;">'+escapeHTML(u.name)+'</strong> '+roleLabel
        +' <span style="color:#666;font-size:.8rem;margin-left:8px;">'+escapeHTML(u.email)+' · '+(TRACK_LABELS[u.track]||u.track)+' · '+(u.team?u.team+'팀':'')+'</span></div>'
        +'<div style="display:flex;align-items:center;">'+selectHtml+deleteBtn+'</div></div>';
    }).join('');
  }).catch(function(err) { console.error('User management error:', err); });
}

// User management - event delegation
document.getElementById('userManagementList').addEventListener('click', function(e) {
  var btn = e.target.closest('.btn-delete');
  if (btn) {
    if (!confirm(btn.dataset.uname + '님의 계정을 삭제하시겠습니까?\n제출 내역도 모두 삭제됩니다.')) return;
    fetchAPI('/admin/users/' + btn.dataset.uid, { method: 'DELETE' }).then(function(res) {
      showToast('success', res.message || '삭제되었습니다.');
      loadUserManagement(); loadMatrix('');
    }).catch(function(err) { showToast('error', err.message); });
  }
});
document.getElementById('userManagementList').addEventListener('change', function(e) {
  var sel = e.target.closest('.role-select');
  if (sel) {
    fetchAPI('/admin/users/' + sel.dataset.uid + '/set-role?role=' + sel.value, { method: 'PATCH' }).then(function(res) {
      showToast('success', res.message || '역할이 변경되었습니다.');
      loadUserManagement();
    }).catch(function(err) { showToast('error', err.message); });
  }
});

loadUserManagement();

// ---- Warnings ----
function loadWarnings() {
  fetchAPI('/admin/warnings').then(function(warnings) {
    var section = document.getElementById('warningsSection');
    if (warnings.length === 0) { section.style.display = 'none'; return; }
    section.style.display = 'block';
    section.innerHTML = '<div class="warning-alert"><h3>⚠️ 미제출 경고 (2회 이상 미제출: '+warnings.length+'명)</h3>'
      + warnings.map(function(w) {
        return '<div class="warning-alert-item"><strong>'+escapeHTML(w.name)+'</strong>'
          +'<span style="color:#888;margin-left:8px;">'+(TRACK_LABELS[w.track]||w.track)+' · '+(w.team?w.team+'팀':'')+'</span>'
          +'<span style="color:#f87171;margin-left:8px;">미제출 '+w.missed_count+'회 (미션 '+w.missed_missions.join(', ')+')</span></div>';
      }).join('') + '</div>';
  }).catch(function(err) { console.error('Warnings error:', err); });
}
loadWarnings();

// ---- Progress Matrix ----
function loadMatrix(track) {
  var qs = track ? '?track=' + track : '';
  fetchAPI('/admin/progress-matrix' + qs).then(function(data) {
    var table = document.getElementById('progressMatrix');
    var maxMissions = 11;
    var headerHtml = '<tr><th>이름</th><th>트랙</th><th>팀</th>';
    for (var i = 0; i <= 10; i++) headerHtml += '<th>M' + i + '</th>';
    headerHtml += '</tr>';
    table.querySelector('thead').innerHTML = headerHtml;
    if (data.length === 0) {
      table.querySelector('tbody').innerHTML = '<tr><td colspan="'+(maxMissions+3)+'" style="text-align:center;color:#888;">데이터 없음</td></tr>';
      return;
    }
    table.querySelector('tbody').innerHTML = data.map(function(u) {
      var cells = '<td>'+escapeHTML(u.name)+'</td><td>'+(TRACK_LABELS[u.track]||u.track)+'</td><td>'+(u.team||'-')+'</td>';
      for (var i = 0; i < maxMissions; i++) {
        var ms = u.missions[i];
        var st = ms ? ms.status : 'upcoming';
        var cls = st === 'passed' ? 'passed' : st === 'pending' ? 'pending' : st === 'reviewing' ? 'reviewing' : st === 'rejected' ? 'rejected' : st === 'missed' ? 'missed' : 'none';
        cells += '<td><span class="progress-cell progress-cell-'+cls+'" title="미션 '+(ms?ms.number:i)+': '+st+'"></span></td>';
      }
      return '<tr>' + cells + '</tr>';
    }).join('');
  }).catch(function(err) { console.error('Matrix error:', err); });
}
loadMatrix('');
document.getElementById('matrixTrackFilter').addEventListener('change', function() { loadMatrix(this.value); });

// ---- Stats ----
loadAdminStats().then(function(stats) {
  var s = stats.stats || stats;
  document.getElementById('statTotal').textContent = s.total_users != null ? s.total_users : '-';
  document.getElementById('statSubmissions').textContent = s.total_submissions != null ? s.total_submissions : '-';
  document.getElementById('statPassed').textContent = s.passed_count != null ? s.passed_count : '-';
  document.getElementById('statRejected').textContent = s.rejected_count != null ? s.rejected_count : '-';
  document.getElementById('statPending').textContent = s.pending_count != null ? s.pending_count : '-';
}).catch(function() {});

// ---- Submissions Table ----
function loadTable(params) {
  params = params || {};
  var tbody = document.getElementById('submissionTable');
  tbody.innerHTML = '<tr><td colspan="6" class="text-center"><span class="spinner"></span></td></tr>';
  loadAdminSubmissions(params).then(function(data) {
    var list = Array.isArray(data) ? data : (data.submissions || []);
    if (list.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">데이터 없음</td></tr>';
      return;
    }
    window._submissionList = list;
    tbody.innerHTML = list.map(function(s, i) {
      return '<tr class="clickable" data-idx="'+i+'">'
        +'<td>'+escapeHTML(s.user_name)+'</td>'
        +'<td>'+escapeHTML(s.track)+'</td>'
        +'<td>'+(s.team||'-')+'</td>'
        +'<td>미션 '+s.mission_number+'</td>'
        +'<td><span class="badge badge-'+s.status+'">'+statusLabel(s.status)+'</span></td>'
        +'<td>'+new Date(s.submitted_at).toLocaleDateString('ko-KR')+'</td>'
        +'</tr>';
    }).join('');
  }).catch(function(err) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-muted">'+escapeHTML(err.message)+'</td></tr>';
  });
}

// Submission table - event delegation
document.getElementById('submissionTable').addEventListener('click', function(e) {
  var tr = e.target.closest('tr[data-idx]');
  if (tr && window._submissionList) {
    showDetail(window._submissionList[parseInt(tr.dataset.idx)]);
  }
});

loadTable();

function applyFilters() {
  var params = {};
  var track = document.getElementById('filterTrack').value;
  var mission = document.getElementById('filterMission').value;
  var status = document.getElementById('filterStatus').value;
  if (track) params.track = track;
  if (mission) params.mission_number = mission;
  if (status) params.status = status;
  loadTable(params);
}

function showDetail(s) {
  document.getElementById('modalTitle').textContent = s.user_name + ' - 미션 ' + s.mission_number;
  document.getElementById('modalBody').innerHTML =
    '<div style="margin-bottom:1rem"><span class="badge badge-'+s.status+'">'+statusLabel(s.status)+'</span>'
    +'<span class="text-muted" style="margin-left:.5rem;font-size:.8rem">'+new Date(s.submitted_at).toLocaleString('ko-KR')+'</span></div>'
    +(s.github_url ? '<p><strong>GitHub:</strong> <a href="'+escapeHTML(s.github_url)+'" target="_blank">'+escapeHTML(s.github_url)+'</a></p>' : '')
    +(s.deploy_url ? '<p><strong>배포:</strong> <a href="'+escapeHTML(s.deploy_url)+'" target="_blank">'+escapeHTML(s.deploy_url)+'</a></p>' : '')
    +(s.figma_url ? '<p><strong>Figma:</strong> <a href="'+escapeHTML(s.figma_url)+'" target="_blank">'+escapeHTML(s.figma_url)+'</a></p>' : '')
    +(s.description ? '<p><strong>설명:</strong> '+escapeHTML(s.description)+'</p>' : '')
    +(s.review && s.review.ai_score != null ? '<p><strong>AI 점수:</strong> '+s.review.ai_score+'/100</p>' : '')
    +(s.review && s.review.ai_summary ? '<div class="feedback-box"><strong>AI 피드백</strong><br>'+escapeHTML(s.review.ai_summary)+'</div>' : '');

  var footer = document.getElementById('modalFooter');
  if (s.status === 'pending' || s.status === 'reviewing') {
    footer.innerHTML = '<div style="display:flex;gap:8px;align-items:center;width:100%;flex-wrap:wrap;">'
      +'<input type="text" id="modalComment" placeholder="사유 입력 (선택)" style="flex:1;min-width:150px;padding:8px 12px;background:#111;color:#fff;border:1px solid #333;border-radius:6px;font-size:.85rem;">'
      +'<button type="button" id="modalApproveBtn" style="padding:8px 16px;background:#10b981;color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:600;">합격</button>'
      +'<button type="button" id="modalRejectBtn" style="padding:8px 16px;background:#ef4444;color:#fff;border:none;border-radius:6px;cursor:pointer;font-weight:600;">반려</button>'
      +'</div>';
    window._reviewSubId = s.id;
  } else {
    footer.innerHTML = '';
  }
  openModal('detailModal');
}

// Modal footer - event delegation
document.getElementById('modalFooter').addEventListener('click', function(e) {
  var approveBtn = e.target.closest('#modalApproveBtn');
  var rejectBtn = e.target.closest('#modalRejectBtn');
  if (!approveBtn && !rejectBtn) return;
  var approved = !!approveBtn;
  var comment = document.getElementById('modalComment').value.trim() || (approved ? '합격' : '반려');
  if (!approved && !document.getElementById('modalComment').value.trim()) {
    if (!confirm('반려 사유 없이 반려하시겠습니까?')) return;
  }
  adminReviewSubmission(window._reviewSubId, approved, comment).then(function() {
    showToast('success', approved ? '합격 처리 완료' : '반려 처리 완료');
    closeModal('detailModal');
    applyFilters();
    loadMatrix(document.getElementById('matrixTrackFilter').value);
  }).catch(function(err) { showToast('error', err.message); });
});
