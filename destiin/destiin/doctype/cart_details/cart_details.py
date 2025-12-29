# Copyright (c) 2025, shilpa@avohilabs.com and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class CartDetails(Document):
	pass

import frappe

@frappe.whitelist(allow_guest=True)
def store_cart_details(data):
    if isinstance(data, str):
        data = frappe.parse_json(data)

    doc = frappe.get_doc({
        "doctype": "Cart Details",
        "employee_id": data.get("employee_id"),
        "employee_name": data.get("employee_name"),
        "company": data.get("company"),
        "booking_id": data.get("booking_id"),
        "check_in_date": data.get("check_in_date"),
        "check_out_date": data.get("check_out_date"),
        "booking_status": data.get("booking_status", "Pending"),
        "guest_count": data.get("guest_count"),
        "cart_items": data.get("cart_items", [])
    })

    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "success": True,
        "cart_id": doc.name
    }

@frappe.whitelist(allow_guest=True)
def fetch_cart_details(employee_id=None):

    filters = {}
    if employee_id:
        filters["employee_id"] = employee_id

    carts = frappe.get_all(
        "Cart Details",
        filters=filters,
        fields=[
            "name",
            "booking_id",
            "employee_id",
            "employee_name",
            "company",
            "check_in_date",
            "check_out_date",
            "booking_status",
            "guest_count"
        ],
        order_by="creation desc"
    )

    data = []

    for cart in carts:
        cart_doc = frappe.get_doc("Cart Details", cart.name)

        for item in cart_doc.cart_items:
            data.append({
                "booking_id": cart.booking_id,
                "user_name": cart.employee_name,
                "hotel_name": item.hotel_name,
                "check_in": cart.check_in_date,
                "check_out": cart.check_out_date,
                "amount": 0,              # placeholder
                "status": cart.booking_status.lower(),
                "status_code": 0,
                "rooms_count": 1,
                "guests_count": int(cart.guest_count or 0),
                "child_count": 0,
                "supplier": item.supplier,
                "company": {
                    "id": cart.company,
                    "name": cart.company
                },
                "employee": {
                    "id": cart.employee_id,
                    "name": cart.employee_name
                }
            })

    frappe.response["response"] = {
        "success": True,
        "data": data
    }


@frappe.whitelist(allow_guest=True)
def remove_cart(employee_id):
    if not employee_id:
        return {
            "status": "error",
            "message": "employee_id is required"
        }

    cart_names = frappe.get_all(
        "Cart Details",
        filters={"employee_id": employee_id},
        pluck="name"
    )

    if not cart_names:
        return {
            "status": "error",
            "message": "No cart found for this employee"
        }

    for name in cart_names:
        frappe.delete_doc(
            "Cart Details",
            name,
            ignore_permissions=True
        )

    frappe.db.commit()

    return {
        "status": "success",
        "message": f"{len(cart_names)} cart item(s) removed"
    }