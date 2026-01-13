/**
 * AutoApply Content Script - Production-Grade Form Filler
 * 
 * A deterministic executor of declarative JSON form specifications.
 * Follows the principles of Simplify and JobRight for reliability and safety.
 * 
 * CORE PRINCIPLES:
 * 1. JSON is the source of truth for element identification
 * 2. XPath resolution with validation, not discovery
 * 3. Conservative filling - skip when uncertain
 * 4. Idempotent - safe to run multiple times
 * 5. Never submits forms under any circumstances
 */

// ============================================================================
// CONFIGURATION
// ============================================================================

const CONFIG = {
    API_BASE: "http://localhost:8000",
    
    // Timing (ms)
    FIELD_FILL_DELAY: 600,          // Delay between fields for visual feedback
    TYPING_DELAY_PER_CHAR: 25,      // Base typing speed
    TYPING_CHUNK_THRESHOLD: 50,     // Characters before chunking
    DROPDOWN_OPEN_DELAY: 250,       // Wait for dropdown to open
    VALIDATION_TIMEOUT: 100,        // Time for validation checks
    
    // Validation thresholds
    MIN_LABEL_MATCH_RATIO: 0.6,     // Minimum similarity for label matching
    MAX_SECTION_DISTANCE: 5,        // Max DOM levels to find section context
    
    // Safety
    BLOCKED_BUTTON_PATTERNS: [
        /submit/i, /apply/i, /send/i, /next/i, /continue/i,
        /finish/i, /complete/i, /confirm/i, /save.*submit/i
    ]
};

// ============================================================================
// LOGGING & REPORTING
// ============================================================================

class FillReport {
    constructor() {
        this.filled = [];
        this.skipped = [];
        this.mismatches = [];
        this.errors = [];
        this.fileUploads = [];
        this.startTime = Date.now();
    }
    
    recordFilled(field, element) {
        this.filled.push({
            xpath: field.xpath,
            label: field.label,
            fieldType: field.field_type,
            timestamp: Date.now()
        });
    }
    
    recordSkipped(field, reason) {
        this.skipped.push({
            xpath: field.xpath,
            label: field.label,
            reason,
            timestamp: Date.now()
        });
        console.warn(`⏭️ Skipped: ${field.label || field.xpath} - ${reason}`);
    }
    
    recordMismatch(field, expected, actual) {
        this.mismatches.push({
            xpath: field.xpath,
            label: field.label,
            expected,
            actual,
            timestamp: Date.now()
        });
        console.warn(`⚠️ Mismatch: ${field.label || field.xpath}`, { expected, actual });
    }
    
    recordError(field, error) {
        this.errors.push({
            xpath: field.xpath,
            label: field.label,
            error: error.message,
            timestamp: Date.now()
        });
        console.error(`❌ Error: ${field.label || field.xpath}`, error);
    }
    
    recordFileUpload(field) {
        this.fileUploads.push({
            xpath: field.xpath,
            label: field.label,
            timestamp: Date.now()
        });
    }
    
    getSummary() {
        return {
            filled: this.filled.length,
            skipped: this.skipped.length,
            mismatches: this.mismatches.length,
            errors: this.errors.length,
            fileUploads: this.fileUploads.length,
            duration: Date.now() - this.startTime
        };
    }
}

// ============================================================================
// UTILITIES
// ============================================================================

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function normalizeText(text) {
    return (text || '').toLowerCase().trim().replace(/\s+/g, ' ');
}

function calculateSimilarity(str1, str2) {
    const s1 = normalizeText(str1);
    const s2 = normalizeText(str2);
    
    if (s1 === s2) return 1;
    if (!s1 || !s2) return 0;
    
    // Check for containment
    if (s1.includes(s2) || s2.includes(s1)) {
        return Math.min(s1.length, s2.length) / Math.max(s1.length, s2.length);
    }
    
    // Word overlap
    const words1 = new Set(s1.split(' '));
    const words2 = new Set(s2.split(' '));
    const intersection = [...words1].filter(w => words2.has(w));
    
    return intersection.length / Math.max(words1.size, words2.size);
}

// ============================================================================
// XPATH RESOLUTION
// ============================================================================

