/**
 * AutoApply Content Script - Production-Grade Form Filler
 * 
 * Architecture: Clean separation of concerns with single-responsibility classes
 * 
 * ┌─────────────────────────────────────────────────────────────────────────────┐
 * │  CONFIG          - All configurable constants                               │
 * │  Utils           - Pure utility functions                                   │
 * │  FillReport      - Logging and reporting                                    │
 * │  XPathResolver   - DOM element resolution                                   │
 * │  ElementValidator- Element validation against spec                          │
 * │  DropdownDetector- Runtime dropdown detection                               │
 * │  OptionMatcher   - Fuzzy option matching with scoring                       │
 * │  EventDispatcher - Framework-compatible event dispatching                   │
 * │  IdempotencyChecker - Check if fields already filled                        │
 * │  FieldFillers    - Strategy pattern for different field types               │
 * │  SubmissionBlocker - Safety: prevent accidental submissions                 │
 * │  UIFeedback      - User notifications and highlights                        │
 * │  FormFiller      - Main orchestrator                                        │
 * └─────────────────────────────────────────────────────────────────────────────┘
 */

// ============================================================================
// CONFIGURATION
// ============================================================================

const CONFIG = {
    API_BASE: "http://localhost:8000",

    // Timing (ms)
    TIMING: {
        FIELD_FILL_DELAY: 600,
        TYPING_DELAY_PER_CHAR: 25,
        DROPDOWN_OPEN_DELAY: 250,
        VALIDATION_TIMEOUT: 100,
        RETRY_DELAY: 200,
    },

    // Thresholds
    THRESHOLDS: {
        MIN_LABEL_MATCH: 0.6,
        GOOD_MATCH: 0.9,          // Stop searching if we find this
        MIN_ACCEPTABLE_MATCH: 0.5, // Minimum score to accept
        MAX_SECTION_DISTANCE: 5,
    },

    // Safety patterns
    BLOCKED_BUTTON_PATTERNS: [
        /submit/i, /apply/i, /send/i, /next/i, /continue/i,
        /finish/i, /complete/i, /confirm/i, /save.*submit/i
    ],

    // Dropdown option selectors (order matters - most specific first)
    DROPDOWN_OPTION_SELECTORS: [
        // ARIA-based (most reliable)
        '[role="option"]',
        '[role="menuitem"]',
        'ul[role="listbox"] li',

        // Greenhouse ATS specific
        '[class*="select__option"]',
        '[class*="css-"][id*="option"]',
        '[id*="react-select"][id*="option"]',
        'div[class*="menu"] div[class*="option"]',
        '[class*="indicatorContainer"]~div div',

        // React Select (used by Greenhouse)
        '[class*="SelectOption"]',
        'div[class*="MenuList"] > div',

        // Material UI
        '[class*="MuiMenuItem"]',
        '[class*="MuiOption"]',
        'div[role="presentation"] li',

        // Ant Design
        '.rc-virtual-list-holder-inner > div',

        // Headless UI
        '[class*="ComboboxOption"]',
        '[class*="Listbox-option"]',

        // Bootstrap
        '[class*="dropdown-item"]',

        // Generic patterns
        '[class*="option"]:not([class*="options"])',
        '[class*="Option"]:not([class*="Options"])',
        '[class*="MenuItem"]',
        '[class*="menu-item"]',
        '[class*="dropdown__option"]',
        '[class*="listbox-option"]',
        '[class*="autocomplete-option"]',
        '[data-testid*="option"]',
        'li[data-value]',
    ],

    // Dropdown indicator selectors (for detection)
    DROPDOWN_INDICATORS: [
        '[class*="indicator"]',
        '[class*="arrow"]',
        '[class*="caret"]',
        '[class*="chevron"]',
        'svg[class*="dropdown"]',
    ],

    // Class names that indicate a dropdown
    DROPDOWN_CLASS_PATTERNS: [
        'select', 'dropdown', 'combobox', 'listbox', 'autocomplete',
        'react-select', 'mui-select', 'ant-select', 'choices',
        'selectize', 'select2', 'chosen', 'typeahead'
    ],
};

// ============================================================================
// UTILITIES
// ============================================================================

const Utils = {
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    },

    normalizeText(text) {
        return (text || '').toLowerCase().trim().replace(/\s+/g, ' ');
    },

    /**
     * Calculate similarity between two strings (0-1)
     */
    calculateSimilarity(str1, str2) {
        const s1 = this.normalizeText(str1);
        const s2 = this.normalizeText(str2);

        if (s1 === s2) return 1;
        if (!s1 || !s2) return 0;

        // Containment check
        if (s1.includes(s2) || s2.includes(s1)) {
            return Math.min(s1.length, s2.length) / Math.max(s1.length, s2.length);
        }

        // Word overlap
        const words1 = new Set(s1.split(' '));
        const words2 = new Set(s2.split(' '));
        const intersection = [...words1].filter(w => words2.has(w));

        return intersection.length / Math.max(words1.size, words2.size);
    },
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
// XPATH RESOLUTION
// ============================================================================

class XPathResolver {
    /**
     * Resolve an XPath to a DOM element
     */
    static resolve(xpath) {
        if (!xpath) return null;

        // Sanitize XPath
        let safeXpath = xpath.trim();
        // Fix triple slashes /// -> //
        safeXpath = safeXpath.replace(/^\/{3,}/, '//');
        // Fix trailing slash
        if (safeXpath.length > 1 && safeXpath.endsWith('/')) {
            safeXpath = safeXpath.slice(0, -1);
        }

        // Support shadow DOM traversal using "/shadow-root/" markers (borrowed from Simplify bundle)
        const segments = safeXpath.split('/shadow-root/');
        try {
            let contextNodes = [document];
            for (let i = 0; i < segments.length; i++) {
                const seg = segments[i];
                const nextContexts = [];

                for (const ctx of contextNodes) {
                    const result = document.evaluate(
                        seg,
                        ctx,
                        null,
                        XPathResult.ORDERED_NODE_ITERATOR_TYPE,
                        null
                    );
                    let node = result.iterateNext();
                    while (node) {
                        if (i === segments.length - 1) {
                            return node;
                        }
                        if (node.shadowRoot) {
                            nextContexts.push(node.shadowRoot);
                        }
                        node = result.iterateNext();
                    }
                }

                contextNodes = nextContexts;
            }
        } catch (e) {
            console.error(`XPath resolution error for "${safeXpath}" (original: "${xpath}"):`, e);
        }

        return null;
    }

    /**
     * Resolve multiple XPaths in priority order
     */
    static resolveWithFallback(xpaths) {
        const xpathList = Array.isArray(xpaths) ? xpaths : [xpaths];

        for (const xpath of xpathList) {
            if (!xpath) continue;
            const element = this.resolve(xpath);
            if (element) return { element, xpath };
        }

        return { element: null, xpath: null };
    }

    /**
     * Resolve XPath with retry - waits for element to appear (for dynamically loaded forms)
     * @param {string|string[]} xpaths - XPath(s) to resolve
     * @param {number} maxWaitMs - Maximum time to wait in milliseconds (default: 3000)
     * @param {number} retryIntervalMs - Time between retries in milliseconds (default: 200)
     * @returns {Promise<{element: Element|null, xpath: string|null}>}
     */
    static async resolveWithWait(xpaths, maxWaitMs = 3000, retryIntervalMs = 200) {
        const xpathList = Array.isArray(xpaths) ? xpaths : [xpaths];
        const startTime = Date.now();

        while (Date.now() - startTime < maxWaitMs) {
            for (const xpath of xpathList) {
                if (!xpath) continue;
                const element = this.resolve(xpath);
                if (element) {
                    console.log(`✅ Element found after ${Date.now() - startTime}ms: ${xpath}`);
                    return { element, xpath };
                }
            }

            await Utils.sleep(retryIntervalMs);
        }

        console.warn(`⚠️ Element not found after ${maxWaitMs}ms: ${xpathList.join(', ')}`);
        return { element: null, xpath: null };
    }
}

// ============================================================================
// ELEMENT VALIDATION
// ============================================================================

class ElementValidator {
    static validate(element, fieldSpec) {
        const issues = [];
        let confidence = 1.0;

        if (!element) {
            return { valid: false, confidence: 0, issues: ['Element not found'] };
        }

        // Visibility check
        if (!this.isVisible(element)) {
            issues.push('Element not visible');
            confidence -= 0.5;
        }

        // Disabled check
        if (element.disabled) {
            return { valid: false, confidence: 0, issues: ['Element is disabled'] };
        }

        // Tag validation
        const tagValidation = this.validateTagName(element, fieldSpec);
        if (!tagValidation.valid) {
            issues.push(tagValidation.issue);
            confidence -= 0.3;
        }

        // Input type validation
        const typeValidation = this.validateInputType(element, fieldSpec);
        if (!typeValidation.valid) {
            issues.push(typeValidation.issue);
            confidence -= 0.3;
        }

        // Label validation (skip if XPath is specific enough - @id= or @name= are reliable)
        const hasSpecificXPath = fieldSpec.xpath && (
            fieldSpec.xpath.includes('@id=') || 
            fieldSpec.xpath.includes('@name=')
        );

        if (!hasSpecificXPath) {
            const labelValidation = this.validateLabel(element, fieldSpec);
            if (!labelValidation.valid) {
                issues.push(labelValidation.issue);
                confidence -= 0.2;
            }
        }

        // Section validation (soft)
        if (fieldSpec.section) {
            const sectionValidation = this.validateSection(element, fieldSpec.section);
            if (!sectionValidation.valid) {
                issues.push(sectionValidation.issue);
                confidence -= 0.2;
            }
        }

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
            'select': ['select', 'div', 'input', 'span', 'button'], // Custom dropdowns
            'textarea': ['textarea'],
            'checkbox': ['input', 'button', 'div', 'span', 'label'], // Custom checkboxes (Yes/No buttons)
            'radio': ['input', 'button', 'div', 'span', 'label'],    // Custom radio (Yes/No buttons)
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
            return { valid: false, issue: `Expected tag ${expected.join('/')} but found ${tagName}` };
        }

