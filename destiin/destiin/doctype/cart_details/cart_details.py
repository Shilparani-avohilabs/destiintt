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
        **data
    })

    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "status": "success",
        "name": doc.name
    }


import frappe

@frappe.whitelist(allow_guest=True)
def fetch_cart_details(employee_id=None):
    # If employee_id not passed directly, try to read from request body
    if not employee_id:
        data = frappe.local.form_dict
        employee_id = data.get("employee_id")

    filters = {}

    if employee_id:
        filters["employee_id"] = employee_id

    carts = frappe.get_all(
        "Cart Details",
        filters=filters,
        fields="*",
        order_by="creation desc"
    )

    return {
        "status": "success",
        "count": len(carts),
        "data": carts
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