class XPathResolver {
    /**
     * Resolve an XPath to a DOM element
     * @param {string} xpath - The XPath expression
     * @returns {Element|null} - The resolved element or null
     */
    static resolve(xpath) {
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
            console.error(`XPath resolution error for "${xpath}":`, e);
            return null;
        }
    }
    
    /**
     * Resolve multiple XPaths in priority order, returning first valid match
     * @param {string[]} xpaths - Array of XPath expressions in priority order
     * @returns {{element: Element|null, xpath: string|null}} - Result with matched xpath
     */
    static resolveWithFallback(xpaths) {
        if (!Array.isArray(xpaths)) {
            xpaths = [xpaths];
        }
        
        for (const xpath of xpaths) {
            if (!xpath) continue;
            const element = this.resolve(xpath);
            if (element) {
                return { element, xpath };
            }
        }
        
        return { element: null, xpath: null };
    }
}

// ============================================================================
// ELEMENT VALIDATION
// ============================================================================

class ElementValidator {
    /**
     * Validate that a resolved element matches the expected field specification
     * @param {Element} element - The DOM element
     * @param {Object} fieldSpec - The field specification from JSON
     * @returns {{valid: boolean, confidence: number, issues: string[]}}
     */
    static validate(element, fieldSpec) {
        const issues = [];
        let confidence = 1.0;
        
        if (!element) {
            return { valid: false, confidence: 0, issues: ['Element not found'] };
        }
        
        // Check element visibility
        if (!this.isVisible(element)) {
            issues.push('Element not visible');
            confidence -= 0.5;
        }
        
        // Check element is not disabled
        if (element.disabled) {
            issues.push('Element is disabled');
            return { valid: false, confidence: 0, issues };
        }
        
        // Validate tag name
        const tagValidation = this.validateTagName(element, fieldSpec);
        if (!tagValidation.valid) {
            issues.push(tagValidation.issue);
            confidence -= 0.3;
        }
        
        // Validate input type
        const typeValidation = this.validateInputType(element, fieldSpec);
        if (!typeValidation.valid) {
            issues.push(typeValidation.issue);
            confidence -= 0.3;
        }
        
        // Validate label match
        const labelValidation = this.validateLabel(element, fieldSpec);
        if (!labelValidation.valid) {
            issues.push(labelValidation.issue);
            confidence -= 0.2;
        }
        
        // Validate section context (if specified)
        if (fieldSpec.section) {
            const sectionValidation = this.validateSection(element, fieldSpec.section);
            if (!sectionValidation.valid) {
                issues.push(sectionValidation.issue);
                confidence -= 0.2;
            }
        }
        
        // Element is valid if confidence remains above threshold
        const valid = confidence >= 0.5 && issues.length < 3;
        
        return { valid, confidence: Math.max(0, confidence), issues };
    }
    
    static isVisible(element) {
        if (!element) return false;
        
        const style = window.getComputedStyle(element);
        if (style.display === 'none' || style.visibility === 'hidden') {
            return false;
        }
        
        const rect = element.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
    }
    
    static validateTagName(element, fieldSpec) {
        const tagName = element.tagName.toLowerCase();
        const fieldType = (fieldSpec.field_type || '').toLowerCase();
        
        const expectedTags = {
            'select': ['select'],
            'textarea': ['textarea'],
            'checkbox': ['input'],
            'radio': ['input'],
            'file': ['input'],
            'text': ['input', 'textarea'],
            'email': ['input'],
            'phone': ['input'],
            'tel': ['input'],
            'url': ['input'],
            'number': ['input'],
            'password': ['input']
        };
        
        const expected = expectedTags[fieldType] || ['input', 'textarea', 'select'];
        
        if (!expected.includes(tagName)) {
            return {
                valid: false,
                issue: `Expected tag ${expected.join('/')} but found ${tagName}`
            };
        }
        
        return { valid: true };
    }
    
    static validateInputType(element, fieldSpec) {
        const elType = (element.type || '').toLowerCase();
        const fieldType = (fieldSpec.field_type || '').toLowerCase();
        
        // Map field types to acceptable input types
        const typeMap = {
            'text': ['text', 'search', ''],
            'email': ['email', 'text'],
            'phone': ['tel', 'text', 'number'],
            'tel': ['tel', 'text'],
            'url': ['url', 'text'],
            'number': ['number', 'text'],
            'password': ['password'],
            'checkbox': ['checkbox'],
            'radio': ['radio'],
            'file': ['file']
        };
        
        const acceptable = typeMap[fieldType];
        if (acceptable && !acceptable.includes(elType)) {
            return {
                valid: false,
                issue: `Expected input type ${acceptable.join('/')} but found ${elType}`
            };
        }
        
        return { valid: true };
    }
    
