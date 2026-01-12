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

    # Valid booking statuses
    valid_statuses = [
        "PENDING_IN_CART",
        "SENT_FOR_APPROVAL",
        "VIEWED",
        "REQUESTED",
        "APPROVED",
        "SUCESS",
        "FAILURE"
    ]

    # Status mapping from input to valid status
    status_map = {
        "pending_in_cart": "PENDING_IN_CART",
        "pending": "PENDING_IN_CART",
        "sent_for_approval": "SENT_FOR_APPROVAL",
        "viewed": "VIEWED",
        "requested": "REQUESTED",
        "approved": "APPROVED",
        "sucess": "SUCESS",
        "success": "SUCESS",
        "failure": "FAILURE"
    }

    # Build cart_items from hotels array
    cart_items = []
    hotels = data.get("hotels", [])

    for hotel in hotels:
        hotel_name = hotel.get("hotel_name", "")
        hotel_id = hotel.get("hotel_id", "")
        supplier = hotel.get("supplier", "")

        for room in hotel.get("rooms", []):
            cart_items.append({
                "hotel_name": hotel_name,
                "hotel_id": hotel_id,
                "supplier": supplier,
                "room_type": room.get("room_type", ""),
                "room_id": room.get("room_id", ""),
                "price": room.get("price", 0),
                "room_count": room.get("room_count", 1),
                "meal_plan": room.get("meal_plan", ""),
                "cancellation_policy": room.get("cancellation_policy", ""),
                "status": "Pending"
            })

    # Get employee details
    employee = data.get("employee", {})
    company = data.get("company", {})

    employee_id = employee.get("id") if isinstance(employee, dict) else data.get("employee_id")
    employee_name = employee.get("name") if isinstance(employee, dict) else data.get("employee_name")
    company_id = company.get("id") if isinstance(company, dict) else data.get("company")

    # Get and validate booking status
    input_status = data.get("status", "pending_in_cart").lower()
    booking_status = status_map.get(input_status, "PENDING_IN_CART")

    # Check if cart already exists for this employee
    existing_cart = frappe.get_all(
        "Cart Details",
        filters={"employee_id": employee_id},
        fields=["name"],
        limit=1
    )

    if existing_cart:
        # Update existing cart - append new hotel items
        doc = frappe.get_doc("Cart Details", existing_cart[0].name)

        # Append new cart items to existing ones
        for item in cart_items:
            doc.append("cart_items", item)

        # Update other fields if provided
        if data.get("check_in"):
            doc.check_in_date = data.get("check_in")
        if data.get("check_out"):
            doc.check_out_date = data.get("check_out")
        if data.get("destination"):
            doc.destination = data.get("destination")
        if data.get("guests_count"):
            doc.guest_count = data.get("guests_count")
        if data.get("child_count") is not None:
            doc.child_count = data.get("child_count")
        if data.get("rooms_count"):
            doc.room_count = data.get("rooms_count")

        doc.save(ignore_permissions=True)
        frappe.db.commit()

        return {
            "success": True,
            "cart_id": doc.name,
            "message": "Cart updated with new items"
        }
    else:
        # Create new cart
        doc = frappe.get_doc({
            "doctype": "Cart Details",
            "employee_id": employee_id,
            "employee_name": employee_name,
            "company": company_id,
            "booking_id": data.get("booking_id"),
            "check_in_date": data.get("check_in"),
            "check_out_date": data.get("check_out"),
            "booking_status": booking_status,
            "guest_count": data.get("guests_count"),
            "child_count": data.get("child_count"),
            "room_count": data.get("rooms_count"),
            "destination": data.get("destination"),
            "cart_items": cart_items
        })

        doc.insert(ignore_permissions=True)
        frappe.db.commit()

        return {
            "success": True,
            "cart_id": doc.name,
            "message": "New cart created"
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
        "pending_in_cart": 0,
        "sent_for_approval": 1,
        "viewed": 2,
        "requested": 3,
        "approved": 4,
        "sucess": 5,
        "failure": 6
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
            hotel_id = item.hotel_id or ""
            room_status = item.status or "Pending"
            approver_level = int(item.approver_level or 0) if hasattr(item, 'approver_level') else 0

            if hotel_name not in hotel_map:
                hotel_map[hotel_name] = {
                    "hotel_id": hotel_id,
                    "hotel_name": hotel_name,
                    "supplier": item.supplier or "",
                    "status": room_status,  # Initial hotel status from first room
                    "approver_level": approver_level,
                    "rooms": []
                }

            hotel_map[hotel_name]["rooms"].append({
                "room_id": item.room_id or "",
                "room_type": item.room_type or "",
                "price": float(item.price or 0),
                "room_count": int(item.room_count or 1) if hasattr(item, 'room_count') else 1,
                "meal_plan": item.meal_plan or "" if hasattr(item, 'meal_plan') else "",
                "cancellation_policy": item.cancellation_policy or "" if hasattr(item, 'cancellation_policy') else "",
                "status": room_status,
                "approver_level": approver_level
            })

            # Update hotel status to highest priority status among its rooms
            # Priority: Approved > Pending_L2_Approval > SENT_FOR_APPROVAL > Pending > Declined
            current_hotel_status = hotel_map[hotel_name]["status"]
            if room_status == "Approved":
                hotel_map[hotel_name]["status"] = "Approved"
                hotel_map[hotel_name]["approver_level"] = approver_level
            elif room_status == "Pending_L2_Approval" and current_hotel_status not in ["Approved"]:
                hotel_map[hotel_name]["status"] = "Pending_L2_Approval"
                hotel_map[hotel_name]["approver_level"] = approver_level
            elif room_status == "SENT_FOR_APPROVAL" and current_hotel_status not in ["Approved", "Pending_L2_Approval"]:
                hotel_map[hotel_name]["status"] = "Sent_For_Approval"
                hotel_map[hotel_name]["approver_level"] = approver_level

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


@frappe.whitelist(allow_guest=True)
def approve_cart_hotel_item(data):
    """
    Approve specific cart hotel item(s) for the employee.
    Supports single item (hotel_id, room_id) or multiple items (selected_items array).
    Implements two-level approval workflow:
    - First approval: approver_level becomes 1, status = "Pending_L2_Approval"
    - Second approval: approver_level becomes 2, status = "Approved", booking_status = "APPROVED"

    Args:
        data: JSON with employee_id and either:
              - hotel_id, room_id (single item)
              - selected_items: [{hotel_id, room_id}, ...] (multiple items)

    Returns:
        Success/error response with updated item details
    """
    if isinstance(data, str):
        data = frappe.parse_json(data)

    employee_id = data.get("employee_id")
    hotel_id = data.get("hotel_id")
    room_id = data.get("room_id")
    selected_items = data.get("selected_items", [])

    # Validate required fields
    if not employee_id:
        return {
            "success": False,
            "message": "employee_id is required"
        }

    # Build list of items to approve (use set to avoid duplicates)
    approve_pairs = set()

    # Check if single item approval
    if hotel_id and room_id:
        approve_pairs.add((hotel_id, room_id))

    # Check if multiple items approval
    if selected_items and len(selected_items) > 0:
        for item in selected_items:
            h_id = item.get("hotel_id")
            r_id = item.get("room_id")
            if h_id and r_id:
                approve_pairs.add((h_id, r_id))

    if not approve_pairs:
        return {
            "success": False,
            "message": "Either (hotel_id and room_id) or selected_items is required"
        }

    # Find cart for the employee
    existing_cart = frappe.get_all(
        "Cart Details",
        filters={"employee_id": employee_id},
        fields=["name"],
        limit=1
    )

    if not existing_cart:
        return {
            "success": False,
            "message": f"No cart found for employee: {employee_id}"
        }

    # Get the cart document
    cart_doc = frappe.get_doc("Cart Details", existing_cart[0].name)

    # Track approved items for response
    approved_items = []
    items_found = 0

    # First pass: Update ALL items that match the approval list
    for item in cart_doc.cart_items:
        item_pair = (item.hotel_id, item.room_id)

        if item_pair in approve_pairs:
            items_found += 1

            # Get current approver_level (default to 0 if not set)
            current_level = int(item.approver_level or 0)

            # Check if already fully approved
            if current_level >= 2:
                approved_items.append({
                    "hotel_id": item.hotel_id,
                    "hotel_name": item.hotel_name,
                    "room_id": item.room_id,
                    "room_type": item.room_type,
                    "price": float(item.price or 0),
                    "room_count": int(item.room_count or 1),
                    "approver_level": current_level,
                    "status": item.status,
                    "message": "Already fully approved"
                })
                continue

            # Increment approver_level
            new_level = current_level + 1
            item.approver_level = new_level

            # Set status based on approver_level
            if new_level >= 2:
                item.status = "Approved"
            else:
                item.status = "Pending_L2_Approval"

            approved_items.append({
                "hotel_id": item.hotel_id,
                "hotel_name": item.hotel_name,
                "room_id": item.room_id,
                "room_type": item.room_type,
                "price": float(item.price or 0),
                "room_count": int(item.room_count or 1),
                "approver_level": new_level,
                "status": item.status
            })

    if items_found == 0:
        return {
            "success": False,
            "message": "No matching cart items found for the provided hotel_id and room_id pairs"
        }

    # Second pass: Decline items not in approval list (only if not already in approval process)
    declined_count = 0
    for item in cart_doc.cart_items:
        item_pair = (item.hotel_id, item.room_id)
        if item_pair not in approve_pairs:
            # Only decline if not already in approval process (approver_level > 0)
            current_level = int(item.approver_level or 0)
            if current_level == 0:
                item.status = "Declined"
                declined_count += 1

    # Check if all approved items have reached level 2
    all_fully_approved = all(item["approver_level"] >= 2 for item in approved_items) if approved_items else False

    # Update cart booking_status to APPROVED when all items are fully approved
    # if all_fully_approved and approved_items:
    #     cart_doc.booking_status = "APPROVED"

    # Save the cart
    cart_doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "success": True,
        "message": "Cart item(s) approved successfully",
        "cart_id": cart_doc.name,
        "booking_status": cart_doc.booking_status,
        "approved_items": approved_items,
        "approved_count": len(approved_items),
        "declined_count": declined_count,
        "fully_approved": all_fully_approved
    }


