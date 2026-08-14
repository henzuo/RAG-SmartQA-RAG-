// ===== Tab切换 =====
function switchTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    document.getElementById(tabName + '-tab').classList.add('active');
    event.target.classList.add('active');

    // 切换到文档管理页时刷新列表
    if (tabName === 'docs') {
        loadDocList();
        loadStats();
    }
}

// ===== 文档管理 =====

// 页面加载时填充策略下拉框
async function loadStrategies() {
    const resp = await fetch('/api/docs/strategies');
    const strategies = await resp.json();
    const select = document.getElementById('strategy-select');
    select.innerHTML = '';
    strategies.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s.key;
        opt.textContent = s.name;
        select.appendChild(opt);
    });
}

// 上传文件
async function uploadFile() {
    const fileInput = document.getElementById('file-input');
    const strategy = document.getElementById('strategy-select').value;
    const resultDiv = document.getElementById('upload-result');

    if (!fileInput.files.length) {
        resultDiv.innerHTML = '<span style="color:red">请选择文件</span>';
        return;
    }

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('strategy', strategy);

    resultDiv.innerHTML = '上传中...';

    try {
        const resp = await fetch('/api/docs/upload', {
            method: 'POST',
            body: formData,
        });
        const data = await resp.json();

        if (resp.ok) {
            resultDiv.innerHTML = `<span style="color:green">上传成功！${data.filename}，切成 ${data.chunk_count} 段，共 ${data.total_chars} 字符</span>`;
            fileInput.value = '';
            loadDocList();
            loadStats();
        } else {
            resultDiv.innerHTML = `<span style="color:red">上传失败：${data.detail}</span>`;
        }
    } catch (e) {
        resultDiv.innerHTML = `<span style="color:red">上传出错：${e.message}</span>`;
    }
}

// 加载文档列表
async function loadDocList() {
    const resp = await fetch('/api/docs/list');
    const docs = await resp.json();
    const listDiv = document.getElementById('doc-list');

    if (docs.length === 0) {
        listDiv.innerHTML = '<p style="color:#999">暂无文档，请先上传</p>';
        return;
    }

    listDiv.innerHTML = docs.map(doc => `
        <div class="doc-item">
            <div class="doc-info">
                <strong>${doc.filename}</strong>
                <span style="color:#888; margin-left:10px">${doc.chunk_count} 段 | ${doc.total_chars} 字符</span>
            </div>
            <button class="delete-btn" onclick="deleteDoc('${doc.doc_id}')">删除</button>
        </div>
    `).join('');
}

// 删除文档
async function deleteDoc(docId) {
    if (!confirm('确定删除这个文档吗？')) return;

    await fetch(`/api/docs/${docId}`, { method: 'DELETE' });
    loadDocList();
    loadStats();
}

// 加载统计信息
async function loadStats() {
    const resp = await fetch('/api/docs/stats');
    const stats = await resp.json();
    document.getElementById('stats-info').textContent =
        `向量库统计：${stats.total_documents} 个文档，${stats.total_chunks} 个分段`;
}

// ===== 聊天问答 =====

function addMessage(role, text) {
    const messagesDiv = document.getElementById('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;

    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.textContent = text;
    msgDiv.appendChild(bubble);

    messagesDiv.appendChild(msgDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function addThinking(text) {
    const messagesDiv = document.getElementById('chat-messages');
    const box = document.createElement('div');
    box.className = 'thinking-box';
    box.textContent = '💭 ' + text;
    messagesDiv.appendChild(box);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function addReferences(refs) {
    const messagesDiv = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = 'references';
    div.innerHTML = refs.map(r =>
        `<span class="ref-tag">${r.filename} #${r.chunk_index} (score: ${r.score})</span>`
    ).join('');
    messagesDiv.appendChild(div);
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    if (!message) return;

    // 显示用户消息
    addMessage('user', message);
    input.value = '';

    // 获取设置
    const mode = document.getElementById('chat-mode').value;
    const topK = parseInt(document.getElementById('chat-top-k').value);
    const threshold = parseFloat(document.getElementById('chat-threshold').value);
    const useHybrid = document.getElementById('chat-hybrid').checked;

    try {
        const resp = await fetch('/api/chat/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                mode: mode,
                top_k: topK,
                threshold: threshold,
                use_hybrid: useHybrid,
            }),
        });

        const data = await resp.json();

        if (resp.ok) {
            // 显示思考过程
            if (data.thinking) {
                addThinking(data.thinking);
            }
            // 显示回答
            addMessage('bot', data.answer);
            // 显示引用来源
            if (data.references && data.references.length > 0) {
                addReferences(data.references);
            }
        } else {
            addMessage('bot', '出错了：' + (data.detail || '未知错误'));
        }
    } catch (e) {
        addMessage('bot', '请求失败：' + e.message);
    }
}

async function clearChatHistory() {
    await fetch('/api/chat/clear', { method: 'POST' });
    document.getElementById('chat-messages').innerHTML = '';
}

// ===== 检索调试 =====

async function debugSearch() {
    const query = document.getElementById('debug-query').value.trim();
    const mode = document.getElementById('debug-mode').value;
    const resultsDiv = document.getElementById('debug-results');

    if (!query) {
        resultsDiv.innerHTML = '<p style="color:#999">请输入查询内容</p>';
        return;
    }

    resultsDiv.innerHTML = '搜索中...';

    try {
        let url = '';
        if (mode === 'vector') {
            url = `/api/chat/send`;
        }

        // 用chat/send接口做检索，但也可以单独调向量库
        // 这里直接调向量库的search接口更直观
        const resp = await fetch('/api/chat/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: query,
                mode: 'cot',
                top_k: 5,
                threshold: 0,
                use_hybrid: mode === 'hybrid',
            }),
        });

        const data = await resp.json();

        if (data.references && data.references.length > 0) {
            resultsDiv.innerHTML = data.references.map(r => {
                let scoreClass = 'score-high';
                if (r.score < 0.5) scoreClass = 'score-low';
                else if (r.score < 0.7) scoreClass = 'score-medium';

                return `
                    <div class="debug-result-item">
                        <span class="score ${scoreClass}">${r.source} | score: ${r.score}</span>
                        <div class="content">${r.content}</div>
                        <div class="meta">${r.filename} | chunk #${r.chunk_index}</div>
                    </div>
                `;
            }).join('');
        } else {
            resultsDiv.innerHTML = '<p style="color:#999">未检索到相关内容</p>';
        }
    } catch (e) {
        resultsDiv.innerHTML = `<p style="color:red">搜索出错：${e.message}</p>`;
    }
}

// ===== 页面加载时初始化 =====
window.onload = function () {
    loadStrategies();
    loadDocList();
    loadStats();
};