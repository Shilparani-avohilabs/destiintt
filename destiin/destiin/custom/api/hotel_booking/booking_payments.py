import frappe
from frappe import _


def on_payment_update(doc, method):
    if doc.payment_status != "payment_success":
        return

    doc_before = doc.get_doc_before_save()
    if doc_before and doc_before.payment_status == "payment_success":
        return

    create_sales_invoice(doc)


def create_sales_invoice(doc):
    if not doc.booking_id:
        frappe.log_error(f"Booking Payment {doc.name} has no Booking ID linked.", "Sales Invoice Creation Failed")
        frappe.msgprint(_("No Hotel Booking linked. Sales Invoice not created."), alert=True)
        return

    hotel_booking = frappe.get_doc("Hotel Bookings", doc.booking_id)

    if not hotel_booking.employee:
        frappe.log_error(f"Hotel Booking {hotel_booking.name} has no Employee.", "Sales Invoice Creation Failed")
        frappe.msgprint(_("No Employee on Hotel Booking. Sales Invoice not created."), alert=True)
        return

    customer = frappe.db.get_value("Employee", hotel_booking.employee, "customer")
    if not customer:
        frappe.log_error(f"Employee {hotel_booking.employee} has no linked Customer.", "Sales Invoice Creation Failed")
        frappe.msgprint(_(f"Employee {hotel_booking.employee} has no linked Customer."), alert=True)
        return

    item_code = "Hotel Booking"  # ← your actual Item name
    if not frappe.db.exists("Item", item_code):
        frappe.throw(_(f"Item '{item_code}' not found in Item master."))

    try:
        rate = float(hotel_booking.total_amount or 0)
    except (ValueError, TypeError):
        rate = 0.0

    nights = 0
    if hotel_booking.check_in and hotel_booking.check_out:
        nights = (hotel_booking.check_out - hotel_booking.check_in).days

    guest_name = " ".join(filter(None, [
        hotel_booking.contact_first_name,
        hotel_booking.contact_last_name
    ])) or "N/A"

    si = frappe.new_doc("Sales Invoice")
    si.customer = customer
    si.currency = hotel_booking.currency or doc.currency or "INR"
    si.set_posting_time = 1

    si.append("items", {
        "item_code": item_code,
        "item_name": f"Hotel Booking - {hotel_booking.hotel_name or ''}",
        "qty": hotel_booking.room_count or 1,
        "rate": rate,
        "description": (
            f"Hotel: {hotel_booking.hotel_name or 'N/A'}\n"
            f"Room Type: {hotel_booking.room_type or 'N/A'} | Rooms: {hotel_booking.room_count or 1}\n"
            f"Check-in: {hotel_booking.check_in} | Check-out: {hotel_booking.check_out} ({nights} night(s))\n"
            f"Guest: {guest_name} | Booking Ref: {hotel_booking.booking_id}"
        )
    })

    si.insert(ignore_permissions=True)

    frappe.msgprint(_(f"✅ Sales Invoice <b>{si.name}</b> created as Draft."), alert=True)
    