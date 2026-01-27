const API_BASE = '/admin/api';
const LOGS_PAGE_SIZE = 50;

let token = null;
let logsPage = 1;
let editingRuleId = null;
let searchTimeout = null;
let currentLogsData = {};

function formatChinaTime(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' });
}

function init() {
    token = localStorage.getItem('token');
    if (token) {
        showDashboard();
        switchTab('rules');
    }
    setupLoginForm();
}

function setupLoginForm() {
    const loginForm = document.getElementById('loginForm');
    if (!loginForm) return;

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const password = document.getElementById('password').value;
        const errorDiv = document.getElementById('loginError');
        const btn = document.getElementById('loginBtn');

        errorDiv.classList.add('hidden');
        btn.disabled = true;
        btn.textContent = 'Logging in...';

        try {
            const res = await fetch('/admin/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password })
            });

            if (res.ok) {
                const data = await res.json();
                token = data.token;
                localStorage.setItem('token', token);
                showDashboard();
            } else {
                const error = await res.json().catch(() => ({ detail: 'Login failed' }));
                errorDiv.querySelector('p').textContent = error.detail || 'Invalid password';
                errorDiv.classList.remove('hidden');
            }
        } catch (err) {
            errorDiv.querySelector('p').textContent = 'Login failed: ' + err.message;
            errorDiv.classList.remove('hidden');
        } finally {
            btn.disabled = false;
            btn.textContent = 'Login';
        }
    });
}

function showDashboard() {
    document.getElementById('loginPage').classList.add('hidden');
    document.getElementById('dashboard').classList.remove('hidden');
    document.getElementById('dashboard').classList.add('fade-in');
    loadRules();
    loadMethods();
}

function logout() {
    localStorage.removeItem('token');
    token = null;
    document.getElementById('dashboard').classList.add('hidden');
    document.getElementById('loginPage').classList.remove('hidden');
}

function showChangePasswordModal() {
    document.getElementById('changePasswordModal').classList.remove('hidden');
    document.getElementById('passwordError').classList.add('hidden');
    document.getElementById('passwordSuccess').classList.add('hidden');
    document.getElementById('oldPassword').value = '';
    document.getElementById('newPassword').value = '';
    document.getElementById('confirmPassword').value = '';
}

function closeChangePasswordModal() {
    document.getElementById('changePasswordModal').classList.add('hidden');
}

async function handleChangePassword(event) {
    event.preventDefault();
    
    const oldPassword = document.getElementById('oldPassword').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    
    const errorEl = document.getElementById('passwordError');
    const successEl = document.getElementById('passwordSuccess');
    const submitBtn = document.getElementById('cpSubmitBtn');
    
    errorEl.classList.add('hidden');
    successEl.classList.add('hidden');
    
    if (newPassword !== confirmPassword) {
        errorEl.classList.remove('hidden');
        errorEl.querySelector('p').textContent = '新密码和确认密码不匹配';
        return;
    }
    
    if (newPassword.length < 6) {
        errorEl.classList.remove('hidden');
        errorEl.querySelector('p').textContent = '新密码长度至少6位';
        return;
    }
    
    submitBtn.disabled = true;
    submitBtn.textContent = '修改中...';
    
    try {
        const res = await apiRequest('/password', {
            method: 'PUT',
            body: JSON.stringify({
                old_password: oldPassword,
                new_password: newPassword
            })
        });
        
        if (res.ok) {
            successEl.classList.remove('hidden');
            submitBtn.classList.add('hidden');
            document.getElementById('cpCancelBtn').textContent = '关闭';
            setTimeout(() => {
                logout();
                closeChangePasswordModal();
            }, 2000);
        } else {
            const error = await res.json().catch(() => ({ detail: '修改失败' }));
            errorEl.classList.remove('hidden');
            errorEl.querySelector('p').textContent = error.detail || '修改失败';
        }
    } catch (err) {
        errorEl.classList.remove('hidden');
        errorEl.querySelector('p').textContent = '修改失败: ' + err.message;
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = '修改密码';
    }
}

function switchTab(tab) {
    document.querySelectorAll('[data-tab]').forEach(el => {
        el.classList.add('hidden');
    });
    document.querySelectorAll('[data-tab-button]').forEach(el => {
        el.classList.remove('border-indigo-500', 'text-indigo-600');
        el.classList.add('border-transparent', 'text-gray-500');
    });

    const tabEl = document.querySelector(`[data-tab="${tab}"]`);
    if (tabEl) tabEl.classList.remove('hidden');

    const tabBtn = document.querySelector(`[data-tab-button="${tab}"]`);
    if (tabBtn) {
        tabBtn.classList.remove('border-transparent', 'text-gray-500');
        tabBtn.classList.add('border-indigo-500', 'text-indigo-600');
    }

    if (tab === 'rules') loadRules();
    if (tab === 'commands') loadCommands();
    if (tab === 'logs') loadLogs();
}

async function apiRequest(url, options = {}) {
    const res = await fetch(API_BASE + url, {
        ...options,
        headers: {
            'Authorization': 'Bearer ' + token,
            'Content-Type': 'application/json',
            ...options.headers
        }
    });
    if (res.status === 401) {
        logout();
        throw new Error('Unauthorized');
    }
    return res;
}



