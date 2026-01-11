// background.js - Handles data fetching to bypass CORS/CSP

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'fetchDraftData') {
        const draftId = request.draftId;
        const apiUrl = `http://localhost:8000/drafts/${draftId}`;

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