    static validateLabel(element, fieldSpec) {
        if (!fieldSpec.label) {
            return { valid: true }; // No label to validate against
        }
        
        const actualLabel = this.extractElementLabel(element);
        const similarity = calculateSimilarity(actualLabel, fieldSpec.label);
        
        if (similarity < CONFIG.MIN_LABEL_MATCH_RATIO) {
            return {
                valid: false,
                issue: `Label mismatch: expected "${fieldSpec.label}", found "${actualLabel}"`
            };
        }
        
        return { valid: true };
    }
    
    static extractElementLabel(element) {
        // 1. Check for explicit label via 'for' attribute
        if (element.id) {
            const label = document.querySelector(`label[for="${CSS.escape(element.id)}"]`);
            if (label) return label.textContent?.trim() || '';
        }
        
        // 2. Check for wrapping label
        const parentLabel = element.closest('label');
        if (parentLabel) {
            return parentLabel.textContent?.trim() || '';
        }
        
        // 3. Check aria-label
        if (element.getAttribute('aria-label')) {
            return element.getAttribute('aria-label');
        }
        
        // 4. Check aria-labelledby
        const labelledBy = element.getAttribute('aria-labelledby');
        if (labelledBy) {
            const labelEl = document.getElementById(labelledBy);
            if (labelEl) return labelEl.textContent?.trim() || '';
        }
        
        // 5. Check placeholder
        if (element.placeholder) {
            return element.placeholder;
        }
        
        // 6. Check name attribute (cleaned up)
        if (element.name) {
            return element.name.replace(/[_-]/g, ' ');
        }
        
        return '';
    }
    
    static validateSection(element, expectedSection) {
        // Look for section indicators in ancestor elements
        const sectionKeywords = {
            'personal': ['personal', 'contact', 'about', 'basic'],
            'experience': ['experience', 'work', 'employment', 'job', 'career'],
            'education': ['education', 'school', 'university', 'degree', 'academic'],
            'skills': ['skills', 'expertise', 'competencies', 'abilities'],
            'documents': ['documents', 'resume', 'cv', 'upload', 'attachments'],
            'additional': ['additional', 'other', 'extra', 'supplemental']
        };
        
        const keywords = sectionKeywords[expectedSection.toLowerCase()] || [expectedSection.toLowerCase()];
        
        // Walk up the DOM tree looking for section context
        let current = element;
        let depth = 0;
        
        while (current && depth < CONFIG.MAX_SECTION_DISTANCE) {
            const text = (
                current.className +
                ' ' + (current.getAttribute('aria-label') || '') +
                ' ' + (current.querySelector('legend, h1, h2, h3, h4, h5, h6')?.textContent || '')
            ).toLowerCase();
            
            for (const keyword of keywords) {
                if (text.includes(keyword)) {
                    return { valid: true };
                }
            }
            
            current = current.parentElement;
            depth++;
        }
        
        // If no section found, don't fail - just note it
        return { valid: true }; // Soft validation - don't fail on section mismatch alone
    }
}

// ============================================================================
// EVENT DISPATCHING (React/Vue/Angular compatible)
// ============================================================================

class EventDispatcher {
    /**
     * Get native value setter for React compatibility
     */
    static getNativeSetter(element) {
        const tagName = element.tagName.toLowerCase();
        
        if (tagName === 'input') {
            return Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
        }
        if (tagName === 'textarea') {
            return Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value')?.set;
        }
        if (tagName === 'select') {
            return Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value')?.set;
        }
        
        return null;
    }
    
    /**
     * Set value using native setter for React compatibility
     */
    static setNativeValue(element, value) {
        const setter = this.getNativeSetter(element);
        if (setter) {
            setter.call(element, value);
        } else {
            element.value = value;
        }
    }
    