async function loadCommands() {
    try {
        const res = await apiRequest('/commands');
        const commands = await res.json();
        const container = document.getElementById('commandsList');

        if (!commands || commands.length === 0) {
            container.innerHTML = '<div class="p-8 text-center text-gray-500">No commands in queue</div>';
            return;
        }

        container.innerHTML = commands.map(cmd => `
            <div class="p-4 hover:bg-gray-50 border-b border-gray-100 last:border-b-0">
                <div class="flex justify-between items-start">
                    <div class="flex-1">
                        <div class="flex items-center space-x-2 mb-2">
                            <span class="px-2 py-1 rounded-full text-xs font-semibold ${cmd.status === 'verified' ? 'bg-green-100 text-green-800' : cmd.status === 'rejected' ? 'bg-red-100 text-red-800' : cmd.status === 'sent' ? 'bg-blue-100 text-blue-800' : 'bg-yellow-100 text-yellow-800'}">${cmd.status}</span>
                            <span class="text-sm text-gray-500">${formatChinaTime(cmd.received_at)}</span>
                        </div>
                        <pre class="text-sm bg-gray-100 p-3 rounded overflow-x-auto">${JSON.stringify(cmd.command, null, 2)}</pre>
                        ${cmd.notes ? `<div class="mt-2 text-sm text-gray-600"><strong>Notes:</strong> ${escapeHtml(cmd.notes)}</div>` : ''}
                    </div>
                    <div class="ml-4 flex flex-col gap-2">
                        ${cmd.status === 'unverified' ? `
                            <button onclick="updateCommand(${cmd.id}, 'verified')" class="px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700">Verify</button>
                            <button onclick="updateCommand(${cmd.id}, 'rejected')" class="px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700">Reject</button>
                        ` : ''}
                        ${cmd.status === 'verified' ? `
                            <button onclick="sendCommandToDevice(${cmd.id})" class="px-3 py-1 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700">Send to Device</button>
                        ` : ''}
                    </div>
                </div>
            </div>
        `).join('');
    } catch (err) {
        document.getElementById('commandsList').innerHTML = '<div class="p-8 text-center text-red-500">Failed to load commands</div>';
    }
}

async function sendCommandToDevice(commandId) {
    try {
        const btn = event.target;
        btn.disabled = true;
        btn.textContent = 'Sending...';
        
        const res = await apiRequest(`/commands/${commandId}/send`, {
            method: 'POST'
        });
        
        if (res.ok) {
            const result = await res.json();
            alert('Command sent successfully: ' + result.message);
            loadCommands();
        } else {
            const error = await res.json().catch(() => ({ detail: 'Failed to send command' }));
            alert('Failed to send command: ' + (error.detail || 'Unknown error'));
        }
    } catch (err) {
        alert('Error sending command: ' + err.message);
    } finally {
        loadCommands();
    }
}

async function updateCommand(id, status) {
    try {
        const res = await apiRequest(`/commands/${id}`, {
            method: 'POST',
            body: JSON.stringify({ status, notes: '' })
        });

        if (res.ok) {
            loadCommands();
        } else {
            alert('Failed to update command');
        }
    } catch (err) {
        alert('Error: ' + err.message);
    }
}

