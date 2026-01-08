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
        "PENDING IN CART",
        "SENT FOR APPROVAL",
        "VIEWED",
        "REQUESTED",
        "APPROVED",
        "SUCESS",
        "FAILURE"
    ]

    # Status mapping from input to valid status
    status_map = {
        "pending in cart": "PENDING IN CART",
        "pending": "PENDING IN CART",
        "sent for approval": "SENT FOR APPROVAL",
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
    input_status = data.get("status", "pending in cart").lower()
    booking_status = status_map.get(input_status, "PENDING IN CART")

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
        "pending in cart": 0,
        "sent for approval": 1,
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


@frappe.whitelist(allow_guest=True)
def approve_cart_hotel_item(data):
    """
    Approve a specific cart hotel item and decline all others for the employee.

    Args:
        data: JSON with employee_id, hotel_id, and room_id

    Returns:
        Success/error response with updated item details
    """
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

    # Track if we found the matching item
    item_found = False
    approved_item = None

    # Update cart items
    for item in cart_doc.cart_items:
        if item.hotel_id == hotel_id and item.room_id == room_id:
            item.status = "Approved"
            item_found = True
            approved_item = {
                "hotel_id": item.hotel_id,
                "hotel_name": item.hotel_name,
                "room_id": item.room_id,
                "room_type": item.room_type,
                "price": float(item.price or 0),
                "status": "Approved"
            }
        else:
            item.status = "Declined"

    if not item_found:
        return {
            "success": False,
            "message": f"No cart item found with hotel_id: {hotel_id} and room_id: {room_id}"
        }

    # Save the cart
    cart_doc.save(ignore_permissions=True)
    frappe.db.commit()

    return {
        "success": True,
        "message": "Cart item approved successfully",
        "cart_id": cart_doc.name,
        "approved_item": approved_item,
        "declined_count": len(cart_doc.cart_items) - 1
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
            item.status = "Pending"  # Mark as pending for approval
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
                "status": "Pending"
            })

    if not selected_items_data:
        return {
            "success": False,
            "message": "No matching cart items found for the selected hotel_id and room_id pairs"
        }

    # Update cart booking status
    cart_doc.booking_status = "SENT FOR APPROVAL"
    cart_doc.save(ignore_permissions=True)
    frappe.db.commit()

    # Fetch employee details
    employee_data = {}
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

    # Fetch company details
    company_data = {}
    company_email = ""
    if employee_data.get("company"):
        company_name = employee_data.get("company")
        if frappe.db.exists("Company", company_name):
            company = frappe.get_doc("Company", company_name)
            company_email = company.email or ""
            company_data = {
                "id": company.name,
                "name": company.company_name,
                "email": company_email,
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
        "booking_status": "SENT FOR APPROVAL",
        "selected_items": selected_items_data,
        "total_amount": total_amount
    }

    # Send approval email via custom email API
    email_status = {
        "sent": False,
        "message": ""
    }

    # Email API configuration
    email_api_url = "http://16.112.129.113/v1/email/send"

    # Get recipient email from company details
    to_email = company_email

    if to_email:
        # Build HTML email body
        items_html = ""
        for item in selected_items_data:
            items_html += f"""
            <tr>
                <td style="padding: 10px; border: 1px solid #ddd;">{item['hotel_name']}</td>
                <td style="padding: 10px; border: 1px solid #ddd;">{item['room_type']}</td>
                <td style="padding: 10px; border: 1px solid #ddd;">{item['room_count']}</td>
                <td style="padding: 10px; border: 1px solid #ddd;">{item['meal_plan']}</td>
                <td style="padding: 10px; border: 1px solid #ddd;">₹{item['price']:.2f}</td>
            </tr>
            """

        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">
                    Cart Approval Request
                </h2>

                <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="color: #2c3e50; margin-top: 0;">Employee Details</h3>
                    <p><strong>Name:</strong> {employee_data.get('name', 'N/A')}</p>
                    <p><strong>Email:</strong> {employee_data.get('email', 'N/A')}</p>
                    <p><strong>Department:</strong> {employee_data.get('department', 'N/A')}</p>
                    <p><strong>Designation:</strong> {employee_data.get('designation', 'N/A')}</p>
                </div>

                <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="color: #2c3e50; margin-top: 0;">Booking Details</h3>
                    <p><strong>Booking ID:</strong> {cart_doc.booking_id or 'N/A'}</p>
                    <p><strong>Destination:</strong> {cart_doc.destination or 'N/A'}</p>
                    <p><strong>Check-in:</strong> {str(cart_doc.check_in_date) if cart_doc.check_in_date else 'N/A'}</p>
                    <p><strong>Check-out:</strong> {str(cart_doc.check_out_date) if cart_doc.check_out_date else 'N/A'}</p>
                    <p><strong>Guests:</strong> {int(cart_doc.guest_count or 0)} Adults, {int(cart_doc.child_count or 0)} Children</p>
                </div>

                <h3 style="color: #2c3e50;">Selected Items</h3>
                <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                    <thead>
                        <tr style="background-color: #3498db; color: white;">
                            <th style="padding: 10px; border: 1px solid #ddd;">Hotel</th>
                            <th style="padding: 10px; border: 1px solid #ddd;">Room Type</th>
                            <th style="padding: 10px; border: 1px solid #ddd;">Rooms</th>
                            <th style="padding: 10px; border: 1px solid #ddd;">Meal Plan</th>
                            <th style="padding: 10px; border: 1px solid #ddd;">Price</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items_html}
                    </tbody>
                </table>

                <div style="background-color: #2c3e50; color: white; padding: 15px; border-radius: 5px; text-align: right;">
                    <h3 style="margin: 0;">Total Amount: ₹{total_amount:.2f}</h3>
                </div>

                <p style="margin-top: 30px; color: #7f8c8d; font-size: 12px;">
                    This is an automated email. Please review and approve the booking request.
                </p>
            </div>
        </body>
        </html>
        """

        # Email API payload
        email_payload = {
            "toEmails": [to_email],
            "subject": f"Cart Approval Request - {employee_data.get('name', 'Employee')} - {cart_doc.destination or 'Booking'}",
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
                email_status["sent_to"] = to_email
            else:
                email_status["sent"] = False
                email_status["message"] = f"Email API returned status {response.status_code}: {response.text}"

        except requests.exceptions.RequestException as e:
            email_status["sent"] = False
            email_status["message"] = f"Failed to send email: {str(e)}"
            frappe.log_error(frappe.get_traceback(), "send_cart_for_approval Email Error")
    else:
        email_status["message"] = "No recipient email available (company email not found)"

    return {
        "success": True,
        "message": "Cart items sent for approval",
        "data": response_data,
        "email_status": email_status
    }