    /**
     * Dispatch all necessary events for framework compatibility
     */
    static dispatchInputEvents(element, eventSequence = ['focus', 'input', 'change', 'blur']) {
        for (const eventType of eventSequence) {
            const eventInit = { bubbles: true, cancelable: true };
            
            let event;
            if (eventType === 'input') {
                event = new InputEvent(eventType, { ...eventInit, inputType: 'insertText' });
            } else if (eventType === 'change') {
                event = new Event(eventType, eventInit);
            } else if (eventType === 'focus' || eventType === 'blur') {
                event = new FocusEvent(eventType, eventInit);
            } else {
                event = new Event(eventType, eventInit);
            }
            
            element.dispatchEvent(event);
        }
    }
    
    /**
     * Dispatch click event
     */
    static dispatchClick(element) {
        const event = new MouseEvent('click', {
            bubbles: true,
            cancelable: true,
            view: window
        });
        element.dispatchEvent(event);
    }
}

// ============================================================================
// IDEMPOTENCY CHECKER
// ============================================================================

class IdempotencyChecker {
    /**
     * Check if field already contains the intended value
     * @param {Element} element - The DOM element
     * @param {*} intendedValue - The value we want to set
     * @param {string} fieldType - The field type
     * @returns {boolean} - True if field already has correct value
     */
    static hasCorrectValue(element, intendedValue, fieldType) {
        if (!element || intendedValue === undefined || intendedValue === null) {
            return false;
        }
        
        const type = (fieldType || '').toLowerCase();
        
        switch (type) {
            case 'checkbox':
                const shouldBeChecked = ['true', '1', 'yes', 'on'].includes(
                    String(intendedValue).toLowerCase()
                );
                return element.checked === shouldBeChecked;
                
            case 'radio':
                // For radio, check if the intended option is selected
                return element.checked && (
                    element.value?.toLowerCase() === String(intendedValue).toLowerCase() ||
                    this.getRadioLabel(element).toLowerCase().includes(String(intendedValue).toLowerCase())
                );
                
            case 'select':
                const selectedText = element.options?.[element.selectedIndex]?.text || '';
                return (
                    element.value?.toLowerCase() === String(intendedValue).toLowerCase() ||
                    selectedText.toLowerCase().includes(String(intendedValue).toLowerCase())
                );
                
            case 'file':
                // Can't check file inputs - always return false to show upload prompt
                return false;
                
            default:
                // Text-like fields
                const currentValue = normalizeText(element.value);
                const intended = normalizeText(String(intendedValue));
                return currentValue === intended || currentValue.includes(intended);
        }
    }
    
    static getRadioLabel(radio) {
        if (radio.id) {
            const label = document.querySelector(`label[for="${CSS.escape(radio.id)}"]`);
            if (label) return label.textContent?.trim() || '';
        }
        const parentLabel = radio.closest('label');
        if (parentLabel) return parentLabel.textContent?.trim() || '';
        return radio.nextSibling?.textContent?.trim() || '';
    }
}

// ============================================================================
// FIELD FILLERS (Strategy Pattern)
// ============================================================================

class FieldFillers {
    /**
     * Fill a text-like input field with typing animation
     */
    static async fillText(element, value, report, field) {
        element.focus();
        EventDispatcher.dispatchInputEvents(element, ['focus']);
        await sleep(50);
        
        // Clear existing value
        EventDispatcher.setNativeValue(element, '');
        EventDispatcher.dispatchInputEvents(element, ['input']);
        
        // Type with animation
        const text = String(value);
        const chunkSize = text.length > 200 ? 10 : text.length > 50 ? 3 : 1;
        const delayMs = text.length > 200 ? 15 : text.length > 50 ? 20 : CONFIG.TYPING_DELAY_PER_CHAR;
        
        for (let i = 0; i <= text.length; i += chunkSize) {
            const partial = text.substring(0, Math.min(i + chunkSize, text.length));
            EventDispatcher.setNativeValue(element, partial);
            EventDispatcher.dispatchInputEvents(element, ['input']);
            
            if (i + chunkSize < text.length) {
                await sleep(delayMs);
            }
        }
        
        // Ensure final value
        EventDispatcher.setNativeValue(element, text);
        EventDispatcher.dispatchInputEvents(element, ['input', 'change', 'blur']);
        element.blur();
        
        return true;
    }
    
