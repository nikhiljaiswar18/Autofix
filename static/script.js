const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const fileInfo = document.getElementById('file-info');
const fileName = document.getElementById('file-name');
const removeFile = document.getElementById('remove-file');
const analyzeBtn = document.getElementById('analyze-btn');
const uploadSection = document.getElementById('upload-section');
const loading = document.getElementById('loading');
const results = document.getElementById('results');
const errorDiv = document.getElementById('error');
const errorMessage = document.getElementById('error-message');
const errorDismiss = document.getElementById('error-dismiss');

let selectedFile = null;
let analysisResult = null;
let originalCode = '';

const ALLOWED_EXTENSIONS = ['.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.cc', '.cxx', '.c', '.h', '.hpp', '.go'];

function getFileExtension(name) {
    const dot = name.lastIndexOf('.');
    return dot !== -1 ? name.substring(dot).toLowerCase() : '';
}

// --- Drag & Drop ---
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
});

dropZone.addEventListener('click', (e) => {
    // Avoid double-trigger when clicking the label/button (it already opens the dialog)
    if (e.target.closest('.file-btn') || e.target === fileInput) return;
    fileInput.click();
});

fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) handleFile(fileInput.files[0]);
});

function handleFile(file) {
    const ext = getFileExtension(file.name);
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
        showError(`Unsupported file type "${ext}". Supported: ${ALLOWED_EXTENSIONS.join(', ')}`);
        return;
    }
    if (file.size > 500 * 1024) {
        showError('File too large. Maximum size is 500KB.');
        return;
    }
    selectedFile = file;
    const langMap = {
        '.py': 'Python', '.js': 'JavaScript', '.jsx': 'JavaScript', '.ts': 'TypeScript',
        '.tsx': 'TypeScript', '.java': 'Java', '.cpp': 'C++', '.cc': 'C++',
        '.cxx': 'C++', '.c': 'C', '.h': 'C/C++', '.hpp': 'C++', '.go': 'Go'
    };
    const lang = langMap[ext] || 'Code';
    fileName.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB) — ${lang}`;
    fileInfo.classList.remove('hidden');
    analyzeBtn.classList.remove('hidden');
    dropZone.classList.add('hidden');

    // Pre-read original code
    const reader = new FileReader();
    reader.onload = (e) => { originalCode = e.target.result; };
    reader.readAsText(file);
}

removeFile.addEventListener('click', resetUpload);

function resetUpload() {
    selectedFile = null;
    originalCode = '';
    fileInput.value = '';
    fileInfo.classList.add('hidden');
    analyzeBtn.classList.add('hidden');
    dropZone.classList.remove('hidden');
}

// ===== Progress Steps =====
function resetProgress() {
    ['bugs', 'security', 'style', 'fix'].forEach(id => {
        const el = document.getElementById(`step-${id}`);
        el.className = 'step';
        el.querySelector('.step-icon').textContent = '\u25CB';
    });
    document.getElementById('progress-bar').style.width = '0%';
    document.getElementById('progress-detail').textContent = 'Preparing analysis...';
}

function updateProgress(step, status, detail) {
    const stepMap = { bugs: 'step-bugs', security: 'step-security', style: 'step-style', fix: 'step-fix' };
    const el = document.getElementById(stepMap[step]);
    if (!el) return;

    el.className = `step ${status}`;
    if (status === 'running') {
        el.querySelector('.step-icon').textContent = '\u25CF';
    } else if (status === 'done') {
        el.querySelector('.step-icon').textContent = '\u2713';
    }

    if (detail) {
        document.getElementById('progress-detail').textContent = detail;
    }

    // Update progress bar
    const steps = document.querySelectorAll('.step.done');
    const pct = Math.min((steps.length / 4) * 100, 100);
    document.getElementById('progress-bar').style.width = pct + '%';
}

// ===== Analyze with SSE Streaming =====
analyzeBtn.addEventListener('click', async () => {
    if (!selectedFile) return;

    uploadSection.classList.add('hidden');
    loading.classList.remove('hidden');
    results.classList.add('hidden');
    errorDiv.classList.add('hidden');
    resetProgress();

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
        // Step 1: Upload file and get job_id
        const uploadRes = await fetch('/api/analyze-stream', { method: 'POST', body: formData });
        if (!uploadRes.ok) {
            const err = await uploadRes.json();
            throw new Error(err.detail || 'Upload failed.');
        }
        const { job_id } = await uploadRes.json();

        // Step 2: Connect to SSE for progress
        const evtSource = new EventSource(`/api/analyze-stream/${job_id}`);

        evtSource.addEventListener('progress', (e) => {
            const data = JSON.parse(e.data);
            updateProgress(data.step, data.status, data.detail);
        });

        evtSource.onmessage = (e) => {
            // Final result
            evtSource.close();
            analysisResult = JSON.parse(e.data);
            renderResults(analysisResult);
            loading.classList.add('hidden');
            results.classList.remove('hidden');
        };

        evtSource.onerror = () => {
            evtSource.close();
            // Fallback to non-streaming
            fallbackAnalyze();
        };

    } catch (err) {
        loading.classList.add('hidden');
        showError(err.message);
    }
});

async function fallbackAnalyze() {
    const formData = new FormData();
    formData.append('file', selectedFile);
    try {
        const response = await fetch('/api/analyze', { method: 'POST', body: formData });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Analysis failed.');
        }
        analysisResult = await response.json();
        renderResults(analysisResult);
        loading.classList.add('hidden');
        results.classList.remove('hidden');
    } catch (err) {
        loading.classList.add('hidden');
        showError(err.message);
    }
}

// ===== Render Results =====
function renderResults(data) {
    // Summary
    document.getElementById('bug-count').textContent = data.summary.bugs;
    document.getElementById('security-count').textContent = data.summary.security;
    document.getElementById('style-count').textContent = data.summary.style;
    document.getElementById('total-count').textContent = data.summary.total;

    // Grade ring
    renderGrade(data.grade || { grade: 'A+', score: 100, color: '#3fb950' });

    // Issues
    renderIssues(data.issues, 'all');

    // Diff view
    renderDiff(originalCode, data.fixed_code);

    // Fixed code
    document.getElementById('fixed-code').textContent = data.fixed_code;
    document.getElementById('explanation').textContent = data.explanation;

    // Original code
    document.getElementById('original-code').textContent = originalCode;
}

// ===== Grade Ring Animation =====
function renderGrade(grade) {
    const circumference = 2 * Math.PI * 52; // r=52
    const offset = circumference - (grade.score / 100) * circumference;

    const ring = document.getElementById('grade-ring-fill');
    ring.style.stroke = grade.color;
    // Trigger animation
    setTimeout(() => {
        ring.style.strokeDashoffset = offset;
    }, 100);

    const letter = document.getElementById('grade-letter');
    letter.textContent = grade.grade;
    letter.style.color = grade.color;

    document.getElementById('grade-score').textContent = `${grade.score}/100`;
}

// ===== Diff View =====
function renderDiff(original, fixed) {
    const diffView = document.getElementById('diff-view');
    const origLines = original.split('\n');
    const fixedLines = fixed.split('\n');

    // Simple line-by-line diff using LCS
    const diff = computeDiff(origLines, fixedLines);

    let html = '';
    let lineNum = 0;

    for (const entry of diff) {
        lineNum++;
        if (entry.type === 'removed') {
            html += `<div class="diff-line removed">
                <span class="diff-line-num">${lineNum}</span>
                <span class="diff-line-sign">-</span>
                <span class="diff-line-text">${escapeHtml(entry.text)}</span>
            </div>`;
        } else if (entry.type === 'added') {
            html += `<div class="diff-line added">
                <span class="diff-line-num">${lineNum}</span>
                <span class="diff-line-sign">+</span>
                <span class="diff-line-text">${escapeHtml(entry.text)}</span>
            </div>`;
        } else {
            html += `<div class="diff-line">
                <span class="diff-line-num">${lineNum}</span>
                <span class="diff-line-sign"> </span>
                <span class="diff-line-text">${escapeHtml(entry.text)}</span>
            </div>`;
        }
    }

    diffView.innerHTML = html || '<div class="no-issues">No changes made — code is identical.</div>';
}

function computeDiff(origLines, fixedLines) {
    // Build a simple diff using a greedy approach
    const result = [];
    let oi = 0, fi = 0;

    while (oi < origLines.length || fi < fixedLines.length) {
        if (oi < origLines.length && fi < fixedLines.length) {
            if (origLines[oi] === fixedLines[fi]) {
                result.push({ type: 'same', text: origLines[oi] });
                oi++;
                fi++;
            } else {
                // Look ahead in fixed to see if orig line appears later
                let foundInFixed = -1;
                for (let k = fi + 1; k < Math.min(fi + 5, fixedLines.length); k++) {
                    if (fixedLines[k] === origLines[oi]) { foundInFixed = k; break; }
                }

                let foundInOrig = -1;
                for (let k = oi + 1; k < Math.min(oi + 5, origLines.length); k++) {
                    if (origLines[k] === fixedLines[fi]) { foundInOrig = k; break; }
                }

                if (foundInOrig !== -1 && (foundInFixed === -1 || foundInOrig - oi <= foundInFixed - fi)) {
                    // Lines removed from original
                    while (oi < foundInOrig) {
                        result.push({ type: 'removed', text: origLines[oi] });
                        oi++;
                    }
                } else if (foundInFixed !== -1) {
                    // Lines added in fixed
                    while (fi < foundInFixed) {
                        result.push({ type: 'added', text: fixedLines[fi] });
                        fi++;
                    }
                } else {
                    // Replace: remove old, add new
                    result.push({ type: 'removed', text: origLines[oi] });
                    result.push({ type: 'added', text: fixedLines[fi] });
                    oi++;
                    fi++;
                }
            }
        } else if (oi < origLines.length) {
            result.push({ type: 'removed', text: origLines[oi] });
            oi++;
        } else {
            result.push({ type: 'added', text: fixedLines[fi] });
            fi++;
        }
    }

    return result;
}

function renderIssues(issues, filter) {
    const list = document.getElementById('issues-list');
    const filtered = filter === 'all' ? issues : issues.filter(i => i.type === filter);

    if (filtered.length === 0) {
        list.innerHTML = '<div class="no-issues">No issues found in this category!</div>';
        return;
    }

    list.innerHTML = filtered.map(issue => `
        <div class="issue-item ${issue.severity || 'info'}">
            <div class="issue-header">
                <span class="badge badge-${issue.type}">${issue.type}</span>
                <span class="badge badge-${issue.severity || 'info'}">${issue.severity || 'info'}</span>
                ${issue.line ? `<span class="issue-line">Line ${issue.line}</span>` : ''}
            </div>
            <div class="issue-desc">${escapeHtml(issue.description || '')}</div>
            <div class="issue-fix">Fix: ${escapeHtml(issue.fix || '')}</div>
        </div>
    `).join('');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// --- Tabs ---
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById(`tab-${tab.dataset.tab}`).classList.add('active');
    });
});

// --- Filters ---
document.querySelectorAll('.filter').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.filter').forEach(f => f.classList.remove('active'));
        btn.classList.add('active');
        if (analysisResult) renderIssues(analysisResult.issues, btn.dataset.filter);
    });
});

// --- Copy & Download ---
document.getElementById('copy-btn').addEventListener('click', () => {
    const code = document.getElementById('fixed-code').textContent;
    navigator.clipboard.writeText(code).then(() => {
        const btn = document.getElementById('copy-btn');
        btn.textContent = 'Copied!';
        setTimeout(() => btn.textContent = 'Copy', 2000);
    });
});

document.getElementById('download-btn').addEventListener('click', () => {
    if (!analysisResult) return;
    const blob = new Blob([analysisResult.fixed_code], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `fixed_${analysisResult.original_file}`;
    a.click();
    URL.revokeObjectURL(url);
});

// --- PDF Report ---
document.getElementById('pdf-btn').addEventListener('click', async () => {
    if (!selectedFile) return;

    const btn = document.getElementById('pdf-btn');
    btn.textContent = 'Generating...';
    btn.disabled = true;

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
        const response = await fetch('/api/report', { method: 'POST', body: formData });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Report generation failed.');
        }
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `autofix_report_${selectedFile.name}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
        btn.textContent = 'Downloaded!';
        setTimeout(() => { btn.textContent = 'Download PDF Report'; btn.disabled = false; }, 2000);
    } catch (err) {
        btn.textContent = 'Download PDF Report';
        btn.disabled = false;
        showError(err.message);
    }
});

