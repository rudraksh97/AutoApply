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
        GOOD_MATCH: 0.8,          // Stop searching if we find this
        MIN_ACCEPTABLE_MATCH: 0.3, // Minimum score to accept
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
        
        // React Select
        '[class*="select__option"]',
        '[class*="SelectOption"]',
        
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
        
        // Label validation
        const labelValidation = this.validateLabel(element, fieldSpec);
        if (!labelValidation.valid) {
            issues.push(labelValidation.issue);
            confidence -= 0.2;
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
            return { valid: false, issue: `Expected tag ${expected.join('/')} but found ${tagName}` };
        }
        
        return { valid: true };
    }
    
    static validateInputType(element, fieldSpec) {
        const elType = (element.type || '').toLowerCase();
        const fieldType = (fieldSpec.field_type || '').toLowerCase();
        
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
        
        // 4. Placeholder
        if (element.placeholder) return element.placeholder;
        
        // 5. Name attribute
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
     * Works for both native <select> and custom dropdown components
     */
    static isDropdown(element) {
        if (!element) return false;
        
        const tagName = element.tagName.toLowerCase();
        
        // Native select
        if (tagName === 'select') return true;
        
        // ARIA attributes (most reliable for custom dropdowns)
        if (this.hasDropdownARIA(element)) return true;
        
        // Class name patterns
        if (this.hasDropdownClass(element)) return true;
        
        // Data attributes
        if (this.hasDropdownDataAttr(element)) return true;
        
        // Visual indicators (arrow icons)
        if (this.hasDropdownIndicator(element)) return true;
        
        // Parent/wrapper check
        if (this.parentIsDropdown(element)) return true;
        
        return false;
    }
    
    static hasDropdownARIA(element) {
        const role = element.getAttribute('role');
        const ariaHasPopup = element.getAttribute('aria-haspopup');
        const ariaExpanded = element.getAttribute('aria-expanded');
        const ariaAutocomplete = element.getAttribute('aria-autocomplete');
        
        return (
            role === 'combobox' ||
            role === 'listbox' ||
            ariaHasPopup === 'listbox' ||
            ariaHasPopup === 'menu' ||
            ariaHasPopup === 'true' ||
            ariaExpanded !== null ||
            ariaAutocomplete === 'list' ||
            ariaAutocomplete === 'both'
        );
    }
    
    static hasDropdownClass(element) {
        const className = (element.className || '').toLowerCase();
        return CONFIG.DROPDOWN_CLASS_PATTERNS.some(pattern => className.includes(pattern));
    }
    
    static hasDropdownDataAttr(element) {
        const dataRole = element.dataset?.role || element.dataset?.type || '';
        return dataRole.includes('select') || dataRole.includes('dropdown') || dataRole.includes('combobox');
    }
    
    static hasDropdownIndicator(element) {
        const selector = CONFIG.DROPDOWN_INDICATORS.join(', ');
        return element.querySelector(selector) !== null;
    }
    
    static parentIsDropdown(element) {
        const parent = element.parentElement;
        if (!parent) return false;
        
        const parentClass = (parent.className || '').toLowerCase();
        const parentRole = parent.getAttribute('role');
        
        return (
            parentRole === 'combobox' ||
            parentClass.includes('select') ||
            parentClass.includes('dropdown')
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
            
            // Early exit for excellent matches
            if (bestScore >= CONFIG.THRESHOLDS.GOOD_MATCH) {
                console.log(`✅ Found good match "${optText}" = ${(bestScore * 100).toFixed(1)}% (stopped early)`);
                break;
            }
        }
        
        return { match: bestMatch, score: bestScore };
    }
    
    /**
     * Calculate match score between option text and target value
     */
    static calculateMatchScore(optText, targetValue) {
        // Exact match
        if (optText === targetValue) return 1.0;
        
        // Substring matches
        if (optText.includes(targetValue)) {
            return 0.85 + (0.1 * targetValue.length / optText.length);
        }
        if (targetValue.includes(optText)) {
            return 0.8 + (0.1 * optText.length / targetValue.length);
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
        
        switch (type) {
            case 'checkbox':
                const shouldBeChecked = ['true', '1', 'yes', 'on'].includes(intended);
                return element.checked === shouldBeChecked;
                
            case 'radio':
                return element.checked && (
                    element.value?.toLowerCase() === intended ||
                    this.getRadioLabel(element).toLowerCase().includes(intended)
                );
                
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
        element.focus();
        EventDispatcher.dispatchInputEvents(element, ['focus']);
        await Utils.sleep(50);
        
        // Clear existing value
        EventDispatcher.setNativeValue(element, '');
        EventDispatcher.dispatchInputEvents(element, ['input']);
        
        // Type with animation (chunked for performance)
        const text = String(value);
        const chunkSize = text.length > 200 ? 10 : text.length > 50 ? 3 : 1;
        const delayMs = text.length > 200 ? 15 : text.length > 50 ? 20 : CONFIG.TIMING.TYPING_DELAY_PER_CHAR;
        
        for (let i = 0; i <= text.length; i += chunkSize) {
            const partial = text.substring(0, Math.min(i + chunkSize, text.length));
            EventDispatcher.setNativeValue(element, partial);
            EventDispatcher.dispatchInputEvents(element, ['input']);
            
            if (i + chunkSize < text.length) {
                await Utils.sleep(delayMs);
            }
        }
        
        // Ensure final value
        EventDispatcher.setNativeValue(element, text);
        EventDispatcher.dispatchInputEvents(element, ['input', 'change', 'blur']);
        element.blur();
        
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
            
            element.focus();
            EventDispatcher.setNativeValue(element, match.value);
            EventDispatcher.dispatchInputEvents(element, ['input', 'change', 'blur']);
            element.blur();
            
            return true;
        }
        
        report.recordMismatch(field, value, `No matching option. Available: ${domOptions.map(o => o.text).join(', ')}`);
        return false;
    }
    
    // -------------------------------------------------------------------------
    // Custom Dropdown (React Select, Material UI, etc.)
    // -------------------------------------------------------------------------
    
    static async fillCustomDropdown(element, value, report, field) {
        // Step 1: Open the dropdown
        const opened = await this._openDropdown(element);
        if (!opened) {
            report.recordMismatch(field, value, 'Could not open dropdown');
            return false;
        }
        
        // Step 2: Find options in DOM
        let options = await this._findDropdownOptions();
        
        // Step 3: If no options, try searchable dropdown
        if (options.length === 0) {
            options = await this._trySearchableDropdown(element, value);
            if (options.length > 0) {
                // For searchable, first option after typing is usually correct
                EventDispatcher.dispatchClick(options[0]);
                await Utils.sleep(100);
                return true;
            }
            
            this._closeDropdown();
            report.recordMismatch(field, value, 'Could not find dropdown options');
            return false;
        }
        
        // Step 4: Find best matching option
        const { match, score } = OptionMatcher.findBestMatch(
            options,
            value,
            option => option.textContent
        );
        
        if (match && OptionMatcher.isAcceptableMatch(score)) {
            console.log(`✅ Selected: "${Utils.normalizeText(match.textContent)}" (${(score * 100).toFixed(1)}%)`);
            
            match.scrollIntoView({ block: 'nearest' });
            await Utils.sleep(50);
            EventDispatcher.dispatchClick(match);
            await Utils.sleep(100);
            
            return true;
        }
        
        this._closeDropdown();
        report.recordMismatch(field, value, `No matching option. Available: ${options.slice(0, 5).map(o => o.textContent?.trim()).join(', ')}`);
        return false;
    }
    
    static async _openDropdown(element) {
        // Find clickable target (could be arrow icon, button, etc.)
        const clickTarget = element.querySelector(
            '[role="combobox"], [role="button"], button, [class*="indicator"], [class*="arrow"]'
        ) || element;
        
        // Focus then click
        element.focus();
        await Utils.sleep(50);
        EventDispatcher.dispatchClick(clickTarget);
        await Utils.sleep(CONFIG.TIMING.DROPDOWN_OPEN_DELAY);
        
        // Retry with keyboard if needed
        let options = this._queryOptions();
        if (options.length === 0) {
            EventDispatcher.dispatchKeydown(element, 'ArrowDown');
            await Utils.sleep(CONFIG.TIMING.RETRY_DELAY);
            
            options = this._queryOptions();
            if (options.length === 0) {
                EventDispatcher.dispatchKeydown(element, ' ');
                await Utils.sleep(CONFIG.TIMING.RETRY_DELAY);
            }
        }
        
        return this._queryOptions().length > 0 || true; // Continue anyway
    }
    
    static async _findDropdownOptions() {
        return this._queryOptions();
    }
    
    static _queryOptions() {
        for (const selector of CONFIG.DROPDOWN_OPTION_SELECTORS) {
            const options = Array.from(document.querySelectorAll(selector));
            if (options.length > 0) return options;
        }
        return [];
    }
    
    static async _trySearchableDropdown(element, value) {
        const input = element.querySelector('input') || 
                     (element.tagName === 'INPUT' ? element : null);
        
        if (!input) return [];
        
        input.focus();
        EventDispatcher.setNativeValue(input, value);
        EventDispatcher.dispatchInputEvents(input, ['input']);
        await Utils.sleep(300);
        
        return this._queryOptions();
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
            EventDispatcher.dispatchClick(element);
            await Utils.sleep(50);
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
                EventDispatcher.dispatchClick(radio);
                await Utils.sleep(50);
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
        
        // Resolve element
        const xpaths = Array.isArray(field.xpaths) ? field.xpaths : [field.xpath];
        const { element } = XPathResolver.resolveWithFallback(xpaths);
        
        if (!element) {
            this.report.recordSkipped(field, 'Element not found via XPath');
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
        
        // Auto-detect dropdown (overrides backend field_type if needed)
        const isDropdown = DropdownDetector.isDropdown(element);
        const shouldUseDropdownFiller = isDropdown && 
            !['checkbox', 'radio', 'file'].includes(fieldType);
        
        if (shouldUseDropdownFiller && fieldType !== 'select') {
            console.log(`🔄 Auto-detected dropdown for "${field.label}" (was: ${fieldType})`);
        }
        
        // Route to appropriate filler
        if (shouldUseDropdownFiller || fieldType === 'select') {
            return tagName === 'select'
                ? FieldFillers.fillSelect(element, field.value, this.report, field)
                : FieldFillers.fillCustomDropdown(element, field.value, this.report, field);
        }
        
        switch (fieldType) {
            case 'checkbox':
                return FieldFillers.fillCheckbox(element, field.value, this.report, field);
            case 'radio':
                return FieldFillers.fillRadio(element, field.value, this.report, field);
            case 'file':
                return FieldFillers.handleFile(element, field.value, this.report, field);
            default:
                return tagName === 'select'
                    ? FieldFillers.fillSelect(element, field.value, this.report, field)
                    : FieldFillers.fillText(element, field.value, this.report, field);
        }
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

// Auto-fill from URL hash
function checkAndFill() {
    const hash = window.location.hash;
    if (!hash?.startsWith('#autoapply_id=')) return;
    
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
        await Utils.sleep(1000);
        
        // Execute fill
        const filler = new FormFiller();
        await filler.fill(draft.form_state);
    });
}

// Initialize
checkAndFill();
window.addEventListener('hashchange', checkAndFill);
