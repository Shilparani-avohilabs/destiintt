import frappe
import json
import requests
from datetime import timedelta, datetime
from destiin.destiin.custom.api.request_booking.request import update_request_status_from_rooms

EMAIL_API_URL = "http://16.112.56.253/main/v1/email/send"
HITPAY_API_URL= "http://16.112.56.253/payments/v1/hitpay/create-payment"


def send_payment_email(to_emails, payment_url, hotel_name, amount, currency, employee_name, check_in, check_out, room_type="", number_of_guests=0, expiry_time=0, agent_email=""):
    """
    Send payment URL email to the specified recipients.

    Args:
        to_emails (list): List of email addresses to send to
        payment_url (str): The HitPay payment URL
        hotel_name (str): Name of the hotel
        amount (float): Payment amount
        currency (str): Currency code
        employee_name (str): Name of the employee
        check_in (str): Check-in date
        check_out (str): Check-out date
        room_type (str): Room type name
        number_of_guests (int): Number of guests
        expiry_time (int): Expiry time in minutes
        agent_email (str): Agent email address

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    if not to_emails:
        return False

    # Filter out empty emails
    valid_emails = [email for email in to_emails if email]
    if not valid_emails:
        return False

    subject = f"Payment Link for Hotel Booking - {hotel_name}"

    body = f"""<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml"
    xmlns:o="urn:schemas-microsoft-com:office:office">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="x-apple-disable-message-reformatting">
    <title>Payment Required - Destiin</title>
    <!--[if mso]>
    <noscript>
        <xml>
            <o:OfficeDocumentSettings>
                <o:PixelsPerInch>96</o:PixelsPerInch>
            </o:OfficeDocumentSettings>
        </xml>
    </noscript>
    <![endif]-->
    <style>
        /* Reset styles */
        body,
        table,
        td,
        a {{{{
            -webkit-text-size-adjust: 100%;
            -ms-text-size-adjust: 100%;
        }}}}

        table,
        td {{{{
            mso-table-lspace: 0pt;
            mso-table-rspace: 0pt;
        }}}}

        img {{{{
            -ms-interpolation-mode: bicubic;
            border: 0;
            height: auto;
            line-height: 100%;
            outline: none;
            text-decoration: none;
        }}}}

        /* Base styles */
        body {{{{
            margin: 0 !important;
            padding: 0 !important;
            width: 100% !important;
            height: 100% !important;
            font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif !important;
            background-color: transparent !important;
            color: #ededed !important;
        }}}}

        /* Prevent auto-scaling in iOS */
        * {{{{
            -webkit-text-size-adjust: none;
        }}}}

        /* Link styles */
        a {{{{
            color: #7ecda5;
            text-decoration: none;
        }}}}

        a:hover {{{{
            text-decoration: underline;
        }}}}

        /* Responsive */
        @media only screen and (max-width: 700px) {{{{
            .email-container {{{{
                width: 100% !important;
            }}}}

            .mobile-padding {{{{
                padding: 20px !important;
            }}}}

            .mobile-text-center {{{{
                text-align: center !important;
            }}}}

            .cta-button {{{{
                padding: 14px 36px !important;
                font-size: 15px !important;
            }}}}
        }}}}
    </style>
</head>

