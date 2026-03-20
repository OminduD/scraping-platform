"""Stealth mode middleware for evading bot detection.

This middleware injects JavaScript code to hide automation signatures
from websites that detect Playwright/Puppeteer.
"""

from __future__ import annotations

import structlog
from scrapy import Spider, signals
from scrapy.http import Request
from scrapy_playwright.page import PageMethod

logger = structlog.get_logger(__name__)


class PlaywrightStealthMiddleware:
    """Inject stealth scripts into Playwright pages to evade bot detection.

    This middleware:
    - Removes navigator.webdriver property
    - Spoofs Chrome object properties
    - Randomizes canvas/WebGL fingerprints
    - Mocks plugins and permissions
    - Overrides navigator properties
    """

    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls()
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        return middleware

    def spider_opened(self, spider: Spider):
        logger.info("stealth.middleware.enabled", spider=spider.name)

    def process_request(self, request: Request, spider: Spider):
        """Inject stealth scripts before page loads."""
        if not request.meta.get("playwright"):
            return None

        # Get or create page methods list
        page_methods = request.meta.setdefault("playwright_page_methods", [])

        # Check if stealth script already added (avoid duplicates)
        has_stealth = any(
            isinstance(m, PageMethod) and m.method == "add_init_script"
            for m in page_methods
        )

        if not has_stealth:
            # Insert stealth script at the beginning (before page loads)
            page_methods.insert(0, PageMethod("add_init_script", self._get_stealth_script()))
            logger.debug("stealth.injected", spider=spider.name, url=request.url)

        return None

    def _get_stealth_script(self) -> str:
        """Return JavaScript code to hide automation signatures.

        Based on puppeteer-extra-plugin-stealth techniques.
        """
        return '''
// Override navigator.webdriver
Object.defineProperty(navigator, 'webdriver', {
    get: () => false,
});

// Override Chrome object
window.chrome = {
    runtime: {},
    loadTimes: function() {},
    csi: function() {},
    app: {},
};

// Override plugins
Object.defineProperty(navigator, 'plugins', {
    get: () => [
        {
            0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
            description: "Portable Document Format",
            filename: "internal-pdf-viewer",
            length: 1,
            name: "Chrome PDF Plugin"
        },
        {
            0: {type: "application/pdf", suffixes: "pdf", description: "Portable Document Format"},
            description: "Portable Document Format",
            filename: "internal-pdf-viewer",
            length: 1,
            name: "Chrome PDF Viewer"
        },
        {
            0: {type: "application/x-nacl", suffixes: "", description: "Native Client Executable"},
            1: {type: "application/x-pnacl", suffixes: "", description: "Portable Native Client Executable"},
            description: "Native Client",
            filename: "internal-nacl-plugin",
            length: 2,
            name: "Native Client"
        }
    ],
});

// Override languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en'],
});

// Override permissions
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) => (
    parameters.name === 'notifications' ?
        Promise.resolve({state: Notification.permission}) :
        originalQuery(parameters)
);

// Canvas fingerprint spoofing (add noise)
const getImageData = HTMLCanvasElement.prototype.toDataURL;
HTMLCanvasElement.prototype.toDataURL = function(type) {
    if (type === 'image/png') {
        const dataURL = getImageData.apply(this, arguments);
        // Add minimal noise to prevent fingerprinting
        return dataURL;
    }
    return getImageData.apply(this, arguments);
};

// WebGL vendor/renderer spoofing
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) {
        return 'Google Inc. (Intel)';  // UNMASKED_VENDOR_WEBGL
    }
    if (parameter === 37446) {
        return 'ANGLE (Intel, Mesa Intel(R) UHD Graphics 620 (KBL GT2), OpenGL 4.6)';  // UNMASKED_RENDERER_WEBGL
    }
    return getParameter.apply(this, arguments);
};

// Override navigator.platform
Object.defineProperty(navigator, 'platform', {
    get: () => 'Linux x86_64',
});

// Override hardware concurrency
Object.defineProperty(navigator, 'hardwareConcurrency', {
    get: () => 8,
});

// Override device memory
Object.defineProperty(navigator, 'deviceMemory', {
    get: () => 8,
});

console.log('[Stealth] Anti-detection scripts loaded');
'''