        return { valid: true };
    }

    static validateInputType(element, fieldSpec) {
        const tagName = element.tagName.toLowerCase();
        const elType = (element.type || '').toLowerCase();
        const fieldType = (fieldSpec.field_type || '').toLowerCase();

        // Skip input type validation for non-input elements (buttons, divs, etc.)
        // These are valid for custom radio/checkbox implementations
        if (tagName !== 'input') {
            return { valid: true };
        }

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
            return { valid: false, issue: `Expected input type ${acceptable.join('/')} but found ${elType}` };
        }

        return { valid: true };
    }

    static validateLabel(element, fieldSpec) {
        if (!fieldSpec.label) return { valid: true };

        const actualLabel = this.extractElementLabel(element);
        const similarity = Utils.calculateSimilarity(actualLabel, fieldSpec.label);

        if (similarity < CONFIG.THRESHOLDS.MIN_LABEL_MATCH) {
            return { valid: false, issue: `Label mismatch: expected "${fieldSpec.label}", found "${actualLabel}"` };
        }

        return { valid: true };
    }

    static extractElementLabel(element) {
        // 1. Explicit label via 'for'
        if (element.id) {
            const label = document.querySelector(`label[for="${CSS.escape(element.id)}"]`);
            if (label) return label.textContent?.trim() || '';
        }

        // 2. Wrapping label
        const parentLabel = element.closest('label');
        if (parentLabel) return parentLabel.textContent?.trim() || '';

        // 3. ARIA attributes
        if (element.getAttribute('aria-label')) {
            return element.getAttribute('aria-label');
        }

        const labelledBy = element.getAttribute('aria-labelledby');
        if (labelledBy) {
            const labelEl = document.getElementById(labelledBy);
            if (labelEl) return labelEl.textContent?.trim() || '';
        }

        // 4. For buttons/divs in Yes/No groups, look in parent container for label
        const tagName = element.tagName.toLowerCase();
        if (tagName === 'button' || tagName === 'div' || tagName === 'span') {
            // Look for field entry container (common in Ashby, Greenhouse, etc.)
            const fieldContainer = element.closest('[class*="field"], [class*="entry"], [class*="question"], [class*="form-group"]');
            if (fieldContainer) {
                // Find label or heading within the container
                const containerLabel = fieldContainer.querySelector('label, [class*="heading"], [class*="title"], [class*="question"]');
                if (containerLabel && containerLabel !== element && !containerLabel.contains(element)) {
                    return containerLabel.textContent?.trim() || '';
                }
            }
            
            // Also try looking at previous sibling label
            const parent = element.parentElement;
            if (parent) {
                const siblingLabel = parent.previousElementSibling;
                if (siblingLabel && siblingLabel.tagName.toLowerCase() === 'label') {
                    return siblingLabel.textContent?.trim() || '';
                }
                // Or label as sibling within same parent
                const parentParent = parent.parentElement;
                if (parentParent) {
                    const label = parentParent.querySelector(':scope > label');
                    if (label) return label.textContent?.trim() || '';
                }
            }
        }

        // 5. Placeholder
        if (element.placeholder) return element.placeholder;

        // 6. Name attribute
        if (element.name) return element.name.replace(/[_-]/g, ' ');

        return '';
    }

    static validateSection(element, expectedSection) {
        const sectionKeywords = {
            'personal': ['personal', 'contact', 'about', 'basic'],
            'experience': ['experience', 'work', 'employment', 'job', 'career'],
            'education': ['education', 'school', 'university', 'degree', 'academic'],
            'skills': ['skills', 'expertise', 'competencies', 'abilities'],
            'documents': ['documents', 'resume', 'cv', 'upload', 'attachments'],
            'additional': ['additional', 'other', 'extra', 'supplemental']
        };

        const keywords = sectionKeywords[expectedSection.toLowerCase()] || [expectedSection.toLowerCase()];

        let current = element;
        let depth = 0;

        while (current && depth < CONFIG.THRESHOLDS.MAX_SECTION_DISTANCE) {
            const text = (
                current.className +
                ' ' + (current.getAttribute('aria-label') || '') +
                ' ' + (current.querySelector('legend, h1, h2, h3, h4, h5, h6')?.textContent || '')
            ).toLowerCase();

            for (const keyword of keywords) {
                if (text.includes(keyword)) return { valid: true };
            }

            current = current.parentElement;
            depth++;
        }

        return { valid: true }; // Soft validation
    }
}

// ============================================================================
// DROPDOWN DETECTION
// ============================================================================

class DropdownDetector {
    /**
     * Detect if an element is a dropdown based on DOM attributes
     * CONSERVATIVE: Only return true if we're confident it's a dropdown
     */
    static isDropdown(element) {
        if (!element) return false;

        const tagName = element.tagName.toLowerCase();
        const inputType = (element.type || '').toLowerCase();

        // Native select is always a dropdown
        if (tagName === 'select') return true;

        // Text/email/tel/number inputs are NOT dropdowns (even if they have some dropdown-like attributes)
        if (tagName === 'input' && ['text', 'email', 'tel', 'number', 'password', 'search'].includes(inputType)) {
            // Exception: if it has combobox role, it IS a dropdown
            if (element.getAttribute('role') === 'combobox') {
                return true;
            }
            // Exception: if it has aria-haspopup=listbox, it's a searchable dropdown
            if (element.getAttribute('aria-haspopup') === 'listbox') {
                return true;
            }
            return false;
        }

        // For non-input elements, check ARIA (most reliable)
        if (this.hasStrongDropdownARIA(element)) return true;

        return false;
    }

    /**
     * Strong ARIA indicators that this IS a dropdown
     */
    static hasStrongDropdownARIA(element) {
        const role = element.getAttribute('role');
        const ariaHasPopup = element.getAttribute('aria-haspopup');

        // These are definitive dropdown indicators
        return (
            role === 'combobox' ||
            role === 'listbox' ||
            ariaHasPopup === 'listbox'
        );
    }
}

// ============================================================================
// OPTION MATCHING
// ============================================================================

class OptionMatcher {
    /**
     * Find the best matching option from a list
     * @returns {{ match: Element|null, score: number }}
     */
    static findBestMatch(options, targetValue, getOptionText) {
        const normalizedTarget = Utils.normalizeText(targetValue);
        let bestMatch = null;
        let bestScore = 0;

        for (const option of options) {
            const optText = Utils.normalizeText(getOptionText(option));
            const score = this.calculateMatchScore(optText, normalizedTarget);

            if (score > bestScore) {
                bestScore = score;
                bestMatch = option;
            }

            // Early exit ONLY for absolute perfect matches
            if (bestScore === 1.0) {
                break;
            }
        }

        return { match: bestMatch, score: bestScore };
    }

    /**
     * Calculate match score between option text and target value
     */
    static calculateMatchScore(optText, targetValue) {
        // Exact match (highest priority)
        if (optText === targetValue) return 1.0;

        // Exact word match (e.g. "Male" vs "Male/Female")
        const targetWords = targetValue.split(/[\s,/\-\(\)]+/);
        const optWords = optText.split(/[\s,/\-\(\)]+/);

        const hasExactWord = targetWords.some(tw => optWords.includes(tw)) ||
            optWords.some(ow => targetWords.includes(ow));

        // Substring matches - ONLY if it's not a partial word match of a common gender/state pattern
        // This prevents "male" matching "female"
        const isGenderConflict = (targetValue === 'male' && optText === 'female') ||
            (targetValue === 'female' && optText === 'male');

        if (!isGenderConflict) {
            if (optText.includes(targetValue)) {
                // If it's a whole word or at least 4 chars and not a conflict
                const isWholeWord = new RegExp(`\\b${targetValue}\\b`, 'i').test(optText);
                if (isWholeWord) {
                    return 0.9 + (0.05 * targetValue.length / optText.length);
                }
                return 0.75 + (0.1 * targetValue.length / optText.length);
            }
            if (targetValue.includes(optText)) {
                const isWholeWord = new RegExp(`\\b${optText}\\b`, 'i').test(targetValue);
                if (isWholeWord) {
                    return 0.85 + (0.05 * optText.length / targetValue.length);
                }
                return 0.7 + (0.1 * optText.length / targetValue.length);
            }
        }

        // Fuzzy similarity
        return Utils.calculateSimilarity(optText, targetValue);
    }