@frappe.whitelist(allow_guest=True)
def fetch_approved_cart_items(employee_id=None):
    """
    Fetch only approved cart hotel items.

    Args:
        employee_id: Optional filter by employee

    Returns:
        List of approved cart items with cart details
    """
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

    data = []

    for cart in carts:
        cart_doc = frappe.get_doc("Cart Details", cart.name)

        # Filter only approved items
        approved_items = []
        for item in cart_doc.cart_items:
            if item.status == "Approved":
                approved_items.append({
                    "hotel_id": item.hotel_id,
                    "hotel_name": item.hotel_name,
                    "supplier": item.supplier,
                    "room_id": item.room_id,
                    "room_type": item.room_type,
                    "price": float(item.price or 0),
                    "room_count": int(item.room_count or 1),
                    "meal_plan": item.meal_plan or "",
                    "cancellation_policy": item.cancellation_policy or "",
                    "status": item.status
                })

        # Only include carts that have approved items
        if approved_items:
            total_amount = sum(item["price"] for item in approved_items)

            data.append({
                "cart_id": cart.name,
                "booking_id": cart.booking_id,
                "employee": {
                    "id": cart.employee_id or "",
                    "name": cart.employee_name or ""
                },
                "company": cart.company or "",
                "destination": cart.destination or "",
                "check_in": str(cart.check_in_date) if cart.check_in_date else "",
                "check_out": str(cart.check_out_date) if cart.check_out_date else "",
                "guest_count": int(cart.guest_count or 0),
                "child_count": int(cart.child_count or 0),
                "booking_status": cart.booking_status or "",
                "approved_items": approved_items,
                "total_amount": total_amount
            })

    return {
        "success": True,
        "count": len(data),
        "data": data
    }