// ===== Test Cases =====
document.getElementById('run-tests-btn').addEventListener('click', async () => {
    if (!selectedFile) return;

    const btn = document.getElementById('run-tests-btn');
    const testLoading = document.getElementById('test-loading');
    const testPrompt = document.getElementById('test-prompt');
    const testResults = document.getElementById('test-results');

    btn.disabled = true;
    testPrompt.classList.add('hidden');
    testLoading.classList.remove('hidden');
    testResults.classList.add('hidden');

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
        const response = await fetch('/api/test-cases', { method: 'POST', body: formData });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Test generation failed.');
        }
        const data = await response.json();
        renderTestResults(data);
        testLoading.classList.add('hidden');
        testResults.classList.remove('hidden');
    } catch (err) {
        testLoading.classList.add('hidden');
        testPrompt.classList.remove('hidden');
        btn.disabled = false;
        showError(err.message);
    }
});

function renderTestResults(data) {
    // Summary bar
    const s = data.summary;
    document.getElementById('test-summary').innerHTML = `
        <span class="test-stat total">Total: ${s.total}</span>
        <span class="test-stat passed">Passed: ${s.passed}</span>
        <span class="test-stat failed">Failed: ${s.failed}</span>
        <span class="test-stat errors">Errors: ${s.errors}</span>
        <span class="test-stat skipped">Skipped: ${s.skipped}</span>
    `;

    // Table rows
    const tbody = document.getElementById('test-table-body');
    tbody.innerHTML = data.test_cases.map(tc => {
        const statusClass = tc.status;
        const statusLabel = tc.status === 'pass' ? 'PASS' : tc.status === 'fail' ? 'FAIL' : tc.status === 'error' ? 'ERROR' : 'SKIP';

        return `<tr>
            <td><span class="test-status ${statusClass}">${statusLabel}</span></td>
            <td><strong>${escapeHtml(tc.function)}</strong></td>
            <td>
                <div class="test-code">${escapeHtml(tc.test_code)}</div>
                <div style="color:#8b949e;font-size:0.8rem;margin-top:2px">${escapeHtml(tc.description)}</div>
                ${tc.error ? `<div class="test-error-msg">${escapeHtml(tc.error)}</div>` : ''}
                ${tc.notes ? `<div style="color:#8957e5;font-size:0.8rem;margin-top:4px">${escapeHtml(tc.notes)}</div>` : ''}
            </td>
            <td><code>${escapeHtml(tc.expected)}</code></td>
            <td><code>${tc.actual !== null ? escapeHtml(tc.actual) : '—'}</code></td>
            <td><span class="test-category ${tc.category}">${tc.category}</span></td>
        </tr>`;
    }).join('');

    // Suggestions
    const sugDiv = document.getElementById('test-suggestions');
    if (data.suggestions && data.suggestions.length > 0) {
        sugDiv.innerHTML = `
            <h4>Suggestions for Improvement</h4>
            ${data.suggestions.map(s => `<div class="suggestion-item">${escapeHtml(s)}</div>`).join('')}
        `;
    } else {
        sugDiv.innerHTML = '';
    }
}

// --- Reset ---
document.getElementById('reset-btn').addEventListener('click', () => {
    results.classList.add('hidden');
    uploadSection.classList.remove('hidden');
    resetUpload();
    analysisResult = null;
    // Reset grade ring
    document.getElementById('grade-ring-fill').style.strokeDashoffset = '326.73';
    // Reset test cases tab
    document.getElementById('test-prompt').classList.remove('hidden');
    document.getElementById('test-results').classList.add('hidden');
    document.getElementById('test-loading').classList.add('hidden');
    document.getElementById('run-tests-btn').disabled = false;
});

// --- Error ---
function showError(msg) {
    errorMessage.textContent = msg;
    errorDiv.classList.remove('hidden');
    uploadSection.classList.add('hidden');
    loading.classList.add('hidden');
}

errorDismiss.addEventListener('click', () => {
    errorDiv.classList.add('hidden');
    uploadSection.classList.remove('hidden');
    resetUpload();
});
