const API_URL = '/api';
let currentUserData = null;

document.addEventListener('DOMContentLoaded', function() {
    checkAuth();
    setupCharCounters();
});

async function checkAuth() {
    const token = localStorage.getItem('token');
    if (token) {
        try {
            const response = await fetch(`${API_URL}/auth/me`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (response.ok) {
                const user = await response.json();
                currentUserData = user;
                showUserMenu(user);
            } else {
                showAuthButtons();
                localStorage.removeItem('token');
            }
        } catch (error) {
            showAuthButtons();
        }
    } else {
        showAuthButtons();
    }
}

function showAuthButtons() {
    document.getElementById('authButtons').style.display = 'flex';
    document.getElementById('userMenu').style.display = 'none';
}

function showUserMenu(user) {
    document.getElementById('authButtons').style.display = 'none';
    document.getElementById('userMenu').style.display = 'flex';
    const bell = document.getElementById('notifBell');
    const msgLink = document.getElementById('msgLink');
    if (bell) bell.style.display = 'flex';
    if (msgLink) msgLink.style.display = 'flex';
    if (user.is_admin) {
        const adminLink = document.getElementById('adminLink');
        if (adminLink) adminLink.style.display = 'flex';
    }
    loadUnreadNotifCount();
}

function showModal(modalId) { document.getElementById(modalId).classList.add('show'); }
function closeModal(modalId) { document.getElementById(modalId).classList.remove('show'); }
// Backward-compatible alias (some templates call openModal)
function openModal(modalId) { showModal(modalId); }
function showLoginModal() { showModal('loginModal'); }
function showRegisterModal() { showModal('registerModal'); }
function showUploadModal() { showModal('uploadModal'); }

function toggleUserDropdown() {
    document.getElementById('userDropdown').classList.toggle('show');
}

document.addEventListener('click', function(event) {
    const dropdown = document.getElementById('userDropdown');
    const avatar = document.querySelector('.user-avatar');
    if (dropdown && avatar && !avatar.contains(event.target) && !dropdown.contains(event.target)) {
        dropdown.classList.remove('show');
    }
    const notifPanel = document.getElementById('notifPanel');
    const notifBell = document.getElementById('notifBell');
    if (notifPanel && notifBell && !notifBell.contains(event.target) && !notifPanel.contains(event.target)) {
        notifPanel.style.display = 'none';
    }
});

async function login(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const data = { username: formData.get('username'), password: formData.get('password') };
    const errorDiv = document.getElementById('loginError');
    errorDiv.classList.remove('show');
    try {
        const response = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        if (response.ok) {
            localStorage.setItem('token', result.token);
            closeModal('loginModal');
            form.reset();
            checkAuth();
            showNotification('Вы успешно вошли!', 'success');
        } else {
            errorDiv.textContent = result.error.message;
            errorDiv.classList.add('show');
        }
    } catch (error) {
        errorDiv.textContent = 'Ошибка подключения к серверу';
        errorDiv.classList.add('show');
    }
}

async function register(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const data = {
        username: formData.get('username'),
        email: formData.get('email'),
        password: formData.get('password'),
        display_name: formData.get('display_name') || null
    };
    const errorDiv = document.getElementById('registerError');
    errorDiv.classList.remove('show');
    if (!passwordGenerated) {
        const confirm = formData.get('password_confirm');
        if (!confirm || data.password !== confirm) {
            errorDiv.textContent = 'Пароли не совпадают';
            errorDiv.classList.add('show');
            return;
        }
    }
    try {
        const response = await fetch(`${API_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        if (response.ok) {
            closeModal('registerModal');
            form.reset();
            showNotification(`Регистрация успешна! Ваш тег: ${result.tag}`, 'success');
            showLoginModal();
        } else {
            errorDiv.textContent = result.error.message;
            errorDiv.classList.add('show');
        }
    } catch (error) {
        errorDiv.textContent = 'Ошибка подключения к серверу';
        errorDiv.classList.add('show');
    }
}

async function logout() {
    const token = localStorage.getItem('token');
    if (token) {
        try { await fetch(`${API_URL}/auth/logout`, { method: 'POST', headers: { 'Authorization': `Bearer ${token}` } }); } catch (e) {}
    }
    localStorage.removeItem('token');
    currentUserData = null;
    checkAuth();
    showNotification('Вы вышли из системы', 'info');
    setTimeout(() => window.location.reload(), 1000);
}

async function uploadVideo(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);

    // If user didn't pick a thumbnail, try to attach an auto-generated one (grabbed from ~2s video frame).
    try {
        const thumbInput = document.getElementById('thumbInput');
        const hasCustomThumb = !!(thumbInput && thumbInput.files && thumbInput.files.length);
        if (!hasCustomThumb && window.__autoThumbnailBlob) {
            formData.set('thumbnail', window.__autoThumbnailBlob, window.__autoThumbnailName || 'auto_thumbnail.jpg');
        }
    } catch (e) {
        // non-fatal
    }
    const token = localStorage.getItem('token');
    if (!token) { showNotification('Необходимо войти', 'error'); return; }
    const errorDiv = document.getElementById('uploadError');
    const progressDiv = document.getElementById('uploadProgress');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    errorDiv.classList.remove('show');
    progressDiv.style.display = 'block';
    try {
        const xhr = new XMLHttpRequest();
        xhr.upload.addEventListener('progress', function(e) {
            if (e.lengthComputable) {
                const pct = (e.loaded / e.total) * 100;
                progressFill.style.width = pct + '%';
                progressText.textContent = `Загрузка: ${Math.round(pct)}%`;
            }
        });
        xhr.addEventListener('load', function() {
            if (xhr.status === 201) {
                closeModal('uploadModal');
                form.reset();
                progressDiv.style.display = 'none';
                progressFill.style.width = '0%';
                showNotification('Видео загружено!', 'success');
                setTimeout(() => window.location.reload(), 1000);
            } else {
                const result = JSON.parse(xhr.responseText);
                errorDiv.textContent = result.error ? result.error.message : 'Ошибка загрузки';
                errorDiv.classList.add('show');
                progressDiv.style.display = 'none';
            }
        });
        xhr.addEventListener('error', function() {
            errorDiv.textContent = 'Ошибка подключения';
            errorDiv.classList.add('show');
            progressDiv.style.display = 'none';
        });
        xhr.open('POST', `${API_URL}/videos`);
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
        xhr.send(formData);
    } catch (error) {
        errorDiv.textContent = 'Ошибка загрузки';
        errorDiv.classList.add('show');
        progressDiv.style.display = 'none';
    }
}

function handleVideoSelect(input) {
    const file = input.files[0];
    if (file) {
        const video = document.createElement('video');
        video.preload = 'metadata';
        video.onloadedmetadata = function() {
            window.URL.revokeObjectURL(video.src);
            document.getElementById('videoDuration').value = Math.floor(video.duration) || 60;
        };
        video.src = URL.createObjectURL(file);

        // Auto-generate thumbnail if user hasn't selected one.
        const thumbInput = document.getElementById('thumbInput');
        const hasCustomThumb = !!(thumbInput && thumbInput.files && thumbInput.files.length);
        if (!hasCustomThumb) {
            generateAutoThumbnail(file);
        }
    }
}

async function generateAutoThumbnail(file) {
    try {
        const url = URL.createObjectURL(file);
        const video = document.createElement('video');
        video.src = url;
        video.muted = true;
        video.playsInline = true;
        video.preload = 'metadata';

        // Wait for metadata so we know duration
        await new Promise((resolve, reject) => {
            video.onloadedmetadata = () => resolve();
            video.onerror = () => reject(new Error('metadata error'));
        });

        // Seek to ~2 seconds (or earlier if the video is very short)
        const targetTime = Math.min(2, Math.max(0, (video.duration || 0) - 0.1));
        video.currentTime = targetTime;

        await new Promise((resolve, reject) => {
            const onSeeked = () => { video.removeEventListener('seeked', onSeeked); resolve(); };
            video.addEventListener('seeked', onSeeked);
            video.onerror = () => reject(new Error('seek error'));
        });

        const canvas = document.createElement('canvas');
        canvas.width = video.videoWidth || 1280;
        canvas.height = video.videoHeight || 720;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.85));
        if (!blob) throw new Error('toBlob failed');

        window.__autoThumbnailBlob = blob;
        window.__autoThumbnailName = 'auto_thumbnail.jpg';

        // Update UI preview
        const preview = document.getElementById('thumbPreview');
        if (preview) {
            const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
            preview.innerHTML = `<img src="${dataUrl}" style="width:100%;height:100%;object-fit:cover;border-radius:12px;">`;
            preview.className = 'thumb-preview-filled';
        }

        URL.revokeObjectURL(url);
    } catch (e) {
        // If browser can't extract a frame (codec restrictions), just leave without thumbnail.
        window.__autoThumbnailBlob = null;
        window.__autoThumbnailName = null;
    }
}

async function showMyChannel() {
    const token = localStorage.getItem('token');
    if (!token) { showNotification('Войдите в систему', 'error'); return; }
    try {
        const userResp = await fetch(`${API_URL}/auth/me`, { headers: { 'Authorization': `Bearer ${token}` } });
        if (!userResp.ok) return;
        const user = await userResp.json();
        const chResp = await fetch(`${API_URL}/channels`);
        if (!chResp.ok) return;
        const channels = await chResp.json();
        let myChannel = channels.find(c => c.author_id === user.id);
        if (myChannel) {
            window.location.href = `/channel/${myChannel.id}`;
        } else {
            const resp = await fetch(`${API_URL}/channels`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ name: user.display_name || user.username, description: '' })
            });
            if (resp.ok) {
                const ch = await resp.json();
                window.location.href = `/channel/${ch.id}`;
            }
        }
    } catch (e) { showNotification('Ошибка', 'error'); }
}

async function createUserChannel(name) {
    const token = localStorage.getItem('token');
    try {
        const resp = await fetch(`${API_URL}/channels`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ name, description: 'Мой канал' })
        });
        if (resp.ok) {
            const ch = await resp.json();
            showNotification('Канал создан!', 'success');
            setTimeout(() => window.location.href = `/channel/${ch.id}`, 1000);
        }
    } catch (e) { showNotification('Ошибка', 'error'); }
}

async function showSubscriptions() {
    const token = localStorage.getItem('token');
    if (!token) { showNotification('Войдите', 'error'); return; }
    try {
        const resp = await fetch(`${API_URL}/subscriptions/my`, { headers: { 'Authorization': `Bearer ${token}` } });
        if (resp.ok) {
            const subs = await resp.json();
            if (subs.length === 0) showNotification('Нет подписок', 'info');
            else window.location.href = `/channel/${subs[0].channel_id}`;
        }
    } catch (e) { showNotification('Ошибка', 'error'); }
}

function goToMyProfile() {
    if (currentUserData) window.location.href = `/profile/${currentUserData.id}`;
}

let passwordGenerated = false;

async function checkPwdStrength() {
    const pwd = document.getElementById('regPassword').value;
    const bar = document.getElementById('pwdStrength');
    if (!pwd) { bar.innerHTML = ''; return; }
    try {
        const resp = await fetch(`${API_URL}/auth/password-strength`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: pwd })
        });
        const data = await resp.json();
        const colors = { weak: '#f5576c', medium: '#ff9800', strong: '#4caf50', invalid: '#f5576c' };
        const labels = { weak: 'Слабый', medium: 'Средний', strong: 'Сильный', invalid: data.message || 'Невалидный' };
        const widths = { weak: '33%', medium: '66%', strong: '100%', invalid: '10%' };
        bar.innerHTML = `<div style="height:4px;background:rgba(255,255,255,0.1);border-radius:2px;"><div style="height:100%;width:${widths[data.strength]};background:${colors[data.strength]};border-radius:2px;transition:width 0.3s;"></div></div><small style="color:${colors[data.strength]}">${labels[data.strength]}</small>`;
    } catch (e) {}
}

function onPasswordInput() {
    passwordGenerated = false;
    const confirmGroup = document.getElementById('confirmPwdGroup');
    if (confirmGroup) confirmGroup.style.display = 'block';
    checkPwdStrength();
    checkPasswordMatch();
}

function checkPasswordMatch() {
    const pwd = document.getElementById('regPassword').value;
    const confirm = document.getElementById('regPasswordConfirm').value;
    const status = document.getElementById('pwdMatchStatus');
    if (!status) return;
    if (!confirm) { status.innerHTML = ''; return; }
    if (pwd === confirm) {
        status.innerHTML = '<span style="color:#4caf50;">✓ Пароли совпадают</span>';
    } else {
        status.innerHTML = '<span style="color:#f5576c;">✗ Пароли не совпадают</span>';
    }
}

function togglePasswordVisibility(inputId, btn) {
    const input = document.getElementById(inputId);
    if (!input) return;
    if (input.type === 'password') {
        input.type = 'text';
        btn.innerHTML = '<i class="fas fa-eye-slash"></i>';
    } else {
        input.type = 'password';
        btn.innerHTML = '<i class="fas fa-eye"></i>';
    }
}

async function generatePwd() {
    try {
        const resp = await fetch(`${API_URL}/auth/generate-password`);
        const data = await resp.json();
        const pwdInput = document.getElementById('regPassword');
        pwdInput.value = data.password;
        pwdInput.type = 'text';
        const eyeBtn = pwdInput.parentElement.querySelector('.pwd-eye-btn');
        if (eyeBtn) eyeBtn.innerHTML = '<i class="fas fa-eye-slash"></i>';
        passwordGenerated = true;
        const confirmGroup = document.getElementById('confirmPwdGroup');
        if (confirmGroup) confirmGroup.style.display = 'none';
        const confirmInput = document.getElementById('regPasswordConfirm');
        if (confirmInput) confirmInput.value = '';
        const matchStatus = document.getElementById('pwdMatchStatus');
        if (matchStatus) matchStatus.innerHTML = '';
        checkPwdStrength();
        showNotification('Пароль сгенерирован! Скопируйте его.', 'info');
    } catch (e) {}
}

async function loadUnreadNotifCount() {
    const token = localStorage.getItem('token');
    if (!token) return;
    try {
        const resp = await fetch(`${API_URL}/notifications/unread-count`, { headers: { 'Authorization': `Bearer ${token}` } });
        if (resp.ok) {
            const data = await resp.json();
            const badge = document.getElementById('notifBadge');
            if (data.count > 0) {
                badge.textContent = data.count > 99 ? '99+' : data.count;
                badge.style.display = 'flex';
            } else {
                badge.style.display = 'none';
            }
        }
    } catch (e) {}
}

async function toggleNotifPanel() {
    const panel = document.getElementById('notifPanel');
    if (panel.style.display === 'none') {
        panel.style.display = 'block';
        await loadNotifications();
    } else {
        panel.style.display = 'none';
    }
}

async function loadNotifications() {
    const token = localStorage.getItem('token');
    if (!token) return;
    try {
        const resp = await fetch(`${API_URL}/notifications`, { headers: { 'Authorization': `Bearer ${token}` } });
        if (resp.ok) {
            const notifs = await resp.json();
            const list = document.getElementById('notifList');
            if (notifs.length === 0) {
                list.innerHTML = '<div class="notif-empty">Нет уведомлений</div>';
            } else {
                list.innerHTML = notifs.map(n => `
                    <div class="notif-item ${n.is_read ? '' : 'unread'}" onclick="markNotifRead(${n.id}, this)">
                        <div class="notif-content">${escapeHtml(n.content)}</div>
                        <div class="notif-time">${new Date(n.created_at).toLocaleString('ru-RU')}</div>
                    </div>
                `).join('');
            }
        }
    } catch (e) {}
}

async function markNotifRead(id, el) {
    const token = localStorage.getItem('token');
    try {
        await fetch(`${API_URL}/notifications/${id}/read`, { method: 'POST', headers: { 'Authorization': `Bearer ${token}` } });
        if (el) el.classList.remove('unread');
        loadUnreadNotifCount();
    } catch (e) {}
}

async function markAllNotifsRead() {
    const token = localStorage.getItem('token');
    try {
        await fetch(`${API_URL}/notifications/read-all`, { method: 'POST', headers: { 'Authorization': `Bearer ${token}` } });
        loadNotifications();
        loadUnreadNotifCount();
    } catch (e) {}
}

function setupCharCounters() {
    const titleInput = document.querySelector('input[name="title"]');
    const descInput = document.querySelector('textarea[name="description"]');
    if (titleInput) {
        titleInput.addEventListener('input', () => {
            const counter = document.getElementById('titleCounter');
            if (counter) counter.textContent = `${titleInput.value.length}/100`;
        });
    }
    if (descInput) {
        descInput.addEventListener('input', () => {
            const counter = document.getElementById('descCounter');
            if (counter) counter.textContent = `${descInput.value.length}/2000`;
        });
    }
}

function previewThumbnail(input) {
    const file = input.files[0];
    const preview = document.getElementById('thumbPreview');
    if (file) {
        // User picked a custom thumbnail → override auto one.
        window.__autoThumbnailBlob = null;
        window.__autoThumbnailName = null;
        const reader = new FileReader();
        reader.onload = function(e) {
            preview.innerHTML = `<img src="${e.target.result}" style="width:100%;height:100%;object-fit:cover;border-radius:12px;">`;
            preview.className = 'thumb-preview-filled';
        };
        reader.readAsDataURL(file);
    } else {
        preview.innerHTML = '<i class="fas fa-image"></i><span>Нажмите для загрузки обложки</span><small>JPG, PNG, WebP. Рекомендуется 1280x720</small>';
        preview.className = 'thumb-preview-empty';
    }
}

let notifStack = [];
function showNotification(message, type = 'info') {
    const container = document.getElementById('notificationContainer') || document.body;
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    const icons = { success: 'check-circle', error: 'exclamation-circle', info: 'info-circle', warning: 'exclamation-triangle' };
    notification.innerHTML = `<i class="fas fa-${icons[type] || 'info-circle'}"></i><span>${message}</span><button onclick="this.parentElement.remove()" style="background:none;border:none;color:inherit;cursor:pointer;margin-left:auto;"><i class="fas fa-times"></i></button>`;
    const offset = 80 + notifStack.length * 60;
    notification.style.top = offset + 'px';
    notifStack.push(notification);
    container.appendChild(notification);
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(400px)';
        setTimeout(() => {
            notification.remove();
            notifStack = notifStack.filter(n => n !== notification);
            repositionNotifications();
        }, 300);
    }, 3000);
}

function repositionNotifications() {
    notifStack.forEach((n, i) => { n.style.top = (80 + i * 60) + 'px'; });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        document.querySelectorAll('.modal.show').forEach(m => m.classList.remove('show'));
    }
});

document.querySelectorAll('.modal').forEach(modal => {
    modal.addEventListener('click', function(event) {
        if (event.target === modal) modal.classList.remove('show');
    });
});
