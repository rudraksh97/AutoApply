// content.js - Injected into job pages to auto-fill forms

const API_BASE = "http://localhost:8000";

// Check if this page was opened with an AutoApply draft ID
function checkAndFill() {
    const hash = window.location.hash;
    if (hash && hash.startsWith('#autoapply_id=')) {
        const draftId = hash.replace('#autoapply_id=', '');
        console.log('🚀 AutoApply: Detected Draft ID:', draftId);

        // Remove hash to clean URL
        history.replaceState(null, null, ' ');

        // Notify user
        showNotification("Fetching draft data...", "loading");

        // Ask background script to fetch data (bypasses CORS/CSP)
        chrome.runtime.sendMessage({
            action: 'fetchDraftData',
            draftId: draftId
        }, (response) => {
            if (response && response.success) {
                const draft = response.data;
                console.log('✅ AutoApply: Data received', draft);

                if (draft.form_state && draft.form_state.fields) {
                    showNotification(`Filling ${draft.form_state.fields.length} fields...`, "info");

                    // Wait a moment for dynamic forms to render
                    setTimeout(() => {
                        const filledCount = fillForm(draft.form_state.fields);

                        if (filledCount > 0) {
                            showNotification(`✅ Success! Filled ${filledCount} fields.`, "success");
                        } else {
                            showNotification(`⚠️ Loaded data but found no matching fields.`, "warning");
                        }
                    }, 1000);
                }
            } else {
                console.error('AutoApply Error:', response.error);
                showNotification("Failed to load draft data. Is backend running?", "error");
            }
        });
    }
}

// Visual notification helper
function showNotification(message, type) {
    let el = document.getElementById('autoapply-toast');
    if (!el) {
        el = document.createElement('div');
        el.id = 'autoapply-toast';
        el.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 8px;
            z-index: 999999;
            font-family: system-ui, -apple-system, sans-serif;
            font-size: 14px;
            font-weight: 500;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            transition: all 0.3s ease;
            opacity: 0;
            transform: translateY(-20px);
        `;
        document.body.appendChild(el);
    }

    // Colors
    const colors = {
        loading: { bg: '#3b82f6', text: '#fff' },
        success: { bg: '#10b981', text: '#fff' },
        error: { bg: '#ef4444', text: '#fff' },
        warning: { bg: '#f59e0b', text: '#fff' },
        info: { bg: '#1f2937', text: '#fff' }
    };

    const style = colors[type] || colors.info;
    el.style.backgroundColor = style.bg;
    el.style.color = style.text;
    el.innerText = message;

    // Animate in
    requestAnimationFrame(() => {
        el.style.opacity = '1';
        el.style.transform = 'translateY(0)';
    });

    // Auto dismiss
    if (type !== 'loading') {
        setTimeout(() => {
            el.style.opacity = '0';
            el.style.transform = 'translateY(-20px)';
        }, 4000);
    }
}

// Core form filling logic (ported from backend)
function fillForm(fields) {
    let filledCount = 0;

    fields.forEach(field => {
        if (!field.value) return;

        const selectors = [
            `#${CSS.escape(field.field_id)}`,
            `[name="${CSS.escape(field.field_id)}"]`,
            `[id="${CSS.escape(field.field_id)}"]`,
            `[data-field="${CSS.escape(field.field_id)}"]`,
            // Fuzzy match for common labels if exact ID fails
            `[aria-label*="${CSS.escape(field.label || '')}"]`
        ];

        let found = false;
        for (const selector of selectors) {
            try {
                if (!selector || selector.includes('""')) continue; // Skip invalid

                const el = document.querySelector(selector);
                if (el) {
                    // Handle different input types
                    if (el.type === 'checkbox') {
                        el.checked = field.value.toLowerCase() === 'true' || field.value === '1';
                    } else if (el.type === 'radio') {
                        // Radio needs special handling - we likely found one of the options
                        // We need to find the specific radio button with this value
                        const radiogroup = document.querySelectorAll(`[name="${el.name}"]`);
                        radiogroup.forEach(radio => {
                            if (radio.value === field.value || radio.nextSibling?.textContent?.includes(field.value)) {
                                radio.checked = true;
                                found = true;
                            }
                        });
                        if (found) el.dispatchEvent(new Event('change', { bubbles: true }));
                    } else {
                        // Text, email, textarea, select
                        el.focus();
                        el.value = field.value;
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                        el.blur();
                    }

                    found = true;
                    console.log(`✅ Filled ${field.field_id}`);
                    break;
                }
            } catch (e) {
                // Ignore querySelector errors
            }
        }

        if (found) filledCount++;
    });

    return filledCount;
}

// Run verification on load
checkAndFill();

// Listen for hash changes (for SPAs)
window.addEventListener('hashchange', checkAndFill);