    /**
     * Fill a native <select> element
     */
    static async fillSelect(element, value, report, field) {
        const normalizedValue = normalizeText(value);
        const options = Array.from(element.options);
        
        // Find best matching option
        let bestMatch = null;
        let bestScore = 0;
        
        for (const option of options) {
            const optText = normalizeText(option.text);
            const optValue = normalizeText(option.value);
            
            // Exact matches
            if (optText === normalizedValue || optValue === normalizedValue) {
                bestMatch = option;
                break;
            }
            
            // Partial matches
            const textScore = calculateSimilarity(optText, normalizedValue);
            const valueScore = calculateSimilarity(optValue, normalizedValue);
            const score = Math.max(textScore, valueScore);
            
            if (score > bestScore && score > 0.5) {
                bestScore = score;
                bestMatch = option;
            }
        }
        
        if (!bestMatch) {
            report.recordMismatch(field, value, `No matching option found. Available: ${options.map(o => o.text).join(', ')}`);
            return false;
        }
        
        element.focus();
        EventDispatcher.setNativeValue(element, bestMatch.value);
        EventDispatcher.dispatchInputEvents(element, ['input', 'change', 'blur']);
        element.blur();
        
        return true;
    }
    
    /**
     * Fill a custom dropdown component (React Select, Material UI, etc.)
     */
    static async fillCustomDropdown(element, value, report, field) {
        // Click to open
        EventDispatcher.dispatchClick(element);
        await sleep(CONFIG.DROPDOWN_OPEN_DELAY);
        
        // Look for options
        const optionSelectors = [
            '[role="option"]',
            '[role="menuitem"]',
            '[class*="option"]:not([class*="options"])',
            '[class*="Option"]:not([class*="Options"])',
            '[class*="MenuItem"]',
            '[class*="menu-item"]',
            'li[data-value]',
            'ul[role="listbox"] li'
        ];
        
        let options = [];
        for (const selector of optionSelectors) {
            options = Array.from(document.querySelectorAll(selector));
            if (options.length > 0) break;
        }
        
        if (options.length === 0) {
            // Try searchable dropdown
            const input = element.querySelector('input') || 
                         (element.tagName === 'INPUT' ? element : null);
            
            if (input) {
                input.focus();
                EventDispatcher.setNativeValue(input, value);
                EventDispatcher.dispatchInputEvents(input, ['input']);
                await sleep(300);
                
                // Look for filtered options
                for (const selector of optionSelectors) {
                    options = Array.from(document.querySelectorAll(selector));
                    if (options.length > 0) {
                        EventDispatcher.dispatchClick(options[0]);
                        await sleep(100);
                        return true;
                    }
                }
            }
            
            // Close dropdown
            document.body.click();
            report.recordMismatch(field, value, 'Could not find dropdown options');
            return false;
        }
        
        // Find matching option
        const normalizedValue = normalizeText(value);
        for (const option of options) {
            const optText = normalizeText(option.textContent);
            if (optText === normalizedValue || optText.includes(normalizedValue) || normalizedValue.includes(optText)) {
                EventDispatcher.dispatchClick(option);
                await sleep(100);
                return true;
            }
        }
        
        // Close dropdown
        document.body.click();
        report.recordMismatch(field, value, `No matching option. Available: ${options.slice(0, 5).map(o => o.textContent?.trim()).join(', ')}`);
        return false;
    }
    
    /**
     * Fill a checkbox
     */
    static async fillCheckbox(element, value, report, field) {
        const shouldCheck = ['true', '1', 'yes', 'on'].includes(String(value).toLowerCase());
        
        if (element.checked !== shouldCheck) {
            EventDispatcher.dispatchClick(element);
            await sleep(50);
        }
        
        return true;
    }
    
    /**
     * Fill a radio button group
     */
    static async fillRadio(element, value, report, field) {
        const name = element.name || element.getAttribute('name');
        let radioGroup = [];
        
        if (name) {
            radioGroup = Array.from(document.querySelectorAll(`input[type="radio"][name="${CSS.escape(name)}"]`));
        }
        
        if (radioGroup.length === 0) {
            const parent = element.closest('fieldset, [role="radiogroup"], [class*="radio"]');
            if (parent) {
                radioGroup = Array.from(parent.querySelectorAll('input[type="radio"]'));
            }
        }
        
        if (radioGroup.length === 0) {
            radioGroup = [element];
        }
        
        const normalizedValue = normalizeText(value);
        
        for (const radio of radioGroup) {
            const labelText = normalizeText(IdempotencyChecker.getRadioLabel(radio));
            const radioValue = normalizeText(radio.value);
            
            if (labelText.includes(normalizedValue) || normalizedValue.includes(labelText) ||
                radioValue === normalizedValue) {
                EventDispatcher.dispatchClick(radio);
                await sleep(50);
                return true;
            }
        }
        
        report.recordMismatch(field, value, `No matching radio option. Available: ${radioGroup.map(r => IdempotencyChecker.getRadioLabel(r)).join(', ')}`);
        return false;
    }
    