<body
    style="margin: 0; padding: 0; font-family: 'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">

    <!-- Wrapper Table -->
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
        <tr>
            <td align="center" style="padding: 20px 0;">

                <!-- Main Container -->
                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="700"
                    class="email-container"
                    style="max-width: 700px; background-color: #0e0f1d; border-radius: 16px; overflow: hidden;">

                    <!-- Header -->
                    <tr>
                        <td
                            style="background: linear-gradient(135deg, #0e0f1d 0%, #1a1d35 100%); padding: 40px 30px; text-align: center; border-bottom: 2px solid rgba(126, 205, 165, 0.2);">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td align="center">
                                        <h1
                                            style="margin: 0 0 8px 0; font-size: 32px; font-weight: 700; color: #7ecda5; letter-spacing: -0.5px;">
                                            DESTIIN</h1>
                                        <p style="margin: 0; font-size: 14px; color: #a0a0a0; font-weight: 400;">Your
                                            Travel, Simplified</p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px 40px;" class="mobile-padding">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">

                                <!-- Greeting -->
                                <tr>
                                    <td style="padding-bottom: 16px;">
                                        <p style="margin: 0; font-size: 18px; font-weight: 600; color: #ededed;">Hello
                                            {employee_name or 'Guest'},</p>
                                    </td>
                                </tr>

                                <!-- Message -->
                                <tr>
                                    <td style="padding-bottom: 24px;">
                                        <p style="margin: 0; font-size: 15px; color: #c0c0c0; line-height: 1.7;">
                                            Great news! Your hotel selection has been confirmed. Please complete the
                                            payment to finalize your booking.
                                        </p>
                                    </td>
                                </tr>

                                <!-- Hotel Details Card -->
                                <tr>
                                    <td style="padding: 24px 0;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0"
                                            width="100%"
                                            style="background-color: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px;">
                                            <tr>
                                                <td style="padding: 24px;">
                                                    <table role="presentation" cellspacing="0" cellpadding="0"
                                                        border="0" width="100%">
                                                        <!-- Card Title -->
                                                        <tr>
                                                            <td colspan="2" style="padding-bottom: 16px;">
                                                                <p
                                                                    style="margin: 0; font-size: 14px; font-weight: 600; color: #7ecda5; text-transform: uppercase; letter-spacing: 1px;">
                                                                    🏨 BOOKING DETAILS</p>
                                                            </td>
                                                        </tr>

                                                        <!-- Hotel Name -->
                                                        <tr>
                                                            <td
                                                                style="padding: 8px 16px 8px 0; font-size: 13px; color: #a0a0a0; font-weight: 500; width: 40%;">
                                                                Hotel:</td>
                                                            <td
                                                                style="padding: 8px 0; font-size: 14px; color: #ededed; font-weight: 500;">
                                                                {hotel_name}</td>
                                                        </tr>

                                                        <!-- Room Type -->
                                                        <tr>
                                                            <td
                                                                style="padding: 8px 16px 8px 0; font-size: 13px; color: #a0a0a0; font-weight: 500;">
                                                                Room Type:</td>
                                                            <td
                                                                style="padding: 8px 0; font-size: 14px; color: #ededed; font-weight: 500;">
                                                                {room_type or 'Standard Room'}</td>
                                                        </tr>

                                                        <!-- Check-in -->
                                                        <tr>
                                                            <td
                                                                style="padding: 8px 16px 8px 0; font-size: 13px; color: #a0a0a0; font-weight: 500;">
                                                                Check-in:</td>
                                                            <td
                                                                style="padding: 8px 0; font-size: 14px; color: #ededed; font-weight: 500;">
                                                                {check_in or 'N/A'}</td>
                                                        </tr>

                                                        <!-- Check-out -->
                                                        <tr>
                                                            <td
                                                                style="padding: 8px 16px 8px 0; font-size: 13px; color: #a0a0a0; font-weight: 500;">
                                                                Check-out:</td>
                                                            <td
                                                                style="padding: 8px 0; font-size: 14px; color: #ededed; font-weight: 500;">
                                                                {check_out or 'N/A'}</td>
                                                        </tr>

                                                        <!-- Guests -->
                                                        <tr>
                                                            <td
                                                                style="padding: 8px 16px 8px 0; font-size: 13px; color: #a0a0a0; font-weight: 500;">
                                                                Guests:</td>
                                                            <td
                                                                style="padding: 8px 0; font-size: 14px; color: #ededed; font-weight: 500;">
                                                                {number_of_guests}</td>
                                                        </tr>

                                                        <!-- Total Amount -->
                                                        <tr>
                                                            <td colspan="2"
                                                                style="padding-top: 16px; border-top: 1px solid rgba(255, 255, 255, 0.1);">
                                                            </td>
                                                        </tr>
                                                        <tr>
                                                            <td
                                                                style="padding: 12px 16px 8px 0; font-size: 15px; color: #7ecda5; font-weight: 600;">
                                                                Total Amount:</td>
                                                            <td
                                                                style="padding: 12px 0 8px 0; font-size: 18px; color: #7ecda5; font-weight: 700;">
                                                                {currency} {amount:.2f}</td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>

                                <!-- Payment Link Expiry Warning -->
                                <tr>
                                    <td align="center" style="padding: 24px 0;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0"
                                            width="100%"
                                            style="background-color: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 8px;">
                                            <tr>
                                                <td style="padding: 16px; text-align: center;">
                                                    <p
                                                        style="margin: 0 0 4px 0; font-size: 13px; color: #fbbf24; font-weight: 600;">
                                                        ⏱️ PAYMENT LINK EXPIRES IN</p>
                                                    <p
                                                        style="margin: 0; font-size: 20px; color: #fbbf24; font-weight: 700;">
                                                        {expiry_time} Minutes</p>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>

                                <!-- CTA Button -->
                                <tr>
                                    <td align="center" style="padding: 32px 0;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                                            <tr>
                                                <td align="center"
                                                    style="border-radius: 12px; background-color: #7ecda5;">
                                                    <a href="{payment_url}" target="_blank" class="cta-button"
                                                        style="display: inline-block; padding: 16px 48px; font-size: 16px; font-weight: 600; color: #0e0f1d; text-decoration: none; border-radius: 12px; font-family: 'Outfit', Arial, sans-serif;">
                                                        Complete Payment Now
                                                    </a>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>

                                <!-- Important Note -->
                                <tr>
                                    <td style="padding: 24px 0;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0"
                                            width="100%"
                                            style="background-color: rgba(126, 205, 165, 0.1); border-left: 4px solid #7ecda5; border-radius: 4px;">
                                            <tr>
                                                <td style="padding: 16px 20px;">
                                                    <p
                                                        style="margin: 0 0 8px 0; font-size: 14px; color: #7ecda5; font-weight: 600;">
                                                        📌 Important</p>
                                                    <p
                                                        style="margin: 0; font-size: 13px; color: #c0c0c0; line-height: 1.6;">
                                                        After completing the payment, your booking will be confirmed
                                                        automatically. You will receive a confirmation email with your
                                                        booking details and voucher.
                                                    </p>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>

                                <!-- Divider -->
                                <tr>
                                    <td style="padding: 32px 0;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0"
                                            width="100%">
                                            <tr>
                                                <td style="border-top: 1px solid rgba(255, 255, 255, 0.1);"></td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>

                                <!-- Help Text -->
                                <tr>
                                    <td align="center" style="padding: 24px 0;">
                                        <p
                                            style="margin: 0 0 8px 0; font-size: 14px; color: #a0a0a0; line-height: 1.6;">
                                            Need assistance or have questions?
                                        </p>
                                        <p style="margin: 0; font-size: 14px; color: #a0a0a0; line-height: 1.6;">
                                            Contact your travel agent at <a href="mailto:{agent_email}"
                                                style="color: #7ecda5; text-decoration: none; font-weight: 500;">{agent_email}</a>
                                        </p>
                                    </td>
                                </tr>

                            </table>
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td
                            style="background-color: #050a14; padding: 30px; text-align: center; border-top: 1px solid rgba(255, 255, 255, 0.05);">
                            <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                <tr>
                                    <td align="center">
                                        <p style="margin: 0 0 8px 0; font-size: 12px; color: #a0a0a0;">
                                            © 2026 Destiin. All rights reserved.
                                        </p>
                                        <p style="margin: 0 0 16px 0; font-size: 12px; color: #a0a0a0;">
                                            This is an automated payment notification for your booking.
                                        </p>
                                        <p style="margin: 0; font-size: 12px;">
                                            <a href="[PRIVACY_POLICY_URL]"
                                                style="color: #7ecda5; text-decoration: none; font-weight: 500; margin: 0 12px;">Privacy
                                                Policy</a>
                                            <a href="[TERMS_URL]"
                                                style="color: #7ecda5; text-decoration: none; font-weight: 500; margin: 0 12px;">Terms
                                                of Service</a>
                                            <a href="[SUPPORT_URL]"
                                                style="color: #7ecda5; text-decoration: none; font-weight: 500; margin: 0 12px;">Support</a>
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                </table>
                <!-- End Main Container -->

            </td>
        </tr>
    </table>
    <!-- End Wrapper Table -->