    /**
     * Check if match score is acceptable
     */
    static isAcceptableMatch(score) {
        return score >= CONFIG.THRESHOLDS.MIN_ACCEPTABLE_MATCH;
    }
}

// ============================================================================
// EVENT DISPATCHING (React/Vue/Angular compatible)
// ============================================================================

class EventDispatcher {
    static getNativeSetter(element) {
        const tagName = element.tagName.toLowerCase();

        const setterMap = {
            'input': HTMLInputElement.prototype,
            'textarea': HTMLTextAreaElement.prototype,
            'select': HTMLSelectElement.prototype,
        };

        const proto = setterMap[tagName];
        return proto ? Object.getOwnPropertyDescriptor(proto, 'value')?.set : null;
    }

    static setNativeValue(element, value) {
        const setter = this.getNativeSetter(element);
        if (setter) {
            setter.call(element, value);
        } else {
            element.value = value;
        }
        // Keep attribute in sync for components that read attributes instead of properties
        try {
            if (typeof value === 'string' || typeof value === 'number') {
                element.setAttribute('value', value);
            }
        } catch (e) {
            // non-fatal
        }
    }

    static dispatchInputEvents(element, events = ['focus', 'input', 'change', 'blur']) {
        for (const eventType of events) {
            const eventInit = { bubbles: true, cancelable: true };

            let event;
            switch (eventType) {
                case 'input':
                    event = new InputEvent(eventType, { ...eventInit, inputType: 'insertText' });
                    break;
                case 'focus':
                case 'blur':
                    event = new FocusEvent(eventType, eventInit);
                    break;
                default:
                    event = new Event(eventType, eventInit);
            }

            element.dispatchEvent(event);
        }
    }

    static dispatchClick(element) {
        element.dispatchEvent(new MouseEvent('click', {
            bubbles: true,
            cancelable: true,
            view: window
        }));
    }

    static dispatchMouseDown(element) {
        element.dispatchEvent(new MouseEvent('mousedown', {
            bubbles: true,
            cancelable: true,
            view: window
        }));
    }

    static dispatchMouseUp(element) {
        element.dispatchEvent(new MouseEvent('mouseup', {
            bubbles: true,
            cancelable: true,
            view: window
        }));
    }

    static dispatchPointerDown(element) {
        element.dispatchEvent(new PointerEvent('pointerdown', {
            bubbles: true,
            cancelable: true,
            view: window
        }));
    }

    static dispatchClickSequence(element) {
        this.dispatchPointerDown(element);
        this.dispatchMouseDown(element);
        this.dispatchMouseUp(element);
        this.dispatchClick(element);
    }

    // Text/textarea value entry with rich event sequence (mirrors Simplify bundle order)
    static dispatchTextSequence(element, value) {
        element.focus();
        element.dispatchEvent(new FocusEvent('focusin', { bubbles: true, cancelable: true }));
        this.dispatchClick(element);
        this.dispatchKeydown(element, 'Unidentified');
        this.dispatchKeydown(element, 'Unidentified'); // keypress substitute
        this.setNativeValue(element, value);
        element.dispatchEvent(new CustomEvent('textInput', { bubbles: true, cancelable: true }));
        element.dispatchEvent(new InputEvent('input', { bubbles: true, cancelable: true }));
        element.dispatchEvent(new KeyboardEvent('keyup', { bubbles: true, cancelable: true }));
        element.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
        element.blur();
        element.dispatchEvent(new FocusEvent('focusout', { bubbles: true, cancelable: true }));
    }

    // Select value entry with rich event sequence
    static dispatchSelectSequence(element, value) {
        element.focus();
        this.dispatchClick(element);
        this.setNativeValue(element, value);
        element.dispatchEvent(new CustomEvent('textInput', { bubbles: true, cancelable: true }));
        element.dispatchEvent(new InputEvent('input', { bubbles: true, cancelable: true }));
        element.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
        this.dispatchClick(element);
        element.blur();
    }

    // Checkbox / radio toggle with events
    static dispatchCheckableSequence(element, checked) {
        element.focus();
        this.dispatchClick(element);
        element.checked = Boolean(checked);
        element.dispatchEvent(new CustomEvent('textInput', { bubbles: true, cancelable: true }));
        element.dispatchEvent(new InputEvent('input', { bubbles: true, cancelable: true }));
        element.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
        element.blur();
    }

    static dispatchReactHandlers(element, handlers = []) {
        const key = Object.keys(element).find(k => /^(__reactProps|__reactEventHandlers)/.test(k));
        if (!key) return;
        const props = element[key];
        handlers.forEach(h => {
            const fn = props?.[h];
            if (typeof fn === 'function') {
                try {
                    const evt = new Event(h.toLowerCase().replace(/^on/, ''), { bubbles: true, cancelable: true });
                    Object.defineProperty(evt, 'target', { value: element, writable: false });
                    Object.defineProperty(evt, 'currentTarget', { value: element, writable: false });
                    // React expects 'nativeEvent' to be present on the synthetic event
                    evt.nativeEvent = evt;
                    fn(evt);
                } catch (e) { }
            }
        });
    }

    static dispatchKeydown(element, key) {
        element.dispatchEvent(new KeyboardEvent('keydown', {
            key,
            bubbles: true,
            cancelable: true
        }));
    }
}

// ============================================================================
// IDEMPOTENCY CHECKER
// ============================================================================

class IdempotencyChecker {
    static hasCorrectValue(element, intendedValue, fieldType) {
        if (!element || intendedValue === undefined || intendedValue === null) {
            return false;
        }

        const type = (fieldType || '').toLowerCase();
        const intended = String(intendedValue).toLowerCase();
        const tagName = element.tagName.toLowerCase();
        const inputType = (element.type || '').toLowerCase();

        // Check for custom binary choice elements first
        if (this._isCustomBinaryElement(element, type)) {
            return this._hasCorrectCustomBinaryValue(element, intended);
        }

        switch (type) {
            case 'checkbox':
                const shouldBeChecked = ['true', '1', 'yes', 'on'].includes(intended);
                // Native checkbox
                if (tagName === 'input' && inputType === 'checkbox') {
                    return element.checked === shouldBeChecked;
                }
                // Custom checkbox - check aria-checked
                return this._hasCorrectCustomBinaryValue(element, intended);

            case 'radio':
                // Native radio
                if (tagName === 'input' && inputType === 'radio') {
                    return element.checked && (
                        element.value?.toLowerCase() === intended ||
                        this.getRadioLabel(element).toLowerCase().includes(intended)
                    );
                }
                // Custom radio - check aria-checked or selected state
                return this._hasCorrectCustomBinaryValue(element, intended);

            case 'select':
                const selectedText = element.options?.[element.selectedIndex]?.text || '';
                return (
                    element.value?.toLowerCase() === intended ||
                    selectedText.toLowerCase().includes(intended)
                );

            case 'file':
                return false; // Always show file upload prompt

            default:
                const currentValue = Utils.normalizeText(element.value);
                const intendedNorm = Utils.normalizeText(intendedValue);
                return currentValue === intendedNorm || currentValue.includes(intendedNorm);
        }
    }

    /**
     * Check if element is a custom binary choice (not native input)
     */
    static _isCustomBinaryElement(element, fieldType) {
        const tagName = element.tagName.toLowerCase();
        const inputType = (element.type || '').toLowerCase();
        const role = element.getAttribute('role');

        // Native inputs are NOT custom
        if (tagName === 'input' && (inputType === 'radio' || inputType === 'checkbox')) {
            return false;
        }

        // Check for custom indicators
        return role === 'radiogroup' ||
               role === 'radio' ||
               role === 'checkbox' ||
               element.hasAttribute('aria-checked') ||
               element.closest('[role="radiogroup"]') !== null;
    }

