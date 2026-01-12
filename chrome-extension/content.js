// content.js - Injected into job pages to auto-fill forms

const API_BASE = "http://localhost:8000";

// Expose extension presence for detection by frontend
window.__AUTOAPPLY_EXTENSION__ = true;
document.dispatchEvent(new CustomEvent('autoapply-extension-ready'));

// Listen for ping requests from the page
window.addEventListener('message', (event) => {
    if (event.source !== window) return;
    if (event.data && event.data.type === 'AUTOAPPLY_PING') {
        window.postMessage({ type: 'AUTOAPPLY_PONG', version: '1.0' }, '*');
    }
});

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
                    // Separate fillable fields from skipped fields
                    const fillableFields = draft.form_state.fields.filter(f => !f.skipped && f.value);
                    const skippedFields = draft.form_state.fields.filter(f => f.skipped);
                    
                    showNotification(`Filling ${fillableFields.length} fields...`, "info");

                    // Wait a moment for dynamic forms to render
                    setTimeout(() => {
                        const filledCount = fillForm(fillableFields);

                        if (filledCount > 0) {
                            let msg = `✅ Filled ${filledCount} fields.`;
                            if (skippedFields.length > 0) {
                                msg += ` ${skippedFields.length} need your input.`;
                            }
                            showNotification(msg, "success");
                            
                            // Log skipped fields for debugging
                            if (skippedFields.length > 0) {
                                console.log('⚠️ AutoApply: Fields needing user input:', 
                                    skippedFields.map(f => ({ label: f.label, reason: f.skip_reason }))
                                );
                            }
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

// Core form filling logic (aligned with backend deterministic engine)
function fillForm(fields) {
    let filledCount = 0;

    fields.forEach(field => {
        // Skip fields without values (should already be filtered, but defensive)
        if (!field.value) return;

        let el = null;
        
        // Primary: Use XPath selector (new approach)
        if (field.xpath) {
            el = getElementByXPath(field.xpath);
            if (el) {
                console.log(`🎯 Found via XPath: ${field.xpath}`);
            }
        }
        
        // Fallback: Try CSS selectors if xpath fails (backwards compatibility)
        if (!el && field.field_id) {
            const selectors = [
                `#${CSS.escape(field.field_id)}`,
                `[name="${CSS.escape(field.field_id)}"]`,
                `[id="${CSS.escape(field.field_id)}"]`
            ];
            
            for (const selector of selectors) {
                try {
                    el = document.querySelector(selector);
                    if (el) {
                        console.log(`🎯 Found via CSS fallback: ${selector}`);
                        break;
                    }
                } catch (e) {}
            }
        }
        
        // Last resort: Fuzzy match using label
        if (!el && field.label) {
            const fuzzySelectors = [
                `[aria-label*="${CSS.escape(field.label)}"]`,
                `[placeholder*="${CSS.escape(field.label)}"]`
            ];
            
            for (const selector of fuzzySelectors) {
                try {
                    el = document.querySelector(selector);
                    if (el) {
                        console.log(`🎯 Found via label fuzzy: ${selector}`);
                        break;
                    }
                } catch (e) {}
            }
        }

        if (el) {
            const filled = fillElement(el, field);
            if (filled) {
                console.log(`✅ Filled: ${field.label || field.xpath} (${field.field_type})`);
                filledCount++;
            }
        } else {
            console.warn(`⚠️ Element not found: ${field.xpath || field.label}`);
        }
    });

    return filledCount;
}

// Helper: Get element by XPath
function getElementByXPath(xpath) {
    try {
        const result = document.evaluate(
            xpath,
            document,
            null,
            XPathResult.FIRST_ORDERED_NODE_TYPE,
            null
        );
        return result.singleNodeValue;
    } catch (e) {
        console.error(`XPath error for "${xpath}":`, e);
        return null;
    }
}

// Fill a single element based on its type
function fillElement(el, field) {
    const elType = el.type || el.tagName.toLowerCase();
    
    try {
        switch (elType) {
            case 'checkbox':
                const shouldCheck = ['true', '1', 'yes'].includes(String(field.value).toLowerCase());
                if (el.checked !== shouldCheck) {
                    el.checked = shouldCheck;
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                }
                return true;
                
            case 'radio':
                // Find the specific radio button in the group
                const radiogroup = document.querySelectorAll(`[name="${el.name}"]`);
                let radioFound = false;
                radiogroup.forEach(radio => {
                    const radioLabel = radio.nextSibling?.textContent?.trim() || 
                                       radio.parentElement?.textContent?.trim() || '';
                    if (radio.value === field.value || 
                        radioLabel.toLowerCase().includes(field.value.toLowerCase())) {
                        radio.checked = true;
                        radio.dispatchEvent(new Event('change', { bubbles: true }));
                        radioFound = true;
                    }
                });
                return radioFound;
                
            case 'select':
            case 'select-one':
            case 'select-multiple':
                // Find matching option
                const options = Array.from(el.options);
                const match = options.find(opt => 
                    opt.value === field.value || 
                    opt.text.toLowerCase().includes(field.value.toLowerCase())
                );
                if (match) {
                    el.value = match.value;
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                    return true;
                }
                return false;
                
            case 'file':
                // Cannot programmatically set file inputs for security
                console.log(`⚠️ File input skipped: ${field.label || field.field_id}`);
                return false;
                
            default:
                // text, email, phone, tel, textarea, etc.
                el.focus();
                el.value = field.value;
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                el.blur();
                return true;
        }
    } catch (e) {
        console.error(`Error filling ${field.field_id}:`, e);
        return false;
    }
}

// Run verification on load
checkAndFill();

// Listen for hash changes (for SPAs)
window.addEventListener('hashchange', checkAndFill);