</body>

</html>
"""

    try:
        headers = {
            "Content-Type": "application/json",
            "info": "true"
        }

        payload = {
            "toEmails": valid_emails,
            "subject": subject,
            "body": body
        }

        response = requests.post(
            EMAIL_API_URL,
            headers=headers,
            data=json.dumps(payload),
            timeout=30
        )

        if response.status_code == 200:
            return True
        else:
            frappe.log_error(
                f"Email API Error: Status {response.status_code}, Response: {response.text}",
                "send_payment_email Error"
            )
            return False
    except Exception as e:
        frappe.log_error(f"Email sending failed: {str(e)}", "send_payment_email Error")
        return False

# SBT
@frappe.whitelist(allow_guest=False)
def create_payment_url(request_booking_id, mode=None):
    """
    API to create or retrieve a payment URL using HitPay.

    This API handles three scenarios:
    1. If a pending payment exists and is NOT expired:
       - Returns the existing payment URL
       - Sends payment email to employee and agent
    2. If a pending payment exists and IS expired:
       - Updates the payment status to 'payment_expired'
       - Creates a new payment URL
       - Links to existing Request Booking and Hotel Bookings
    3. If no payment exists:
       - Creates a new Booking Payments record
       - Calls HitPay API to create a payment request
       - Links to Request Booking and Hotel Bookings

    Args:
        request_booking_id (str): The request_booking_id field value (required)
        mode (str, optional): Payment mode - 'direct_pay' or 'bill_to_company' (default: 'direct_pay')

    Returns:
        dict: Response with success status, payment URL data, and is_existing flag
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

        # ==================== CHECK FOR EXISTING PAYMENT ====================
        # Check if a payment already exists for this request booking
        existing_payment = frappe.db.get_value(
            "Booking Payments",
            {
                "request_booking_link": request_booking_name,
                "payment_status": ["in", ["payment_pending", "payment_expired"]]
            },
            ["name", "payment_status", "expire_at", "created_at"],
            order_by="creation desc",
            as_dict=True
        )

        if existing_payment:
            existing_payment_doc = frappe.get_doc("Booking Payments", existing_payment.name)

            # Check if payment is expired
            is_expired = False
            if existing_payment.payment_status == "payment_expired":
                is_expired = True
            elif existing_payment.expire_at:
                current_time = frappe.utils.now_datetime()
                if current_time > existing_payment.expire_at:
                    is_expired = True
                    # Update status to expired
                    existing_payment_doc.payment_status = "payment_expired"
                    existing_payment_doc.save(ignore_permissions=True)

                    # Update Hotel Bookings payment_status if linked
                    if existing_payment_doc.booking_id:
                        frappe.db.set_value(
                            "Hotel Bookings",
                            existing_payment_doc.booking_id,
                            "payment_status",
                            "payment_expired"
                        )

                    # Update Request Booking Details payment_status
                    frappe.db.set_value(
                        "Request Booking Details",
                        request_booking_name,
                        "payment_status",
                        "payment_expired"
                    )
                    frappe.db.commit()

            # If NOT expired, return existing payment URL and send email
            if not is_expired:
                # Get the existing payment URL from child table
                existing_payment_url = ""
                if existing_payment_doc.payment_link and len(existing_payment_doc.payment_link) > 0:
                    existing_payment_url = existing_payment_doc.payment_link[-1].payment_url or ""

                if existing_payment_url:
                    # Get employee details for email
                    employee_name = ""
                    employee_email = request_booking.employee_email or ""
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
                            if not employee_email:
                                employee_email = employee_details.get("company_email") or employee_details.get("personal_email") or ""
                            employee_phone = employee_details.get("cell_number") or ""

                    # Get agent email
                    agent_email = ""
                    if request_booking.agent:
                        agent_email = frappe.db.get_value("User", request_booking.agent, "email") or ""

                    # Send payment URL email
                    email_recipients = []
                    if employee_email:
                        email_recipients.append(employee_email)
                    if agent_email:
                        email_recipients.append(agent_email)

                    # Calculate remaining expiry time in minutes
                    expiry_minutes = 0
                    if existing_payment.expire_at:
                        current_time = frappe.utils.now_datetime()
                        remaining = existing_payment.expire_at - current_time
                        expiry_minutes = max(0, int(remaining.total_seconds() / 60))

                    email_sent = False
                    if email_recipients:
                        email_sent = send_payment_email(
                            to_emails=email_recipients,
                            payment_url=existing_payment_url,
                            hotel_name=existing_payment_doc.hotel_name or "Hotel",
                            amount=float(existing_payment_doc.total_amount or 0) + float(existing_payment_doc.tax or 0),
                            currency=existing_payment_doc.currency or "USD",
                            employee_name=employee_name,
                            check_in=str(request_booking.check_in) if request_booking.check_in else None,
                            check_out=str(request_booking.check_out) if request_booking.check_out else None,
                            room_type="",
                            number_of_guests=existing_payment_doc.adult_count or 0,
                            expiry_time=expiry_minutes,
                            agent_email=agent_email or ""
                        )

                    return {
                        "success": True,
                        "message": "Existing payment URL found and email sent",
                        "is_existing": True,
                        "data": {
                            "payment_id": existing_payment_doc.name,
                            "request_booking_id": request_booking_id,
                            "request_booking_name": request_booking_name,
                            "payment_url": existing_payment_url,
                            "amount": float(existing_payment_doc.total_amount or 0) + float(existing_payment_doc.tax or 0),
                            "currency": existing_payment_doc.currency,
                            "hotel_id": existing_payment_doc.hotel_id,
                            "hotel_name": existing_payment_doc.hotel_name,
                            "room_count": existing_payment_doc.room_count,
                            "total_amount": existing_payment_doc.total_amount,
                            "tax": existing_payment_doc.tax,
                            "employee_name": employee_name,
                            "employee_email": employee_email,
                            "agent_email": agent_email,
                            "email_sent": email_sent,
                            "email_recipients": email_recipients,
                            "payment_status": existing_payment_doc.payment_status,
                            "payment_mode": existing_payment_doc.payment_mode,
                            "expire_at": str(existing_payment_doc.expire_at) if existing_payment_doc.expire_at else None
                        }
                    }

            # If expired, we'll continue below to create a new payment
            # Reload request_booking as it may have been updated
            request_booking = frappe.get_doc("Request Booking Details", request_booking_name)

        # ==================== END CHECK FOR EXISTING PAYMENT ====================

        # Get employee details for payment — prefer employee_email stored on the request booking
        employee_name = ""
        employee_email = request_booking.employee_email or ""
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
                if not employee_email:
                    employee_email = employee_details.get("company_email") or employee_details.get("personal_email") or ""
                employee_phone = employee_details.get("cell_number") or ""

        # Get agent email from User doctype
        agent_email = ""
        if request_booking.agent:
            agent_email = frappe.db.get_value("User", request_booking.agent, "email") or ""

        # Get all Cart Hotel Items linked to this Request Booking via back-link
        cart_hotel_item_names = frappe.get_all(
            "Cart Hotel Item",
            filters={"request_booking": request_booking_name},
            pluck="name"
        )

        if not cart_hotel_item_names:
            return {
                "success": False,
                "error": "No Cart Hotel Item linked to this Request Booking"
            }

        # Collect approved rooms across all linked Cart Hotel Items
        cart_hotel_docs = []
        approved_rooms = []
        cart_hotel = None
        for chi_name in cart_hotel_item_names:
            chi_doc = frappe.get_doc("Cart Hotel Item", chi_name)
            cart_hotel_docs.append(chi_doc)
            if not cart_hotel:
                cart_hotel = chi_doc
            for room in chi_doc.rooms:
                if room.status in ["approved", "payment_pending", "payment_success", "payment_failure"]:
                    approved_rooms.append(room)

        if not approved_rooms:
            return {
                "success": False,
                "error": "No approved rooms found in Cart Hotel Item"
            }

        # Calculate total amount and tax from approved rooms
        total_amount = sum(float(room.total_price or room.price or 0) for room in approved_rooms)
        total_tax = sum(float(room.tax or 0) for room in approved_rooms)
        currency = approved_rooms[0].currency if approved_rooms[0].currency else "USD"

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
        # hitpay_url = "http://16.112.56.253/payments/v1/hitpay/create-payment"
        headers = {
            "Content-Type": "application/json"
        }

        # Build purpose string
        purpose = f"Hotel Booking Payment - {cart_hotel.hotel_name or 'Hotel'}"

        # Fetch config for redirect URL and expiration settings
        config = frappe.db.get_value(
            "Hotel Booking Config",
            {"company": request_booking.company},
            ["payment_redirect_url", "d_p_expire_type", "d_p_expire_value", "c_p_expire_type", "c_p_expire_value"],
            as_dict=True
        )

        payment_redirect_url = config.get("payment_redirect_url") if config else None

        # Build expire_after string based on mode
        expire_after = None
        if config:
            if mode == "direct_pay":
                expire_type = config.get("d_p_expire_type")
                expire_value = int(config.get("d_p_expire_value") or 0)
            else:
                expire_type = config.get("c_p_expire_type")
                expire_value = int(config.get("c_p_expire_value") or 0)

            if expire_type and expire_value:
                expire_after = f"{expire_value} {expire_type}"

        payload = {
            "amount": amount,
            "currency":currency,
            "email": employee_email or "customer@example.com",
            "name": employee_name or "Customer",
            "phone": employee_phone or "+918760839303",
            "purpose": purpose,
            "request_booking_id":request_booking_id,
            "redirect_url": payment_redirect_url,
            "payment_methods": ["card"]
        }

        # Add expire_after to payload if configured
        if expire_after:
            payload["expires_after"] = expire_after

        # Call HitPay API
        response = requests.post(
            HITPAY_API_URL,
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

        # Calculate expire_at using the expire_type and expire_value extracted earlier
        if expire_after and expire_type and expire_value:
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

        # Update Request Booking Details with the payment link (Table MultiSelect) and payment status
        request_booking.append("payment", {
            "booking_payment": payment_doc.name
        })
        request_booking.payment_status = "payment_pending"
        request_booking.save(ignore_permissions=True)

        # Update cart hotel room statuses to payment_pending across all linked CHIs
        for chi_doc in cart_hotel_docs:
            for room in chi_doc.rooms:
                if room.status == "approved":
                    room.status = "payment_pending"
            chi_doc.save(ignore_permissions=True)

        # Update request booking status based on room statuses
        update_request_status_from_rooms(request_booking_name)

        # Explicitly set request_status after update_request_status_from_rooms to ensure it's payment_pending
        frappe.db.set_value("Request Booking Details", request_booking_name, "request_status", "req_payment_pending")

        frappe.db.commit()

        # Send payment URL email to employee and agent
        email_recipients = []
        if employee_email:
            email_recipients.append(employee_email)
        if agent_email:
            email_recipients.append(agent_email)

        # Calculate expiry time in minutes
        expiry_minutes = 0
        if expire_type and expire_value:
            if expire_type == "mins":
                expiry_minutes = expire_value
            elif expire_type == "hours":
                expiry_minutes = expire_value * 60
            elif expire_type == "days":
                expiry_minutes = expire_value * 1440

        # Get room type from first approved room
        room_type = approved_rooms[0].room_name if approved_rooms else ""

        email_sent = False
        if email_recipients:
            email_sent = send_payment_email(
                to_emails=email_recipients,
                payment_url=payment_url,
                hotel_name=cart_hotel.hotel_name or "Hotel",
                amount=amount,
                currency=currency,
                employee_name=employee_name,
                check_in=str(request_booking.check_in) if request_booking.check_in else None,
                check_out=str(request_booking.check_out) if request_booking.check_out else None,
                room_type=room_type,
                number_of_guests=request_booking.adult_count or 0,
                expiry_time=expiry_minutes,
                agent_email=agent_email or ""
            )

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
                "agent_email": agent_email,
                "email_sent": email_sent,
                "email_recipients": email_recipients,
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
                "payment_cancel": "req_payment_pending",
                "payment_expired": "req_payment_pending"
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
            cart_hotel_item_names = frappe.get_all(
                "Cart Hotel Item",
                filters={"request_booking": payment_doc.request_booking_link},
                pluck="name"
            )

            if cart_hotel_item_names:
                for chi_name in cart_hotel_item_names:
                    cart_hotel = frappe.get_doc("Cart Hotel Item", chi_name)
                    for room in cart_hotel.rooms:
                        if room.status in ["payment_pending", "booking_success"]:
                            room.status = new_cart_status
                    cart_hotel.save(ignore_permissions=True)

                # Update request booking status based on room statuses
                update_request_status_from_rooms(payment_doc.request_booking_link)

            # Explicitly set request_status after update_request_status_from_rooms to ensure correct status
            frappe.db.set_value(
                "Request Booking Details",
                payment_doc.request_booking_link,
                "request_status", new_request_status
            )

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
                   payment_mode=None, total_amount=None, tax=None, currency=None,
                   refund_status=None, refund_amount=None, refund_date=None,
                   cancellation_reason=None, remarks=None):
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
        refund_status (str, optional): initialized, partially_refunded, fully_refunded
        refund_amount (float, optional): Refund amount
        refund_date (str, optional): Refund date (YYYY-MM-DD)
        cancellation_reason (str, optional): Reason for cancellation
        remarks (str, optional): Additional remarks

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
            # Append new callback response with timestamp instead of replacing
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_entry = {
                "timestamp": timestamp,
                "data": callback_response if isinstance(callback_response, dict) else json.loads(callback_response) if callback_response else {}
            }

            existing_callbacks = []
            if payment_doc.call_back_res:
                try:
                    existing_data = json.loads(payment_doc.call_back_res)
                    # Check if existing data is already a list of callbacks
                    if isinstance(existing_data, list):
                        existing_callbacks = existing_data
                    else:
                        # Wrap existing single response in list format
                        existing_callbacks = [{"timestamp": "legacy", "data": existing_data}]
                except (json.JSONDecodeError, TypeError):
                    # If existing data is not valid JSON, keep it as legacy entry
                    existing_callbacks = [{"timestamp": "legacy", "data": payment_doc.call_back_res}]

            existing_callbacks.append(new_entry)
            payment_doc.call_back_res = json.dumps(existing_callbacks, indent=2)
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

        # Handle refund fields
        if refund_status:
            valid_refund_statuses = ["initialized", "partially_refunded", "fully_refunded"]
            if refund_status not in valid_refund_statuses:
                return {"success": False, "error": f"Invalid refund_status. Must be one of: {', '.join(valid_refund_statuses)}"}
            payment_doc.refund_status = refund_status
            updated_fields.append("refund_status")

        if refund_amount is not None:
            payment_doc.refund_amount = float(refund_amount)
            updated_fields.append("refund_amount")

        if refund_date:
            payment_doc.refund_date = refund_date
            updated_fields.append("refund_date")

        if cancellation_reason:
            payment_doc.cancellation_reason = cancellation_reason
            updated_fields.append("cancellation_reason")

        if remarks:
            payment_doc.remarks = remarks
            updated_fields.append("remarks")

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
                # Map payment_status to request_status (keep req_payment_pending for expired)
                payment_to_request_status_map = {
                    "payment_pending": "req_payment_pending",
                    "payment_success": "req_payment_success",
                    "payment_failure": "req_payment_pending",
                    "payment_declined": "req_payment_pending",
                    "payment_awaiting": "req_payment_pending",
                    "payment_cancel": "req_payment_pending",
                    "payment_expired": "req_payment_pending",
                    "payment_refunded":"req_closed"
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
            # Note: Do not update cart room status when payment expires - keep as payment_pending
            if payment_doc.request_booking_link and payment_status != "payment_expired":
                cart_hotel_item_names = frappe.get_all(
                    "Cart Hotel Item",
                    filters={"request_booking": payment_doc.request_booking_link},
                    pluck="name"
                )

                if cart_hotel_item_names:
                    cart_status_map = {
                        "payment_pending": "payment_pending",
                        "payment_success": "payment_success",
                        "payment_failure": "payment_failure",
                        "payment_cancel": "payment_cancel",
                        "payment_refunded": "payment_success"
                    }
                    new_cart_status = cart_status_map.get(payment_status)

                    if new_cart_status:
                        for chi_name in cart_hotel_item_names:
                            cart_hotel = frappe.get_doc("Cart Hotel Item", chi_name)
                            for room in cart_hotel.rooms:
                                if room.status in ["approved", "payment_pending", "payment_failure"]:
                                    room.status = new_cart_status
                            cart_hotel.save(ignore_permissions=True)

                    # Update Request Booking status based on room statuses
                    update_request_status_from_rooms(payment_doc.request_booking_link)

                # Explicitly set request_status after update_request_status_from_rooms to ensure correct status
                frappe.db.set_value(
                    "Request Booking Details", payment_doc.request_booking_link,
                    "request_status", new_request_status
                )

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


@frappe.whitelist(allow_guest=False)
def check_payment_expiry(request_booking_id=None, payment_id=None):
    """
    API to check if a payment has expired based on the expire_at field
    and update the payment_status to 'payment_expired' across all linked doctypes.

    This API:
    1. Checks if the current time has passed the expire_at datetime
    2. If expired and payment is still pending, updates:
       - Booking Payments payment_status to 'payment_expired'
       - Hotel Bookings payment_status to 'payment_expired'
       - Request Booking Details payment_status to 'payment_expired'
       - Request Booking Details request_status to 'req_payment_expired'

    Args:
        request_booking_id (str, optional): The request_booking_id field value
        payment_id (str, optional): The Booking Payments record name

    Returns:
        dict: Response with expiry status and updated data
    """
    try:
        if not request_booking_id and not payment_id:
            return {
                "success": False,
                "error": "Either request_booking_id or payment_id is required"
            }

        payment_doc = None

        # Find payment by payment_id or request_booking_id
        if payment_id:
            if frappe.db.exists("Booking Payments", payment_id):
                payment_doc = frappe.get_doc("Booking Payments", payment_id)

        if not payment_doc and request_booking_id:
            # Find the request booking name first
            request_booking_name = frappe.db.get_value(
                "Request Booking Details",
                {"request_booking_id": request_booking_id},
                "name"
            )
            if request_booking_name:
                # Get the latest payment linked to this request booking
                payment_name = frappe.db.get_value(
                    "Booking Payments",
                    {"request_booking_link": request_booking_name, "payment_status": "payment_pending"},
                    "name",
                    order_by="creation desc"
                )
                if payment_name:
                    payment_doc = frappe.get_doc("Booking Payments", payment_name)

        if not payment_doc:
            return {
                "success": False,
                "error": "No pending payment found for the provided identifier"
            }

        # Check if payment is already not pending
        if payment_doc.payment_status != "payment_pending":
            return {
                "success": True,
                "expired": False,
                "message": f"Payment is not pending. Current status: {payment_doc.payment_status}",
                "data": {
                    "payment_id": payment_doc.name,
                    "payment_status": payment_doc.payment_status,
                    "expire_at": str(payment_doc.expire_at) if payment_doc.expire_at else None
                }
            }

        # Check if expire_at is set
        if not payment_doc.expire_at:
            return {
                "success": True,
                "expired": False,
                "message": "Payment has no expiry set",
                "data": {
                    "payment_id": payment_doc.name,
                    "payment_status": payment_doc.payment_status,
                    "expire_at": None
                }
            }

        # Check if current time has passed expire_at
        current_time = frappe.utils.now_datetime()
        expire_at = payment_doc.expire_at

        if current_time <= expire_at:
            return {
                "success": True,
                "expired": False,
                "message": "Payment has not expired yet",
                "data": {
                    "payment_id": payment_doc.name,
                    "payment_status": payment_doc.payment_status,
                    "expire_at": str(expire_at),
                    "current_time": str(current_time)
                }
            }

        # Payment has expired - update all statuses
        payment_doc.payment_status = "payment_expired"
        payment_doc.save(ignore_permissions=True)

        # Update Hotel Bookings payment_status if linked
        if payment_doc.booking_id:
            frappe.db.set_value(
                "Hotel Bookings",
                payment_doc.booking_id,
                "payment_status",
                "payment_expired"
            )

        # Update Request Booking Details payment_status if linked (keep request_status as payment_pending)
        if payment_doc.request_booking_link:
            frappe.db.set_value(
                "Request Booking Details",
                payment_doc.request_booking_link,
                "payment_status",
                "payment_expired"
            )

        frappe.db.commit()

        return {
            "success": True,
            "expired": True,
            "message": "Payment has expired and statuses have been updated",
            "data": {
                "payment_id": payment_doc.name,
                "payment_status": "payment_expired",
                "expire_at": str(expire_at),
                "current_time": str(current_time),
                "request_booking_link": payment_doc.request_booking_link,
                "booking_id": payment_doc.booking_id
            }
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "check_payment_expiry API Error")
        return {"success": False, "error": str(e)}