    /**
     * Handle file upload field (highlight for user)
     */
    static async handleFile(element, value, report, field) {
        // Validate accepted file types if specified
        const accept = element.accept || '';
        if (field.accepted_types && accept) {
            const acceptedTypes = accept.split(',').map(t => t.trim().toLowerCase());
            const specifiedTypes = field.accepted_types.map(t => t.toLowerCase());
            
            const hasValidType = specifiedTypes.some(t => 
                acceptedTypes.some(a => a.includes(t) || t.includes(a))
            );
            
            if (!hasValidType) {
                report.recordMismatch(field, field.accepted_types, `Accepted types: ${accept}`);
            }
        }
        
        // Check if file already uploaded (if possible)
        if (element.files && element.files.length > 0 && !field.allow_replacement) {
            report.recordSkipped(field, 'File already uploaded and replacement not allowed');
            return false;
        }
        
        // Highlight for user attention
        const parent = element.closest('div, label, [class*="upload"], [class*="file"]') || element;
        
        const originalStyles = {
            border: parent.style.border,
            background: parent.style.background,
            borderRadius: parent.style.borderRadius,
            position: parent.style.position
        };
        
        parent.style.border = '3px solid #f59e0b';
        parent.style.background = 'rgba(245, 158, 11, 0.1)';
        parent.style.borderRadius = '8px';
        parent.style.position = 'relative';
        
        // Add tooltip
        const tooltip = document.createElement('div');
        tooltip.id = `autoapply-file-tooltip-${Date.now()}`;
        tooltip.innerHTML = `
            <div style="
                position: absolute;
                top: -40px;
                left: 0;
                background: #f59e0b;
                color: white;
                padding: 8px 14px;
                border-radius: 6px;
                font-size: 13px;
                font-family: system-ui, -apple-system, sans-serif;
                font-weight: 500;
                white-space: nowrap;
                z-index: 999999;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            ">
                📎 Please upload: ${field.label || value || 'Document'}
            </div>
        `;
        parent.appendChild(tooltip);
        
        // Auto-cleanup after 15 seconds
        setTimeout(() => {
            Object.assign(parent.style, originalStyles);
            tooltip.remove();
        }, 15000);
        
        report.recordFileUpload(field);
        return true; // Return true as we've done what we can
    }
}

// ============================================================================
// SUBMISSION BLOCKER (Safety)
// ============================================================================

class SubmissionBlocker {
    static isSubmitElement(element) {
        if (!element) return false;
        
        const tagName = element.tagName.toLowerCase();
        const type = (element.type || '').toLowerCase();
        const text = normalizeText(element.textContent || element.value || '');
        const ariaLabel = normalizeText(element.getAttribute('aria-label') || '');
        
        // Check type
        if (type === 'submit') return true;
        
        // Check role
        if (element.getAttribute('role') === 'submit') return true;
        
        // Check text patterns
        const textToCheck = text + ' ' + ariaLabel;
        for (const pattern of CONFIG.BLOCKED_BUTTON_PATTERNS) {
            if (pattern.test(textToCheck)) return true;
        }
        
        return false;
    }
    
    static blockSubmission() {
        // Find and mark all submit-like elements
        const potentialSubmits = document.querySelectorAll(
            'button, input[type="submit"], [role="button"], a[class*="submit"], a[class*="apply"]'
        );
        
        for (const el of potentialSubmits) {
            if (this.isSubmitElement(el)) {
                console.log('🛑 AutoApply: Blocking submit element:', el);
                // Don't actually disable - just log for awareness
            }
        }
    }
}

// ============================================================================
// UI FEEDBACK
// ============================================================================

class UIFeedback {
    static toastElement = null;
    