    /**
     * Check if custom binary choice has correct value selected
     */
    static _hasCorrectCustomBinaryValue(element, intended) {
        // Check aria-checked on element itself
        if (element.getAttribute('aria-checked') === 'true') {
            const optText = Utils.normalizeText(element.textContent);
            if (optText.includes(intended) || intended.includes(optText)) {
                return true;
            }
        }

        // Check for selected option in container
        const container = element.closest('[role="radiogroup"]') || element.parentElement;
        if (container) {
            const selectedOption = container.querySelector('[aria-checked="true"], .selected, .active');
            if (selectedOption) {
                const selectedText = Utils.normalizeText(selectedOption.textContent);
                if (selectedText.includes(intended) || intended.includes(selectedText)) {
                    return true;
                }
            }
        }

        return false;
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
    // -------------------------------------------------------------------------
    // Text Fields
    // -------------------------------------------------------------------------

    static async fillText(element, value, report, field) {
        const text = String(value);
        EventDispatcher.dispatchTextSequence(element, text);
        // Dispatch fuller set of React events for robust validation handling
        EventDispatcher.dispatchReactHandlers(element, [
            'onFocus', 'onKeyDown', 'onKeyPress', 'onInput', 'onKeyUp', 'onChange', 'onBlur'
        ]);

        // If value did not persist, try jQuery fallback
        if (window.jQuery && Utils.normalizeText(element.value) !== Utils.normalizeText(text)) {
            try {
                const jq = window.jQuery(element);
                jq.trigger('focus').trigger('click').val(text).trigger('input').trigger('change').trigger('blur');
            } catch (e) { }
        }

        return true;
    }

    // -------------------------------------------------------------------------
    // Native Select
    // -------------------------------------------------------------------------

    static async fillSelect(element, value, report, field) {
        const domOptions = Array.from(element.options);

        const { match, score } = OptionMatcher.findBestMatch(
            domOptions,
            value,
            option => option.text
        );

        if (match && OptionMatcher.isAcceptableMatch(score)) {
            console.log(`✅ Selected: "${Utils.normalizeText(match.text)}" (${(score * 100).toFixed(1)}%)`);
            EventDispatcher.dispatchSelectSequence(element, match.value);
            EventDispatcher.dispatchReactHandlers(element, ['onInput', 'onChange', 'onClick']);
            return true;
        }

        report.recordMismatch(field, value, `No matching option. Available: ${domOptions.map(o => o.text).join(', ')}`);
        return false;
    }

    // -------------------------------------------------------------------------
    // Custom Dropdown (React Select, Material UI, etc.)
    // -------------------------------------------------------------------------

    static async fillCustomDropdown(element, value, report, field) {
        console.log(`🔽 Filling dropdown "${field.label}" with value "${value}"`);

        // Step 1: Open the dropdown
        await this._openDropdown(element);
        await Utils.sleep(500); // Extra wait for dropdown animation (Greenhouse needs this)

        // Step 2: Find options in DOM
        let options = await this._findDropdownOptions();
        console.log(`📋 Found ${options.length} options after opening dropdown`);

        // Step 2b: LAZY LOADING TRIGGER - If no/few options, type first char to trigger load
        let lazyLoadInput = null;
        if (options.length === 0 && value.length > 0) {
            console.log(`⚡ Triggering lazy load: typing first char "${value[0]}"`);

            const input = element.querySelector('input') ||
                (element.tagName === 'INPUT' ? element : null);

            if (input) {
                lazyLoadInput = input; // Remember for cleanup later
                input.focus();
                // Type first char
                EventDispatcher.setNativeValue(input, value[0]);
                EventDispatcher.dispatchInputEvents(input, ['input']);
                await Utils.sleep(500); // Wait for options to load

                // Re-scan for options
                options = await this._findDropdownOptions();
                console.log(`📋 Found ${options.length} options after typing first char`);
            }
        }

        // Step 3: If no options found, try searchable dropdown ONLY if it has autocomplete
        if (options.length === 0) {
            console.log(`🔍 No options found, checking if searchable dropdown...`);

            // Try standard searchable approach first
            options = await this._trySearchableDropdown(element, value);
            if (options.length > 0) {
                const { match, score } = OptionMatcher.findBestMatch(
                    options,
                    value,
                    option => option.textContent
                );

                if (match && score > 0.5) {
                    console.log(`✅ Searchable dropdown: selecting "${match.textContent?.trim()}" (${(score * 100).toFixed(1)}%)`);
                    EventDispatcher.dispatchClick(match);
                    await Utils.sleep(200);

                    // Clear any text that was typed for searchable dropdown and blur
                    const searchInput = element.querySelector('input') || (element.tagName === 'INPUT' ? element : null);
                    if (searchInput) {
                        // Wait for selection to register, then clear if needed
                        const currentValue = searchInput.value || '';
                        const selectedText = match.textContent?.trim() || '';

                        // Only clear if it's still the search text and not the selected value
                        if (currentValue === value && !currentValue.includes(selectedText) && !selectedText.includes(currentValue)) {
                            console.log('🧹 Clearing search input after selection');
                            EventDispatcher.setNativeValue(searchInput, '');
                            EventDispatcher.dispatchInputEvents(searchInput, ['input']);
                        }

                        // Blur to prevent further text input
                        searchInput.blur();
                    }

                    this._closeDropdown();
                    return true;
                }
            }

            // FALLBACK: Blind fill (Type + Enter)
            // Useful for virtualized lists or shadow DOM where we can't see options
            console.log(`⚠️ Falling back to blind fill (Type + Enter) for "${value}"`);
            const input = element.querySelector('input') || (element.tagName === 'INPUT' ? element : null);

            if (input) {
                input.focus();
                EventDispatcher.setNativeValue(input, value);
                EventDispatcher.dispatchInputEvents(input, ['input']);
                await Utils.sleep(500); // Wait for potential filtering

                EventDispatcher.dispatchKeydown(input, 'Enter');
                await Utils.sleep(200);

                // Check if value stuck
                if (input.value === value || input.value.includes(value)) {
                    console.log(`✅ Blind fill success: Value persisted`);
                    return true;
                }
            }

            this._closeDropdown();
            const errorMsg = 'Could not find dropdown options - this may not be a dropdown';
            console.warn(`❌ ${errorMsg}`);
            report.recordMismatch(field, value, errorMsg);
            return false;
        }

        // Log available options for debugging
        const optionTexts = options.slice(0, 10).map(o => o.textContent?.trim()).filter(Boolean);
        console.log(`📋 Available options (${options.length} total): ${optionTexts.join(', ')}${options.length > 10 ? '...' : ''}`);
        console.log(`🎯 Looking for value: "${value}"`);

        // Step 4: Find best matching option
        const { match, score } = OptionMatcher.findBestMatch(
            options,
            value,
            option => option.textContent
        );

        if (match) {
            console.log(`🔍 Best match found: "${Utils.normalizeText(match.textContent)}" with score ${(score * 100).toFixed(1)}%`);
            console.log(`   Match is option #${options.indexOf(match) + 1} of ${options.length}`);
        } else {
            console.log(`❌ No match found for "${value}"`);
        }

        if (match && OptionMatcher.isAcceptableMatch(score)) {
            const selectedText = Utils.normalizeText(match.textContent);
            const matchIndex = options.indexOf(match);
            console.log(`✅ Selecting option #${matchIndex + 1}: "${selectedText}" (score: ${(score * 100).toFixed(1)}%)`);
            console.log(`   Target value was: "${value}"`);

            // Extra check: if it's the first option with a low score, be suspicious
            if (matchIndex === 0 && score < 0.5) {
                console.warn(`⚠️ First option selected with low score (${(score * 100).toFixed(1)}%). This might be wrong.`);
                console.warn(`   First option text: "${selectedText}"`);
                console.warn(`   Target value: "${value}"`);
                // Still proceed, but log a warning
            }

            // Verify this is actually a good match before clicking
            if (score < CONFIG.THRESHOLDS.MIN_ACCEPTABLE_MATCH) {
                console.warn(`⚠️ Match score too low (${(score * 100).toFixed(1)}%), not selecting`);
                this._closeDropdown();
                report.recordMismatch(field, value, `Match score too low: ${(score * 100).toFixed(1)}%`);
                return false;
            }

            match.scrollIntoView({ block: 'nearest' });
            await Utils.sleep(50);

            // Click the option
            EventDispatcher.dispatchClick(match);
            await Utils.sleep(500); // Wait for dynamic components to load
            await Utils.sleep(300); // Wait for selection to register

            // Verify selection worked - check if input/display shows the selected value
            const input = element.querySelector('input') || (element.tagName === 'INPUT' ? element : null);
            if (input) {
                const currentValue = input.value || input.textContent || '';
                const currentNormalized = Utils.normalizeText(currentValue);
                // Check if the selected text appears in the current value OR the element display text
                const elText = Utils.normalizeText(element.textContent);
                const selectionWorked = currentNormalized.includes(selectedText) ||
                    selectedText.includes(currentNormalized) ||
                    currentNormalized.includes(Utils.normalizeText(value)) ||
                    elText.includes(selectedText) ||
                    elText.includes(Utils.normalizeText(value));

                if (!selectionWorked && currentValue && currentValue.length > 0 && !currentValue.includes('...') && currentValue !== 'Select...') {
                    console.warn(`⚠️ Selection may not have worked. Current value: "${currentValue}", Expected: "${selectedText}"`);
                    // Don't just fail if textContent looks correct
                    if (!elText.includes(selectedText)) {
                        this._closeDropdown();
                        report.recordMismatch(field, value, `Selection didn't register. Current: "${currentValue}", Display: "${elText}"`);
                        return false;
                    }
                }

                // Clear any lazy load text if it's still there
                if (lazyLoadInput && lazyLoadInput.value && lazyLoadInput.value.length <= 1) {
                    console.log('🧹 Clearing lazy load input after selection');
                    EventDispatcher.setNativeValue(lazyLoadInput, '');
                    EventDispatcher.dispatchInputEvents(lazyLoadInput, ['input']);
                }

                // Blur to prevent any text input
                input.blur();
            }

            // Close dropdown
            this._closeDropdown();

            console.log(`✅ Dropdown selection complete. No text input will be attempted.`);
            return true;
        }

        this._closeDropdown();
        const errorMsg = `No matching option for "${value}". Available: ${optionTexts.slice(0, 5).join(', ')}`;
        console.warn(`❌ ${errorMsg}`);
        report.recordMismatch(field, value, errorMsg);
        return false;
    }

    static async _openDropdown(element) {
        // Snapshot existing options BEFORE opening
        const optionsBefore = new Set(
            Array.from(document.querySelectorAll('[role="option"], [role="menuitem"], [class*="option"], li[data-value]'))
                .map(el => el)
        );

        // Strategy 1: Click specific dropdown indicators (arrow/caret)
        // Order matters: look for common indicators inside the element first
        const indicators = [
            '[class*="-control"]',      // React Select Control (Best for React Select)
            '[class*="__control"]',     // React Select Control (Alternative)
            '[class*="indicator"]',
            '[class*="arrow"]',
            '[class*="caret"]',
            '[class*="chevron"]',
            'svg',
            'button',
            '[role="button"]',
            '[class*="icon"]'
        ];

        // Search scopes: element -> parent -> closest select/dropdown wrapper
        const scopes = [element];
        if (element.parentElement) scopes.push(element.parentElement);
        const wrapper = element.closest('[class*="select"], [class*="dropdown"], [class*="combobox"], [role="combobox"], [role="button"]');
        if (wrapper && !scopes.includes(wrapper)) scopes.push(wrapper);

        let clickTarget = element;
        let indicatorFound = false;

        for (const selector of indicators) {
            for (const scope of scopes) {
                const indicator = scope.querySelector(selector);
                if (indicator && this._isVisible(indicator)) {
                    clickTarget = indicator;
                    indicatorFound = true;
                    console.log(`🖱️ Found dropdown interactive element: ${selector}`);
                    break;
                }
            }
            if (indicatorFound) break;
        }

        // Sibling fallback: some arrows sit next to the input
        if (!indicatorFound && element.nextElementSibling) {
            for (const selector of indicators) {
                const sibIndicator = element.nextElementSibling.matches?.(selector)
                    ? element.nextElementSibling
                    : element.nextElementSibling.querySelector?.(selector);
                if (sibIndicator && this._isVisible(sibIndicator)) {
                    clickTarget = sibIndicator;
                    indicatorFound = true;
                    console.log(`🖱️ Found dropdown indicator in sibling: ${selector}`);
                    break;
                }
            }
        }

        // Focus first
        element.focus();
        await Utils.sleep(50);

        // Click the target
        console.log('🖱️ Clicking primary target (pointer+mouse sequence)...');
        EventDispatcher.dispatchClickSequence(clickTarget);
        await Utils.sleep(120);

        // If we clicked a specific indicator (like an SVG), also click its parent
        // often SVGs have pointer-events:none and the click listener is on the parent div
        if (indicatorFound && clickTarget.parentElement) {
            console.log('🖱️ Clicking indicator parent (backup)...');
            EventDispatcher.dispatchClickSequence(clickTarget.parentElement);
            await Utils.sleep(100);
        }

        // Also click the main element itself if we targeted something inside
        if (clickTarget !== element) {
            console.log('🖱️ Clicking main element (backup)...');
            EventDispatcher.dispatchClickSequence(element);
        }

        // Additional backup: click common control wrappers (React Select shells, containers)
        const controlSelectors = [
            '[class*="select-shell"]',
            '[class*="remix"][class*="container"]',
            '[class*="__container"]',
            '[class*="-container"]',
            '[class*="control"]',
            '[role="combobox"]',
            '[role="textbox"]',
            'div[tabindex]'
        ];
        for (const sel of controlSelectors) {
            const ctl = element.querySelector(sel);
            if (ctl && this._isVisible(ctl)) {
                console.log(`🖱️ Clicking control wrapper: ${sel}`);
                EventDispatcher.dispatchClickSequence(ctl);
                await Utils.sleep(80);
            }
        }

        // Fallback: click the element at the visual center (helps when a pseudo-element handles the click)
        const rect = element.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0) {
            const centerTarget = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
            if (centerTarget && this._isVisible(centerTarget) && centerTarget !== clickTarget && centerTarget !== element) {
                console.log('🖱️ Clicking element at center point (backup)...');
                EventDispatcher.dispatchClickSequence(centerTarget);
                await Utils.sleep(80);
            }
        }

        await Utils.sleep(CONFIG.TIMING.DROPDOWN_OPEN_DELAY);

        this._currentDropdownElement = element;
        this._optionsBefore = optionsBefore;

        // Strategy 2: Check if open. If no options found, try keyboard triggers as fallback
        const currentOptions = await this._findDropdownOptions();
        if (currentOptions.length === 0) {
            console.log(`⌨️ No options found after clicking, trying ArrowDown trigger`);
            EventDispatcher.dispatchKeydown(element, 'ArrowDown');
            await Utils.sleep(200);

            // Re-check
            const afterArrowOptions = await this._findDropdownOptions();
            if (afterArrowOptions.length === 0) {
                console.log('⌨️ Still no options, trying Space trigger');
                EventDispatcher.dispatchKeydown(element, ' ');
                await Utils.sleep(200);
            }
        }

        return true;
    }

