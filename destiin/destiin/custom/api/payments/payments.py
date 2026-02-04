import frappe
import json
import requests
from datetime import timedelta
from destiin.destiin.custom.api.request_booking.request import update_request_status_from_rooms

# SBT
@frappe.whitelist(allow_guest=False)
def create_payment_url(request_booking_id, mode=None):
    """
    API to create a payment URL using HitPay and create a Booking Payments record.

    This API:
    1. Fetches the Request Booking Details by request_booking_id field
    2. Gets employee details (name, email, phone) from the request booking
    3. Fetches the approved hotel and room details from Cart Hotel Item
    4. Creates a new Booking Payments record linked to Request Booking
    5. Calls HitPay API to create a payment request based on approved room prices
    6. Updates the Booking Payments record with the payment URL
    7. Sets payment status to 'payment_pending'

    Args:
        request_booking_id (str): The request_booking_id field value (required)
        mode (str, optional): Payment mode - 'direct_pay' or 'bill_to_company' (default: 'direct_pay')

    Returns:
        dict: Response with success status and payment URL data
    """
    try:
        if not request_booking_id:
            return {
                "success": False,
                "error": "request_booking_id is required"
            }

        # Set default mode to direct_pay if not provided
        if not mode:
            mode = "direct_pay"

        valid_modes = ["direct_pay", "bill_to_company"]
        if mode not in valid_modes:
            return {
                "success": False,
                "error": f"Invalid mode. Must be one of: {', '.join(valid_modes)}"
            }

        # First, find the document name by request_booking_id field
        request_booking_name = frappe.db.get_value(
            "Request Booking Details",
            {"request_booking_id": request_booking_id},
            "name"
        )

        if not request_booking_name:
            return {
                "success": False,
                "error": f"Request Booking not found for request_booking_id: {request_booking_id}"
            }

        # Fetch the Request Booking Details record
        request_booking = frappe.get_doc("Request Booking Details", request_booking_name)

        # Get employee details for payment
        employee_name = ""
        employee_email = ""
        employee_phone = ""

        if request_booking.employee:
            employee_details = frappe.get_value(
                "Employee",
                request_booking.employee,
                ["employee_name", "company_email", "personal_email", "cell_number"],
                as_dict=True
            )
            if employee_details:
                employee_name = employee_details.get("employee_name", "")
                employee_email = employee_details.get("company_email") or employee_details.get("personal_email") or ""
                employee_phone = employee_details.get("cell_number") or ""

        # Get approved hotel from Cart Hotel Item
        if not request_booking.cart_hotel_item:
            return {
                "success": False,
                "error": "No Cart Hotel Item linked to this Request Booking"
            }

        cart_hotel = frappe.get_doc("Cart Hotel Item", request_booking.cart_hotel_item)

        if not cart_hotel:
            return {
                "success": False,
                "error": f"Cart Hotel Item not found: {request_booking.cart_hotel_item}"
            }

        # Find approved rooms and calculate total amount
        # approved_rooms = [room for room in cart_hotel.rooms if room.status == "approved"]
        approved_rooms = [room for room in cart_hotel.rooms if room.status in ["approved", "payment_pending", "payment_success", "payment_failure"]]


        if not approved_rooms:
            return {
                "success": False,
                "error": "No approved rooms found in Cart Hotel Item"
            }

        # Calculate total amount and tax from approved rooms
        total_amount = sum(float(room.total_price or room.price or 0) for room in approved_rooms)
        total_tax = sum(float(room.tax or 0) for room in approved_rooms)
        currency = approved_rooms[0].currency if approved_rooms[0].currency else "INR"

        amount = total_amount + total_tax

        if amount <= 0:
            return {
                "success": False,
                "error": "Payment amount must be greater than 0"
            }

        # Create a new Booking Payments record
        payment_doc = frappe.new_doc("Booking Payments")
        payment_doc.request_booking_link = request_booking_name
        payment_doc.employee = request_booking.employee
        payment_doc.company = request_booking.company
        payment_doc.hotel_id = cart_hotel.hotel_id
        payment_doc.hotel_name = cart_hotel.hotel_name
        payment_doc.room_count = len(approved_rooms)
        payment_doc.check_in = request_booking.check_in
        payment_doc.check_out = request_booking.check_out
        payment_doc.occupancy = request_booking.occupancy
        payment_doc.adult_count = request_booking.adult_count
        payment_doc.child_count = request_booking.child_count
        payment_doc.total_amount = total_amount
        payment_doc.tax = total_tax
        payment_doc.currency = currency
        payment_doc.payment_status = "payment_pending"
        payment_doc.payment_mode = mode
        payment_doc.booking_status = "pending"

        # Link to existing booking if available
        if request_booking.booking:
            payment_doc.booking_id = request_booking.booking

        # Prepare HitPay API request
        hitpay_url = "http://16.112.56.253/payments/v1/hitpay/create-payment"
        headers = {
            "Content-Type": "application/json"
        }

        # Build purpose string
        purpose = f"Hotel Booking Payment - {cart_hotel.hotel_name or 'Hotel'}"

        payload = {
            "amount": amount,
            "email": employee_email or "customer@example.com",
            "name": employee_name or "Customer",
            "phone": employee_phone or "+918760839303",
            "purpose": purpose,
            "request_booking_id":request_booking_id,
            "payment_methods": ["card"]
        }

        # Call HitPay API
        response = requests.post(
            hitpay_url,
            headers=headers,
            data=json.dumps(payload),
            timeout=30
        )

        if response.status_code != 200:
            frappe.log_error(
                f"HitPay API Error: Status {response.status_code}, Response: {response.text}",
                "create_payment_url HitPay Error"
            )
            return {
                "success": False,
                "error": f"HitPay API returned status code {response.status_code}"
            }

        hitpay_response = response.json()

        # Extract payment URL from HitPay response
        payment_url = hitpay_response.get("url") or hitpay_response.get("payment_url") or hitpay_response.get("data", {}).get("payment_url") or ""

        if not payment_url:
            return {
                "success": False,
                "error": "Payment URL not found in HitPay response",
                "hitpay_response": hitpay_response
            }

        # Store HitPay id in order_id and set created_at / expire_at
        payment_doc.order_id = hitpay_response.get("data", {}).get("id") or ""
        payment_doc.created_at = frappe.utils.now_datetime()

        config = frappe.db.get_value(
            "Hotel Booking Config",
            {"company": payment_doc.company},
            ["d_p_expire_type", "d_p_expire_value", "c_p_expire_type", "c_p_expire_value"],
            as_dict=True
        )
        if config:
            if mode == "direct_pay":
                expire_type = config.get("d_p_expire_type")
                expire_value = int(config.get("d_p_expire_value") or 0)
            else:
                expire_type = config.get("c_p_expire_type")
                expire_value = int(config.get("c_p_expire_value") or 0)

            if expire_type and expire_value:
                if expire_type == "mins":
                    delta = timedelta(minutes=expire_value)
                elif expire_type == "hours":
                    delta = timedelta(hours=expire_value)
                elif expire_type == "days":
                    delta = timedelta(days=expire_value)
                else:
                    delta = timedelta(0)
                payment_doc.expire_at = payment_doc.created_at + delta

        # Add payment URL to the payment_link child table
        payment_doc.append("payment_link", {
            "payment_url": payment_url
        })

        # Insert payment document with child table
        payment_doc.insert(ignore_permissions=True)

        # Update Request Booking Details with the payment link (Table MultiSelect), payment status, and request status
        request_booking.append("payment", {
            "booking_payment": payment_doc.name
        })
        request_booking.payment_status = "payment_pending"
        request_booking.request_status = "req_payment_pending"
        request_booking.save(ignore_permissions=True)

        # Update cart hotel room statuses to payment_pending
        for room in cart_hotel.rooms:
            if room.status == "approved":
                room.status = "payment_pending"
        cart_hotel.save(ignore_permissions=True)

        # Update request booking status
        update_request_status_from_rooms(request_booking_name, request_booking.cart_hotel_item)

        frappe.db.commit()

        return {
            "success": True,
            "message": "Payment URL created successfully",
            "data": {
                "payment_id": payment_doc.name,
                "request_booking_id": request_booking_id,
                "request_booking_name": request_booking_name,
                "payment_url": payment_url,
                "amount": amount,
                "currency": currency,
                "hotel_id": cart_hotel.hotel_id,
                "hotel_name": cart_hotel.hotel_name,
                "room_count": len(approved_rooms),
                "total_amount": total_amount,
                "tax": total_tax,
                "employee_name": employee_name,
                "employee_email": employee_email,
                "payment_status": "payment_pending",
                "payment_mode": mode,
                "hitpay_response": hitpay_response
            }
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "create_payment_url API Error")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=False)
def payment_callback(payment_id, status, transaction_id=None, error_message=None):
    """
    API to handle payment callback (success/failure/cancel).

    This API:
    1. Fetches the Booking Payments record by payment_id
    2. Updates the payment status based on the callback status
    3. Updates the linked Hotel Bookings payment status
    4. Updates the cart hotel room statuses
    5. Updates the request booking status

    Args:
        payment_id (str): The Booking Payments record name/ID (required)
        status (str): Payment status - 'success', 'failure', or 'cancel' (required)
        transaction_id (str, optional): Transaction ID from payment gateway
        error_message (str, optional): Error message if payment failed

    Returns:
        dict: Response with success status and updated data
    """
    try:
        if not payment_id:
            return {
                    "success": False,
                    "error": "payment_id is required"
            }

        if not status:
            return {
                    "success": False,
                    "error": "status is required"
            }

        valid_statuses = ["success", "failure", "cancel"]
        if status.lower() not in valid_statuses:
            return {
                    "success": False,
                    "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            }

        # Fetch the Booking Payments record
        payment_doc = frappe.get_doc("Booking Payments", payment_id)

        if not payment_doc:
            return {
                    "success": False,
                    "error": f"Booking Payment not found for ID: {payment_id}"
            }

        # Map callback status to payment_status
        status_map = {
            "success": "payment_success",
            "failure": "payment_failure",
            "cancel": "payment_cancel"
        }
        new_payment_status = status_map.get(status.lower(), "payment_failure")

        # Map payment status to cart room status
        cart_status_map = {
            "payment_success": "payment_success",
            "payment_failure": "payment_failure",
            "payment_cancel": "payment_cancel"
        }
        new_cart_status = cart_status_map.get(new_payment_status, "payment_failure")

        # Update Booking Payments record
        payment_doc.payment_status = new_payment_status
        if transaction_id:
            payment_doc.transaction_id = transaction_id
        if error_message:
            payment_doc.error_message = error_message
        payment_doc.save(ignore_permissions=True)

        # Update the linked Hotel Bookings payment status
        if payment_doc.booking_id:
            frappe.db.set_value(
                "Hotel Bookings",
                payment_doc.booking_id,
                "payment_status",
                new_payment_status
            )

        # Update the linked Request Booking Details payment status and request status
        if payment_doc.request_booking_link:
            # Map payment_status to request_status
            payment_to_request_status_map = {
                "payment_pending": "req_payment_pending",
                "payment_success": "req_payment_success",
                "payment_failure": "req_payment_pending",
                "payment_declined": "req_payment_pending",
                "payment_awaiting": "req_payment_pending",
                "payment_cancel": "req_payment_pending"
            }
            new_request_status = payment_to_request_status_map.get(new_payment_status, "req_payment_pending")

            frappe.db.set_value(
                "Request Booking Details",
                payment_doc.request_booking_link,
                {
                    "payment_status": new_payment_status,
                    "request_status": new_request_status
                }
            )

        # Update cart hotel room statuses and request booking status
        if payment_doc.request_booking_link:
            cart_hotel_item_name = frappe.db.get_value(
                "Request Booking Details",
                payment_doc.request_booking_link,
                "cart_hotel_item"
            )

            if cart_hotel_item_name:
                cart_hotel = frappe.get_doc("Cart Hotel Item", cart_hotel_item_name)

                # Update room statuses based on payment result
                for room in cart_hotel.rooms:
                    if room.status in ["payment_pending", "booking_success"]:
                        room.status = new_cart_status
                cart_hotel.save(ignore_permissions=True)

                # Update request booking status based on room statuses
                update_request_status_from_rooms(payment_doc.request_booking_link, cart_hotel_item_name)

        frappe.db.commit()

        return {
                "success": True,
                "message": f"Payment {status} processed successfully",
                "data": {
                    "payment_id": payment_id,
                    "payment_status": new_payment_status,
                    "transaction_id": transaction_id or "",
                    "request_booking_link": payment_doc.request_booking_link,
                    "cart_status": new_cart_status
                }
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "payment_callback API Error")
        return {
                "success": False,
                "error": str(e)
        }


@frappe.whitelist(allow_guest=False)
def update_payment(order_id=None, transaction_id=None, request_booking_id=None, booking_id=None,
                   payment_status=None, callback_response=None,
                   payment_mode=None, total_amount=None, tax=None, currency=None):
    """
    API to update payment details and cascade status to linked doctypes.

    Lookup priority: order_id → transaction_id → request_booking_id → booking_id

    Args:
        order_id (str, optional): HitPay payment ID (data.id from create-payment response)
        transaction_id (str, optional): Transaction ID from payment gateway
        request_booking_id (str, optional): The request_booking_id field value
        booking_id (str, optional): The Hotel Bookings record name
        payment_status (str, optional): payment_pending, payment_success, payment_failure,
                                        payment_declined, payment_awaiting, payment_cancel
        callback_response (str/dict, optional): Raw callback payload from payment gateway
        payment_mode (str, optional): direct_pay, bill_to_company
        total_amount (float, optional): Total amount
        tax (float, optional): Tax amount
        currency (str, optional): Currency code

    Returns:
        dict: Response with success status and updated data
    """
    try:
        if not any([order_id, transaction_id, request_booking_id, booking_id]):
            return {"success": False, "error": "At least one identifier is required: order_id, transaction_id, request_booking_id, or booking_id"}

        payment_name = None

        # Lookup priority: order_id → transaction_id → request_booking_id → booking_id
        if order_id:
            payment_name = frappe.db.get_value(
                "Booking Payments", {"order_id": order_id}, "name"
            )

        if not payment_name and transaction_id:
            payment_name = frappe.db.get_value(
                "Booking Payments", {"transaction_id": transaction_id}, "name"
            )

        if not payment_name and request_booking_id:
            payment_name = frappe.db.get_value(
                "Booking Payments", {"request_booking_id": request_booking_id}, "name"
            )

        if not payment_name and booking_id:
            payment_name = frappe.db.get_value(
                "Booking Payments", {"booking_id": booking_id}, "name"
            )

        if not payment_name:
            return {"success": False, "error": "No Booking Payment found for the provided identifier"}

        payment_doc = frappe.get_doc("Booking Payments", payment_name)
        updated_fields = []

        if payment_status:
            payment_doc.payment_status = payment_status
            updated_fields.append("payment_status")

        if transaction_id:
            payment_doc.transaction_id = transaction_id
            updated_fields.append("transaction_id")

        if callback_response:
            payment_doc.call_back_res = json.dumps(callback_response) if isinstance(callback_response, dict) else callback_response
            updated_fields.append("call_back_res")

        if payment_mode:
            payment_doc.payment_mode = payment_mode
            updated_fields.append("payment_mode")

        if total_amount is not None:
            payment_doc.total_amount = total_amount
            updated_fields.append("total_amount")

        if tax is not None:
            payment_doc.tax = tax
            updated_fields.append("tax")

        if currency:
            payment_doc.currency = currency
            updated_fields.append("currency")

        if not updated_fields:
            return {"success": False, "error": "No fields provided to update"}

        payment_doc.save(ignore_permissions=True)

        # Cascade payment_status to Hotel Bookings and Request Booking Details
        if payment_status:
            # Update Hotel Bookings payment_status
            if payment_doc.booking_id:
                frappe.db.set_value(
                    "Hotel Bookings", payment_doc.booking_id,
                    "payment_status", payment_status
                )

            # Update Request Booking Details payment_status and request_status
            if payment_doc.request_booking_link:
                # Map payment_status to request_status
                payment_to_request_status_map = {
                    "payment_pending": "req_payment_pending",
                    "payment_success": "req_payment_success",
                    "payment_failure": "req_payment_pending",
                    "payment_declined": "req_payment_pending",
                    "payment_awaiting": "req_payment_pending",
                    "payment_cancel": "req_payment_pending"
                }
                new_request_status = payment_to_request_status_map.get(payment_status, "req_payment_pending")

                frappe.db.set_value(
                    "Request Booking Details", payment_doc.request_booking_link,
                    {
                        "payment_status": payment_status,
                        "request_status": new_request_status
                    }
                )

            # Update Cart Hotel Item room statuses and Request Booking status
            if payment_doc.request_booking_link:
                cart_hotel_item_name = frappe.db.get_value(
                    "Request Booking Details",
                    payment_doc.request_booking_link,
                    "cart_hotel_item"
                )

                if cart_hotel_item_name:
                    cart_hotel = frappe.get_doc("Cart Hotel Item", cart_hotel_item_name)

                    cart_status_map = {
                        "payment_pending": "payment_pending",
                        "payment_success": "payment_success",
                        "payment_failure": "payment_failure",
                        "payment_cancel": "payment_cancel"
                    }
                    new_cart_status = cart_status_map.get(payment_status)

                    if new_cart_status:
                        for room in cart_hotel.rooms:
                            if room.status in ["approved", "payment_pending", "payment_failure"]:
                                room.status = new_cart_status
                        cart_hotel.save(ignore_permissions=True)

                    # Update Request Booking status based on room statuses
                    update_request_status_from_rooms(payment_doc.request_booking_link, cart_hotel_item_name)

        frappe.db.commit()

        return {
            "success": True,
            "message": "Payment updated successfully",
            "data": {
                "payment_id": payment_name,
                "order_id": payment_doc.order_id,
                "transaction_id": payment_doc.transaction_id,
                "request_booking_link": payment_doc.request_booking_link,
                "booking_id": payment_doc.booking_id,
                "updated_fields": updated_fields,
                "payment_status": payment_doc.payment_status
            }
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "update_payment API Error")
        return {"success": False, "error": str(e)}