    static showNotification(message, type = 'info') {
        if (!this.toastElement) {
            this.toastElement = document.createElement('div');
            this.toastElement.id = 'autoapply-toast';
            this.toastElement.style.cssText = `
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
                max-width: 400px;
            `;
            document.body.appendChild(this.toastElement);
        }
        
        const colors = {
            loading: { bg: '#3b82f6', text: '#fff' },
            success: { bg: '#10b981', text: '#fff' },
            error: { bg: '#ef4444', text: '#fff' },
            warning: { bg: '#f59e0b', text: '#fff' },
            info: { bg: '#1f2937', text: '#fff' }
        };
        
        const style = colors[type] || colors.info;
        this.toastElement.style.backgroundColor = style.bg;
        this.toastElement.style.color = style.text;
        this.toastElement.textContent = message;
        
        requestAnimationFrame(() => {
            this.toastElement.style.opacity = '1';
            this.toastElement.style.transform = 'translateY(0)';
        });
        
        if (type !== 'loading') {
            setTimeout(() => {
                this.toastElement.style.opacity = '0';
                this.toastElement.style.transform = 'translateY(-20px)';
            }, 4000);
        }
    }
    
    static highlightElement(element, color = '#3b82f6') {
        const original = {
            outline: element.style.outline,
            outlineOffset: element.style.outlineOffset,
            transition: element.style.transition
        };
        
        element.style.transition = 'outline 0.2s ease';
        element.style.outline = `3px solid ${color}`;
        element.style.outlineOffset = '2px';
        
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        return original;
    }
    
    static removeHighlight(element, original) {
        element.style.outline = original.outline;
        element.style.outlineOffset = original.outlineOffset;
        setTimeout(() => {
            element.style.transition = original.transition;
        }, 200);
    }
}

// ============================================================================
// MAIN FORM FILLER
// ============================================================================

class FormFiller {
    constructor() {
        this.report = new FillReport();
    }
    
    /**
     * Main entry point - fill form based on JSON specification
     * @param {Object} formSpec - The form specification from backend
     */
    async fill(formSpec) {
        if (!formSpec || !formSpec.fields || !Array.isArray(formSpec.fields)) {
            console.error('AutoApply: Invalid form specification');
            return this.report;
        }
        
        const fields = formSpec.fields.filter(f => !f.skipped && f.value !== null && f.value !== undefined);
        const totalFields = fields.length;
        
        console.log(`🚀 AutoApply: Starting fill for ${totalFields} fields`);
        UIFeedback.showNotification(`Starting form fill (${totalFields} fields)...`, 'loading');
        
        // Block any accidental submissions
        SubmissionBlocker.blockSubmission();
        
        let currentIndex = 0;
        
        for (const field of fields) {
            currentIndex++;
            
            try {
                await this.fillField(field, currentIndex, totalFields);
            } catch (error) {
                this.report.recordError(field, error);
            }
            
            // Delay between fields
            await sleep(CONFIG.FIELD_FILL_DELAY);
        }
        
        // Show completion summary
        const summary = this.report.getSummary();
        let message = `🎉 Done! Filled ${summary.filled}/${totalFields} fields.`;
        
        if (summary.skipped > 0) {
            message += ` Skipped: ${summary.skipped}.`;
        }
        if (summary.fileUploads > 0) {
            message += ` 📎 ${summary.fileUploads} file(s) need upload.`;
        }
        if (summary.mismatches > 0) {
            message += ` ⚠️ ${summary.mismatches} mismatches.`;
        }
        
        UIFeedback.showNotification(message, summary.errors.length > 0 ? 'warning' : 'success');
        
        console.log('📊 AutoApply Fill Report:', this.report);
        
        return this.report;
    }
    
