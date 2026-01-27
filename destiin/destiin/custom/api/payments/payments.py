import frappe
import json
import requests
from destiin.destiin.custom.api.request_booking.request import update_request_status_from_rooms

# SBT
@frappe.whitelist(allow_guest=False)
def create_payment_url(payment_id):
    """
    API to create a payment URL using HitPay and update the Booking Payments record.

    This API:
    1. Fetches the Booking Payments record by payment_id
    2. Gets employee details (name, email, phone)
    3. Calls HitPay API to create a payment request
    4. Updates the Booking Payments record with the payment URL
    5. Updates payment status to 'payment_awaiting'

    Args:
        payment_id (str): The Booking Payments record name/ID (required)

    Returns:
        dict: Response with success status and payment URL data
    """
    try:
        if not payment_id:
            return {
                    "success": False,
                    "error": "payment_id is required"
            }

        # Fetch the Booking Payments record
        payment_doc = frappe.get_doc("Booking Payments", payment_id)

        if not payment_doc:
            return {
                    "success": False,
                    "error": f"Booking Payment not found for ID: {payment_id}"
            }

        # Get employee details for payment
        employee_name = ""
        employee_email = ""
        employee_phone = ""

        if payment_doc.employee:
            employee_details = frappe.get_value(
                "Employee",
                payment_doc.employee,
                ["employee_name", "company_email", "personal_email", "cell_number"],
                as_dict=True
            )
            if employee_details:
                employee_name = employee_details.get("employee_name", "")
                employee_email = employee_details.get("company_email") or employee_details.get("personal_email") or ""
                employee_phone = employee_details.get("cell_number") or ""

        # Prepare payment amount
        amount = float(payment_doc.total_amount or 0) + float(payment_doc.tax or 0)

        if amount <= 0:
            return {
                    "success": False,
                    "error": "Payment amount must be greater than 0"
            }

        # Prepare HitPay API request
        hitpay_url = "http://16.112.56.253/payments/v1/hitpay/create-payment"
        headers = {
            "Content-Type": "application/json"
        }

        # Build purpose string
        purpose = f"Hotel Booking Payment - {payment_doc.hotel_name or 'Hotel'}"
        if payment_doc.booking_id:
            purpose = f"Booking {payment_doc.booking_id.name if hasattr(payment_doc.booking_id, 'name') else payment_doc.booking_id} - {payment_doc.hotel_name or 'Hotel'}"

        payload = {
            "amount": amount,
            "email": employee_email or "customer@example.com",
            "name": employee_name or "Customer",
            "phone": employee_phone or "+918760839303",
            "purpose": purpose,
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
        payment_url = hitpay_response.get("url") or hitpay_response.get("payment_url") or hitpay_response.get("data", {}).get("url") or ""

        if not payment_url:
            return {
                    "success": False,
                    "error": "Payment URL not found in HitPay response",
                    "hitpay_response": hitpay_response
            }

        # Create Booking Payment URL child record
        payment_url_doc = frappe.new_doc("Booking Payment URL")
        payment_url_doc.payment_url = payment_url
        payment_url_doc.parent = payment_doc.name
        payment_url_doc.parenttype = "Booking Payments"
        payment_url_doc.parentfield = "payment_link"
        payment_url_doc.insert(ignore_permissions=True)

        # Update Booking Payments record
        payment_doc.payment_status = "payment_awaiting"
        payment_doc.save(ignore_permissions=True)

        # Also update the linked Hotel Bookings payment status
        if payment_doc.booking_id:
            frappe.db.set_value(
                "Hotel Bookings",
                payment_doc.booking_id,
                "payment_status",
                "payment_awaiting"
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

                # Update room statuses to payment_pending (payment awaiting is still pending)
                for room in cart_hotel.rooms:
                    if room.status in ["approved", "booking_success"]:
                        room.status = "payment_pending"
                cart_hotel.save(ignore_permissions=True)

                # Update request booking status based on room statuses
                update_request_status_from_rooms(payment_doc.request_booking_link, cart_hotel_item_name)

        frappe.db.commit()

        return {
                "success": True,
                "message": "Payment URL created successfully",
                "data": {
                    "payment_id": payment_id,
                    "payment_url": payment_url,
                    "amount": amount,
                    "currency": payment_doc.currency or "INR",
                    "employee_name": employee_name,
                    "employee_email": employee_email,
                    "payment_status": "payment_awaiting",
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