@frappe.whitelist(allow_guest=True)
def send_cart_for_approval(data):
    """
    Select specific hotel/room items, change status to 'Sent for Approval',
    fetch selected items with employee and company details, and send approval email.

    Args:
        data: JSON with employee_id, selected_items (list of {hotel_id, room_id}),
              email_api_url (third party email API endpoint)

    Returns:
        Selected items with employee/company details and email status
    """
    import requests

    if isinstance(data, str):
        data = frappe.parse_json(data)

    employee_id = data.get("employee_id")
    selected_items = data.get("selected_items", [])
    email_api_url = data.get("email_api_url")

    # Validate required fields
    if not employee_id:
        return {
            "success": False,
            "message": "employee_id is required"
        }

    if not selected_items or len(selected_items) == 0:
        return {
            "success": False,
            "message": "selected_items is required (list of {hotel_id, room_id})"
        }

    # Find cart for the employee
    existing_cart = frappe.get_all(
        "Cart Details",
        filters={"employee_id": employee_id},
        fields=["name"],
        limit=1
    )

    if not existing_cart:
        return {
            "success": False,
            "message": f"No cart found for employee: {employee_id}"
        }

    # Get the cart document
    cart_doc = frappe.get_doc("Cart Details", existing_cart[0].name)

    # Create a set of selected (hotel_id, room_id) pairs for quick lookup
    selected_pairs = set()
    for item in selected_items:
        hotel_id = item.get("hotel_id")
        room_id = item.get("room_id")
        if hotel_id and room_id:
            selected_pairs.add((hotel_id, room_id))

    # Update cart items and collect selected items data
    selected_items_data = []
    for item in cart_doc.cart_items:
        if (item.hotel_id, item.room_id) in selected_pairs:
            item.status = "Sent_For_Approval"  # Mark as sent for approval
            selected_items_data.append({
                "hotel_id": item.hotel_id,
                "hotel_name": item.hotel_name,
                "supplier": item.supplier,
                "room_id": item.room_id,
                "room_type": item.room_type,
                "price": float(item.price or 0),
                "room_count": int(item.room_count or 1),
                "meal_plan": item.meal_plan or "",
                "cancellation_policy": item.cancellation_policy or "",
                "status": "Sent_For_Approval"
            })

    if not selected_items_data:
        return {
            "success": False,
            "message": "No matching cart items found for the selected hotel_id and room_id pairs"
        }

    # Save the cart with updated item statuses (SENT_FOR_APPROVAL at room level)
    cart_doc.save(ignore_permissions=True)
    frappe.db.commit()

    # Fetch employee details and approver emails
    employee_data = {}
    approver_emails = []
    if frappe.db.exists("Employee", employee_id):
        employee = frappe.get_doc("Employee", employee_id)
        employee_data = {
            "id": employee.name,
            "name": employee.employee_name,
            "email": employee.company_email or employee.personal_email or "",
            "designation": employee.designation or "",
            "department": employee.department or "",
            "company": employee.company or ""
        }
        # Get L1 and L2 approver emails
        l1_approver_email = getattr(employee, 'custom_l1__approver_email', None) or ""
        l2_approver_email = getattr(employee, 'custom_l2_approver_email', None) or ""
        if l1_approver_email:
            approver_emails.append(l1_approver_email)
        if l2_approver_email:
            approver_emails.append(l2_approver_email)

    # Fetch company details
    company_data = {}
    if employee_data.get("company"):
        company_name = employee_data.get("company")
        if frappe.db.exists("Company", company_name):
            company = frappe.get_doc("Company", company_name)
            company_data = {
                "id": company.name,
                "name": company.company_name,
                "email": company.email or "",
                "phone": company.phone_no or "",
                "website": company.website or ""
            }

    # Calculate total amount
    total_amount = sum(item["price"] for item in selected_items_data)

    # Prepare response data
    response_data = {
        "cart_id": cart_doc.name,
        "booking_id": cart_doc.booking_id,
        "employee": employee_data,
        "company": company_data,
        "destination": cart_doc.destination or "",
        "check_in": str(cart_doc.check_in_date) if cart_doc.check_in_date else "",
        "check_out": str(cart_doc.check_out_date) if cart_doc.check_out_date else "",
        "guest_count": int(cart_doc.guest_count or 0),
        "child_count": int(cart_doc.child_count or 0),
        "booking_status": "SENT_FOR_APPROVAL",
        "selected_items": selected_items_data,
        "total_amount": total_amount
    }

    # Send approval email via custom email API
    email_status = {
        "sent": False,
        "message": ""
    }

    # Email API configuration
    email_api_url = "http://16.112.129.113/main/v1/email/send"

    if approver_emails:
        # Build hotel cards HTML
        hotel_cards_html = ""
        for item in selected_items_data:
            # Generate select link with hotel_id and room_id
            select_link = f"https://cbt-destiin-frontend.vercel.app/view-hotel/{item['hotel_id']}?employee_id={employee_id}&room_id={item['room_id']}"

            hotel_cards_html += f"""
                    <tr>
                        <td style="padding:0 30px 30px 30px;">

                            <table width="100%" cellpadding="0" cellspacing="0" style="
background:#0F1F33;
border:1px solid #1F3B4D;
border-radius:16px;
overflow:hidden;
">

                                <!-- CONTENT -->
                                <tr>
                                    <td style="padding:22px; text-align:left;">

                                        <!-- ROOM NAME -->
                                        <h3 style="
margin:0 0 6px 0;
font-size:19px;
font-weight:600;
color:#FFFFFF;
">
                                            {item['hotel_name']}
                                        </h3>



                                        <!-- AMENITIES -->
                                        <p style="
margin:0 0 16px 0;
font-size:13px;
color:#9CA3AF;
">
                                            {item['room_type']} | {item['meal_plan'] or 'N/A'} | {item['room_count']} Room(s)
                                        </p>

                                        <!-- PRICE BOX -->
                                        <table width="100%" cellpadding="0" cellspacing="0" style="
background:rgba(255,255,255,0.05);
border:1px solid #1F3B4D;
border-radius:12px;
">
                                            <tr>
                                                <td style="padding:14px;">
                                                    <p style="margin:0;font-size:12px;color:#9CA3AF;">
                                                        Price per night
                                                    </p>
                                                    <p
                                                        style="margin:4px 0 0 0;font-size:20px;font-weight:700;color:#FFFFFF;">
                                                        ₹ {item['price']:.2f}
                                                    </p>
                                                    <p style="margin:4px 0 0 0;font-size:12px;color:#9CA3AF;">
                                                        {item['status']}
                                                    </p>
                                                </td>
                                            </tr>
                                        </table>

                                        <!-- CTA -->
                                        <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:18px;">
                                            <tr>
                                                <td align="center">
                                                    <a href="{select_link}" style="
display:block;
background:#10B981;
color:#FFFFFF;
padding:14px;
border-radius:999px;
text-decoration:none;
font-size:14px;
font-weight:600;
">
                                                        Select Room
                                                    </a>
                                                </td>
                                            </tr>
                                        </table>

                                    </td>
                                </tr>

                            </table>

                        </td>
                    </tr>
            """

        email_body = f"""<!DOCTYPE html
    PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">

<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Hotel Selection</title>

    <style type="text/css">
        body,
        table,
        td,
        a {{
            -webkit-text-size-adjust: 100%;
            -ms-text-size-adjust: 100%;
        }}

        table,
        td {{
            mso-table-lspace: 0pt;
            mso-table-rspace: 0pt;
        }}

        img {{
            border: 0;
            display: block;
            height: auto;
        }}

        table {{
            border-collapse: collapse !important;
        }}

        body {{
            margin: 0;
            padding: 0;
            width: 100%;
            background: #0E0F1D;
            font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
        }}

        @media screen and (max-width:600px) {{
            .container {{
                width: 100% !important;
            }}

            .pad {{
                padding: 20px !important;
            }}
        }}
    </style>
</head>

<body>

    <table width="100%" cellpadding="0" cellspacing="0" style="background:#0E0F1D;">
        <tr>
            <td align="center" style="padding:40px 10px;">

                <!-- MAIN CONTAINER -->
                <table width="500" class="container" cellpadding="0" cellspacing="0" style="background:#161B22;border-radius:16px;overflow:hidden;
box-shadow:0 20px 40px rgba(0,0,0,0.45);">

                    <!-- HEADER -->
                    <tr>
                        <td align="center" style="padding:26px;
background:linear-gradient(90deg,#7ECDA5,#5B8FD6,#7A63A8);">
                            <h2 style="margin:0;color:#FFFFFF;font-size:22px;font-weight:600;">
                                Hotel Selection Request
                            </h2>
                        </td>
                    </tr>

                    <!-- INTRO -->
                    <tr>
                        <td class="pad" style="padding:30px 40px;color:#E5E7EB;font-size:15px;line-height:1.5;">
                            <p style="margin:0 0 8px;">
                                Dear <strong>{employee_data.get('name', 'User')}</strong>,
                            </p>
                            <p style="margin:0;">
                                Choose your preferred room for your stay in
                                <span style="color:#7ECDA5;font-weight:600;">{cart_doc.destination or 'your destination'}</span>.
                            </p>
                        </td>
                    </tr>

                    <!-- =============== HOTEL LOOP START =============== -->
                    {hotel_cards_html}
                    <!-- =============== HOTEL LOOP END ================= -->

                    <!-- FOOTER -->
                    <tr>
                        <td align="center" style="padding:26px;background:#0A0B14;border-top:1px solid #1F2937;">
                            <p style="margin:0;color:#6B7280;font-size:12px;">
                                © 2026 DESTIIN TRAVEL
                            </p>
                        </td>
                    </tr>

                </table>

            </td>
        </tr>
    </table>

</body>

</html>"""

        # Email API payload - send to L1 and L2 approvers
        email_payload = {
            "toEmails": approver_emails,
            "subject": f"Hotel Selection Request - {employee_data.get('name', 'Employee')} - {cart_doc.destination or 'Booking'}",
            "body": email_body
        }

        try:
            response = requests.post(
                email_api_url,
                json=email_payload,
                headers={
                    "Content-Type": "application/json"
                },
                timeout=30
            )

            if response.status_code in [200, 201]:
                email_status["sent"] = True
                email_status["message"] = "Approval email sent successfully"
                email_status["sent_to"] = approver_emails
            else:
                email_status["sent"] = False
                email_status["message"] = f"Email API returned status {response.status_code}: {response.text}"

        except requests.exceptions.RequestException as e:
            email_status["sent"] = False
            email_status["message"] = f"Failed to send email: {str(e)}"
            frappe.log_error(frappe.get_traceback(), "send_cart_for_approval Email Error")
    else:
        email_status["message"] = "No approver emails found (custom_l1__approver_email and custom_l2_approver_email not set)"

    return {
        "success": True,
        "message": "Cart items sent for approval",
        "data": response_data,
        "email_status": email_status
    }


