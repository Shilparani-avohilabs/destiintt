// Destiin CRM Override - Sidebar Customization
// This module adds the Request Bookings menu item to Frappe CRM sidebar

import { addSidebarItem } from './sidebarOverride.js';

// Initialize sidebar customization when the CRM app loads
if (typeof window !== 'undefined') {
    // Wait for the CRM app to initialize
    const initSidebar = () => {
        addSidebarItem({
            label: 'Request Bookings',
            icon: 'calendar',
            route: '/crm/request-bookings',
            doctype: 'Request Booking Details'
        });
    };

    if (document.readyState === 'complete') {
        initSidebar();
    } else {
        window.addEventListener('load', initSidebar);
    }
}

export { addSidebarItem };