    async fillField(field, currentIndex, totalFields) {
        // Update progress
        const label = field.label || 'field';
        const truncatedLabel = label.length > 30 ? label.substring(0, 30) + '...' : label;
        UIFeedback.showNotification(`Filling ${currentIndex}/${totalFields}: ${truncatedLabel}`, 'info');
        
        // Resolve element via XPath
        const xpaths = Array.isArray(field.xpaths) ? field.xpaths : [field.xpath];
        const { element, xpath: resolvedXpath } = XPathResolver.resolveWithFallback(xpaths);
        
        if (!element) {
            this.report.recordSkipped(field, 'Element not found via XPath');
            return;
        }
        
        // Validate element matches specification
        const validation = ElementValidator.validate(element, field);
        
        if (!validation.valid) {
            this.report.recordMismatch(field, 
                { label: field.label, type: field.field_type },
                { issues: validation.issues, confidence: validation.confidence }
            );
            this.report.recordSkipped(field, `Validation failed: ${validation.issues.join(', ')}`);
            return;
        }
        
        // Check idempotency - skip if already has correct value
        if (IdempotencyChecker.hasCorrectValue(element, field.value, field.field_type)) {
            this.report.recordSkipped(field, 'Already has correct value');
            console.log(`⏭️ Skipped (already filled): ${field.label || field.xpath}`);
            return;
        }
        
        // Check if free-text field is marked as unsafe (opt-in safety)
        // Only skip if explicitly marked as unsafe_to_generate: true
        if (field.field_type === 'textarea' && field.unsafe_to_generate === true) {
            this.report.recordSkipped(field, 'Free-text field marked as unsafe to generate');
            return;
        }
        
        // Highlight element
        const originalStyles = UIFeedback.highlightElement(element);
        await sleep(200);
        
        // Fill based on field type
        let filled = false;
        const fieldType = (field.field_type || 'text').toLowerCase();
        const tagName = element.tagName.toLowerCase();
        
        try {
            switch (fieldType) {
                case 'checkbox':
                    filled = await FieldFillers.fillCheckbox(element, field.value, this.report, field);
                    break;
                    
                case 'radio':
                    filled = await FieldFillers.fillRadio(element, field.value, this.report, field);
                    break;
                    
                case 'select':
                    if (tagName === 'select') {
                        filled = await FieldFillers.fillSelect(element, field.value, this.report, field);
                    } else {
                        filled = await FieldFillers.fillCustomDropdown(element, field.value, this.report, field);
                    }
                    break;
                    
                case 'file':
                    filled = await FieldFillers.handleFile(element, field.value, this.report, field);
                    break;
                    
                default:
                    // Text-like fields
                    if (tagName === 'select') {
                        filled = await FieldFillers.fillSelect(element, field.value, this.report, field);
                    } else {
                        filled = await FieldFillers.fillText(element, field.value, this.report, field);
                    }
            }
            
            if (filled) {
                this.report.recordFilled(field, element);
                element.style.outline = '3px solid #10b981'; // Green success
                await sleep(300);
            } else {
                element.style.outline = '3px solid #ef4444'; // Red failure
                await sleep(300);
            }
        } finally {
            UIFeedback.removeHighlight(element, originalStyles);
        }
    }
}

// ============================================================================
// EXTENSION INTEGRATION
// ============================================================================

// Expose extension presence
window.__AUTOAPPLY_EXTENSION__ = true;
document.dispatchEvent(new CustomEvent('autoapply-extension-ready'));

// Listen for ping requests
window.addEventListener('message', (event) => {
    if (event.source !== window) return;
    if (event.data?.type === 'AUTOAPPLY_PING') {
        window.postMessage({ type: 'AUTOAPPLY_PONG', version: '2.0' }, '*');
    }
});

// Check for draft ID in URL hash
function checkAndFill() {
    const hash = window.location.hash;
    if (!hash || !hash.startsWith('#autoapply_id=')) return;
    
    const draftId = hash.replace('#autoapply_id=', '');
    console.log('🚀 AutoApply: Detected Draft ID:', draftId);
    
    // Clean URL
    history.replaceState(null, null, ' ');
    
    UIFeedback.showNotification('Fetching draft data...', 'loading');
    
    // Fetch draft via background script
    chrome.runtime.sendMessage({
        action: 'fetchDraftData',
        draftId: draftId
    }, async (response) => {
        if (!response?.success) {
            console.error('AutoApply Error:', response?.error);
            UIFeedback.showNotification('Failed to load draft data. Is backend running?', 'error');
            return;
        }
        
        const draft = response.data;
        console.log('✅ AutoApply: Data received', draft);
        
        if (!draft.form_state?.fields) {
            UIFeedback.showNotification('No form fields in draft', 'warning');
            return;
        }
        
        // Wait for dynamic forms to render
        await sleep(1000);
        
        // Create filler and execute
        const filler = new FormFiller();
        await filler.fill(draft.form_state);
    });
}

// Run on load and hash changes
checkAndFill();
window.addEventListener('hashchange', checkAndFill);