@frappe.whitelist(allow_guest=True)
def confirm_booking(data):
    """
    Move approved cart item to Travel Bookings doctype and delete cart records.
    Sends booking confirmation email to the employee.

    Args:
        data: JSON with employee_id, hotel_id, room_id

    Returns:
        Success/error response with booking details
    """
    import requests

    if isinstance(data, str):
        data = frappe.parse_json(data)

    employee_id = data.get("employee_id")
    hotel_id = data.get("hotel_id")
    room_id = data.get("room_id")

    # Validate required fields
    if not employee_id:
        return {
            "success": False,
            "message": "employee_id is required"
        }

    if not hotel_id:
        return {
            "success": False,
            "message": "hotel_id is required"
        }

    if not room_id:
        return {
            "success": False,
            "message": "room_id is required"
        }

    # Find cart for the employee
    existing_cart = frappe.get_all(
        "Cart Details",
        filters={"employee_id": employee_id},
        fields=["name"],
        limit=1
    )

    if not existing_cart:
        return {
            "success": False,
            "message": f"No cart found for employee: {employee_id}"
        }

    # Get the cart document
    cart_doc = frappe.get_doc("Cart Details", existing_cart[0].name)

    # Find the approved item matching hotel_id and room_id
    approved_item = None
    for item in cart_doc.cart_items:
        if item.hotel_id == hotel_id and item.room_id == room_id and item.status == "Approved":
            approved_item = item
            break

    if not approved_item:
        return {
            "success": False,
            "message": f"No approved cart item found with hotel_id: {hotel_id} and room_id: {room_id}"
        }

    # Calculate total price (price * room_count)
    item_price = float(approved_item.price or 0)
    room_count = int(approved_item.room_count or 1)
    total_price = item_price * room_count

    # Create Travel Booking record
    try:
        booking_doc = frappe.get_doc({
            "doctype": "Travel Bookings",
            "employee_id": cart_doc.employee_id,
            "employee_name": cart_doc.employee_name,
            "company": cart_doc.company,
            "booking_id": cart_doc.booking_id,
            "check_in_date": cart_doc.check_in_date,
            "check_out_date": cart_doc.check_out_date,
            "booking_status": "Success",
            "guest_count": cart_doc.guest_count,
            "child_count": cart_doc.child_count,
            "room_count": room_count,
            "hotel_name": approved_item.hotel_name,
            "supplier": approved_item.supplier,
            "room_type": approved_item.room_type,
            "occupency": cart_doc.guest_count,  # Using guest_count as occupancy
            "destination": cart_doc.destination,
            "price": item_price,
            "total_price": total_price,
            "payment_status": "Pending"
        })

        booking_doc.insert(ignore_permissions=True)
        frappe.db.commit()

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "confirm_booking Create Booking Error")
        return {
            "success": False,
            "message": f"Failed to create travel booking: {str(e)}"
        }

    # Fetch employee email for sending confirmation
    employee_email = ""
    employee_name = cart_doc.employee_name or ""
    if frappe.db.exists("Employee", employee_id):
        employee = frappe.get_doc("Employee", employee_id)
        employee_email = employee.company_email or employee.personal_email or ""
        employee_name = employee.employee_name or employee_name

    # Delete all cart records for this employee
    cart_names = frappe.get_all(
        "Cart Details",
        filters={"employee_id": employee_id},
        pluck="name"
    )

    for name in cart_names:
        frappe.delete_doc("Cart Details", name, ignore_permissions=True)

    frappe.db.commit()

    # Send booking confirmation email to employee
    email_status = {
        "sent": False,
        "message": ""
    }

    email_api_url = "http://16.112.129.113/main/v1/email/send"

    if employee_email:
        # Build HTML email body for booking confirmation
        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background-color: #27ae60; color: white; padding: 20px; border-radius: 5px 5px 0 0; text-align: center;">
                    <h1 style="margin: 0;">🎉 Booking Confirmed!</h1>
                </div>

                <div style="background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; border-top: none;">
                    <p>Dear <strong>{employee_name}</strong>,</p>
                    <p>Your hotel booking has been successfully confirmed. Here are your booking details:</p>

                    <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #27ae60;">
                        <h3 style="color: #2c3e50; margin-top: 0;">Hotel Details</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 8px 0; border-bottom: 1px solid #eee;"><strong>Hotel Name:</strong></td>
                                <td style="padding: 8px 0; border-bottom: 1px solid #eee;">{approved_item.hotel_name or 'N/A'}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; border-bottom: 1px solid #eee;"><strong>Room Type:</strong></td>
                                <td style="padding: 8px 0; border-bottom: 1px solid #eee;">{approved_item.room_type or 'N/A'}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; border-bottom: 1px solid #eee;"><strong>Number of Rooms:</strong></td>
                                <td style="padding: 8px 0; border-bottom: 1px solid #eee;">{room_count}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; border-bottom: 1px solid #eee;"><strong>Meal Plan:</strong></td>
                                <td style="padding: 8px 0; border-bottom: 1px solid #eee;">{approved_item.meal_plan or 'N/A'}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; border-bottom: 1px solid #eee;"><strong>Destination:</strong></td>
                                <td style="padding: 8px 0; border-bottom: 1px solid #eee;">{cart_doc.destination or 'N/A'}</td>
                            </tr>
                        </table>
                    </div>

                    <div style="background-color: white; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #3498db;">
                        <h3 style="color: #2c3e50; margin-top: 0;">Booking Information</h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr>
                                <td style="padding: 8px 0; border-bottom: 1px solid #eee;"><strong>Booking ID:</strong></td>
                                <td style="padding: 8px 0; border-bottom: 1px solid #eee;">{booking_doc.name}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; border-bottom: 1px solid #eee;"><strong>Check-in Date:</strong></td>
                                <td style="padding: 8px 0; border-bottom: 1px solid #eee;">{str(cart_doc.check_in_date) if cart_doc.check_in_date else 'N/A'}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; border-bottom: 1px solid #eee;"><strong>Check-out Date:</strong></td>
                                <td style="padding: 8px 0; border-bottom: 1px solid #eee;">{str(cart_doc.check_out_date) if cart_doc.check_out_date else 'N/A'}</td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; border-bottom: 1px solid #eee;"><strong>Guests:</strong></td>
                                <td style="padding: 8px 0; border-bottom: 1px solid #eee;">{int(cart_doc.guest_count or 0)} Adults, {int(cart_doc.child_count or 0)} Children</td>
                            </tr>
                        </table>
                    </div>

                    <div style="background-color: #2c3e50; color: white; padding: 15px; border-radius: 5px; text-align: center;">
                        <h3 style="margin: 0;">Total Amount: ₹{total_price:.2f}</h3>
                    </div>

                    <p style="margin-top: 20px;">Thank you for booking with us. We hope you have a pleasant stay!</p>

                    <p style="color: #7f8c8d; font-size: 12px; margin-top: 30px;">
                        This is an automated confirmation email. For any queries, please contact our support team.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        # Email API payload
        email_payload = {
            "toEmails": [employee_email],
            "subject": f"Booking Confirmed - {approved_item.hotel_name or 'Hotel'} - {cart_doc.destination or 'Booking'}",
            "body": email_body
        }

        try:
            response = requests.post(
                email_api_url,
                json=email_payload,
                headers={
                    "Content-Type": "application/json"
                },
                timeout=30
            )

            if response.status_code in [200, 201]:
                email_status["sent"] = True
                email_status["message"] = "Booking confirmation email sent successfully"
                email_status["sent_to"] = employee_email
            else:
                email_status["sent"] = False
                email_status["message"] = f"Email API returned status {response.status_code}: {response.text}"

        except requests.exceptions.RequestException as e:
            email_status["sent"] = False
            email_status["message"] = f"Failed to send email: {str(e)}"
            frappe.log_error(frappe.get_traceback(), "confirm_booking Email Error")
    else:
        email_status["message"] = "No recipient email available (employee email not found)"

    return {
        "success": True,
        "message": "Booking confirmed successfully",
        "booking_id": booking_doc.name,
        "booking_details": {
            "employee_id": booking_doc.employee_id,
            "employee_name": booking_doc.employee_name,
            "hotel_name": booking_doc.hotel_name,
            "room_type": booking_doc.room_type,
            "room_count": booking_doc.room_count,
            "destination": booking_doc.destination,
            "check_in_date": str(booking_doc.check_in_date) if booking_doc.check_in_date else None,
            "check_out_date": str(booking_doc.check_out_date) if booking_doc.check_out_date else None,
            "total_price": total_price,
            "booking_status": booking_doc.booking_status
        },
        "cart_deleted": True,
        "deleted_cart_count": len(cart_names),
        "email_status": email_status
    }