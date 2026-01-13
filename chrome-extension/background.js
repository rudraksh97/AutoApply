// background.js - Handles data fetching and triggers form filling

const API_BASE = 'http://localhost:8000';

console.log('🚀 AutoApply background script loaded');

// Handle extension icon click - fetch draft for current URL and fill
chrome.action.onClicked.addListener(async (tab) => {
    console.log('🖱️ AutoApply: Extension clicked for tab', tab.url);
    
    // Show loading state
    chrome.action.setBadgeText({ text: '...', tabId: tab.id });
    chrome.action.setBadgeBackgroundColor({ color: '#3b82f6', tabId: tab.id });
    
    try {
        // Try to find a draft matching the current URL
        // The API uses path parameter: /drafts/by-url/{job_url}
        const apiUrl = `${API_BASE}/drafts/by-url/${encodeURIComponent(tab.url)}`;
        console.log('📡 Fetching draft from:', apiUrl);
        
        const response = await fetch(apiUrl);
        
        if (!response.ok) {
            // No draft found for this URL
            console.log('❌ AutoApply: No draft found for URL', tab.url, 'Status:', response.status);
            
            // Notify user via badge
            chrome.action.setBadgeText({ text: '!', tabId: tab.id });
            chrome.action.setBadgeBackgroundColor({ color: '#ef4444', tabId: tab.id });
            setTimeout(() => chrome.action.setBadgeText({ text: '', tabId: tab.id }), 3000);
            return;
        }
        
        const draft = await response.json();
        console.log('✅ AutoApply: Found draft', draft.id, draft);
        
        if (!draft.form_state) {
            console.error('❌ Draft has no form_state');
            chrome.action.setBadgeText({ text: '!', tabId: tab.id });
            chrome.action.setBadgeBackgroundColor({ color: '#ef4444', tabId: tab.id });
            setTimeout(() => chrome.action.setBadgeText({ text: '', tabId: tab.id }), 3000);
            return;
        }
        
        // Send form spec to content script
        console.log('📤 Sending fillForm message to content script...');
        chrome.tabs.sendMessage(tab.id, {
            action: 'fillForm',
            data: draft.form_state
        }, (result) => {
            if (chrome.runtime.lastError) {
                console.error('❌ AutoApply: Failed to send message', chrome.runtime.lastError.message);
                chrome.action.setBadgeText({ text: '!', tabId: tab.id });
                chrome.action.setBadgeBackgroundColor({ color: '#ef4444', tabId: tab.id });
            } else if (result?.success) {
                console.log('✅ AutoApply: Fill completed', result.filled, 'fields');
                chrome.action.setBadgeText({ text: '✓', tabId: tab.id });
                chrome.action.setBadgeBackgroundColor({ color: '#10b981', tabId: tab.id });
            } else {
                console.log('⚠️ AutoApply: Fill result', result);
                chrome.action.setBadgeText({ text: '?', tabId: tab.id });
                chrome.action.setBadgeBackgroundColor({ color: '#f59e0b', tabId: tab.id });
            }
            setTimeout(() => chrome.action.setBadgeText({ text: '', tabId: tab.id }), 3000);
        });
        
    } catch (error) {
        console.error('❌ AutoApply: Error', error);
        chrome.action.setBadgeText({ text: '!', tabId: tab.id });
        chrome.action.setBadgeBackgroundColor({ color: '#ef4444', tabId: tab.id });
        setTimeout(() => chrome.action.setBadgeText({ text: '', tabId: tab.id }), 3000);
    }
});

// Handle messages from content script or other parts of extension
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('📨 Background received message:', request.action);
    
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
                sendResponse({ success: false, error: error.message });
            });

        return true; // Will respond asynchronously
    }
});
