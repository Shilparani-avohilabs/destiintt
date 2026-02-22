// Sidebar Override for Frappe CRM
// Adds custom menu items to the CRM sidebar

/**
 * Add a custom item to the CRM sidebar
 * @param {Object} item - The menu item configuration
 * @param {string} item.label - Display label for the menu item
 * @param {string} item.icon - Icon name (lucide icons)
 * @param {string} item.route - Route path
 * @param {string} item.doctype - Optional doctype for the link
 */
export function addSidebarItem(item) {
    // Method 1: Try to access the CRM router/store if available
    if (window.__CRM_SIDEBAR_ITEMS__) {
        window.__CRM_SIDEBAR_ITEMS__.push(item);
        return;
    }

    // Method 2: DOM-based injection for fallback
    waitForSidebar(item);
}

/**
 * Wait for sidebar to be rendered and inject the menu item
 */
function waitForSidebar(item) {
    let attempts = 0;
    const maxAttempts = 60; // 30 seconds max wait

    const checkAndInject = () => {
        attempts++;

        // Look for Frappe CRM sidebar container
        const sidebar = document.querySelector(
            '[class*="LeftSidebar"], ' +
            '[class*="left-sidebar"], ' +
            'aside[class*="sidebar"], ' +
            'nav[class*="sidebar"]'
        );

        if (sidebar) {
            injectMenuItem(sidebar, item);
            return true;
        }

        if (attempts < maxAttempts) {
            setTimeout(checkAndInject, 500);
        }

        return false;
    };

    checkAndInject();
}

/**
 * Inject the menu item into the sidebar
 */
function injectMenuItem(sidebar, item) {
    // Check if already injected
    if (document.querySelector(`[data-custom-menu="${item.label}"]`)) {
        return;
    }

    // Find the navigation list
    const navList = sidebar.querySelector('ul, [class*="menu-list"], [class*="nav-list"]');

    if (!navList) {
        console.warn('Destiin: Could not find navigation list in sidebar');
        return;
    }

    // Clone an existing menu item as template
    const existingItem = navList.querySelector('li, [class*="menu-item"], [class*="nav-item"]');

    if (!existingItem) {
        console.warn('Destiin: Could not find existing menu items to use as template');
        return;
    }

    // Create new menu item
    const newItem = existingItem.cloneNode(true);
    newItem.setAttribute('data-custom-menu', item.label);

    // Update the link
    const link = newItem.querySelector('a');
    if (link) {
        link.href = item.route;
        link.removeAttribute('class');
        link.classList.add(...(existingItem.querySelector('a')?.classList || []));

        link.addEventListener('click', (e) => {
            e.preventDefault();
            // Use frappe router if available
            if (window.frappe && window.frappe.router) {
                window.frappe.router.push(item.route);
            } else {
                window.location.href = item.route;
            }
        });
    }

    // Update the label text
    const spans = newItem.querySelectorAll('span');
    spans.forEach(span => {
        if (!span.querySelector('svg') && !span.classList.contains('icon')) {
            span.textContent = item.label;
        }
    });

    // Update or add icon
    const iconContainer = newItem.querySelector('[class*="icon"], svg');
    if (iconContainer) {
        iconContainer.outerHTML = getIconSvg(item.icon);
    }

    // Append to navigation
    navList.appendChild(newItem);

    console.log(`Destiin: Added "${item.label}" to CRM sidebar`);
}

/**
 * Get SVG icon markup
 */
function getIconSvg(iconName) {
    const icons = {
        calendar: `<svg class="h-4 w-4" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
            <line x1="16" y1="2" x2="16" y2="6"></line>
            <line x1="8" y1="2" x2="8" y2="6"></line>
            <line x1="3" y1="10" x2="21" y2="10"></line>
        </svg>`,
        booking: `<svg class="h-4 w-4" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
        </svg>`,
        list: `<svg class="h-4 w-4" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="8" y1="6" x2="21" y2="6"></line>
            <line x1="8" y1="12" x2="21" y2="12"></line>
            <line x1="8" y1="18" x2="21" y2="18"></line>
            <line x1="3" y1="6" x2="3.01" y2="6"></line>
            <line x1="3" y1="12" x2="3.01" y2="12"></line>
            <line x1="3" y1="18" x2="3.01" y2="18"></line>
        </svg>`
    };

    return icons[iconName] || icons.list;
}

// Export for external use
if (typeof window !== 'undefined') {
    window.DestiinSidebarOverride = { addSidebarItem };
}
