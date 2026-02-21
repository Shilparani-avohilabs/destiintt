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
            "guest_count",
            "child_count",
            "room_count",
            "destination"
        ],
        order_by="creation desc"
    )

    # Status mapping for status_code
    status_code_map = {
        "pending": 0,
        "viewed": 1,
        "requested": 2,
        "approved": 3,
        "success": 4,
        "failure": 5
    }

    data = []

    for cart in carts:
        cart_doc = frappe.get_doc("Cart Details", cart.name)

        # Calculate total amount from all cart items
        total_amount = sum(float(item.price or 0) for item in cart_doc.cart_items)

        # Get rooms count from cart items or room_count field
        rooms_count = len(cart_doc.cart_items) if cart_doc.cart_items else int(cart.room_count or 1)

        # Get status and status_code
        status = (cart.booking_status or "pending").lower()
        status_code = status_code_map.get(status, 0)

        # Build hotels array with their rooms
        hotels = []
        hotel_map = {}  # To group rooms by hotel

        for item in cart_doc.cart_items:
            hotel_name = item.hotel_name or ""
            if hotel_name not in hotel_map:
                hotel_map[hotel_name] = {
                    "hotel_name": hotel_name,
                    "supplier": item.supplier or "",
                    "rooms": []
                    
                }

            hotel_map[hotel_name]["rooms"].append({
                "room_type": item.room_type or "",
                "price": float(item.price or 0),
                "room_count": int(item.room_count or 1) if hasattr(item, 'room_count') else 1,
                "meal_plan": item.meal_plan or "" if hasattr(item, 'meal_plan') else "",
                "cancellation_policy": item.cancellation_policy or "" if hasattr(item, 'cancellation_policy') else ""
            })

        hotels = list(hotel_map.values())

        data.append({
            "booking_id": cart.booking_id,
            "user_name": cart.employee_name,
            "hotels": hotels,
            "destination": cart.destination or "",
            "check_in": str(cart.check_in_date) if cart.check_in_date else "",
            "check_out": str(cart.check_out_date) if cart.check_out_date else "",
            "amount": total_amount,
            "status": status,
            "status_code": status_code,
            "rooms_count": rooms_count,
            "guests_count": int(cart.guest_count or 0),
            "child_count": int(cart.child_count or 0),
            "company": {
                "id": cart.company or "",
                "name": cart.company or ""
            },
            "employee": {
                "id": cart.employee_id or "",
                "name": cart.employee_name or ""
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