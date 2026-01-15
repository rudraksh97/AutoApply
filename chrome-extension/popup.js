/**
 * PopupManager handles the UI logic for the extension popup.
 */
class PopupManager {
    constructor() {
        this.elements = {
            fillBtn: document.getElementById('fill-btn'),
            clearLogsBtn: document.getElementById('clear-logs-btn'),
            logsView: document.getElementById('logs-view'),
            statusDisplay: document.getElementById('status-display')
        };

        this.init();
    }

    init() {
        this.attachListeners();
        this.loadLogs();
        this.listenForStorageUpdates();
    }

    attachListeners() {
        this.elements.fillBtn.addEventListener('click', () => this.handleFillClick());
        this.elements.clearLogsBtn.addEventListener('click', () => this.clearLogs());
    }

    listenForStorageUpdates() {
        chrome.storage.onChanged.addListener((changes, area) => {
            if (area === 'local' && changes.logs) {
                this.renderLogs(changes.logs.newValue || []);
            }
        });
    }

    async handleFillClick() {
        try {
            const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

            if (!tab) {
                this.showStatus('No active tab found', 'error');
                return;
            }

            // Send message to background to trigger auto-apply
            await chrome.runtime.sendMessage({
                action: 'triggerAutoApply',
                tabId: tab.id,
                url: tab.url
            });

            this.showStatus('Started filling process...', 'success');
        } catch (error) {
            this.showStatus(`Error: ${error.message}`, 'error');
            console.error(error);
        }
    }

    async loadLogs() {
        try {
            const result = await chrome.storage.local.get('logs');
            this.renderLogs(result.logs || []);
        } catch (error) {
            console.error('Failed to load logs', error);
        }
    }

    async clearLogs() {
        await chrome.storage.local.set({ logs: [] });
        this.renderLogs([]);
    }

    renderLogs(logs) {
        // Clear current view
        while (this.elements.logsView.firstChild) {
            this.elements.logsView.removeChild(this.elements.logsView.firstChild);
        }

        if (!logs || logs.length === 0) {
            this.addLogEntry(null, 'info', 'No logs recorded.');
            return;
        }

        logs.forEach(log => {
            this.addLogEntry(log.timestamp, log.level, log.message);
        });

        // Scroll to bottom
        this.elements.logsView.scrollTop = this.elements.logsView.scrollHeight;
    }

    addLogEntry(timestamp, level, message) {
        const entry = document.createElement('div');
        entry.className = 'log-entry';

        if (timestamp) {
            const timeSpan = document.createElement('span');
            timeSpan.className = 'log-time';
            const date = new Date(timestamp);
            timeSpan.textContent = date.toLocaleTimeString('en-US', { hour12: false });
            entry.appendChild(timeSpan);
        }

        const msgSpan = document.createElement('span');
        msgSpan.className = `log-level-${level || 'info'}`;
        msgSpan.textContent = ` ${message}`;

        entry.appendChild(msgSpan);
        this.elements.logsView.appendChild(entry);
    }

    showStatus(message, type) {
        const { statusDisplay } = this.elements;
        statusDisplay.textContent = message;
        statusDisplay.className = `status-area status-${type}`;
        statusDisplay.style.display = 'block';

        // Auto-hide after 3 seconds
        setTimeout(() => {
            statusDisplay.style.display = 'none';
        }, 3000);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new PopupManager();
});
