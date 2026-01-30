// Copyright (c) 2026, Destiin and contributors
// For license information, please see license.txt

frappe.ui.form.on("Cancel Booking", {
    refresh(frm) {
        // Add custom buttons or actions if needed
        if (frm.doc.hotel_booking && !frm.is_new()) {
            frm.add_custom_button(__("View Hotel Booking"), function() {
                frappe.set_route("Form", "Hotel Bookings", frm.doc.hotel_booking);
            });
        }
    },

    status(frm) {
        // Show warning when status is changed to Approved or Processed
        if (frm.doc.status === "Approved" || frm.doc.status === "Processed") {
            frappe.msgprint({
                title: __("Status Update"),
                indicator: "orange",
                message: __("The linked Hotel Booking will be marked as 'cancelled' when you save this document.")
            });
        }
    }
});
