// Destiin CRM Sidebar Customization
// Adds "Request Bookings" menu item to Frappe CRM sidebar

(function() {
    'use strict';

    // Configuration for the custom menu item
    const CUSTOM_MENU_ITEMS = [
        {
            label: 'Request Bookings',
            icon: 'calendar',
            route: '/app/request-booking-details',
            crmRoute: '/crm/request-bookings',
            doctype: 'Request Booking Details'
        }
    ];

    // SVG icons
    const ICONS = {
        calendar: '<svg class="h-4 w-4" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>',
        booking: '<svg class="h-4 w-4" xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path></svg>'
    };

    // Track injection state
    let injected = false;
    let observer = null;

    /**
     * Main initialization function
     */
    function init() {
        // Check if we're in the CRM app
        if (window.location.pathname.startsWith('/crm')) {
            startSidebarWatch();
        }

        // Watch for route changes (SPA navigation)
        watchRouteChanges();
    }

    /**
     * Watch for route changes in SPA
     */
    function watchRouteChanges() {
        // Listen to popstate for browser back/forward
        window.addEventListener('popstate', function() {
            if (window.location.pathname.startsWith('/crm')) {
                injected = false;
                startSidebarWatch();
            }
        });

        // Override pushState and replaceState
        const originalPushState = history.pushState;
        const originalReplaceState = history.replaceState;

        history.pushState = function() {
            originalPushState.apply(this, arguments);
            if (window.location.pathname.startsWith('/crm')) {
                injected = false;
                setTimeout(startSidebarWatch, 100);
            }
        };

        history.replaceState = function() {
            originalReplaceState.apply(this, arguments);
            if (window.location.pathname.startsWith('/crm')) {
                injected = false;
                setTimeout(startSidebarWatch, 100);
            }
        };
    }

    /**
     * Start watching for the sidebar to appear
     */
    function startSidebarWatch() {
        // Stop any existing observer
        if (observer) {
            observer.disconnect();
        }

        // Create a MutationObserver to watch for the sidebar
        observer = new MutationObserver(function(mutations) {
            if (!injected) {
                attemptInjection();
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        // Also try immediately
        attemptInjection();

        // Fallback: try periodically for 30 seconds
        let attempts = 0;
        const interval = setInterval(function() {
            attempts++;
            if (injected || attempts > 60) {
                clearInterval(interval);
                return;
            }
            attemptInjection();
        }, 500);
    }

    /**
     * Attempt to inject the menu items
     */
    function attemptInjection() {
        // Look for Frappe CRM sidebar - it uses different class patterns
        const sidebarSelectors = [
            // Frappe CRM specific selectors
            'aside.w-56',
            'aside[class*="sidebar"]',
            '[class*="LeftSidebar"]',
            'nav[class*="sidebar"]',
            '.layout-side-section',
            // Generic sidebar patterns
            'aside nav',
            'aside ul'
        ];

        let sidebar = null;
        for (const selector of sidebarSelectors) {
            sidebar = document.querySelector(selector);
            if (sidebar) break;
        }

        if (!sidebar) {
            return false;
        }

        // Check if already injected
        if (document.querySelector('[data-destiin-menu]')) {
            injected = true;
            return true;
        }

        // Find the menu list
        const menuList = findMenuList(sidebar);
        if (!menuList) {
            return false;
        }

        // Inject each custom menu item
        CUSTOM_MENU_ITEMS.forEach(item => {
            injectMenuItem(menuList, item);
        });

        injected = true;
        console.log('Destiin: Custom menu items added to CRM sidebar');
        return true;
    }

    /**
     * Find the menu list container
     */
    function findMenuList(sidebar) {
        // Try different patterns
        const listSelectors = [
            'ul',
            '[class*="menu"]',
            '[class*="nav-list"]',
            'nav > div'
        ];

        for (const selector of listSelectors) {
            const list = sidebar.querySelector(selector);
            if (list && list.children.length > 0) {
                return list;
            }
        }

        return null;
    }

    /**
     * Inject a single menu item
     */
    function injectMenuItem(menuList, item) {
        // Find an existing menu item to use as template
        const existingItem = menuList.querySelector('li, a[class*="flex"], div[class*="flex"]');

        if (!existingItem) {
            // Create a new menu item from scratch
            createMenuItemFromScratch(menuList, item);
            return;
        }

        // Clone the existing item
        const newItem = existingItem.cloneNode(true);
        newItem.setAttribute('data-destiin-menu', item.label);

        // Remove any active/selected classes
        newItem.classList.remove('active', 'selected', 'bg-gray-100', 'bg-white');

        // Update the link/button
        const clickable = newItem.tagName === 'A' ? newItem : newItem.querySelector('a, button');
        if (clickable) {
            if (clickable.tagName === 'A') {
                clickable.href = item.route;
            }
            clickable.onclick = function(e) {
                e.preventDefault();
                e.stopPropagation();
                // Navigate to the doctype list
                window.location.href = item.route;
            };
        }

        // Update text content
        const textNodes = newItem.querySelectorAll('span, p, div');
        textNodes.forEach(node => {
            // Skip icon containers
            if (node.querySelector('svg') || node.classList.contains('icon')) {
                return;
            }
            // Update text that looks like a label
            if (node.textContent.trim().length > 0 && node.textContent.trim().length < 50) {
                node.textContent = item.label;
            }
        });

        // Update icon
        const iconContainer = newItem.querySelector('svg, [class*="icon"]');
        if (iconContainer) {
            const icon = ICONS[item.icon] || ICONS.calendar;
            if (iconContainer.tagName === 'SVG') {
                iconContainer.outerHTML = icon;
            } else {
                iconContainer.innerHTML = icon;
            }
        }

        // Append to menu list
        menuList.appendChild(newItem);
    }

    /**
     * Create menu item from scratch if no template available
     */
    function createMenuItemFromScratch(menuList, item) {
        const li = document.createElement('li');
        li.setAttribute('data-destiin-menu', item.label);
        li.className = 'group flex items-center gap-2 px-3 py-2 text-sm cursor-pointer rounded-md hover:bg-gray-100';

        const link = document.createElement('a');
        link.href = item.route;
        link.className = 'flex items-center gap-2 w-full text-gray-700 hover:text-gray-900';
        link.onclick = function(e) {
            e.preventDefault();
            window.location.href = item.route;
        };

        // Add icon
        const iconSpan = document.createElement('span');
        iconSpan.className = 'flex-shrink-0';
        iconSpan.innerHTML = ICONS[item.icon] || ICONS.calendar;
        link.appendChild(iconSpan);

        // Add label
        const labelSpan = document.createElement('span');
        labelSpan.textContent = item.label;
        link.appendChild(labelSpan);

        li.appendChild(link);
        menuList.appendChild(li);
    }

    // Initialize when ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Also run on window load as backup
    window.addEventListener('load', init);

})();