    static async _findDropdownOptions() {
        return this._queryOptions(this._currentDropdownElement);
    }

    static _queryOptions(element) {
        // Strategy 1: Check aria-controls first (most reliable)
        if (element) {
            const ariaControls = element.getAttribute('aria-controls');
            if (ariaControls) {
                const controlledElement = document.getElementById(ariaControls);
                if (controlledElement && this._isVisible(controlledElement)) {
                    const options = this._getOptionsFromContainer(controlledElement);
                    if (options.length > 0) {
                        console.log(`📋 Found ${options.length} options via aria-controls (#${ariaControls})`);
                        return options;
                    }
                }
            }

            // Check aria-owns
            const ariaOwns = element.getAttribute('aria-owns');
            if (ariaOwns) {
                const ownedElement = document.getElementById(ariaOwns);
                if (ownedElement && this._isVisible(ownedElement)) {
                    const options = this._getOptionsFromContainer(ownedElement);
                    if (options.length > 0) {
                        console.log(`📋 Found ${options.length} options via aria-owns`);
                        return options;
                    }
                }
            }
        }

        // Strategy 2: Look for visible popup/listbox containers (most recently appeared)
        const popupSelectors = [
            '[role="listbox"]:not([aria-hidden="true"])',
            '[role="menu"]:not([aria-hidden="true"])',
            '[class*="dropdown-menu"]:not(.hidden)',
            '[class*="select-menu"]:not(.hidden)',
            '[class*="listbox"]:not(.hidden)',
            '[class*="MenuList"]',
            '[class*="menu-list"]',
            '[class*="options-list"]',
            '[class*="select__menu"]',
            'ul[class*="dropdown"]',
            'div[class*="dropdown"][class*="open"]',
            'div[class*="dropdown"][class*="show"]',
        ];

        for (const selector of popupSelectors) {
            try {
                const popups = Array.from(document.querySelectorAll(selector));
                for (const popup of popups.reverse()) { // Check most recent first
                    if (this._isVisible(popup)) {
                        const options = this._getOptionsFromContainer(popup);
                        if (options.length > 0 && options.length < 50) { // Reasonable number of options
                            console.log(`📋 Found ${options.length} options in popup (${selector})`);
                            return options;
                        }
                    }
                }
            } catch (e) {
                // Invalid selector, skip
            }
        }

        // Strategy 3: Look for newly appeared options (not in original snapshot)
        if (this._optionsBefore && this._optionsBefore.size > 0) {
            const allCurrentOptions = [];
            for (const selector of CONFIG.DROPDOWN_OPTION_SELECTORS) {
                try {
                    const found = Array.from(document.querySelectorAll(selector));
                    allCurrentOptions.push(...found.filter(el => this._isVisible(el)));
                } catch (e) { }
            }

            const newOptions = allCurrentOptions.filter(opt => !this._optionsBefore.has(opt));
            if (newOptions.length > 0 && newOptions.length < 50) {
                console.log(`📋 Found ${newOptions.length} newly appeared options`);
                return newOptions;
            }
        }

        // Strategy 4: Check element's parent/sibling for options
        if (element) {
            const wrapper = element.closest('[class*="select"], [class*="dropdown"], [class*="combobox"]');
            if (wrapper) {
                const options = this._getOptionsFromContainer(wrapper);
                if (options.length > 0 && options.length < 50) {
                    console.log(`📋 Found ${options.length} options in wrapper`);
                    return options;
                }
            }
        }

        // Strategy 5: Last resort - scan entire document for ANY visible options
        console.log(`🔍 Strategy 5: Scanning entire document for options...`);
        for (const selector of CONFIG.DROPDOWN_OPTION_SELECTORS) {
            try {
                const allOptions = Array.from(document.querySelectorAll(selector))
                    .filter(el => this._isVisible(el));
                if (allOptions.length > 0 && allOptions.length < 100) {
                    console.log(`📋 Found ${allOptions.length} visible options with selector: ${selector}`);
                    // Log first few options for debugging
                    allOptions.slice(0, 3).forEach((opt, i) => {
                        console.log(`   ${i + 1}. "${opt.textContent?.trim().substring(0, 50)}"`);
                    });
                    return allOptions;
                }
            } catch (e) { }
        }

        console.log(`⚠️ No options found with any strategy`);
        return [];
    }

    static _getOptionsFromContainer(container) {
        for (const selector of CONFIG.DROPDOWN_OPTION_SELECTORS) {
            const options = Array.from(container.querySelectorAll(selector));
            if (options.length > 0) return options;
        }
        // Also try direct children that look like options
        const children = Array.from(container.children).filter(child => {
            const role = child.getAttribute('role');
            return role === 'option' || role === 'menuitem' || child.tagName === 'LI';
        });
        return children;
    }

