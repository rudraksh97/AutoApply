// background.js - Handles data fetching and triggers form filling

const API_BASE = 'http://localhost:8000';

console.log('🚀 AutoApply background script loaded');

logToStorage('info', 'Background script loaded');

// Helper to log to storage for popup view
async function logToStorage(level, message, data = null) {
    try {
        const timestamp = Date.now();
        const logEntry = {
            timestamp,
            level,
            message: data ? `${message} ${JSON.stringify(data)}` : message
        };

        const result = await chrome.storage.local.get('logs');
        const logs = result.logs || [];
        logs.push(logEntry);

        // Keep last 100 logs
        if (logs.length > 100) {
            logs.shift();
        }

        await chrome.storage.local.set({ logs });
    } catch (e) {
        console.error('Failed to save log', e);
    }
}

// Handle messages from Popup and Content Script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'triggerAutoApply') {
        const { tabId, url } = request;
        handleAutoApply(tabId, url);
        return true;
    }

    if (request.action === 'log') {
        logToStorage(request.level, request.message, request.data);
        return true;
    }

    if (request.action === 'fetchDraftData') {
        const draftId = request.draftId;
        const apiUrl = `${API_BASE}/drafts/${draftId}`;

        fetch(apiUrl)
            .then(response => {
                if (!response.ok) throw new Error('API request failed');
                return response.json();
            })
            .then(data => {
                sendResponse({ success: true, data: data });
            })
            .catch(error => {
                console.error('AutoApply Fetch Error:', error);
                logToStorage('error', 'Fetch Error', error.message);
                sendResponse({ success: false, error: error.message });
            });

        return true; // Will respond asynchronously
    }
});

async function handleAutoApply(tabId, url) {
    console.log('🖱️ AutoApply: Triggered for tab', url);
    logToStorage('info', 'Triggered for URL', url);

    // Show loading state
    chrome.action.setBadgeText({ text: '...', tabId: tabId });
    chrome.action.setBadgeBackgroundColor({ color: '#3b82f6', tabId: tabId });

    try {
        // Try to find a draft matching the current URL
        const apiUrl = `${API_BASE}/drafts/by-url/${encodeURIComponent(url)}`;
        console.log('📡 Fetching draft from:', apiUrl);
        logToStorage('info', 'Fetching draft...');

        const response = await fetch(apiUrl);

        if (!response.ok) {
            // No draft found for this URL
            console.log('❌ AutoApply: No draft found for URL', url, 'Status:', response.status);
            logToStorage('warn', `No draft found (Status: ${response.status})`);

            // Notify user via badge
            chrome.action.setBadgeText({ text: '!', tabId: tabId });
            chrome.action.setBadgeBackgroundColor({ color: '#ef4444', tabId: tabId });
            setTimeout(() => chrome.action.setBadgeText({ text: '', tabId: tabId }), 3000);
            return;
        }

        const draft = await response.json();
        console.log('✅ AutoApply: Found draft', draft.id, draft);
        logToStorage('success', `Found draft ${draft.id}`);

        if (!draft.form_state) {
            console.error('❌ Draft has no form_state');
            logToStorage('error', 'Draft has no form_state');
            chrome.action.setBadgeText({ text: '!', tabId: tabId });
            chrome.action.setBadgeBackgroundColor({ color: '#ef4444', tabId: tabId });
            setTimeout(() => chrome.action.setBadgeText({ text: '', tabId: tabId }), 3000);
            return;
        }

        // Send form spec to content script
        console.log('📤 Sending fillForm message to content script...');
        logToStorage('info', 'Sending fillForm message to content script');

        chrome.tabs.sendMessage(tabId, {
            action: 'fillForm',
            data: draft.form_state
        }, (result) => {
            if (chrome.runtime.lastError) {
                console.error('❌ AutoApply: Failed to send message', chrome.runtime.lastError.message);
                logToStorage('error', 'Failed to send message: ' + chrome.runtime.lastError.message);
                chrome.action.setBadgeText({ text: '!', tabId: tabId });
                chrome.action.setBadgeBackgroundColor({ color: '#ef4444', tabId: tabId });
            } else if (result?.success) {
                console.log('✅ AutoApply: Fill completed', result.filled, 'fields');
                logToStorage('success', `Fill completed: ${result.filled} fields`);
                chrome.action.setBadgeText({ text: '✓', tabId: tabId });
                chrome.action.setBadgeBackgroundColor({ color: '#10b981', tabId: tabId });
            } else {
                console.log('⚠️ AutoApply: Fill result', result);
                logToStorage('warn', 'Fill finished with issues', result);
                chrome.action.setBadgeText({ text: '?', tabId: tabId });
                chrome.action.setBadgeBackgroundColor({ color: '#f59e0b', tabId: tabId });
            }
            setTimeout(() => chrome.action.setBadgeText({ text: '', tabId: tabId }), 3000);
        });

    } catch (error) {
        console.error('❌ AutoApply: Error', error);
        logToStorage('error', 'Unexpected error', error.message);
        chrome.action.setBadgeText({ text: '!', tabId: tabId });
        chrome.action.setBadgeBackgroundColor({ color: '#ef4444', tabId: tabId });
        setTimeout(() => chrome.action.setBadgeText({ text: '', tabId: tabId }), 3000);
    }
}

// Handle messages from content script or other parts of extension

