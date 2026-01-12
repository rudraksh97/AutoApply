"""
Remote browser controller using Chrome DevTools Protocol (CDP).

This allows the Docker container to control the user's local Chrome browser,
enabling form filling that the user can actually see and interact with.

Usage:
1. User starts Chrome with: chrome --remote-debugging-port=9222
2. Docker connects via CDP to fill forms
3. User sees the form being filled in their own browser
"""

import asyncio
import json
import aiohttp
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


@dataclass
class CDPTarget:
    """Represents a Chrome page/tab."""
    id: str
    title: str
    url: str
    websocket_url: str


class RemoteBrowserController:
    """
    Controls a user's Chrome browser via Chrome DevTools Protocol.
    
    This enables Docker-based automation that the user can actually see,
    by connecting to their locally-running Chrome instance.
    """
    
    def __init__(self, host: str = "host.docker.internal", port: int = 9222):
        """
        Initialize the remote browser controller.
        
        Args:
            host: Chrome's host. Use 'host.docker.internal' to connect from Docker to host.
            port: Chrome's remote debugging port (default 9222).
        """
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self._ws = None
        self._message_id = 0
        
    async def is_chrome_available(self) -> bool:
        """Check if Chrome is running with remote debugging enabled."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/json/version", timeout=aiohttp.ClientTimeout(total=2)) as resp:
                    if resp.status == 200:
                        return True
        except Exception:
            pass
        return False
    
    async def get_targets(self) -> List[CDPTarget]:
        """Get list of available browser targets (tabs)."""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/json") as resp:
                targets = await resp.json()
                return [
                    CDPTarget(
                        id=t["id"],
                        title=t.get("title", ""),
                        url=t.get("url", ""),
                        websocket_url=t.get("webSocketDebuggerUrl", "")
                    )
                    for t in targets
                    if t.get("type") == "page"
                ]
    
    async def create_new_tab(self, url: str = "") -> CDPTarget:
        """Create a new browser tab."""
        async with aiohttp.ClientSession() as session:
            endpoint = f"{self.base_url}/json/new"
            if url:
                endpoint += f"?{url}"
            async with session.put(endpoint) as resp:
                target = await resp.json()
                return CDPTarget(
                    id=target["id"],
                    title=target.get("title", ""),
                    url=target.get("url", ""),
                    websocket_url=target.get("webSocketDebuggerUrl", "")
                )
    
    async def navigate(self, target: CDPTarget, url: str) -> bool:
        """Navigate a tab to a URL."""
        result = await self._send_command(target, "Page.navigate", {"url": url})
        return result is not None
    
    async def execute_script(self, target: CDPTarget, script: str) -> Any:
        """Execute JavaScript in the page context."""
        result = await self._send_command(target, "Runtime.evaluate", {
            "expression": script,
            "returnByValue": True,
            "awaitPromise": True
        })
        if result and "result" in result:
            return result["result"].get("value")
        return None
    
    async def fill_form_field_by_xpath(self, target: CDPTarget, xpath: str, value: str, field_type: str = "text") -> bool:
        """Fill a form field by XPath selector."""
        # Escape value for JavaScript
        value_escaped = json.dumps(value)
        
        script = f"""
        (function() {{
            // Get element by XPath
            function getElementByXPath(xpath) {{
                try {{
                    const result = document.evaluate(
                        xpath,
                        document,
                        null,
                        XPathResult.FIRST_ORDERED_NODE_TYPE,
                        null
                    );
                    return result.singleNodeValue;
                }} catch (e) {{
                    return null;
                }}
            }}
            
            const el = getElementByXPath({json.dumps(xpath)});
            if (!el) return {{ success: false, error: 'Element not found by XPath' }};
            
            const elType = el.type || el.tagName.toLowerCase();
            
            try {{
                switch (elType) {{
                    case 'checkbox':
                        const shouldCheck = ['true', '1', 'yes'].includes(String({value_escaped}).toLowerCase());
                        if (el.checked !== shouldCheck) {{
                            el.checked = shouldCheck;
                            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                        return {{ success: true }};
                        
                    case 'radio':
                        // Find the specific radio button in the group
                        const radiogroup = document.querySelectorAll(`[name="${{el.name}}"]`);
                        let radioFound = false;
                        radiogroup.forEach(radio => {{
                            if (radio.value === {value_escaped} || 
                                radio.nextSibling?.textContent?.trim().toLowerCase().includes(String({value_escaped}).toLowerCase())) {{
                                radio.checked = true;
                                radio.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                radioFound = true;
                            }}
                        }});
                        return {{ success: radioFound }};
                        
                    case 'select':
                    case 'select-one':
                    case 'select-multiple':
                        // Find matching option
                        const options = Array.from(el.options);
                        const match = options.find(opt => 
                            opt.value === {value_escaped} || 
                            opt.text.toLowerCase().includes(String({value_escaped}).toLowerCase())
                        );
                        if (match) {{
                            el.value = match.value;
                            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            return {{ success: true }};
                        }}
                        return {{ success: false, error: 'Option not found' }};
                        
                    case 'file':
                        // Cannot programmatically set file inputs for security
                        return {{ success: false, error: 'File input cannot be filled programmatically' }};
                        
                    default:
                        // text, email, phone, tel, textarea, etc.
                        el.focus();
                        el.value = {value_escaped};
                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        el.blur();
                        return {{ success: true }};
                }}
            }} catch (e) {{
                return {{ success: false, error: e.message }};
            }}
        }})();
        """
        result = await self.execute_script(target, script)
        return result and result.get("success", False)
    
    async def fill_form_field(self, target: CDPTarget, selector: str, value: str) -> bool:
        """Fill a form field by CSS selector (legacy support)."""
        value_escaped = json.dumps(value)
        script = f"""
        (function() {{
            const el = document.querySelector({json.dumps(selector)});
            if (!el) return {{ success: false, error: 'Element not found' }};
            
            el.focus();
            el.value = {value_escaped};
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            
            return {{ success: true }};
        }})();
        """
        result = await self.execute_script(target, script)
        return result and result.get("success", False)
    
    async def fill_form_from_state(self, target: CDPTarget, form_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fill all form fields from a FormState object.
        
        Args:
            target: The browser tab to fill
            form_state: FormState dictionary with fields list
            
        Returns:
            Dictionary with success count and any errors
        """
        results = {"filled": 0, "failed": 0, "errors": []}
        
        fields = form_state.get("fields", [])
        import logging
        logging.info(f"Attempting to fill {len(fields)} fields from form state")
        
        for field in fields:
            # Skip fields that are marked as skipped or have no value
            if field.get("skipped", False) or not field.get("value"):
                logging.debug(f"Skipping field: {field.get('label', 'unknown')} - skipped={field.get('skipped')}, has_value={bool(field.get('value'))}")
                continue
            
            xpath = field.get("xpath", "")
            value = field.get("value", "")
            field_type = field.get("field_type", "text")
            label = field.get("label", "")
            
            if not xpath or not value:
                continue
            
            # Primary: Use XPath selector (new approach)
            filled = False
            try:
                if await self.fill_form_field_by_xpath(target, xpath, value, field_type):
                    results["filled"] += 1
                    filled = True
            except Exception as e:
                results["errors"].append(f"XPath error for {label or xpath}: {str(e)}")
            
            # Fallback: Try CSS selectors if xpath fails (backwards compatibility)
            if not filled:
                # Try to extract field_id from xpath or use label for fuzzy matching
                field_id = field.get("field_id", "")
                if field_id:
                    selectors = [
                        f"#{field_id}",
                        f"[name='{field_id}']",
                        f"[id='{field_id}']",
                        f"[data-field='{field_id}']"
                    ]
                    
                    for selector in selectors:
                        try:
                            if await self.fill_form_field(target, selector, value):
                                results["filled"] += 1
                                filled = True
                                break
                        except Exception as e:
                            continue
            
            if not filled:
                results["failed"] += 1
                field_identifier = label or xpath or field_id
                results["errors"].append(f"Could not fill {field_identifier}")
        
        return results
    
    async def _send_command(self, target: CDPTarget, method: str, params: Dict = None) -> Optional[Dict]:
        """Send a CDP command via WebSocket."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(target.websocket_url) as ws:
                    self._message_id += 1
                    message = {
                        "id": self._message_id,
                        "method": method,
                        "params": params or {}
                    }
                    await ws.send_json(message)
                    
                    # Wait for response
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            if data.get("id") == self._message_id:
                                return data.get("result")
        except Exception as e:
            import logging
            logging.error(f"CDP command failed: {e}")
            return None


async def open_and_fill_draft(form_state: Dict[str, Any], job_url: str) -> Dict[str, Any]:
    """
    Open the user's Chrome browser and fill a form with draft data.
    
    This requires Chrome to be running with:
    chrome --remote-debugging-port=9222
    
    Args:
        form_state: The FormState dictionary
        job_url: The job application URL
        
    Returns:
        Dictionary with status and results
    """
    controller = RemoteBrowserController()
    
    # Check if Chrome is available
    if not await controller.is_chrome_available():
        return {
            "success": False,
            "error": "Chrome not available. Start Chrome with: chrome --remote-debugging-port=9222"
        }
    
    try:
        # Create new tab and navigate
        target = await controller.create_new_tab()
        await asyncio.sleep(0.5)
        
        await controller.navigate(target, job_url)
        await asyncio.sleep(3)  # Wait for page to load
        
        # Fill the form
        results = await controller.fill_form_from_state(target, form_state)
        
        return {
            "success": True,
            "fields_filled": results["filled"],
            "fields_failed": results["failed"],
            "errors": results["errors"]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
