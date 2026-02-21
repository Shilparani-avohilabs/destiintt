# Copyright (c) 2026, Destiin and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CancelBooking(Document):
    def validate(self):
        self.update_hotel_booking_status()

    def update_hotel_booking_status(self):
        """Update the Hotel Booking status based on Cancel Booking status"""
        if not self.hotel_booking:
            return

        hotel_booking = frappe.get_doc("Hotel Bookings", self.hotel_booking)

        # Update booking status based on cancellation status
        if self.status == "Approved" or self.status == "Processed":
            if hotel_booking.booking_status != "cancelled":
                hotel_booking.booking_status = "cancelled"
                hotel_booking.save(ignore_permissions=True)
                frappe.msgprint(
                    f"Hotel Booking {self.hotel_booking} status updated to 'cancelled'",
                    alert=True
                )

    def on_update(self):
        """Called after the document is saved"""
        self.update_hotel_booking_status()