    static _isVisible(element) {
        if (!element) return false;
        const style = window.getComputedStyle(element);
        if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') {
            return false;
        }
        const rect = element.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
    }

    static async _trySearchableDropdown(element, value) {
        // Only try searchable if this element actually has an input AND aria-autocomplete
        const input = element.querySelector('input[aria-autocomplete]') ||
            (element.tagName === 'INPUT' && element.getAttribute('aria-autocomplete') ? element : null);

        if (!input) {
            console.log(`⚠️ Not a searchable dropdown - no autocomplete input found`);
            return [];
        }

        console.log(`🔍 Trying searchable dropdown - typing "${value}"`);
        input.focus();
        EventDispatcher.setNativeValue(input, value);
        EventDispatcher.dispatchInputEvents(input, ['input']);
        await Utils.sleep(400);

        return this._queryOptions(element);
    }

    static _closeDropdown() {
        document.body.click();
        EventDispatcher.dispatchKeydown(document, 'Escape');
    }

    // -------------------------------------------------------------------------
    // Checkbox
    // -------------------------------------------------------------------------

    static async fillCheckbox(element, value, report, field) {
        const shouldCheck = ['true', '1', 'yes', 'on'].includes(String(value).toLowerCase());

        if (element.checked !== shouldCheck) {
            EventDispatcher.dispatchCheckableSequence(element, shouldCheck);
            EventDispatcher.dispatchReactHandlers(element, ['onChange', 'onClick']);
        }

        return true;
    }

    // -------------------------------------------------------------------------
    // Radio Button
    // -------------------------------------------------------------------------

    static async fillRadio(element, value, report, field) {
        const radioGroup = this._getRadioGroup(element);
        const normalizedValue = Utils.normalizeText(value);

        for (const radio of radioGroup) {
            const labelText = Utils.normalizeText(IdempotencyChecker.getRadioLabel(radio));
            const radioValue = Utils.normalizeText(radio.value);

            if (labelText.includes(normalizedValue) ||
                normalizedValue.includes(labelText) ||
                radioValue === normalizedValue) {
                EventDispatcher.dispatchCheckableSequence(radio, true);
                EventDispatcher.dispatchReactHandlers(radio, ['onChange', 'onClick']);
                return true;
            }
        }

        report.recordMismatch(field, value, `No matching radio. Available: ${radioGroup.map(r => IdempotencyChecker.getRadioLabel(r)).join(', ')}`);
        return false;
    }

    static _getRadioGroup(element) {
        const name = element.name || element.getAttribute('name');

        if (name) {
            const group = Array.from(document.querySelectorAll(`input[type="radio"][name="${CSS.escape(name)}"]`));
            if (group.length > 0) return group;
        }

        const parent = element.closest('fieldset, [role="radiogroup"], [class*="radio"]');
        if (parent) {
            const group = Array.from(parent.querySelectorAll('input[type="radio"]'));
            if (group.length > 0) return group;
        }

        return [element];
    }

    // -------------------------------------------------------------------------
    // Custom Binary Choice (Yes/No buttons, styled radio groups)
    // -------------------------------------------------------------------------

    /**
     * Fill custom Yes/No or binary choice elements that use styled buttons
     * instead of native radio inputs.
     * 
     * Handles:
     * - Elements with role="radio" or role="checkbox"
     * - Button groups inside role="radiogroup" containers
     * - Styled div/button elements with Yes/No text
     */
    static async fillCustomBinaryChoice(element, value, report, field) {
        const normalizedValue = Utils.normalizeText(value);
        const tagName = element.tagName.toLowerCase();
        console.log(`🔘 Filling custom binary choice "${field.label}" with value "${value}"`);

        // Strategy 0: If element itself is a button/option that matches the value, click it directly
        if (tagName === 'button' || element.getAttribute('role') === 'radio' || element.getAttribute('role') === 'option') {
            const elemText = Utils.normalizeText(element.textContent);
            const elemMatches = elemText === normalizedValue ||
                               elemText.includes(normalizedValue) ||
                               (normalizedValue === 'yes' && elemText === 'yes') ||
                               (normalizedValue === 'no' && elemText === 'no');
            
            if (elemMatches) {
                console.log(`✅ Element itself matches value, clicking directly: "${element.textContent?.trim()}"`);
                element.scrollIntoView({ block: 'nearest' });
                await Utils.sleep(50);
                EventDispatcher.dispatchClickSequence(element);
                await Utils.sleep(200);
                EventDispatcher.dispatchReactHandlers(element, ['onChange', 'onClick']);
                
                // Also check for sibling hidden input and update it
                const parent = element.parentElement;
                if (parent) {
                    const hiddenInput = parent.querySelector('input[type="checkbox"], input[type="radio"]');
                    if (hiddenInput) {
                        hiddenInput.value = value;
                        EventDispatcher.dispatchInputEvents(hiddenInput, ['input', 'change']);
                    }
                }
                return true;
            }
        }

        // Strategy 1: Find the container (look for yesno, radiogroup, or button-group containers)
        let container = element;
        if (element.getAttribute('role') !== 'radiogroup') {
            container = element.closest('[role="radiogroup"]') || 
                        element.closest('[class*="yesno"]') ||      // Ashby-style
                        element.closest('[class*="yes-no"]') ||
                        element.closest('[class*="radio-group"]') ||
                        element.closest('[class*="button-group"]') ||
                        element.closest('[class*="choice"]') ||
                        element.closest('[class*="toggle"]') ||
                        element.parentElement;
        }

        // Find all clickable options in the container
        const optionSelectors = [
            '[role="radio"]',
            '[role="option"]',
            '[role="checkbox"]',
            '[aria-checked]',
            'button:not([type="submit"]):not([class*="toggle"])',  // Exclude toggle buttons that aren't options
            '[class*="_option"]',  // Ashby-style option classes
            '[class*="option"]:not([class*="options"])',
            '[class*="choice"]',
            'label:has(input[type="radio"])',
            'label:has(input[type="checkbox"])'
        ];

        let options = [];
        for (const selector of optionSelectors) {
            try {
                const found = Array.from(container.querySelectorAll(selector));
                // Filter to only visible elements, and exclude the hidden input
                const visible = found.filter(opt => 
                    this._isVisible(opt) && 
                    !(opt.tagName === 'INPUT' && opt.type === 'checkbox' && opt.tabIndex === -1)
                );
                if (visible.length > 0 && visible.length <= 10) {
                    options = visible;
                    console.log(`📋 Found ${options.length} options with selector: ${selector}`);
                    break;
                }
            } catch (e) { }
        }

        // Strategy 2: If no options found in container, element itself might be one option
        // Try to find siblings that are also options (buttons)
        if (options.length === 0) {
            const parent = element.parentElement;
            if (parent) {
                const siblings = Array.from(parent.children).filter(child => {
                    return (child.getAttribute('role') === 'radio' ||
                           child.getAttribute('role') === 'checkbox' ||
                           child.hasAttribute('aria-checked') ||
                           (child.tagName === 'BUTTON' && child.type !== 'submit')) &&
                           this._isVisible(child);
                });
                if (siblings.length > 0 && siblings.length <= 10) {
                    options = siblings;
                    console.log(`📋 Found ${options.length} sibling button options`);
                }
            }
        }

        if (options.length === 0) {
            console.warn(`❌ No custom binary options found for "${field.label}"`);
            report.recordMismatch(field, value, 'No custom binary choice options found');
            return false;
        }

        // Log available options
        const optionTexts = options.map(o => o.textContent?.trim()).filter(Boolean);
        console.log(`📋 Available options: ${optionTexts.join(', ')}`);

        // Find the matching option
        for (const option of options) {
            const optText = Utils.normalizeText(option.textContent);
            const ariaLabel = Utils.normalizeText(option.getAttribute('aria-label') || '');
            const dataValue = Utils.normalizeText(option.getAttribute('data-value') || '');
            const optValue = Utils.normalizeText(option.getAttribute('value') || '');

            // Check for match
            const isMatch = 
                optText === normalizedValue ||
                optText.includes(normalizedValue) ||
                normalizedValue.includes(optText) ||
                ariaLabel === normalizedValue ||
                dataValue === normalizedValue ||
                optValue === normalizedValue ||
                // Handle Yes/No variations
                (normalizedValue === 'yes' && (optText.includes('yes') || optText === 'y')) ||
                (normalizedValue === 'no' && (optText.includes('no') || optText === 'n')) ||
                (normalizedValue === 'true' && optText.includes('yes')) ||
                (normalizedValue === 'false' && optText.includes('no'));

            if (isMatch) {
                console.log(`✅ Clicking matching option: "${option.textContent?.trim()}"`);
                
                // Check if already selected
                const isSelected = option.getAttribute('aria-checked') === 'true' ||
                                   option.classList.contains('selected') ||
                                   option.classList.contains('active');
                
                if (isSelected) {
                    console.log(`⏭️ Option already selected`);
                    return true;
                }

                // Click the option
                option.scrollIntoView({ block: 'nearest' });
                await Utils.sleep(50);
                
                EventDispatcher.dispatchClickSequence(option);
                
                // Also try clicking any nested input
                const nestedInput = option.querySelector('input[type="radio"], input[type="checkbox"]');
                if (nestedInput && !nestedInput.checked) {
                    EventDispatcher.dispatchCheckableSequence(nestedInput, true);
                }
                
                // For Ashby-style Yes/No: update the sibling hidden input if it exists
                // The hidden input stores the actual form value
                const siblingContainer = option.parentElement;
                if (siblingContainer) {
                    const hiddenInput = siblingContainer.querySelector('input[type="checkbox"][tabindex="-1"], input[type="radio"][tabindex="-1"]');
                    if (hiddenInput) {
                        console.log(`📝 Updating sibling hidden input value to "${value}"`);
                        const optionText = option.textContent?.trim() || value;
                        hiddenInput.value = optionText;
                        if (hiddenInput.type === 'checkbox') {
                            hiddenInput.checked = normalizedValue === 'yes' || normalizedValue === 'true';
                        }
                        EventDispatcher.dispatchInputEvents(hiddenInput, ['input', 'change']);
                    }
                }
                
                await Utils.sleep(200);
                
                // Dispatch React handlers
                EventDispatcher.dispatchReactHandlers(option, ['onChange', 'onClick']);
                
                return true;
            }
        }

        report.recordMismatch(field, value, `No matching option. Available: ${optionTexts.join(', ')}`);
        return false;
    }

    // -------------------------------------------------------------------------
    // File Upload (highlight for user)
    // -------------------------------------------------------------------------

    static async handleFile(element, value, report, field) {
        // Check if file already uploaded
        if (element.files?.length > 0 && !field.allow_replacement) {
            report.recordSkipped(field, 'File already uploaded');
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

        Object.assign(parent.style, {
            border: '3px solid #f59e0b',
            background: 'rgba(245, 158, 11, 0.1)',
            borderRadius: '8px',
            position: 'relative'
        });

        // Add tooltip
        const tooltip = document.createElement('div');
        tooltip.innerHTML = `
            <div style="
                position: absolute; top: -40px; left: 0;
                background: #f59e0b; color: white;
                padding: 8px 14px; border-radius: 6px;
                font-size: 13px; font-weight: 500;
                font-family: system-ui, -apple-system, sans-serif;
                white-space: nowrap; z-index: 999999;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            ">📎 Please upload: ${field.label || value || 'Document'}</div>
        `;
        parent.appendChild(tooltip);

        // Auto-cleanup
        setTimeout(() => {
            Object.assign(parent.style, originalStyles);
            tooltip.remove();
        }, 15000);

        report.recordFileUpload(field);
        return true;
    }
}