async function loadLogs(method = '', search = '') {
    try {
        // 如果没有提供method参数，重置筛选框为All Methods
        if (!method) {
            const select = document.getElementById('logMethodFilter');
            if (select) {
                select.value = '';
            }
        }
        
        let url = `/logs?page=${logsPage}&limit=${LOGS_PAGE_SIZE}`;
        if (method) url += `&method=${encodeURIComponent(method)}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;

        const res = await apiRequest(url);
        const data = await res.json();
        const logs = data.data || [];
        const total = data.total || 0;

        currentLogsData = {};
        logs.forEach(log => { currentLogsData[log.id] = log; });

        const tbody = document.getElementById('logsTableBody');

        if (logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="px-6 py-12 text-center text-gray-500">No logs found.</td></tr>';
            updateLogsPagination(total, false);
            return;
        }

        tbody.innerHTML = logs.map(log => `
            <tr class="hover:bg-gray-50 cursor-pointer" onclick='showLogDetail(${log.id})'>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">${log.method || '-'}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm">
                    ${log.email ? 
                        `<span class="px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-800">${escapeHtml(log.email)}</span>` : 
                        `<span class="px-2 py-1 rounded-full text-xs bg-purple-100 text-purple-800">全局</span>`
                    }
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${formatChinaTime(log.created_at)}</td>
                <td class="px-6 py-4 text-sm text-gray-500 font-mono truncate max-w-md">${escapeHtml(JSON.stringify(log.request_body))}</td>
            </tr>
        `).join('');

        updateLogsPagination(total, true);
    } catch (err) {
        document.getElementById('logsTableBody').innerHTML = '<tr><td colspan="4" class="px-6 py-12 text-center text-red-500">Failed to load logs</td></tr>';
    }
}

function updateLogsPagination(total, hasData) {
    const pagination = document.getElementById('logsPagination');
    const info = document.getElementById('logsPaginationInfo');
    const prevBtn = document.getElementById('logsPrevBtn');
    const nextBtn = document.getElementById('logsNextBtn');

    if (!hasData || total === 0) {
        pagination.classList.add('hidden');
        return;
    }

    pagination.classList.remove('hidden');
    const start = (logsPage - 1) * LOGS_PAGE_SIZE + 1;
    const end = Math.min(logsPage * LOGS_PAGE_SIZE, total);
    info.textContent = `Showing ${start}-${end} of ${total}`;

    prevBtn.disabled = logsPage <= 1;
    nextBtn.disabled = end >= total;
}

function goToLogsPage(direction) {
    if (direction === 'prev' && logsPage > 1) {
        logsPage--;
    } else if (direction === 'next') {
        logsPage++;
    }
    const method = document.getElementById('logMethodFilter').value;
    const search = document.getElementById('logSearch').value;
    loadLogs(method, search);
}

async function loadMethods() {
    try {
        const res = await apiRequest('/logs/methods');
        const methods = await res.json();
        const select = document.getElementById('logMethodFilter');
        select.innerHTML = '<option value="">All Methods</option>' +
            methods.map(m => `<option value="${m}">${m}</option>`).join('');
    } catch (err) {
    }
}

function toggleRuleEditor() {
    const editor = document.getElementById('ruleEditor');
    const globalSection = document.getElementById('globalRulesSection');
    const userSection = document.getElementById('userRulesSection');
    
    if (editor.classList.contains('hidden')) {
        editor.classList.remove('hidden');
        globalSection.classList.add('hidden');
        userSection.classList.add('hidden');
        document.getElementById('ruleEditorTitle').textContent = '创建新规则';
        cancelRuleEdit();
        loadEmailOptions();
    } else {
        editor.classList.add('hidden');
        if (selectedUserEmail) {
            userSection.classList.remove('hidden');
        } else {
            globalSection.classList.remove('hidden');
        }
    }
}

function toggleCustomResponse() {
    const action = document.getElementById('ruleAction').value;
    const section = document.getElementById('customResponseSection');
    const randomizeSection = document.getElementById('randomizeConfigSection');
    
    if (action === 'replace' || action === 'modify') {
        section.classList.remove('hidden');
    } else {
        section.classList.add('hidden');
    }
    
    if (action === 'randomize_app_duration') {
        randomizeSection.classList.remove('hidden');
        updateExpectedRequestPreview();
    } else {
        randomizeSection.classList.add('hidden');
        updateExpectedRequestPreview();
    }
}

function addPackageInput(value = '') {
    const container = document.getElementById('packagesContainer');
    const div = document.createElement('div');
    div.className = 'flex items-center space-x-2 package-input-row';
    div.innerHTML = `
        <input type="text" name="rulePackageItem" 
            class="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="com.kingsoft" value="${escapeHtml(value)}">
        <button type="button" onclick="removePackageInput(this)"
            class="px-3 py-2 bg-red-500 text-white rounded-lg text-sm hover:bg-red-600 flex-shrink-0">
            -
        </button>
    `;
    container.appendChild(div);
    console.log('Added package input, rows count:', container.querySelectorAll('.package-input-row').length);
}

function removePackageInput(button) {
    let row = button.closest('.package-input-row');
    const container = document.getElementById('packagesContainer');
    
    if (!row) {
        row = button.parentElement;
    }
    
    const allRows = container.querySelectorAll('.package-input-row');
    const totalRows = allRows.length > 0 ? allRows.length : 1;
    
    console.log('removePackageInput called, total rows:', totalRows, 'row:', row);
    
    if (totalRows > 1) {
        row.remove();
        console.log('Removed row, remaining rows:', container.querySelectorAll('.package-input-row').length);
    } else {
        const input = row.querySelector('input[name="rulePackageItem"]');
        if (input) {
            input.value = '';
            console.log('Cleared input value');
        }
    }
}

function clearPackageInputs() {
    const container = document.getElementById('packagesContainer');
    const rows = container.querySelectorAll('.package-input-row');
    if (rows.length <= 1) {
        const input = container.querySelector('input[name="rulePackageItem"]');
        if (input) input.value = '';
    } else {
        container.innerHTML = `
            <div class="flex items-center space-x-2 package-input-row">
                <input type="text" name="rulePackageItem" 
                    class="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="com.kingsoft">
                <button type="button" onclick="addPackageInput()"
                    class="px-3 py-2 bg-green-500 text-white rounded-lg text-sm hover:bg-green-600 flex-shrink-0">
                    +
                </button>
            </div>
        `;
    }
}

let _availableEmails = [];

async function loadEmailOptions() {
    try {
        const res = await apiRequest('/logs/emails');
        if (res.ok) {
            _availableEmails = await res.json();
            renderEmailOptions(_availableEmails);
        }
    } catch (err) {
        console.error('Failed to load emails:', err);
        document.getElementById('emailOptionsList').innerHTML = '<p class="p-3 text-sm text-red-500 text-center">加载失败</p>';
    }
}

function renderEmailOptions(emails) {
    const container = document.getElementById('emailOptionsList');
    if (!emails || emails.length === 0) {
        container.innerHTML = '<p class="p-3 text-sm text-gray-500 text-center">暂无用户</p>';
        return;
    }
    
    container.innerHTML = emails.map(email => `
        <label class="flex items-center space-x-3 px-3 py-2 cursor-pointer hover:bg-gray-100">
            <input type="checkbox" value="${escapeHtml(email)}" 
                class="email-checkbox w-4 h-4 text-indigo-600 rounded focus:ring-indigo-500"
                onchange="onEmailCheckboxChange()">
            <span class="text-sm text-gray-700 truncate">${escapeHtml(email)}</span>
        </label>
    `).join('');
}

function toggleEmailDropdown() {
    const dropdown = document.getElementById('emailOptions');
    dropdown.classList.toggle('hidden');
    
    if (!dropdown.classList.contains('hidden')) {
        if (_availableEmails.length === 0) {
            loadEmailOptions();
        }
    }
}

function toggleEmailSelectAll() {
    const selectAll = document.getElementById('emailSelectAll');
    const checkboxes = document.querySelectorAll('.email-checkbox');
    checkboxes.forEach(cb => cb.checked = selectAll.checked);
    updateSelectedEmailsDisplay();
}

function onEmailCheckboxChange() {
    const checkboxes = document.querySelectorAll('.email-checkbox');
    const checkedCount = Array.from(checkboxes).filter(cb => cb.checked).length;
    
    document.getElementById('emailSelectAll').checked = checkedCount === checkboxes.length && checkboxes.length > 0;
    updateSelectedEmailsDisplay();
    updateRuleScopeHint();
}

function updateSelectedEmailsDisplay() {
    const selected = getSelectedEmails();
    const container = document.getElementById('selectedEmails');
    const textDisplay = document.getElementById('emailDropdownText');
    
    if (selected.length === 0) {
        container.innerHTML = '';
        textDisplay.textContent = '请选择用户...';
        textDisplay.classList.add('text-gray-500');
        textDisplay.classList.remove('text-gray-900');
    } else if (selected.length === 1) {
        container.innerHTML = `<span class="px-2 py-1 bg-indigo-100 text-indigo-800 rounded text-sm">${escapeHtml(selected[0])}</span>`;
        textDisplay.textContent = `已选择: ${escapeHtml(selected[0])}`;
        textDisplay.classList.remove('text-gray-500');
        textDisplay.classList.add('text-gray-900');
    } else {
        container.innerHTML = selected.map(email => 
            `<span class="px-2 py-1 bg-indigo-100 text-indigo-800 rounded text-sm">${escapeHtml(email)}</span>`
        ).join('');
        textDisplay.textContent = `已选择 ${selected.length} 个用户`;
        textDisplay.classList.remove('text-gray-500');
        textDisplay.classList.add('text-gray-900');
    }
}

function getSelectedEmails() {
    const checkboxes = document.querySelectorAll('.email-checkbox:checked');
    return Array.from(checkboxes).map(cb => cb.value);
}

function setSelectedEmails(emails) {
    const checkboxes = document.querySelectorAll('.email-checkbox');
    checkboxes.forEach(cb => {
        cb.checked = emails.includes(cb.value);
    });
    
    document.getElementById('emailSelectAll').checked = checkboxes.length > 0 && 
        Array.from(checkboxes).every(cb => cb.checked);
    updateSelectedEmailsDisplay();
}

function clearEmailSelection() {
    const checkboxes = document.querySelectorAll('.email-checkbox');
    checkboxes.forEach(cb => cb.checked = false);
    document.getElementById('emailSelectAll').checked = false;
    updateSelectedEmailsDisplay();
    updateRuleScopeHint();
}

function getActionDisplayName(action) {
    const actionMap = {
        'passthrough': '直连',
        'modify': '修改请求',
        'replace': '覆写响应',
        'randomize_app_duration': '随机时长'
    };
    return actionMap[action] || action;
}

function updateRuleScopeHint() {
    const selected = getSelectedEmails();
    const hint = document.getElementById('ruleScopeHint');
    if (selected.length === 0) {
        hint.textContent = '当前: 全局规则';
        hint.className = 'text-xs text-purple-600 mt-1';
    } else if (selected.length === 1) {
        hint.textContent = `当前: 用户规则 - ${escapeHtml(selected[0])}`;
        hint.className = 'text-xs text-blue-600 mt-1';
    } else {
        hint.textContent = `当前: 用户规则 (${selected.length}个用户)`;
        hint.className = 'text-xs text-blue-600 mt-1';
    }
    
    updateExpectedRequestPreview();
}

function updateExpectedRequestPreview() {
    const action = document.getElementById('ruleAction').value;
    const previewSection = document.getElementById('expectedRequestPreview');
    
    if (action === 'randomize_app_duration') {
        const config = getRandomizeConfig();
        const preview = generateRandomizePreview(config);
        previewSection.innerHTML = `
            <div class="p-3 bg-blue-50 rounded-lg mt-2">
                <h4 class="text-sm font-medium text-blue-800 mb-2">预计请求格式</h4>
                <pre class="text-xs text-blue-700 whitespace-pre-wrap">${preview}</pre>
            </div>
        `;
    } else {
        previewSection.innerHTML = '';
    }
}

function getRandomizeConfig() {
    const packageInputs = document.querySelectorAll('input[name="rulePackageItem"]');
    const packages = Array.from(packageInputs)
        .map(input => input.value.trim())
        .filter(p => p);
    const maxDuration = document.getElementById('ruleMaxDuration').value.trim() || '30';
    const keepCount = document.getElementById('ruleKeepCount').value.trim() || '2';
    
    return {
        packages: packages.length > 0 ? packages : ['com.kingsoft'],
        max_duration_minutes: parseInt(maxDuration, 10) || 30,
        keep_count: parseInt(keepCount, 10) || 2
    };
}

function generateRandomizePreview(config) {
    return `{
  "!version": 6,
  "client_version": "...",
  "id": 1,
  "jsonrpc": "2.0",
  "method": "${document.getElementById('ruleMethodName').value || 'com.linspirer.app.setappdurationlogs'}",
  "params": {
    "email": "...",
    "logs": [
      {
        "mAppName": "...",
        "mBeginTimeStamp": 原起始时间戳,
        "mEndTimeStamp": 原终止时间戳,
        "mPackageName": "非目标应用 - 不修改"
      },
      {
        "mAppName": "覆写应用名",
        "mBeginTimeStamp": 原起始时间戳,
        "mEndTimeStamp": <随机生成>,
        "mPackageName": "${config.packages[0] || 'com.kingsoft'}" - 随机时长为1-${config.max_duration_minutes}分钟
      }
    ],
    "model": "...",
    "swdid": "..."
  }
}`;
}

function editRule(id, methodName, action, customResponse, email = '', isGlobal = false, remark = '') {
    editingRuleId = id;
    document.getElementById('globalRulesSection').classList.add('hidden');
    document.getElementById('userRulesSection').classList.add('hidden');
    document.getElementById('ruleEditor').classList.remove('hidden');
    document.getElementById('ruleEditorTitle').textContent = '编辑规则';
    document.getElementById('ruleMethodName').value = methodName;
    document.getElementById('ruleRemark').value = remark || '';
    
    loadEmailOptions().then(() => {
        if (email) {
            setSelectedEmails(email.split(',').map(e => e.trim()));
        } else {
            clearEmailSelection();
        }
        updateRuleScopeHint();
    });
    
    document.getElementById('ruleAction').value = action;
    
    if (action === 'randomize_app_duration' && customResponse) {
        try {
            const config = JSON.parse(customResponse);
            clearPackageInputs();
            const packages = config.packages || [];
            packages.forEach((pkg, index) => {
                if (index === 0) {
                    const firstInput = document.querySelector('input[name="rulePackageItem"]');
                    if (firstInput) firstInput.value = pkg;
                } else {
                    addPackageInput(pkg);
                }
            });
            document.getElementById('ruleMaxDuration').value = config.max_duration_minutes || 30;
            document.getElementById('ruleKeepCount').value = config.keep_count || 2;
        } catch (e) {
            console.error('Failed to parse randomize config:', e);
        }
    } else {
        document.getElementById('ruleCustomResponse').value = customResponse || '';
    }
    
    toggleCustomResponse();
}

function cancelRuleEdit() {
    editingRuleId = null;
    document.getElementById('ruleEditorTitle').textContent = '创建新规则';
    document.getElementById('ruleMethodName').value = '';
    document.getElementById('ruleRemark').value = '';
    clearPackageInputs();
    document.getElementById('ruleMaxDuration').value = '30';
    document.getElementById('ruleKeepCount').value = '2';
    clearEmailSelection();
    document.getElementById('ruleAction').value = 'passthrough';
    document.getElementById('ruleCustomResponse').value = '';
    document.getElementById('customResponseSection').classList.add('hidden');
    document.getElementById('randomizeConfigSection').classList.add('hidden');
    document.getElementById('ruleEditor').classList.add('hidden');
    if (selectedUserEmail) {
        document.getElementById('userRulesSection').classList.remove('hidden');
    } else {
        document.getElementById('globalRulesSection').classList.remove('hidden');
    }
}

async function saveRule() {
    const methodName = document.getElementById('ruleMethodName').value.trim();
    const selectedEmails = getSelectedEmails();
    const email = selectedEmails.length > 0 ? selectedEmails.join(',') : null;
    const action = document.getElementById('ruleAction').value;
    const remark = document.getElementById('ruleRemark').value.trim() || null;
    let customResponse = null;
    
    if (action === 'randomize_app_duration') {
        const packageInputs = document.querySelectorAll('input[name="rulePackageItem"]');
        const packageList = Array.from(packageInputs)
            .map(input => input.value.trim())
            .filter(p => p);
        const maxDuration = document.getElementById('ruleMaxDuration').value.trim() || '30';
        const keepCount = document.getElementById('ruleKeepCount').value.trim() || '2';
        
        const config = {
            packages: packageList.length > 0 ? packageList : ['com.kingsoft'],
            max_duration_minutes: parseInt(maxDuration, 10) || 30,
            keep_count: parseInt(keepCount, 10) || 2
        };
        customResponse = JSON.stringify(config);
    } else if (action === 'replace' || action === 'modify') {
        customResponse = document.getElementById('ruleCustomResponse').value.trim();
    }

    if (!methodName) {
        alert('Please enter a method name');
        return;
    }

    const btn = document.getElementById('saveRuleBtn');
    btn.disabled = true;
    btn.textContent = 'Saving...';

    try {
        const url = editingRuleId ? `/rules/${editingRuleId}` : '/rules';
        const method = editingRuleId ? 'PUT' : 'POST';

        const body = {
            method_name: methodName,
            action,
            custom_response: customResponse,
            email: email,
            remark: remark,
            is_global: !email
        };

        const res = await apiRequest(url, {
            method,
            body: JSON.stringify(body)
        });

        console.log('Save rule response:', res.status);
        
        if (res.ok) {
            toggleRuleEditor();
            loadRules();
        } else {
            const errorText = await res.text();
            console.log('Save rule error:', errorText);
            let error;
            try {
                error = JSON.parse(errorText);
            } catch {
                error = { error: errorText || 'Failed to save rule' };
            }
            alert(error.detail || error.error || 'Failed to save rule');
        }
    } catch (err) {
        alert('Failed to save rule: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = editingRuleId ? 'Update Rule' : 'Create Rule';
    }
}

async function toggleRuleStatus(id, isEnabled) {
    try {
        const rule = await apiRequest(`/rules/${id}`).then(r => r.json());

        const res = await apiRequest(`/rules/${id}`, {
            method: 'PUT',
            body: JSON.stringify({
                method_name: rule.method_name,
                action: rule.action,
                is_enabled: isEnabled,
                email: rule.email,
                is_global: rule.is_global
            })
        });

        if (res.ok) {
            loadRules();
        } else {
            alert('Failed to update rule status');
        }
    } catch (err) {
        alert('Error: ' + err.message);
    }
}

async function deleteRule(id) {
    if (!confirm('Are you sure you want to delete this rule?')) return;

    try {
        const res = await apiRequest(`/rules/${id}`, { method: 'DELETE' });

        if (res.ok) {
            loadRules();
        } else {
            alert('Failed to delete rule');
        }
    } catch (err) {
        alert('Error: ' + err.message);
    }
}

function formatJsonTree(obj, name, isRoot = false) {
    if (obj === null) {
        return `<div class="tree-item font-mono text-sm py-0.5">
            <span class="w-4 inline-block text-gray-500"></span>
            <span class="font-semibold text-gray-800">${name}:</span>
            <span class="ml-2 text-purple-600">null</span>
        </div>`;
    }

    if (obj === undefined) {
        return `<div class="tree-item font-mono text-sm py-0.5">
            <span class="w-4 inline-block text-gray-500"></span>
            <span class="font-semibold text-gray-800">${name}:</span>
            <span class="ml-2 text-gray-400">undefined</span>
        </div>`;
    }

    const type = typeof obj;

    if (type !== 'object') {
        let valueHtml = '';
        if (type === 'string') {
            if (obj.startsWith('com.') || obj.includes('.') || /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(obj)) {
                valueHtml = `<span class="text-green-600">"${obj}"</span>`;
            } else {
                valueHtml = `<span class="text-green-600">"${escapeHtml(obj)}"</span>`;
            }
        } else if (type === 'number') {
            valueHtml = `<span class="text-blue-600">${obj}</span>`;
        } else if (type === 'boolean') {
            valueHtml = `<span class="text-purple-600">${obj}</span>`;
        } else {
            valueHtml = `<span class="text-gray-500">${String(obj)}</span>`;
        }

        return `<div class="tree-item font-mono text-sm py-0.5">
            <span class="w-4 inline-block text-gray-500"></span>
            <span class="font-semibold text-gray-800">${name}:</span>
            <span class="ml-2">${valueHtml}</span>
        </div>`;
    }

    const isArray = Array.isArray(obj);
    const length = isArray ? obj.length : Object.keys(obj).length;
    const isEmpty = length === 0;

    const toggleId = `toggle-${Math.random().toString(36).substr(2, 9)}`;
    const contentId = `content-${Math.random().toString(36).substr(2, 9)}`;

    let html = `<div class="font-mono text-sm py-0.5">
        <div class="flex items-center cursor-pointer hover:bg-gray-100 rounded px-1" onclick="toggleTreeView('${toggleId}', '${contentId}')">
            <span class="w-4 inline-block text-gray-500 text-xs" id="${toggleId}">${isEmpty ? '' : (isRoot ? '▼' : '►')}</span>
            <span class="font-semibold text-gray-800">${name}:</span>
            ${isEmpty ? `<span class="ml-2 text-gray-500">${isArray ? '[]' : '{}'}</span>` : ''}
        </div>
        <div id="${contentId}" class="${isRoot || isEmpty ? '' : 'hidden'} pl-4 border-l border-gray-200 ml-1">`;

    if (!isEmpty) {
        if (isArray) {
            obj.forEach((item, idx) => {
                html += formatJsonTree(item, String(idx));
            });
        } else {
            Object.keys(obj).forEach((key) => {
                const value = obj[key];
                html += formatJsonTree(value, key);
            });
        }
    }

    html += `</div></div>`;

    return html;
}

function toggleTreeView(toggleId, contentId) {
    const toggle = document.getElementById(toggleId);
    const content = document.getElementById(contentId);

    if (toggle && content) {
        if (content.classList.contains('hidden')) {
            content.classList.remove('hidden');
            toggle.textContent = '▼';
        } else {
            content.classList.add('hidden');
            toggle.textContent = '►';
        }
    }
}

function renderTreeView(containerId, data, isRoot = false) {
    const container = document.getElementById(containerId);
    if (!container) return;

    let obj;
    try {
        if (typeof data === 'string') {
            obj = JSON.parse(data);
        } else {
            obj = data;
        }
    } catch (e) {
        container.textContent = data || 'N/A';
        return;
    }

    container.innerHTML = formatJsonTree(obj, 'body', isRoot);
}

function toggleViewMode(section, mode) {
    const treeEl = document.getElementById(`logDetail${section.charAt(0).toUpperCase() + section.slice(1)}Tree`);
    const rawEl = document.getElementById(`logDetail${section.charAt(0).toUpperCase() + section.slice(1)}Raw`);
    const treeBtn = document.getElementById(`${section}-view-tree`);
    const rawBtn = document.getElementById(`${section}-view-raw`);

    if (mode === 'tree') {
        if (treeEl) treeEl.classList.remove('hidden');
        if (rawEl) rawEl.classList.add('hidden');
        if (treeBtn) {
            treeBtn.className = 'px-2 py-1 bg-gray-200 text-gray-900 font-medium';
            rawBtn.className = 'px-2 py-1 border-l border-gray-300 bg-white text-gray-600 hover:bg-gray-50';
        }
    } else {
        if (treeEl) treeEl.classList.add('hidden');
        if (rawEl) rawEl.classList.remove('hidden');
        if (rawBtn) {
            rawBtn.className = 'px-2 py-1 bg-gray-200 text-gray-900 font-medium';
            treeBtn.className = 'px-2 py-1 border-l border-gray-300 bg-white text-gray-600 hover:bg-gray-50';
        }
    }
}

function showLogDetail(logId) {
    const log = currentLogsData[logId];
    if (!log) return;

    document.getElementById('logDetailTime').textContent = `${log.method} at ${formatChinaTime(log.created_at)}`;

    const requestRaw = document.getElementById('logDetailRequestRaw');
    requestRaw.textContent = JSON.stringify(log.request_body, null, 2);
    renderTreeView('logDetailRequestTree', log.request_body, true);

    const responseRaw = document.getElementById('logDetailResponseRaw');
    responseRaw.textContent = JSON.stringify(log.response_body, null, 2);
    renderTreeView('logDetailResponseTree', log.response_body, true);

    toggleViewMode('request', 'tree');
    toggleViewMode('response', 'tree');

    if (log.intercepted_request && log.request_interception_action && log.request_interception_action !== 'passthrough') {
        document.getElementById('interceptedRequestSection').classList.remove('hidden');
        const interceptedRequestRaw = document.getElementById('logDetailInterceptedRequestRaw');
        interceptedRequestRaw.textContent = JSON.stringify(log.intercepted_request, null, 2);
        renderTreeView('logDetailInterceptedRequestTree', log.intercepted_request, true);

        const badge = document.getElementById('interceptedRequestBadge');
        badge.textContent = log.request_interception_action || 'passthrough';
        badge.className = `px-2 py-1 rounded-full text-xs status-${log.request_interception_action || 'passthrough'}`;

        toggleViewMode('interceptedRequest', 'tree');
    } else {
        document.getElementById('interceptedRequestSection').classList.add('hidden');
    }

    if (log.intercepted_response && log.response_interception_action && log.response_interception_action !== 'passthrough') {
        document.getElementById('interceptedResponseSection').classList.remove('hidden');
        const interceptedResponseRaw = document.getElementById('logDetailInterceptedResponseRaw');
        interceptedResponseRaw.textContent = JSON.stringify(log.intercepted_response, null, 2);
        renderTreeView('logDetailInterceptedResponseTree', log.intercepted_response, true);

        const badge = document.getElementById('interceptedResponseBadge');
        badge.textContent = log.response_interception_action || 'passthrough';
        badge.className = `px-2 py-1 rounded-full text-xs status-${log.response_interception_action || 'passthrough'}`;

        toggleViewMode('interceptedResponse', 'tree');
    } else {
        document.getElementById('interceptedResponseSection').classList.add('hidden');
    }

    renderMatchedRules(log);
    document.getElementById('logDetailModal').classList.remove('hidden');
}

function renderMatchedRules(log) {
    const container = document.getElementById('userRulesDisplay');
    const methodName = log.method;
    
    const matchedRules = allRules.filter(rule => {
        if (rule.is_global) {
            return rule.method_name === methodName;
        }
        return rule.method_name === methodName && rule.email;
    });

    if (matchedRules.length === 0) {
        container.innerHTML = `
            <div class="p-8 text-center text-gray-500">
                <p class="mb-2">没有找到匹配的规则</p>
                <p class="text-sm text-gray-400">Method: ${escapeHtml(methodName)}</p>
            </div>
        `;
        return;
    }

    container.innerHTML = matchedRules.map(rule => `
        <div class="p-4 hover:bg-gray-50">
            <div class="flex items-center justify-between mb-2">
                <span class="font-medium text-gray-900">${escapeHtml(rule.method_name)}</span>
                <span class="px-2 py-1 rounded-full text-xs ${rule.is_enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}">
                    ${rule.is_enabled ? 'Enabled' : 'Disabled'}
                </span>
            </div>
            <div class="grid grid-cols-2 gap-2 text-sm">
                <div>
                    <span class="text-gray-500">动作:</span>
                    <span class="ml-1 text-gray-900">${rule.action}</span>
                </div>
                <div>
                    <span class="text-gray-500">类型:</span>
                    <span class="ml-1 text-gray-900">${rule.is_global ? '全局' : '用户: ' + rule.email}</span>
                </div>
            </div>
            ${rule.custom_response ? `
                <div class="mt-2 text-xs text-gray-500">
                    <span class="font-medium">自定义响应:</span>
                    <pre class="mt-1 p-2 bg-gray-100 rounded overflow-x-auto">${escapeHtml(rule.custom_response)}</pre>
                </div>
            ` : ''}
        </div>
    `).join('');
}

function closeLogDetailModal() {
    document.getElementById('logDetailModal').classList.add('hidden');
}

function filterLogsByMethod() {
    logsPage = 1;
    const method = document.getElementById('logMethodFilter').value;
    const search = document.getElementById('logSearch').value;
    loadLogs(method, search);
}

function debounceSearch(e) {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        logsPage = 1;
        const method = document.getElementById('logMethodFilter').value;
        const search = e.target.value;
        loadLogs(method, search);
    }, 300);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

let selectedUserEmail = null;
let allRules = [];

async function loadRules() {
    try {
        const res = await apiRequest('/rules');
        allRules = await res.json();
        renderUsersList();
        renderGlobalRules();
        renderRulesTable();
    } catch (err) {
    }
}

function renderUsersList() {
    const container = document.getElementById('usersList');
    const users = [...new Set(allRules.filter(r => r.email).map(r => r.email))];
    
    if (users.length === 0) {
        container.innerHTML = '<p class="text-sm text-gray-500">暂无用户特定规则</p>';
        return;
    }
    
    container.innerHTML = users.map(email => `
        <button onclick="showUserRules('${escapeHtml(email)}')"
            class="w-full px-3 py-2 text-left text-sm rounded-lg hover:bg-gray-100 transition-colors flex items-center justify-between">
            <span class="truncate text-gray-700">${escapeHtml(email)}</span>
            <span class="text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full">
                ${allRules.filter(r => r.email === email).length}
            </span>
        </button>
    `).join('');
}

function renderGlobalRules() {
    const container = document.getElementById('globalRulesList');
    const globalRules = allRules.filter(r => r.is_global);
    
    if (globalRules.length === 0) {
        container.innerHTML = '<p class="text-sm text-gray-500">未配置全局规则</p>';
        return;
    }
    
    container.innerHTML = globalRules.map(rule => `
        <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-gray-900 truncate">${escapeHtml(rule.method_name)}</p>
                <p class="text-xs text-gray-500">${getActionDisplayName(rule.action)}</p>
            </div>
            <div class="flex items-center space-x-2 flex-shrink-0">
                <span class="px-2 py-1 rounded-full text-xs ${rule.is_enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}">
                    ${rule.is_enabled ? '✓' : '✗'}
                </span>
                <button onclick="openRuleEditor(${rule.id})" class="text-indigo-600 hover:text-indigo-900 text-sm">编辑</button>
                <button onclick="deleteRule(${rule.id})" class="text-red-600 hover:text-red-900 text-sm">删除</button>
            </div>
        </div>
    `).join('');
}

function renderUserRules(email) {
    const container = document.getElementById('userRulesList');
    const userRules = allRules.filter(r => r.email === email);
    
    if (userRules.length === 0) {
        container.innerHTML = '<p class="text-sm text-gray-500">此用户没有规则</p>';
        return;
    }
    
    container.innerHTML = userRules.map(rule => `
        <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-gray-900 truncate">${escapeHtml(rule.method_name)}</p>
                <p class="text-xs text-gray-500">${getActionDisplayName(rule.action)}</p>
            </div>
            <div class="flex items-center space-x-2 flex-shrink-0">
                <span class="px-2 py-1 rounded-full text-xs ${rule.is_enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}">
                    ${rule.is_enabled ? '✓' : '✗'}
                </span>
                <button onclick="openUserRuleEditor(${rule.id})" class="text-indigo-600 hover:text-indigo-900 text-sm">编辑</button>
                <button onclick="deleteRule(${rule.id})" class="text-red-600 hover:text-red-900 text-sm">删除</button>
            </div>
        </div>
    `).join('');
}

function openUserRuleEditor(ruleId) {
    const rule = allRules.find(r => r.id === ruleId);
    if (!rule) return;
    
    editingRuleId = rule.id;
    document.getElementById('globalRulesSection').classList.add('hidden');
    document.getElementById('userRulesSection').classList.add('hidden');
    document.getElementById('ruleEditor').classList.remove('hidden');
    document.getElementById('ruleEditorTitle').textContent = '编辑规则';
    document.getElementById('ruleMethodName').value = rule.method_name || '';
    document.getElementById('ruleRemark').value = rule.remark || '';
    
    loadEmailOptions().then(() => {
        if (rule.email) {
            setSelectedEmails(rule.email.split(',').map(e => e.trim()));
        } else {
            clearEmailSelection();
        }
        updateRuleScopeHint();
    });
    
    document.getElementById('ruleAction').value = rule.action || 'passthrough';
    
    if (rule.action === 'randomize_app_duration' && rule.custom_response) {
        try {
            const config = JSON.parse(rule.custom_response);
            clearPackageInputs();
            const packages = config.packages || [];
            packages.forEach((pkg, index) => {
                if (index === 0) {
                    const firstInput = document.querySelector('input[name="rulePackageItem"]');
                    if (firstInput) firstInput.value = pkg;
                } else {
                    addPackageInput(pkg);
                }
            });
            document.getElementById('ruleMaxDuration').value = config.max_duration_minutes || 30;
            document.getElementById('ruleKeepCount').value = config.keep_count || 2;
        } catch (e) {
            console.error('Failed to parse randomize config:', e);
        }
    } else {
        document.getElementById('ruleCustomResponse').value = rule.custom_response || '';
    }
    
    toggleCustomResponse();
}

function openRuleEditor(ruleId) {
    const rule = allRules.find(r => r.id === ruleId);
    if (!rule) return;
    
    editingRuleId = rule.id;
    document.getElementById('globalRulesSection').classList.add('hidden');
    document.getElementById('userRulesSection').classList.add('hidden');
    document.getElementById('ruleEditor').classList.remove('hidden');
    document.getElementById('ruleEditorTitle').textContent = '编辑规则';
    document.getElementById('ruleMethodName').value = rule.method_name || '';
    document.getElementById('ruleRemark').value = rule.remark || '';
    
    loadEmailOptions().then(() => {
        if (rule.email) {
            setSelectedEmails(rule.email.split(',').map(e => e.trim()));
        } else {
            clearEmailSelection();
        }
        updateRuleScopeHint();
    });
    
    document.getElementById('ruleAction').value = rule.action || 'passthrough';
    
    if (rule.action === 'randomize_app_duration' && rule.custom_response) {
        try {
            const config = JSON.parse(rule.custom_response);
            clearPackageInputs();
            const packages = config.packages || [];
            packages.forEach((pkg, index) => {
                if (index === 0) {
                    const firstInput = document.querySelector('input[name="rulePackageItem"]');
                    if (firstInput) firstInput.value = pkg;
                } else {
                    addPackageInput(pkg);
                }
            });
            document.getElementById('ruleMaxDuration').value = config.max_duration_minutes || 30;
            document.getElementById('ruleKeepCount').value = config.keep_count || 2;
        } catch (e) {
            console.error('Failed to parse randomize config:', e);
        }
    } else {
        document.getElementById('ruleCustomResponse').value = rule.custom_response || '';
    }
    
    toggleCustomResponse();
}

function showGlobalRules() {
    selectedUserEmail = null;
    document.getElementById('globalRulesSection').classList.remove('hidden');
    document.getElementById('userRulesSection').classList.add('hidden');
    document.getElementById('ruleEditor').classList.add('hidden');
    renderRulesTable();
}

function showUserRules(email) {
    selectedUserEmail = email;
    document.getElementById('globalRulesSection').classList.add('hidden');
    document.getElementById('userRulesSection').classList.remove('hidden');
    document.getElementById('ruleEditor').classList.add('hidden');
    document.getElementById('selectedUserTitle').textContent = '用户规则';
    document.getElementById('selectedUserEmail').textContent = email;
    renderUserRules(email);
    renderRulesTable(email);
}

function showGlobalRuleEditor() {
    document.getElementById('globalRulesSection').classList.add('hidden');
    document.getElementById('userRulesSection').classList.add('hidden');
    document.getElementById('ruleEditor').classList.remove('hidden');
    document.getElementById('ruleEditorTitle').textContent = '创建规则';
    editingRuleId = null;
    document.getElementById('ruleMethodName').value = '';
    document.getElementById('ruleAction').value = 'passthrough';
    document.getElementById('ruleCustomResponse').value = '';
    document.getElementById('customResponseSection').classList.add('hidden');
    
    loadEmailOptions().then(() => {
        clearEmailSelection();
    });
}

function showUserRuleEditor() {
    document.getElementById('globalRulesSection').classList.add('hidden');
    document.getElementById('userRulesSection').classList.add('hidden');
    document.getElementById('ruleEditor').classList.remove('hidden');
    document.getElementById('ruleEditorTitle').textContent = '创建规则';
    
    loadEmailOptions().then(() => {
        if (selectedUserEmail) {
            setSelectedEmails([selectedUserEmail]);
        } else {
            clearEmailSelection();
        }
        updateRuleScopeHint();
    });
    
    editingRuleId = null;
    document.getElementById('ruleMethodName').value = '';
    document.getElementById('ruleAction').value = 'passthrough';
    document.getElementById('ruleCustomResponse').value = '';
    document.getElementById('customResponseSection').classList.add('hidden');
}

function renderRulesTable(userEmail = null) {
    const tbody = document.getElementById('rulesTableBody');
    let rules = allRules;
    
    if (userEmail) {
        rules = rules.filter(r => r.email === userEmail);
    } else if (selectedUserEmail) {
        rules = rules.filter(r => r.email === selectedUserEmail);
    }
    
    if (!rules.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="px-4 py-12 text-center text-gray-500">未找到规则</td></tr>';
        return;
    }
    
    tbody.innerHTML = rules.map(rule => `
        <tr class="hover:bg-gray-50">
            <td class="px-4 py-3 text-sm font-medium text-gray-900 whitespace-nowrap">${escapeHtml(rule.method_name)}</td>
            <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                ${rule.is_global 
                    ? '<span class="px-2 py-1 rounded-full text-xs bg-purple-100 text-purple-800">全局</span>'
                    : `<span class="px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-800">${escapeHtml(rule.email || '-')}</span>`
                }
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                <span class="px-2 py-1 rounded-full text-xs font-semibold status-${rule.action}">${getActionDisplayName(rule.action)}</span>
            </td>
            <td class="px-4 py-3 text-sm text-gray-500 max-w-xs truncate">
                ${rule.remark ? `<span class="text-gray-700" title="${escapeHtml(rule.remark)}">${escapeHtml(rule.remark)}</span>` : '<span class="text-gray-400">-</span>'}
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-sm text-gray-500">
                <button onclick="toggleRuleStatus(${rule.id}, ${!rule.is_enabled})" 
                    class="px-2 py-1 rounded-md text-xs font-medium ${rule.is_enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}">
                    ${rule.is_enabled ? '✓ Enabled' : '✗ Disabled'}
                </button>
            </td>
            <td class="px-4 py-3 whitespace-nowrap text-right text-sm font-medium">
                <button onclick="openRuleEditor(${rule.id})" class="text-indigo-600 hover:text-indigo-900 mr-2">编辑</button>
                <button onclick="deleteRule(${rule.id})" class="text-red-600 hover:text-red-900">删除</button>
            </td>
        </tr>
    `).join('');
}

document.addEventListener('click', function(event) {
    const dropdown = document.getElementById('emailDropdown');
    const options = document.getElementById('emailOptions');
    if (dropdown && options && !dropdown.contains(event.target)) {
        options.classList.add('hidden');
    }
});

document.addEventListener('DOMContentLoaded', init);