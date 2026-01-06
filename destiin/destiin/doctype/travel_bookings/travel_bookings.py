# Copyright (c) 2025, shilpa@avohilabs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TravelBookings(Document):
    pass


def get_status_code(status):
    """Convert booking status to status code"""
    status_map = {
        "Pending": 0,
        "Success": 1,
        "Confirmed": 1,
        "Failure": 2,
        "Cancelled": 2
    }
    return status_map.get(status, 0)


def format_booking(booking):
    """Format booking data to match API response structure"""
    return {
        "booking_id": booking.get("booking_id"),
        "user_name": booking.get("employee_name"),
        "hotel_name": booking.get("hotel_name"),
        "check_in": str(booking.get("check_in_date")) if booking.get("check_in_date") else None,
        "check_out": str(booking.get("check_out_date")) if booking.get("check_out_date") else None,
        "amount": booking.get("total_price"),
        "status": booking.get("booking_status").lower() if booking.get("booking_status") else None,
        "status_code": get_status_code(booking.get("booking_status")),
        "rooms_count": 1,
        "guests_count": booking.get("guest_count"),
        "child_count": 0,
        "supplier": booking.get("supplier"),
        "company": {
            "id": booking.get("company"),
            "name": booking.get("company")
        },
        "employee": {
            "id": booking.get("employee_id"),
            "name": booking.get("employee_name")
        }
    }


@frappe.whitelist(allow_guest=False)
def get_all_bookings():
    """Fetch all travel bookings"""
    try:
        bookings = frappe.get_all(
            "Travel Bookings",
            fields=[
                "name",
                "employee_id",
                "employee_name",
                "booking_id",
                "hotel_name",
                "check_in_date",
                "check_out_date",
                "booking_status",
                "guest_count",
                "supplier",
                "company",
                "total_price"
            ],
            order_by="check_in_date desc"
        )

        formatted_bookings = [format_booking(b) for b in bookings]

        return {
            "success": True,
            "data": formatted_bookings
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "get_all_bookings API Error")
        return {"success": False, "error": str(e)}


@frappe.whitelist(allow_guest=False)
def get_cancelled_bookings():
    """Fetch all cancelled travel bookings"""
    try:
        bookings = frappe.get_all(
            "Travel Bookings",
            filters={"booking_status": ["in", ["Cancelled", "Failure"]]},
            fields=[
                "name",
                "employee_id",
                "employee_name",
                "booking_id",
                "hotel_name",
                "check_in_date",
                "check_out_date",
                "booking_status",
                "guest_count",
                "supplier",
                "company",
                "total_price"
            ],
            order_by="check_in_date desc"
        )

        formatted_bookings = []
        for b in bookings:
            formatted = format_booking(b)
            formatted["cancelled_reason"] = "Cancelled by user"
            formatted_bookings.append(formatted)

        return {
            "success": True,
            "data": formatted_bookings
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "get_cancelled_bookings API Error")
        return {"success": False, "error": str(e)}


@frappe.whitelist(allow_guest=False)
def create_booking():
    """Create a new booking"""
    import json
    try:
        # Handle both raw JSON and x-www-form-urlencoded inputs
        if frappe.form_dict.get("data"):
            data = json.loads(frappe.form_dict.data)
        elif frappe.request.data:
            data = json.loads(frappe.request.data)
        else:
            frappe.throw("Missing request body")
        # data = json.loads(data) if isinstance(data, str) else data
        doc = frappe.get_doc({
            "doctype": "Travel Bookings",
            **data
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        return {
            "success": True,
            "message": "Booking created successfully",
            "name": doc.name
        }
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "create_booking API Error")
        return {"success": False, "error": str(e)}
    



@frappe.whitelist(allow_guest=False)
def update_booking():
    """Update an existing booking based on employee_id"""
    import json
    try:
        # Handle both raw JSON and x-www-form-urlencoded inputs
        if frappe.form_dict.get("data"):
            data = json.loads(frappe.form_dict.data)
        elif frappe.request.data:
            data = json.loads(frappe.request.data)
        else:
            frappe.throw("Missing request body")

        # Extract employee_id
        employee_id = data.get("employee_id")
        if not employee_id:
            frappe.throw("Employee ID is required")

        # Find booking by employee_id
        booking_name = frappe.db.get_value("Travel Bookings", {"employee_id": employee_id}, "name")
        if not booking_name:
            return {"success": False, "message": f"No booking found for Employee ID: {employee_id}"}

        # Load and update the booking
        doc = frappe.get_doc("Travel Bookings", booking_name)
        doc.update(data)
        doc.save(ignore_permissions=True)
        frappe.db.commit()

        return {
            "success": True,
            "message": f"Booking for Employee ID {employee_id} updated successfully",
            "name": doc.name
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "update_booking API Error")
        return {"success": False, "error": str(e)}