// ============================================================================
// SUBMISSION BLOCKER (Safety)
// ============================================================================

class SubmissionBlocker {
    static isSubmitElement(element) {
        if (!element) return false;

        const type = (element.type || '').toLowerCase();
        if (type === 'submit') return true;
        if (element.getAttribute('role') === 'submit') return true;

        const text = Utils.normalizeText(
            (element.textContent || '') + ' ' +
            (element.value || '') + ' ' +
            (element.getAttribute('aria-label') || '')
        );

        return CONFIG.BLOCKED_BUTTON_PATTERNS.some(pattern => pattern.test(text));
    }

    static blockSubmission() {
        const potentialSubmits = document.querySelectorAll(
            'button, input[type="submit"], [role="button"], a[class*="submit"], a[class*="apply"]'
        );

        for (const el of potentialSubmits) {
            if (this.isSubmitElement(el)) {
                console.log('🛑 AutoApply: Submit element detected:', el);
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
            this.toastElement = this._createToastElement();
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

    static _createToastElement() {
        const el = document.createElement('div');
        el.id = 'autoapply-toast';
        el.style.cssText = `
            position: fixed; top: 20px; right: 20px;
            padding: 12px 20px; border-radius: 8px;
            z-index: 999999; font-size: 14px; font-weight: 500;
            font-family: system-ui, -apple-system, sans-serif;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            transition: all 0.3s ease;
            opacity: 0; transform: translateY(-20px);
            max-width: 400px;
        `;
        return el;
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
        Object.assign(element.style, {
            outline: original.outline,
            outlineOffset: original.outlineOffset
        });
        setTimeout(() => {
            element.style.transition = original.transition;
        }, 200);
    }
}

// ============================================================================
// MAIN FORM FILLER (Orchestrator)
// ============================================================================

class FormFiller {
    constructor() {
        this.report = new FillReport();
    }

    /**
     * Main entry point - fill form based on JSON specification
     */
    async fill(formSpec) {
        if (!formSpec?.fields?.length) {
            console.error('AutoApply: Invalid form specification');
            return this.report;
        }

        const fields = formSpec.fields.filter(f => !f.skipped && f.value != null);
        const totalFields = fields.length;

        console.log(`🚀 AutoApply: Starting fill for ${totalFields} fields`);
        UIFeedback.showNotification(`Starting form fill (${totalFields} fields)...`, 'loading');

        SubmissionBlocker.blockSubmission();

        for (let i = 0; i < fields.length; i++) {
            try {
                await this._fillField(fields[i], i + 1, totalFields);
            } catch (error) {
                this.report.recordError(fields[i], error);
            }

            await Utils.sleep(CONFIG.TIMING.FIELD_FILL_DELAY);
        }

        this._showCompletionSummary(totalFields);
        return this.report;
    }

    async _fillField(field, currentIndex, totalFields) {
        const label = field.label || 'field';
        const truncatedLabel = label.length > 30 ? label.substring(0, 30) + '...' : label;
        UIFeedback.showNotification(`Filling ${currentIndex}/${totalFields}: ${truncatedLabel}`, 'info');

        // Resolve element with retry (waits for dynamically loaded elements)
        const xpaths = Array.isArray(field.xpaths) ? field.xpaths : [field.xpath];
        const { element } = await XPathResolver.resolveWithWait(xpaths, 3000, 200);

        if (!element) {
            console.warn(`❌ Element not found for "${field.label}" after waiting: ${xpaths.join(', ')}`);
            this.report.recordSkipped(field, 'Element not found via XPath (after retry)');
            return;
        }

        // Validate element
        const validation = ElementValidator.validate(element, field);
        if (!validation.valid) {
            this.report.recordMismatch(field,
                { label: field.label, type: field.field_type },
                { issues: validation.issues, confidence: validation.confidence }
            );
            this.report.recordSkipped(field, `Validation failed: ${validation.issues.join(', ')}`);
            return;
        }

        // Idempotency check
        if (IdempotencyChecker.hasCorrectValue(element, field.value, field.field_type)) {
            this.report.recordSkipped(field, 'Already has correct value');
            console.log(`⏭️ Skipped (already filled): ${field.label || field.xpath}`);
            return;
        }

        // Safety check for textareas
        if (field.field_type === 'textarea' && field.unsafe_to_generate === true) {
            this.report.recordSkipped(field, 'Free-text field marked as unsafe');
            return;
        }

        // Fill the field
        const originalStyles = UIFeedback.highlightElement(element);
        await Utils.sleep(200);

        try {
            const filled = await this._executeFill(element, field);

            if (filled) {
                this.report.recordFilled(field, element);
                element.style.outline = '3px solid #10b981';
            } else {
                element.style.outline = '3px solid #ef4444';
            }
            await Utils.sleep(300);
        } finally {
            UIFeedback.removeHighlight(element, originalStyles);
        }
    }

    async _executeFill(element, field) {
        const fieldType = (field.field_type || 'text').toLowerCase();
        const tagName = element.tagName.toLowerCase();
        const inputType = (element.type || '').toLowerCase();

        // Auto-detect dropdown (overrides backend field_type if needed)
        const isDropdown = DropdownDetector.isDropdown(element);
        const shouldUseDropdownFiller = isDropdown &&
            !['checkbox', 'radio', 'file'].includes(fieldType);

        if (shouldUseDropdownFiller && fieldType !== 'select') {
            console.log(`🔄 Auto-detected dropdown for "${field.label}" (was: ${fieldType})`);
        }

        // Detect custom binary choice elements (Yes/No buttons, styled radio groups)
        const isCustomBinaryChoice = this._isCustomBinaryChoice(element, fieldType);
        
        if (isCustomBinaryChoice) {
            console.log(`🔘 Detected custom binary choice for "${field.label}"`);
            return FieldFillers.fillCustomBinaryChoice(element, field.value, this.report, field);
        }

        // Route to appropriate filler
        if (shouldUseDropdownFiller || fieldType === 'select') {
            return tagName === 'select'
                ? FieldFillers.fillSelect(element, field.value, this.report, field)
                : FieldFillers.fillCustomDropdown(element, field.value, this.report, field);
        }

        switch (fieldType) {
            case 'checkbox':
                // Native checkbox input
                if (tagName === 'input' && inputType === 'checkbox') {
                    return FieldFillers.fillCheckbox(element, field.value, this.report, field);
                }
                // Custom checkbox (role="checkbox" or styled element)
                return FieldFillers.fillCustomBinaryChoice(element, field.value, this.report, field);
                
            case 'radio':
                // Native radio input
                if (tagName === 'input' && inputType === 'radio') {
                    return FieldFillers.fillRadio(element, field.value, this.report, field);
                }
                // Custom radio/binary choice (role="radio", button groups, etc.)
                return FieldFillers.fillCustomBinaryChoice(element, field.value, this.report, field);
                
            case 'file':
                return FieldFillers.handleFile(element, field.value, this.report, field);
            default:
                return tagName === 'select'
                    ? FieldFillers.fillSelect(element, field.value, this.report, field)
                    : FieldFillers.fillText(element, field.value, this.report, field);
        }
    }

    /**
     * Detect if an element is a custom binary choice component (Yes/No buttons, 
     * styled radio groups) rather than a native input.
     */
    _isCustomBinaryChoice(element, fieldType) {
        const tagName = element.tagName.toLowerCase();
        const inputType = (element.type || '').toLowerCase();
        const role = element.getAttribute('role');

        // If it's a native input radio/checkbox, it's NOT a custom binary choice
        if (tagName === 'input' && (inputType === 'radio' || inputType === 'checkbox')) {
            return false;
        }

        // EXCLUDE dropdowns/comboboxes - these are NOT binary choices!
        if (role === 'combobox' || role === 'listbox' || role === 'option' || role === 'menuitem') {
            return false;
        }
        // Also exclude inputs with combobox-like attributes
        if (element.getAttribute('aria-haspopup') === 'listbox' || 
            element.getAttribute('aria-autocomplete')) {
            return false;
        }

        // Only consider as binary choice if fieldType explicitly says so
        if (fieldType !== 'radio' && fieldType !== 'checkbox') {
            return false;
        }

        // Check for custom binary choice indicators
        const isCustomByRole = role === 'radiogroup' || 
                               role === 'radio' || 
                               role === 'checkbox';
        
        const hasAriaChecked = element.hasAttribute('aria-checked');
        
        const isInRadioGroup = element.closest('[role="radiogroup"]') !== null;
        
        // Check for button-style Yes/No (must be a button AND field type is radio/checkbox)
        const isYesNoButton = tagName === 'button' && 
                              /yes|no|true|false/i.test(element.textContent || '');

        // Check if element has yesno or similar class (specific patterns for Yes/No)
        const hasYesNoClass = /yesno|yes-no|binary|toggle-group/i.test(
            element.className || ''
        );

        // If fieldType is radio/checkbox but element is not a native input,
        // AND it's inside a container that looks like a choice group
        const isNonInputRadioCheckbox = tagName !== 'input' && tagName !== 'select';
        const parentHasChoiceIndicator = element.parentElement && 
            /yesno|yes-no|radio|choice|toggle/i.test(element.parentElement.className || '');

        return isCustomByRole || 
               hasAriaChecked || 
               isInRadioGroup || 
               isYesNoButton || 
               hasYesNoClass ||
               (isNonInputRadioCheckbox && parentHasChoiceIndicator);
    }

    _showCompletionSummary(totalFields) {
        const summary = this.report.getSummary();
        let message = `🎉 Done! Filled ${summary.filled}/${totalFields} fields.`;

        if (summary.skipped > 0) message += ` Skipped: ${summary.skipped}.`;
        if (summary.fileUploads > 0) message += ` 📎 ${summary.fileUploads} file(s) need upload.`;
        if (summary.mismatches > 0) message += ` ⚠️ ${summary.mismatches} mismatches.`;

        UIFeedback.showNotification(message, summary.errors.length > 0 ? 'warning' : 'success');
        console.log('📊 AutoApply Fill Report:', this.report);
    }
}

// ============================================================================
// ENTRYPOINT
// ============================================================================

const API_BASE = "http://localhost:8000";

/**
 * Extract draft ID from URL hash (#autoapply_id=...)
 */
function extractDraftIdFromHash() {
    const hash = window.location.hash;
    const match = hash.match(/autoapply_id=([a-f0-9-]+)/i);
    return match ? match[1] : null;
}

/**
 * Fetch draft from backend API (tries direct fetch, falls back to background proxy)
 */
async function fetchDraftById(draftId) {
    try {
        console.log(`📡 AutoApply: Fetching draft ${draftId} from API...`);

        // Try direct fetch first
        try {
            const response = await fetch(`${API_BASE}/drafts/${draftId}`);

            if (response.ok) {
                const draft = await response.json();
                console.log(`✅ AutoApply: Fetched draft ${draftId} (direct)`, draft);
                return draft;
            }
        } catch (fetchError) {
            console.log('⚠️ AutoApply: Direct fetch failed (CORS?), trying background proxy...', fetchError.message);
        }

        // Fallback: proxy through background script
        return new Promise((resolve) => {
            chrome.runtime.sendMessage(
                { action: 'fetchDraftData', draftId: draftId },
                (response) => {
                    if (chrome.runtime.lastError) {
                        console.error(`❌ AutoApply: Background fetch error:`, chrome.runtime.lastError.message);
                        resolve(null);
                    } else if (response?.success && response?.data) {
                        console.log(`✅ AutoApply: Fetched draft ${draftId} (via background)`, response.data);
                        resolve(response.data);
                    } else {
                        console.error(`❌ AutoApply: Failed to fetch draft ${draftId}:`, response?.error || 'Unknown error');
                        resolve(null);
                    }
                }
            );
        });
    } catch (error) {
        console.error(`❌ AutoApply: Error fetching draft ${draftId}:`, error);
        return null;
    }
}

/**
 * Wait for form elements to appear (for dynamically loaded forms like Greenhouse)
 */
async function waitForForm(maxWaitMs = 5000) {
    const startTime = Date.now();

    while (Date.now() - startTime < maxWaitMs) {
        // Check for common form indicators
        const hasInputs = document.querySelectorAll('input, select, textarea').length > 0;
        const hasForm = document.querySelector('form') !== null;
        const hasApplyButton = document.querySelector('button[type="submit"], input[type="submit"], *[class*="apply"], *[class*="submit"]') !== null;

        if (hasInputs || hasForm || hasApplyButton) {
            console.log('✅ AutoApply: Form elements detected');
            return true;
        }

        await Utils.sleep(200);
    }

    console.log('⚠️ AutoApply: Form elements not found after waiting, proceeding anyway...');
    return false;
}

/**
 * Auto-trigger fill if URL contains autoapply_id hash
 */
async function autoTriggerFill() {
    const draftId = extractDraftIdFromHash();

    if (!draftId) {
        console.log('AutoApply: No autoapply_id in URL hash - skipping auto-fill');
        return false;
    }

    console.log(`🚀 AutoApply: Auto-trigger detected! Draft ID: ${draftId}`);

    // Wait for form to appear (especially for SPAs like Greenhouse)
    await waitForForm(5000);

    const draft = await fetchDraftById(draftId);
    if (!draft || !draft.form_state) {
        console.error('❌ AutoApply: Draft not found or has no form_state');
        return false;
    }

    // Store form spec and trigger fill
    window.__AUTOAPPLY_FORM__ = draft.form_state;
    const filledCount = await checkAndFill();
    console.log(`✅ AutoApply: Auto-fill completed! Filled ${filledCount} fields`);
    return true;
}

async function checkAndFill() {
    try {
        // Preferred: form spec injected on window
        let formSpec = window.__AUTOAPPLY_FORM__ || window.__AUTOAPPLY_FORM_SPEC__;

        // Fallback: embedded JSON script tag (<script type="application/json" data-autoapply>)
        if (!formSpec) {
            const embedded = document.querySelector('script[type="application/json"][data-autoapply]');
            if (embedded?.textContent) {
                try {
                    formSpec = JSON.parse(embedded.textContent);
                } catch (parseError) {
                    console.warn('AutoApply: Failed to parse embedded form spec', parseError);
                }
            }
        }

        if (!formSpec) {
            console.log('AutoApply: No form spec found on page - skipping fill');
            return 0;
        }

        const filler = new FormFiller();
        const report = await filler.fill(formSpec);
        const summary = report?.getSummary?.();
        const filledCount = summary?.filled ?? 0;

        return filledCount;
    } catch (error) {
        console.error('AutoApply: Error during form fill', error);
        return 0;
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

// Listen for messages from background script or popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('📨 AutoApply: Received message', request.action);

    if (request.action === 'fillForm' && request.data) {
        // Store form spec and trigger fill
        window.__AUTOAPPLY_FORM__ = request.data;
        checkAndFill().then(filledCount => {
            sendResponse({ success: true, filled: filledCount });
        }).catch(error => {
            console.error('AutoApply: Fill error', error);
            sendResponse({ success: false, error: error.message });
        });
        return true; // Will respond asynchronously
    }

    if (request.action === 'ping') {
        sendResponse({ success: true, ready: true });
        return false;
    }
});

// Auto-trigger on page load if URL has autoapply_id
autoTriggerFill().catch(err => {
    console.error('AutoApply: Auto-trigger error', err);
});

// Also check for injected form spec (fallback)
checkAndFill();

// Listen for hash changes (for SPAs) - auto-trigger if autoapply_id appears
window.addEventListener('hashchange', () => {
    autoTriggerFill().catch(err => {
        console.error('AutoApply: Auto-trigger error on hashchange', err);
    });
    // Also check for injected form spec
    checkAndFill();
});

console.log('✅ AutoApply content script loaded and ready');
