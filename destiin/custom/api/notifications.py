import frappe

def on_new_booking_request(doc, method):
    frappe.publish_realtime(
        event="new_booking_request",
        message={
            "name": doc.name,
            "customer": doc.get("customer_name") or "",
            "hotel": doc.get("hotel_name") or "",
            "status": doc.get("status") or "New",
            "message": f"New booking request {doc.name} received"
        },
        room="all"
    )