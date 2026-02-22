// Destiin CRM Sidebar Customization
// Adds "Request Bookings" menu item to Frappe CRM sidebar

(function() {
    'use strict';

    // Configuration for the custom menu item
    const MENU_ITEM = {
        label: 'Request Bookings',
        route: '/app/request-booking-details'
    };

    // Calendar icon SVG (matches Frappe CRM style)
    const CALENDAR_ICON = `<svg class="h-4 w-4" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
        <line x1="16" y1="2" x2="16" y2="6"></line>
        <line x1="8" y1="2" x2="8" y2="6"></line>
        <line x1="3" y1="10" x2="21" y2="10"></line>
    </svg>`;

    let injected = false;
    let attempts = 0;
    const MAX_ATTEMPTS = 100;

    function init() {
        if (!window.location.pathname.startsWith('/crm')) {
            return;
        }

        // Reset state on navigation
        injected = false;
        attempts = 0;

        // Try to inject
        tryInject();
    }

    function tryInject() {
        if (injected || attempts >= MAX_ATTEMPTS) {
            return;
        }

        attempts++;

        // Check if already injected
        if (document.querySelector('[data-destiin-menu="request-bookings"]')) {
            injected = true;
            return;
        }

        // Find the sidebar navigation - Frappe CRM uses flex flex-col inside nav
        const navElements = document.querySelectorAll('nav.flex.flex-col');

        for (const nav of navElements) {
            // Look for existing SidebarLink items (they have mx-2 my-0.5 classes)
            const existingLinks = nav.querySelectorAll('a[class*="mx-2"]');

            if (existingLinks.length > 0) {
                const lastLink = existingLinks[existingLinks.length - 1];

                // Clone the last link as template
                const newLink = lastLink.cloneNode(true);
                newLink.setAttribute('data-destiin-menu', 'request-bookings');

                // Update href
                newLink.href = MENU_ITEM.route;

                // Remove router-link-active classes if present
                newLink.classList.remove('router-link-active', 'router-link-exact-active');

                // Update the label text
                const spans = newLink.querySelectorAll('span');
                spans.forEach(span => {
                    if (!span.querySelector('svg') && span.textContent.trim()) {
                        span.textContent = MENU_ITEM.label;
                    }
                });

                // Update the icon
                const iconContainer = newLink.querySelector('span.grid, span.flex-shrink-0, [class*="icon"]');
                if (iconContainer) {
                    const svg = iconContainer.querySelector('svg');
                    if (svg) {
                        svg.outerHTML = CALENDAR_ICON;
                    }
                }

                // Add click handler to navigate properly
                newLink.addEventListener('click', function(e) {
                    e.preventDefault();
                    window.location.href = MENU_ITEM.route;
                });

                // Insert after the last link
                lastLink.parentNode.insertBefore(newLink, lastLink.nextSibling);

                injected = true;
                console.log('Destiin: Request Bookings menu item added');
                return;
            }
        }

        // Retry after a delay if not found
        setTimeout(tryInject, 500);
    }

    // Watch for SPA navigation
    function watchNavigation() {
        // Listen for popstate
        window.addEventListener('popstate', function() {
            setTimeout(init, 100);
        });

        // Override history methods
        const originalPushState = history.pushState;
        const originalReplaceState = history.replaceState;

        history.pushState = function() {
            originalPushState.apply(this, arguments);
            setTimeout(init, 100);
        };

        history.replaceState = function() {
            originalReplaceState.apply(this, arguments);
            setTimeout(init, 100);
        };
    }

    // Use MutationObserver to detect DOM changes
    function observeDOM() {
        const observer = new MutationObserver(function(mutations) {
            if (!injected && window.location.pathname.startsWith('/crm')) {
                tryInject();
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    // Start
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            init();
            watchNavigation();
            observeDOM();
        });
    } else {
        init();
        watchNavigation();
        observeDOM();
    }

    // Also try on window load
    window.addEventListener('load', init);

})();
