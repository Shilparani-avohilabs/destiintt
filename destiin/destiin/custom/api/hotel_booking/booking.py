import frappe
import json
import requests
from datetime import datetime
from destiin.destiin.custom.api.request_booking.request import update_request_status_from_rooms


from destiin.destiin.constants import PRICE_COMPARISON_API_URL, HITPAY_REFUND_URL, EMAIL_API_URL

REFUND_API_URL = HITPAY_REFUND_URL


def send_booking_confirmation_email(to_emails, employee_name, booking_reference, hotel_name, hotel_address, number_of_rooms, check_in_date, check_in_time, check_out_date, check_out_time, adults, children, guest_email, currency, amount, tax_amount, total_amount, agent_email, hotel_map_url=""):
    """
    Send booking confirmation email to the specified recipients.

    Args:
        to_emails (list): List of email addresses to send to
        employee_name (str): Name of the employee/guest
        booking_reference (str): Booking confirmation number
        hotel_name (str): Name of the hotel
        hotel_address (str): Hotel address
        number_of_rooms (int): Number of rooms booked
        check_in_date (str): Check-in date
        check_in_time (str): Check-in time
        check_out_date (str): Check-out date
        check_out_time (str): Check-out time
        adults (int): Number of adults
        children (int): Number of children
        guest_email (str): Guest email address
        currency (str): Currency code
        amount (float): Room charges
        tax_amount (float): Tax amount
        total_amount (float): Total amount paid
        agent_email (str): Agent email address
        hotel_map_url (str): Google Maps URL for the hotel location

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    if not to_emails:
        return False

    # Filter out empty emails
    valid_emails = [email for email in to_emails if email]
    if not valid_emails:
        return False

    subject = f"Booking Confirmed - {hotel_name} ({booking_reference})"

    body = f"""<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml"
    xmlns:o="urn:schemas-microsoft-com:office:office">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="x-apple-disable-message-reformatting">
    <title>Booking Confirmation - Destiin</title>
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

                                <!-- Success Badge -->
                                <tr>
                                    <td align="center" style="padding-bottom: 24px;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                                            <tr>
                                                <td
                                                    style="background-color: rgba(126, 205, 165, 0.2); border-radius: 50px; padding: 12px 24px;">
                                                    <p
                                                        style="margin: 0; font-size: 14px; color: #7ecda5; font-weight: 600;">
                                                        ✓ BOOKING CONFIRMED</p>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>

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
                                            Your booking has been successfully confirmed! Below are your complete
                                            booking details. Please save this email for your reference.
                                        </p>
                                    </td>
                                </tr>

                                <!-- Booking Reference -->
                                <tr>
                                    <td style="padding: 24px 0;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0"
                                            width="100%"
                                            style="background: linear-gradient(135deg, rgba(126, 205, 165, 0.15) 0%, rgba(126, 205, 165, 0.05) 100%); border: 1px solid rgba(126, 205, 165, 0.3); border-radius: 12px;">
                                            <tr>
                                                <td style="padding: 20px; text-align: center;">
                                                    <p
                                                        style="margin: 0 0 8px 0; font-size: 13px; color: #a0a0a0; font-weight: 500;">
                                                        Booking Reference</p>
                                                    <p
                                                        style="margin: 0; font-size: 24px; color: #7ecda5; font-weight: 700; letter-spacing: 2px;">
                                                        {booking_reference}</p>
                                                </td>
                                            </tr>
                                        </table>
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
                                                                    🏨 HOTEL INFORMATION</p>
                                                            </td>
                                                        </tr>

                                                        <!-- Hotel Name -->
                                                        <tr>
                                                            <td colspan="2" style="padding: 8px 0;">
                                                                <p
                                                                    style="margin: 0; font-size: 18px; color: #ededed; font-weight: 600;">
                                                                    {hotel_name}</p>
                                                            </td>
                                                        </tr>

                                                        <!-- Address -->
                                                        <tr>
                                                            <td colspan="2" style="padding: 4px 0 16px 0;">
                                                                <p
                                                                    style="margin: 0; font-size: 13px; color: #a0a0a0; line-height: 1.5;">
                                                                    {hotel_address}</p>
                                                            </td>
                                                        </tr>

                                                        <!-- Number of Rooms -->
                                                        <tr>
                                                            <td
                                                                style="padding: 8px 16px 8px 0; font-size: 13px; color: #a0a0a0; font-weight: 500;">
                                                                Rooms:</td>
                                                            <td
                                                                style="padding: 8px 0; font-size: 14px; color: #ededed; font-weight: 500;">
                                                                {number_of_rooms}</td>
                                                        </tr>

                                                        <!-- Check-in -->
                                                        <tr>
                                                            <td
                                                                style="padding: 8px 16px 8px 0; font-size: 13px; color: #a0a0a0; font-weight: 500;">
                                                                Check-in:</td>
                                                            <td
                                                                style="padding: 8px 0; font-size: 14px; color: #ededed; font-weight: 500;">
                                                                {check_in_date} • {check_in_time}</td>
                                                        </tr>

                                                        <!-- Check-out -->
                                                        <tr>
                                                            <td
                                                                style="padding: 8px 16px 8px 0; font-size: 13px; color: #a0a0a0; font-weight: 500;">
                                                                Check-out:</td>
                                                            <td
                                                                style="padding: 8px 0; font-size: 14px; color: #ededed; font-weight: 500;">
                                                                {check_out_date} • {check_out_time}</td>
                                                        </tr>

                                                        <!-- View on Map Button -->
                                                        {"" if not hotel_map_url else '''<tr>
                                                            <td colspan="2" style="padding: 16px 0 0 0;">
                                                                <a href="''' + hotel_map_url + '''" target="_blank"
                                                                    style="display: inline-block; background-color: #7ecda5; color: #0e0f1d; padding: 12px 24px; font-size: 14px; font-weight: 600; text-decoration: none; border-radius: 8px;">
                                                                    📍 View on Google Maps
                                                                </a>
                                                            </td>
                                                        </tr>'''}
                                                    </table>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>

                                <!-- Guest Details Card -->
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
                                                                    👤 GUEST DETAILS</p>
                                                            </td>
                                                        </tr>

                                                        <!-- Primary Guest -->
                                                        <tr>
                                                            <td
                                                                style="padding: 8px 16px 8px 0; font-size: 13px; color: #a0a0a0; font-weight: 500; width: 40%;">
                                                                Primary Guest:</td>
                                                            <td
                                                                style="padding: 8px 0; font-size: 14px; color: #ededed; font-weight: 500;">
                                                                {employee_name or 'Guest'}</td>
                                                        </tr>

                                                        <!-- Total Guests -->
                                                        <tr>
                                                            <td
                                                                style="padding: 8px 16px 8px 0; font-size: 13px; color: #a0a0a0; font-weight: 500;">
                                                                Total Guests:</td>
                                                            <td
                                                                style="padding: 8px 0; font-size: 14px; color: #ededed; font-weight: 500;">
                                                                {adults} Adult(s), {children} Child(ren)</td>
                                                        </tr>

                                                        <!-- Contact Email -->
                                                        <tr>
                                                            <td
                                                                style="padding: 8px 16px 8px 0; font-size: 13px; color: #a0a0a0; font-weight: 500;">
                                                                Email:</td>
                                                            <td
                                                                style="padding: 8px 0; font-size: 14px; color: #ededed; font-weight: 500;">
                                                                {guest_email}</td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>

                                <!-- Payment Summary Card -->
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
                                                                    💳 PAYMENT SUMMARY</p>
                                                            </td>
                                                        </tr>

                                                        <!-- Room Charges -->
                                                        <tr>
                                                            <td
                                                                style="padding: 8px 16px 8px 0; font-size: 13px; color: #a0a0a0; font-weight: 500; width: 60%;">
                                                                Room Charges:</td>
                                                            <td
                                                                style="padding: 8px 0; font-size: 14px; color: #ededed; font-weight: 500; text-align: right;">
                                                                {currency} {amount:.2f}</td>
                                                        </tr>

                                                        <!-- Taxes & Fees -->
                                                        <tr>
                                                            <td
                                                                style="padding: 8px 16px 8px 0; font-size: 13px; color: #a0a0a0; font-weight: 500;">
                                                                Taxes & Fees:</td>
                                                            <td
                                                                style="padding: 8px 0; font-size: 14px; color: #ededed; font-weight: 500; text-align: right;">
                                                                {currency} {tax_amount:.2f}</td>
                                                        </tr>

                                                        <!-- Divider -->
                                                        <tr>
                                                            <td colspan="2"
                                                                style="padding: 12px 0; border-top: 1px solid rgba(255, 255, 255, 0.1);">
                                                            </td>
                                                        </tr>

                                                        <!-- Total Paid -->
                                                        <tr>
                                                            <td
                                                                style="padding: 8px 16px 8px 0; font-size: 15px; color: #7ecda5; font-weight: 600;">
                                                                Total Paid:</td>
                                                            <td
                                                                style="padding: 8px 0; font-size: 18px; color: #7ecda5; font-weight: 700; text-align: right;">
                                                                {currency} {total_amount:.2f}</td>
                                                        </tr>

                                                        <!-- Payment Status -->
                                                        <tr>
                                                            <td colspan="2" style="padding: 12px 0 0 0;">
                                                                <p style="margin: 0; font-size: 12px; color: #a0a0a0;">
                                                                    Payment Status: <span
                                                                        style="color: #7ecda5; font-weight: 600;">PAID</span>
                                                                </p>
                                                            </td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>

                                <!-- Important Information -->
                                <tr>
                                    <td style="padding: 24px 0;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0"
                                            width="100%"
                                            style="background-color: rgba(126, 205, 165, 0.1); border-left: 4px solid #7ecda5; border-radius: 4px;">
                                            <tr>
                                                <td style="padding: 16px 20px;">
                                                    <p
                                                        style="margin: 0 0 12px 0; font-size: 14px; color: #7ecda5; font-weight: 600;">
                                                        📌 Check-in Instructions</p>
                                                    <ul
                                                        style="margin: 0; padding-left: 20px; font-size: 13px; color: #c0c0c0; line-height: 1.8;">
                                                        <li>Please carry a valid government-issued photo ID</li>
                                                        <li>Present this booking confirmation at the hotel reception
                                                        </li>
                                                        <li>Early check-in subject to availability</li>
                                                        <li>Contact hotel directly for special requests</li>
                                                    </ul>
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
                                            Need to modify your booking or have questions?
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
                                            This is your official booking confirmation.
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
                "send_booking_confirmation_email Error"
            )
            return False
    except Exception as e:
        frappe.log_error(f"Email sending failed: {str(e)}", "send_booking_confirmation_email Error")
        return False


def call_price_comparison_api(hotel_booking):
    """
    Call the price comparison API and store the prices from different sites.

    Args:
        hotel_booking: The Hotel Booking document
    """
    try:
        # Try to get room_rate_id from room_details
        room_rate_id = ""
        room_id = hotel_booking.room_id or ""
        frappe.log_error(f" call_price_comparison_api Room ID: {room_id}")

        if hotel_booking.room_details:
            try:
                room_list = json.loads(hotel_booking.room_details)
                if room_list and len(room_list) > 0:
                    first_room = room_list[0]
                    room_rate_id = str(first_room.get("rateId", first_room.get("roomRateId", "")))
                    if not room_id:
                        room_id = str(first_room.get("roomId", ""))
            except (json.JSONDecodeError, TypeError):
                pass

        # Build occupancy array based on room count
        adults = hotel_booking.adult_count or 2
        children = hotel_booking.child_count or 0
        rooms = hotel_booking.room_count or 1

        # Create child ages array (empty if no children)
        child_ages = []
        if children > 0:
            # Default child ages to 10 if not specified
            child_ages = [10] * children

        # Build occupancy for each room
        occupancy = []
        for i in range(rooms):
            occupancy.append({
                "adults": adults,
                "room": i + 1,
                "childAges": child_ages if i == 0 else []  # Assign children to first room
            })

        payload = {
            "hotel_name": hotel_booking.hotel_name or "",
            "city": hotel_booking.city_code or "",
            # "country": hotel_booking.country or "India",
            "check_in": str(hotel_booking.check_in) if hotel_booking.check_in else "",
            "check_out": str(hotel_booking.check_out) if hotel_booking.check_out else "",
            "occupancy": occupancy,
            "adults": adults,
            "children": children,
            "rooms": rooms,
            "room_type": hotel_booking.room_type or "",
            "hotel_id": hotel_booking.hotel_id or "",
            "room_id": room_id,
            "room_rate_id": room_rate_id,
            "currency": hotel_booking.currency or "USD",
            "sites": ["agoda", "booking_com"]
        }

        response = requests.post(
            PRICE_COMPARISON_API_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=800
        )
        frappe.log_error(f" call_price_comparison_api Response: {response}")

        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])

            for result in results:
                site = result.get("site", "")
                if result.get("success"):
                    price_breakdown = result.get("price_breakdown", {})
                    total_with_tax = price_breakdown.get("total_with_tax")

                    if site == "agoda" and total_with_tax is not None:
                        hotel_booking.agoda = total_with_tax
                    elif site == "booking_com" and total_with_tax is not None:
                        hotel_booking.booking_com = total_with_tax

            hotel_booking.save(ignore_permissions=True)

    except Exception as e:
        frappe.log_error(f"Price comparison API error: {str(e)}", "Price Comparison API Error")


def call_refund_api(payment_id, amount, currency=None):
    """
    Call the HitPay refund API to initiate a refund.

    Args:
        payment_id (str): The transaction_id from the payment record
        amount (float): The refund amount
        currency (str, optional): Currency code

    Returns:
        dict: API response with success status and data/error
    """
    try:
        payload = {
            "payment_id": payment_id,
            "amount": float(amount)
        }
        if currency:
            payload["currency"] = currency

        response = requests.post(
            REFUND_API_URL,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "accept": "application/json"
            },
            timeout=30
        )

        if response.status_code == 200:
            return {
                "success": True,
                "data": response.json()
            }
        else:
            return {
                "success": False,
                "error": f"Refund API returned status {response.status_code}: {response.text}"
            }

    except Exception as e:
        frappe.log_error(f"Refund API error for payment_id {payment_id}: {str(e)}", "Refund API Error")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=False)
def confirm_booking(**kwargs):
    """
    API to store booking confirmation details from external hotel API.

    This API receives the booking confirmation webhook/callback from the external
    hotel booking system and updates the existing Hotel Booking record with
    confirmation details.

    The request payload structure:
    {
        "bookingId": "16391528683",
        "clientReference": "request_booking_id",
        "hotelConfirmationNo": "TESTCONFIRMCODE20260126181407041",
        "status": "confirmed",
        "hotel": { "id": 512, "name": "...", "cityCode": "179900" },
        "checkIn": "2026-08-01 00:00:00",
        "checkOut": "2026-08-02 00:00:00",
        "totalPrice": 409.41,
        "currency": "USD",
        "numOfRooms": 1,
        "guestList": [...],
        "roomList": [...],
        "contact": { "firstName": "...", "lastName": "...", "phone": "...", "email": "..." },
        "cancellation": [...],
        "remark": ""
    }

    Returns:
        dict: Response with success status and updated booking data
    """
    try:
        # Extract data from kwargs (handles both direct params and nested JSON)
        data = kwargs

        # ==================== VALIDATION START ====================

        # Validate clientReference (required)
        client_reference = data.get("clientReference")
        if not client_reference:
            return {
                    "success": False,
                    "error": "clientReference is required"
            }

        if not isinstance(client_reference, str) or not client_reference.strip():
            return {
                    "success": False,
                    "error": "clientReference must be a non-empty string"
            }
        client_reference = client_reference.strip()

        # Extract booking details from the payload
        external_booking_id = data.get("bookingId", "")
        hotel_confirmation_no = data.get("hotelConfirmationNo", "")
        status = data.get("status", "")
        hotel_data = data.get("hotel", {})
        check_in = data.get("checkIn", "")
        check_out = data.get("checkOut", "")
        total_price = data.get("totalPrice", 0)
        currency = data.get("currency", "")
        num_of_rooms = data.get("numOfRooms", 0)
        guest_list = data.get("guestList", [])
        room_list = data.get("roomList", [])
        contact = data.get("contact", {})
        cancellation = data.get("cancellation", [])

        # Parse JSON strings if nested objects are passed as strings
        if isinstance(hotel_data, str):
            try:
                hotel_data = json.loads(hotel_data)
            except (json.JSONDecodeError, TypeError):
                hotel_data = {}
        if isinstance(guest_list, str):
            try:
                guest_list = json.loads(guest_list)
            except (json.JSONDecodeError, TypeError):
                guest_list = []
        if isinstance(room_list, str):
            try:
                room_list = json.loads(room_list)
            except (json.JSONDecodeError, TypeError):
                room_list = []
        if isinstance(contact, str):
            try:
                contact = json.loads(contact)
            except (json.JSONDecodeError, TypeError):
                contact = {}
        if isinstance(cancellation, str):
            try:
                cancellation = json.loads(cancellation)
            except (json.JSONDecodeError, TypeError):
                cancellation = []
        remark = data.get("remark", "")
        payment_mode = data.get("paymentMode", "")

        # Validate paymentMode if provided
        if payment_mode:
            valid_payment_modes = ["direct_pay", "bill_to_company"]
            if payment_mode not in valid_payment_modes:
                return {
                        "success": False,
                        "error": f"Invalid paymentMode. Must be one of: {', '.join(valid_payment_modes)}"
                }

        # Validate bookingId (required)
        if not external_booking_id:
            return {
                    "success": False,
                    "error": "bookingId is required"
            }
        external_booking_id = str(external_booking_id).strip()

        # Validate hotelConfirmationNo (required)
        if not hotel_confirmation_no:
            return {
                    "success": False,
                    "error": "hotelConfirmationNo is required"
            }
        hotel_confirmation_no = str(hotel_confirmation_no).strip()

        # Validate status (required)
        if not status:
            return {
                    "success": False,
                    "error": "status is required"
            }

        # Convert status to string if it's not already
        status = str(status) if status else ""

        valid_statuses = ["confirmed", "cancelled", "pending", "completed"]
        if status.lower() not in valid_statuses:
            return {
                    "success": False,
                    "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            }

        # Validate hotel object (required)
        if not hotel_data or not isinstance(hotel_data, dict):
            return {
                    "success": False,
                    "error": "hotel object is required"
            }

        if not hotel_data.get("id"):
            return {
                    "success": False,
                    "error": "hotel.id is required"
            }

        # Validate totalPrice (must be numeric and positive)
        try:
            total_price = float(total_price) if total_price else 0
            if total_price < 0:
                return {
                        "success": False,
                        "error": "totalPrice must be a positive number"
                }
        except (ValueError, TypeError):
            return {
                    "success": False,
                    "error": "totalPrice must be a valid number"
            }

        # Validate numOfRooms (must be positive integer)
        try:
            num_of_rooms = int(num_of_rooms) if num_of_rooms else 0
            if num_of_rooms < 0:
                return {
                        "success": False,
                        "error": "numOfRooms must be a positive integer"
                }
        except (ValueError, TypeError):
            return {
                    "success": False,
                    "error": "numOfRooms must be a valid integer"
            }

        # Validate contact object if provided
        if contact and not isinstance(contact, dict):
            return {
                    "success": False,
                    "error": "contact must be an object"
            }

        # Validate guestList if provided
        if guest_list and not isinstance(guest_list, list):
            return {
                    "success": False,
                    "error": "guestList must be an array"
            }

        # Validate roomList if provided
        if room_list and not isinstance(room_list, list):
            return {
                    "success": False,
                    "error": "roomList must be an array"
            }

        # Validate cancellation if provided
        if cancellation and not isinstance(cancellation, list):
            return {
                    "success": False,
                    "error": "cancellation must be an array"
            }

        # ==================== DUPLICATION CHECKS ====================

        # Check for duplicate external_booking_id (excluding current clientReference)
        duplicate_by_external_id = frappe.db.get_value(
            "Hotel Bookings",
            {
                "external_booking_id": external_booking_id,
                "booking_id": ["!=", client_reference]
            },
            ["name", "booking_id"],
            as_dict=True
        )

        if duplicate_by_external_id:
            return {
                    "success": False,
                    "error": f"Duplicate booking: external bookingId '{external_booking_id}' already exists for booking '{duplicate_by_external_id.booking_id}'"
            }

        # Check for duplicate hotel_confirmation_no (excluding current clientReference)
        duplicate_by_confirmation = frappe.db.get_value(
            "Hotel Bookings",
            {
                "hotel_confirmation_no": hotel_confirmation_no,
                "booking_id": ["!=", client_reference]
            },
            ["name", "booking_id"],
            as_dict=True
        )

        if duplicate_by_confirmation:
            return {
                    "success": False,
                    "error": f"Duplicate booking: hotelConfirmationNo '{hotel_confirmation_no}' already exists for booking '{duplicate_by_confirmation.booking_id}'"
            }

        # ==================== VALIDATION END ====================

        # Fetch the request booking details using clientReference
        request_booking = frappe.db.get_value(
            "Request Booking Details",
            {"request_booking_id": client_reference},
            [
                "name", "request_booking_id", "employee", "company", "agent",
                "check_in", "check_out", "occupancy", "adult_count", "child_count",
                "room_count", "request_status", "payment_status"
            ],
            as_dict=True
        )

        if not request_booking:
            return {
                    "success": False,
                    "error": f"Request booking not found for clientReference: {client_reference}"
            }

        # Find existing Hotel Booking with this request_booking_id as booking_id
        existing_booking = frappe.db.get_value(
            "Hotel Bookings",
            {"booking_id": client_reference},
            ["name", "booking_status", "external_booking_id", "hotel_confirmation_no"],
            as_dict=True
        )

        # Check if booking already confirmed with same confirmation details
        if existing_booking:
            if (existing_booking.booking_status == "confirmed" and
                existing_booking.external_booking_id == external_booking_id and
                existing_booking.hotel_confirmation_no == hotel_confirmation_no):
                return {
                        "success": False,
                        "error": f"Booking already confirmed with same details. Hotel Booking: {existing_booking.name}, External ID: {external_booking_id}",
                        "data": {
                            "hotel_booking_id": existing_booking.name,
                            "external_booking_id": existing_booking.external_booking_id,
                            "hotel_confirmation_no": existing_booking.hotel_confirmation_no
                        }
                }

        # Parse dates - remove time portion if present
        parsed_check_in = check_in.split(" ")[0] if check_in else None
        parsed_check_out = check_out.split(" ")[0] if check_out else None

        # Validate date formats
        if parsed_check_in:
            try:
                check_in_date = datetime.strptime(parsed_check_in, "%Y-%m-%d")
            except ValueError:
                return {
                        "success": False,
                        "error": f"Invalid checkIn date format: '{check_in}'. Expected format: YYYY-MM-DD"
                }

        if parsed_check_out:
            try:
                check_out_date = datetime.strptime(parsed_check_out, "%Y-%m-%d")
            except ValueError:
                return {
                        "success": False,
                        "error": f"Invalid checkOut date format: '{check_out}'. Expected format: YYYY-MM-DD"
                }

        # Validate checkIn is before checkOut
        if parsed_check_in and parsed_check_out:
            if check_in_date >= check_out_date:
                return {
                        "success": False,
                        "error": "checkIn date must be before checkOut date"
                }

        # Map external status to our booking_status
        booking_status_map = {
            "confirmed": "confirmed",
            "cancelled": "cancelled",
            "pending": "pending",
            "completed": "completed"
        }
        mapped_booking_status = booking_status_map.get(status.lower(), "pending") if status else "pending"

        if existing_booking:
            # Update existing Hotel Booking
            hotel_booking = frappe.get_doc("Hotel Bookings", existing_booking.name)

            hotel_booking.external_booking_id = external_booking_id
            hotel_booking.hotel_confirmation_no = hotel_confirmation_no
            hotel_booking.booking_status = mapped_booking_status

            # Update hotel details from response
            if hotel_data:
                hotel_booking.hotel_id = str(hotel_data.get("id", hotel_booking.hotel_id or ""))
                hotel_booking.hotel_name = hotel_data.get("name", hotel_booking.hotel_name or "")
                hotel_booking.city_code = hotel_data.get("cityCode", "")

            # Update dates if provided
            if parsed_check_in:
                hotel_booking.check_in = parsed_check_in
            if parsed_check_out:
                hotel_booking.check_out = parsed_check_out

            # Update amounts
            if total_price:
                hotel_booking.total_amount = total_price
            if currency:
                hotel_booking.currency = currency
            if num_of_rooms:
                hotel_booking.room_count = num_of_rooms

            # Update contact details
            if contact:
                hotel_booking.contact_first_name = contact.get("firstname", "")
                hotel_booking.contact_last_name = contact.get("lastname", "")
                hotel_booking.contact_phone = contact.get("phone", "")
                hotel_booking.contact_email = contact.get("email", "")

            # Store guest list, room details, and cancellation policy as JSON
            hotel_booking.guest_list = json.dumps(guest_list) if guest_list else None
            hotel_booking.room_details = json.dumps(room_list) if room_list else None
            hotel_booking.cancellation_policy = json.dumps(cancellation) if cancellation else None
            hotel_booking.remark = remark
            if payment_mode:
                hotel_booking.payment_mode = payment_mode

            # Extract room info from roomList
            if room_list:
                room_ids = []
                room_types = []
                for room in room_list:
                    if room.get("roomId"):
                        room_ids.append(str(room.get("roomId")))
                    if room.get("roomName"):
                        room_types.append(room.get("roomName"))

                if room_ids:
                    hotel_booking.room_id = ", ".join(room_ids)
                if room_types:
                    hotel_booking.room_type = ", ".join(room_types)

            hotel_booking.save(ignore_permissions=True)

            # Update all linked Booking Payments
            if hotel_booking.payment_link:
                for payment_row in hotel_booking.payment_link:
                    booking_payment = frappe.get_doc("Booking Payments", payment_row.booking_payment)
                    booking_payment.booking_status = mapped_booking_status
                    if total_price:
                        booking_payment.total_amount = total_price
                    if currency:
                        booking_payment.currency = currency
                    booking_payment.save(ignore_permissions=True)

            # Update cart hotel room statuses based on booking status for existing booking
            cart_hotel_item_links = frappe.db.get_all(
                "Cart Hotel Item Link",
                filters={"parent": request_booking.name, "parenttype": "Request Booking Details"},
                fields=["cart_hotel_item"],
                limit_page_length=0
            )

            room_status_map = {
                "confirmed": "booking_success",
                "cancelled": "booking_failure",
                "pending": "payment_pending",
                "completed": "booking_success"
            }
            new_room_status = room_status_map.get(mapped_booking_status, "payment_pending")

            for link in cart_hotel_item_links:
                cart_hotel_item_name = link["cart_hotel_item"]
                cart_hotel = frappe.get_doc("Cart Hotel Item", cart_hotel_item_name)

                # Update room statuses
                for room in cart_hotel.rooms:
                    if room.status in ["approved", "payment_pending"]:
                        room.status = new_room_status
                cart_hotel.save(ignore_permissions=True)

                # Update request booking status based on room statuses
                update_request_status_from_rooms(request_booking.name, cart_hotel_item_name)

        else:
            # Create new Hotel Booking if not found
            hotel_booking = frappe.new_doc("Hotel Bookings")
            hotel_booking.booking_id = client_reference
            hotel_booking.external_booking_id = external_booking_id
            hotel_booking.hotel_confirmation_no = hotel_confirmation_no
            hotel_booking.request_booking_link = request_booking.name
            hotel_booking.employee = request_booking.employee
            hotel_booking.company = request_booking.company
            hotel_booking.agent = request_booking.agent
            hotel_booking.booking_status = mapped_booking_status
            hotel_booking.payment_status = request_booking.payment_status or "payment_pending"

            # Hotel details
            if hotel_data:
                hotel_booking.hotel_id = str(hotel_data.get("id", ""))
                hotel_booking.hotel_name = hotel_data.get("name", "")
                hotel_booking.city_code = hotel_data.get("cityCode", "")

            # Stay details
            hotel_booking.check_in = parsed_check_in or request_booking.check_in
            hotel_booking.check_out = parsed_check_out or request_booking.check_out
            hotel_booking.occupancy = str(request_booking.occupancy) if request_booking.occupancy else ""
            hotel_booking.adult_count = request_booking.adult_count
            hotel_booking.child_count = request_booking.child_count
            hotel_booking.room_count = num_of_rooms or request_booking.room_count

            # Amount details
            hotel_booking.total_amount = total_price
            hotel_booking.currency = currency

            # Contact details
            if contact:
                hotel_booking.contact_first_name = contact.get("firstname", "")
                hotel_booking.contact_last_name = contact.get("lastname", "")
                hotel_booking.contact_phone = contact.get("phone", "")
                hotel_booking.contact_email = contact.get("email", "")

            # JSON fields
            hotel_booking.guest_list = json.dumps(guest_list) if guest_list else None
            hotel_booking.room_details = json.dumps(room_list) if room_list else None
            hotel_booking.cancellation_policy = json.dumps(cancellation) if cancellation else None
            hotel_booking.remark = remark
            if payment_mode:
                hotel_booking.payment_mode = payment_mode

            # Extract room info from roomList
            if room_list:
                room_ids = []
                room_types = []
                for room in room_list:
                    if room.get("roomId"):
                        room_ids.append(str(room.get("roomId")))
                    if room.get("roomName"):
                        room_types.append(room.get("roomName"))

                if room_ids:
                    hotel_booking.room_id = ", ".join(room_ids)
                if room_types:
                    hotel_booking.room_type = ", ".join(room_types)

            hotel_booking.insert(ignore_permissions=True)

            # Update request_booking status to req_closed
            frappe.db.set_value(
                "Request Booking Details",
                request_booking.name,
                "request_status",
                "req_closed"
            )

            # Find and link existing payments from request_booking_details to this booking
            existing_payments = frappe.get_all(
                "Booking Payments",
                filters={"request_booking_link": request_booking.name},
                fields=["name"]
            )

            # Update existing payments to link to the new Hotel Booking
            for payment in existing_payments:
                frappe.db.set_value(
                    "Booking Payments",
                    payment.name,
                    "booking_id",
                    hotel_booking.name
                )
                hotel_booking.append("payment_link", {
                    "booking_payment": payment.name
                })

            # Only create new Booking Payments record if no existing payments were linked
            if not existing_payments:
                booking_payment = frappe.new_doc("Booking Payments")
                booking_payment.booking_id = hotel_booking.name
                booking_payment.request_booking_link = request_booking.name
                booking_payment.employee = request_booking.employee
                booking_payment.company = request_booking.company
                booking_payment.agent = request_booking.agent
                booking_payment.hotel_id = hotel_booking.hotel_id
                booking_payment.hotel_name = hotel_booking.hotel_name
                booking_payment.room_id = hotel_booking.room_id
                booking_payment.room_type = hotel_booking.room_type
                booking_payment.room_count = hotel_booking.room_count
                booking_payment.check_in = hotel_booking.check_in
                booking_payment.check_out = hotel_booking.check_out
                booking_payment.occupancy = hotel_booking.occupancy
                booking_payment.adult_count = hotel_booking.adult_count
                booking_payment.child_count = hotel_booking.child_count
                booking_payment.booking_status = mapped_booking_status
                booking_payment.payment_status = "payment_pending"
                booking_payment.total_amount = total_price
                booking_payment.currency = currency

                booking_payment.insert(ignore_permissions=True)

                # Update hotel booking with payment link (Table MultiSelect)
                hotel_booking.append("payment_link", {
                    "booking_payment": booking_payment.name
                })

            hotel_booking.save(ignore_permissions=True)

        # Update cart hotel room statuses based on booking status
        cart_hotel_item_links = frappe.db.get_all(
            "Cart Hotel Item Link",
            filters={"parent": request_booking.name, "parenttype": "Request Booking Details"},
            fields=["cart_hotel_item"],
            limit_page_length=0
        )

        room_status_map = {
            "confirmed": "booking_success",
            "cancelled": "booking_failure",
            "pending": "payment_pending",
            "completed": "booking_success"
        }
        new_room_status = room_status_map.get(mapped_booking_status, "payment_pending")

        for link in cart_hotel_item_links:
            cart_hotel_item_name = link["cart_hotel_item"]
            cart_hotel = frappe.get_doc("Cart Hotel Item", cart_hotel_item_name)

            # Update room statuses
            for room in cart_hotel.rooms:
                if room.status in ["approved", "payment_pending"]:
                    room.status = new_room_status
            cart_hotel.save(ignore_permissions=True)

            # Update request booking status based on room statuses
            update_request_status_from_rooms(request_booking.name, cart_hotel_item_name)
        frappe.db.commit()
        # Call price comparison API in background (no need to wait for response)
         frappe.enqueue(
            call_price_comparison_api,
            hotel_booking=hotel_booking,
            queue="long",
            timeout=900,
            now=False
        )

        return {
                "success": True,
                "message": "Booking confirmation stored successfully",
                "data": {
                    "hotel_booking_id": hotel_booking.name,
                    "booking_id": hotel_booking.booking_id,
                    "external_booking_id": hotel_booking.external_booking_id,
                    "hotel_confirmation_no": hotel_booking.hotel_confirmation_no,
                    "request_booking_id": client_reference,
                    "employee": hotel_booking.employee,
                    "company": hotel_booking.company,
                    "hotel_id": hotel_booking.hotel_id,
                    "hotel_name": hotel_booking.hotel_name,
                    "city_code": hotel_booking.city_code,
                    "room_id": hotel_booking.room_id,
                    "room_type": hotel_booking.room_type,
                    "room_count": hotel_booking.room_count,
                    "check_in": str(hotel_booking.check_in) if hotel_booking.check_in else "",
                    "check_out": str(hotel_booking.check_out) if hotel_booking.check_out else "",
                    "total_amount": hotel_booking.total_amount,
                    "currency": hotel_booking.currency,
                    "booking_status": hotel_booking.booking_status,
                    "payment_mode": hotel_booking.payment_mode,
                    "make_my_trip": hotel_booking.make_my_trip,
                    "agoda": hotel_booking.agoda,
                    "booking_com": hotel_booking.booking_com,
                    "contact": {
                        "firstName": hotel_booking.contact_first_name,
                        "lastName": hotel_booking.contact_last_name,
                        "phone": hotel_booking.contact_phone,
                        "email": hotel_booking.contact_email
                    }
                }
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "confirm_booking API Error")
        return {
                "success": False,
                "error": str(e)
        }



@frappe.whitelist(allow_guest=False)
def create_booking(**kwargs):
    """
    API to store booking confirmation details from external hotel API.

    This API receives the booking confirmation webhook/callback from the external
    hotel booking system and updates the existing Hotel Booking record with
    confirmation details.

    The request payload structure:
    {
        "bookingId": "16391528683",
        "clientReference": "request_booking_id",
        "hotelConfirmationNo": "TESTCONFIRMCODE20260126181407041",
        "status": "confirmed",
        "hotel": { "id": 512, "name": "...", "cityCode": "179900" },
        "checkIn": "2026-08-01 00:00:00",
        "checkOut": "2026-08-02 00:00:00",
        "totalPrice": 409.41,
        "currency": "USD",
        "numOfRooms": 1,
        "guestList": [...],
        "roomList": [...],
        "contact": { "firstName": "...", "lastName": "...", "phone": "...", "email": "..." },
        "cancellation": [...],
        "remark": ""
    }

    Returns:
        dict: Response with success status and updated booking data
    """
    try:
        # Extract data from kwargs (handles both direct params and nested JSON)
        data = kwargs

        # ==================== VALIDATION START ====================

        # Validate clientReference (required)
        client_reference = data.get("clientReference")
        if not client_reference:
            return {
                    "success": False,
                    "error": "clientReference is required"
            }

        if not isinstance(client_reference, str) or not client_reference.strip():
            return {
                    "success": False,
                    "error": "clientReference must be a non-empty string"
            }
        client_reference = client_reference.strip()

        # Extract booking details from the payload
        external_booking_id = data.get("bookingId", "")
        hotel_confirmation_no = data.get("hotelConfirmationNo", "")
        status = data.get("status", "")
        hotel_data = data.get("hotel", {})
        check_in = data.get("checkIn", "")
        check_out = data.get("checkOut", "")
        total_price = data.get("totalPrice", 0)
        currency = data.get("currency", "USD")
        num_of_rooms = data.get("numOfRooms", 0)
        guest_list = data.get("guestList", [])
        room_list = data.get("roomList", [])
        contact = data.get("contact", {})
        cancellation = data.get("cancellation", [])

        # Parse JSON strings if nested objects are passed as strings
        if isinstance(hotel_data, str):
            try:
                hotel_data = json.loads(hotel_data)
            except (json.JSONDecodeError, TypeError):
                hotel_data = {}
        if isinstance(guest_list, str):
            try:
                guest_list = json.loads(guest_list)
            except (json.JSONDecodeError, TypeError):
                guest_list = []
        if isinstance(room_list, str):
            try:
                room_list = json.loads(room_list)
            except (json.JSONDecodeError, TypeError):
                room_list = []
        if isinstance(contact, str):
            try:
                contact = json.loads(contact)
            except (json.JSONDecodeError, TypeError):
                contact = {}
        if isinstance(cancellation, str):
            try:
                cancellation = json.loads(cancellation)
            except (json.JSONDecodeError, TypeError):
                cancellation = []
        remark = data.get("remark", "")
        payment_mode = data.get("paymentMode", "")

        # Validate paymentMode if provided
        if payment_mode:
            valid_payment_modes = ["direct_pay", "bill_to_company"]
            if payment_mode not in valid_payment_modes:
                return {
                        "success": False,
                        "error": f"Invalid paymentMode. Must be one of: {', '.join(valid_payment_modes)}"
                }

        # Validate bookingId (required)
        if not external_booking_id:
            return {
                    "success": False,
                    "error": "bookingId is required"
            }
        external_booking_id = str(external_booking_id).strip()

        # Validate hotelConfirmationNo (optional - not required)
        # if not hotel_confirmation_no:
        #     return {
        #             "success": False,
        #             "error": "hotelConfirmationNo is required"
        #     }
        if hotel_confirmation_no:
            hotel_confirmation_no = str(hotel_confirmation_no).strip()

        # Validate status (required)
        if not status:
            return {
                    "success": False,
                    "error": "status is required"
            }

        # Convert status to string if it's not already
        status = str(status) if status else ""

        valid_statuses = ["confirmed", "cancelled", "pending", "completed"]
        if status.lower() not in valid_statuses:
            return {
                    "success": False,
                    "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            }

        # Validate hotel object (required)
        if not hotel_data or not isinstance(hotel_data, dict):
            return {
                    "success": False,
                    "error": "hotel object is required"
            }

        if not hotel_data.get("id"):
            return {
                    "success": False,
                    "error": "hotel.id is required"
            }

        # Validate totalPrice (must be numeric and positive)
        try:
            total_price = float(total_price) if total_price else 0
            if total_price < 0:
                return {
                        "success": False,
                        "error": "totalPrice must be a positive number"
                }
        except (ValueError, TypeError):
            return {
                    "success": False,
                    "error": "totalPrice must be a valid number"
            }

        # Validate numOfRooms (must be positive integer)
        try:
            num_of_rooms = int(num_of_rooms) if num_of_rooms else 0
            if num_of_rooms < 0:
                return {
                        "success": False,
                        "error": "numOfRooms must be a positive integer"
                }
        except (ValueError, TypeError):
            return {
                    "success": False,
                    "error": "numOfRooms must be a valid integer"
            }

        # Validate contact object if provided
        if contact and not isinstance(contact, dict):
            return {
                    "success": False,
                    "error": "contact must be an object"
            }

        # Validate guestList if provided
        if guest_list and not isinstance(guest_list, list):
            return {
                    "success": False,
                    "error": "guestList must be an array"
            }

        # Validate roomList if provided
        if room_list and not isinstance(room_list, list):
            return {
                    "success": False,
                    "error": "roomList must be an array"
            }

        # Validate cancellation if provided
        if cancellation and not isinstance(cancellation, list):
            return {
                    "success": False,
                    "error": "cancellation must be an array"
            }

        # ==================== DUPLICATION CHECKS ====================

        # Check for duplicate external_booking_id (excluding current clientReference)
        duplicate_by_external_id = frappe.db.get_value(
            "Hotel Bookings",
            {
                "external_booking_id": external_booking_id,
                "booking_id": ["!=", client_reference]
            },
            ["name", "booking_id"],
            as_dict=True
        )

        if duplicate_by_external_id:
            return {
                    "success": False,
                    "error": f"Duplicate booking: external bookingId '{external_booking_id}' already exists for booking '{duplicate_by_external_id.booking_id}'"
            }

        # Check for duplicate hotel_confirmation_no (excluding current clientReference)
        # Skip this check if hotel_confirmation_no is not provided (it's optional)
        if hotel_confirmation_no:
            duplicate_by_confirmation = frappe.db.get_value(
                "Hotel Bookings",
                {
                    "hotel_confirmation_no": hotel_confirmation_no,
                    "booking_id": ["!=", client_reference]
                },
                ["name", "booking_id"],
                as_dict=True
            )

            if duplicate_by_confirmation:
                return {
                        "success": False,
                        "error": f"Duplicate booking: hotelConfirmationNo '{hotel_confirmation_no}' already exists for booking '{duplicate_by_confirmation.booking_id}'"
                }

        # ==================== VALIDATION END ====================

        # Fetch the request booking details using clientReference
        request_booking = frappe.db.get_value(
            "Request Booking Details",
            {"request_booking_id": client_reference},
            [
                "name", "request_booking_id", "employee", "company", "agent",
                "check_in", "check_out", "occupancy", "adult_count", "child_count",
                "room_count", "request_status", "payment_status"
            ],
            as_dict=True
        )

        if not request_booking:
            return {
                    "success": False,
                    "error": f"Request booking not found for clientReference: {client_reference}"
            }

        # Find existing Hotel Booking with this request_booking_id as booking_id
        existing_booking = frappe.db.get_value(
            "Hotel Bookings",
            {"booking_id": client_reference},
            ["name", "booking_status", "external_booking_id", "hotel_confirmation_no"],
            as_dict=True
        )

        # Check if booking already confirmed with same confirmation details
        if existing_booking:
            if (existing_booking.booking_status == "confirmed" and
                existing_booking.external_booking_id == external_booking_id and
                existing_booking.hotel_confirmation_no == hotel_confirmation_no):
                return {
                        "success": False,
                        "error": f"Booking already confirmed with same details. Hotel Booking: {existing_booking.name}, External ID: {external_booking_id}",
                        "data": {
                            "hotel_booking_id": existing_booking.name,
                            "external_booking_id": existing_booking.external_booking_id,
                            "hotel_confirmation_no": existing_booking.hotel_confirmation_no
                        }
                }

        # Parse dates - remove time portion if present
        parsed_check_in = check_in.split(" ")[0] if check_in else None
        parsed_check_out = check_out.split(" ")[0] if check_out else None

        # Validate date formats
        if parsed_check_in:
            try:
                check_in_date = datetime.strptime(parsed_check_in, "%Y-%m-%d")
            except ValueError:
                return {
                        "success": False,
                        "error": f"Invalid checkIn date format: '{check_in}'. Expected format: YYYY-MM-DD"
                }

        if parsed_check_out:
            try:
                check_out_date = datetime.strptime(parsed_check_out, "%Y-%m-%d")
            except ValueError:
                return {
                        "success": False,
                        "error": f"Invalid checkOut date format: '{check_out}'. Expected format: YYYY-MM-DD"
                }

        # Validate checkIn is before checkOut
        if parsed_check_in and parsed_check_out:
            if check_in_date >= check_out_date:
                return {
                        "success": False,
                        "error": "checkIn date must be before checkOut date"
                }

        # Map external status to our booking_status
        booking_status_map = {
            "confirmed": "confirmed",
            "cancelled": "cancelled",
            "pending": "pending",
            "completed": "completed"
        }
        mapped_booking_status = booking_status_map.get(status.lower(), "pending") if status else "pending"

        if existing_booking:
            # Update existing Hotel Booking
            hotel_booking = frappe.get_doc("Hotel Bookings", existing_booking.name)

            hotel_booking.external_booking_id = external_booking_id
            hotel_booking.hotel_confirmation_no = hotel_confirmation_no
            hotel_booking.booking_status = mapped_booking_status

            # Update hotel details from response
            if hotel_data:
                hotel_booking.hotel_id = str(hotel_data.get("id", hotel_booking.hotel_id or ""))
                hotel_booking.hotel_name = hotel_data.get("name", hotel_booking.hotel_name or "")
                hotel_booking.city_code = hotel_data.get("cityCode", "")

            # Update dates if provided
            if parsed_check_in:
                hotel_booking.check_in = parsed_check_in
            if parsed_check_out:
                hotel_booking.check_out = parsed_check_out

            # Update amounts
            if total_price:
                hotel_booking.total_amount = total_price
            if currency:
                hotel_booking.currency = currency
            if num_of_rooms:
                hotel_booking.room_count = num_of_rooms

            # Update contact details
            if contact:
                hotel_booking.contact_first_name = contact.get("firstname", "")
                hotel_booking.contact_last_name = contact.get("lastname", "")
                hotel_booking.contact_phone = contact.get("phone", "")
                hotel_booking.contact_email = contact.get("email", "")

            # Store guest list, room details, and cancellation policy as JSON
            hotel_booking.guest_list = json.dumps(guest_list) if guest_list else None
            hotel_booking.room_details = json.dumps(room_list) if room_list else None
            hotel_booking.cancellation_policy = json.dumps(cancellation) if cancellation else None
            hotel_booking.remark = remark
            if payment_mode:
                hotel_booking.payment_mode = payment_mode

            # Extract room info from roomList
            if room_list:
                room_ids = []
                room_types = []
                for room in room_list:
                    if room.get("roomId"):
                        room_ids.append(str(room.get("roomId")))
                    if room.get("roomName"):
                        room_types.append(room.get("roomName"))

                if room_ids:
                    hotel_booking.room_id = ", ".join(room_ids)
                if room_types:
                    hotel_booking.room_type = ", ".join(room_types)

            hotel_booking.save(ignore_permissions=True)

            # Update all linked Booking Payments
            if hotel_booking.payment_link:
                for payment_row in hotel_booking.payment_link:
                    booking_payment = frappe.get_doc("Booking Payments", payment_row.booking_payment)
                    booking_payment.booking_status = mapped_booking_status
                    if total_price:
                        booking_payment.total_amount = total_price
                    if currency:
                        booking_payment.currency = currency
                    booking_payment.save(ignore_permissions=True)

            # Update cart hotel room statuses based on booking status for existing booking
            cart_hotel_item_links = frappe.db.get_all(
                "Cart Hotel Item Link",
                filters={"parent": request_booking.name, "parenttype": "Request Booking Details"},
                fields=["cart_hotel_item"],
                limit_page_length=0
            )

            room_status_map = {
                "confirmed": "booking_success",
                "cancelled": "booking_failure",
                "pending": "payment_pending",
                "completed": "booking_success"
            }
            new_room_status = room_status_map.get(mapped_booking_status, "payment_pending")

            for link in cart_hotel_item_links:
                cart_hotel_item_name = link["cart_hotel_item"]
                cart_hotel = frappe.get_doc("Cart Hotel Item", cart_hotel_item_name)

                # Update room statuses
                for room in cart_hotel.rooms:
                    if room.status in ["approved", "payment_pending"]:
                        room.status = new_room_status
                cart_hotel.save(ignore_permissions=True)

                # Update request booking status based on room statuses
                update_request_status_from_rooms(request_booking.name, cart_hotel_item_name)

        else:
            # Create new Hotel Booking if not found
            hotel_booking = frappe.new_doc("Hotel Bookings")
            hotel_booking.booking_id = client_reference
            hotel_booking.external_booking_id = external_booking_id
            hotel_booking.hotel_confirmation_no = hotel_confirmation_no
            hotel_booking.request_booking_link = request_booking.name
            hotel_booking.employee = request_booking.employee
            hotel_booking.company = request_booking.company
            hotel_booking.agent = request_booking.agent
            hotel_booking.booking_status = mapped_booking_status
            hotel_booking.payment_status = request_booking.payment_status or "payment_pending"

            # Hotel details
            if hotel_data:
                hotel_booking.hotel_id = str(hotel_data.get("id", ""))
                hotel_booking.hotel_name = hotel_data.get("name", "")
                hotel_booking.city_code = hotel_data.get("cityCode", "")

            # Stay details
            hotel_booking.check_in = parsed_check_in or request_booking.check_in
            hotel_booking.check_out = parsed_check_out or request_booking.check_out
            hotel_booking.occupancy = str(request_booking.occupancy) if request_booking.occupancy else ""
            hotel_booking.adult_count = request_booking.adult_count
            hotel_booking.child_count = request_booking.child_count
            hotel_booking.room_count = num_of_rooms or request_booking.room_count

            # Amount details
            hotel_booking.total_amount = total_price
            hotel_booking.currency = currency

            # Contact details
            if contact:
                hotel_booking.contact_first_name = contact.get("firstname", "")
                hotel_booking.contact_last_name = contact.get("lastname", "")
                hotel_booking.contact_phone = contact.get("phone", "")
                hotel_booking.contact_email = contact.get("email", "")

            # JSON fields
            hotel_booking.guest_list = json.dumps(guest_list) if guest_list else None
            hotel_booking.room_details = json.dumps(room_list) if room_list else None
            hotel_booking.cancellation_policy = json.dumps(cancellation) if cancellation else None
            hotel_booking.remark = remark
            if payment_mode:
                hotel_booking.payment_mode = payment_mode

            # Extract room info from roomList
            if room_list:
                room_ids = []
                room_types = []
                for room in room_list:
                    if room.get("roomId"):
                        room_ids.append(str(room.get("roomId")))
                    if room.get("roomName"):
                        room_types.append(room.get("roomName"))

                if room_ids:
                    hotel_booking.room_id = ", ".join(room_ids)
                if room_types:
                    hotel_booking.room_type = ", ".join(room_types)

            hotel_booking.insert(ignore_permissions=True)

            # Update request_booking status to req_closed
            frappe.db.set_value(
                "Request Booking Details",
                request_booking.name,
                "request_status",
                "req_closed"
            )

            # Find and link existing payments from request_booking_details to this booking
            existing_payments = frappe.get_all(
                "Booking Payments",
                filters={"request_booking_link": request_booking.name},
                fields=["name"]
            )

            # Update existing payments to link to the new Hotel Booking
            for payment in existing_payments:
                frappe.db.set_value(
                    "Booking Payments",
                    payment.name,
                    "booking_id",
                    hotel_booking.name
                )
                hotel_booking.append("payment_link", {
                    "booking_payment": payment.name
                })

            # Only create new Booking Payments record if no existing payments were linked
            if not existing_payments:
                booking_payment = frappe.new_doc("Booking Payments")
                booking_payment.booking_id = hotel_booking.name
                booking_payment.request_booking_link = request_booking.name
                booking_payment.employee = request_booking.employee
                booking_payment.company = request_booking.company
                booking_payment.agent = request_booking.agent
                booking_payment.hotel_id = hotel_booking.hotel_id
                booking_payment.hotel_name = hotel_booking.hotel_name
                booking_payment.room_id = hotel_booking.room_id
                booking_payment.room_type = hotel_booking.room_type
                booking_payment.room_count = hotel_booking.room_count
                booking_payment.check_in = hotel_booking.check_in
                booking_payment.check_out = hotel_booking.check_out
                booking_payment.occupancy = hotel_booking.occupancy
                booking_payment.adult_count = hotel_booking.adult_count
                booking_payment.child_count = hotel_booking.child_count
                booking_payment.booking_status = mapped_booking_status
                booking_payment.payment_status = "payment_pending"
                booking_payment.total_amount = total_price
                booking_payment.currency = currency

                booking_payment.insert(ignore_permissions=True)

                # Update hotel booking with payment link (Table MultiSelect)
                hotel_booking.append("payment_link", {
                    "booking_payment": booking_payment.name
                })

            hotel_booking.save(ignore_permissions=True)

        # Update cart hotel room statuses based on booking status
        cart_hotel_item_links = frappe.db.get_all(
            "Cart Hotel Item Link",
            filters={"parent": request_booking.name, "parenttype": "Request Booking Details"},
            fields=["cart_hotel_item"],
            limit_page_length=0
        )

        room_status_map = {
            "confirmed": "booking_success",
            "cancelled": "booking_failure",
            "pending": "payment_pending",
            "completed": "booking_success"
        }
        new_room_status = room_status_map.get(mapped_booking_status, "payment_pending")

        for link in cart_hotel_item_links:
            cart_hotel_item_name = link["cart_hotel_item"]
            cart_hotel = frappe.get_doc("Cart Hotel Item", cart_hotel_item_name)

            # Update room statuses
            for room in cart_hotel.rooms:
                if room.status in ["approved", "payment_pending"]:
                    room.status = new_room_status
            cart_hotel.save(ignore_permissions=True)

            # Update request booking status based on room statuses
            update_request_status_from_rooms(request_booking.name, cart_hotel_item_name)
        frappe.db.commit()
        # Call price comparison API in background to get prices from different sites
        frappe.enqueue(
            call_price_comparison_api,
            hotel_booking=hotel_booking,
            queue="long",
            timeout=900,
            now=False
        )



        # Send booking confirmation email if booking is confirmed
        email_sent = False
        if mapped_booking_status == "confirmed":
            try:
                # Get employee details
                employee_name = ""
                employee_email = ""
                if request_booking.employee:
                    employee_details = frappe.get_value(
                        "Employee",
                        request_booking.employee,
                        ["employee_name", "company_email", "personal_email"],
                        as_dict=True
                    )
                    if employee_details:
                        employee_name = employee_details.get("employee_name", "")
                        employee_email = employee_details.get("company_email") or employee_details.get("personal_email") or ""

                # Get agent email
                agent_email = ""
                if request_booking.agent:
                    agent_email = frappe.db.get_value("User", request_booking.agent, "email") or ""

                # Get contact email from booking
                guest_email = hotel_booking.contact_email or employee_email or ""

                # Build email recipients list
                email_recipients = []
                if employee_email:
                    email_recipients.append(employee_email)
                if agent_email and agent_email != employee_email:
                    email_recipients.append(agent_email)

                # Get payment details for amount breakdown
                payment_amount = 0
                payment_tax = 0
                if hotel_booking.payment_link and len(hotel_booking.payment_link) > 0:
                    first_payment_name = hotel_booking.payment_link[0].booking_payment
                    payment_doc = frappe.get_doc("Booking Payments", first_payment_name)
                    payment_amount = float(payment_doc.total_amount or 0)
                    payment_tax = float(payment_doc.tax or 0)
                else:
                    payment_amount = float(hotel_booking.total_amount or 0)
                    payment_tax = 0

                total_paid = payment_amount + payment_tax

                # Get hotel map URL from cart hotel item
                hotel_map_url = ""
                try:
                    # Find cart hotel item with matching hotel_id
                    cart_hotel_items = frappe.db.get_all(
                        "Cart Hotel Item Link",
                        filters={"parent": request_booking.name, "parenttype": "Request Booking Details"},
                        fields=["cart_hotel_item"],
                        limit_page_length=0
                    )
                    for item_link in cart_hotel_items:
                        cart_item = frappe.get_doc("Cart Hotel Item", item_link.cart_hotel_item)
                        # Match by hotel_id or hotel_name
                        if (cart_item.hotel_id and str(cart_item.hotel_id) == str(hotel_booking.hotel_id)) or \
                           (cart_item.hotel_name and cart_item.hotel_name == hotel_booking.hotel_name):
                            if cart_item.latitude and cart_item.longitude:
                                hotel_map_url = f"https://www.google.com/maps?q={cart_item.latitude},{cart_item.longitude}"
                            break
                except Exception as map_error:
                    frappe.log_error(f"Failed to get hotel map URL: {str(map_error)}", "Hotel Map URL Error")

                # Send confirmation email
                if email_recipients:
                    email_sent = send_booking_confirmation_email(
                        to_emails=email_recipients,
                        employee_name=employee_name,
                        booking_reference=hotel_booking.hotel_confirmation_no or hotel_booking.external_booking_id or hotel_booking.name,
                        hotel_name=hotel_booking.hotel_name or "Hotel",
                        hotel_address=hotel_booking.city_code or "",
                        number_of_rooms=hotel_booking.room_count or 1,
                        check_in_date=str(hotel_booking.check_in) if hotel_booking.check_in else "N/A",
                        check_in_time="14:00",
                        check_out_date=str(hotel_booking.check_out) if hotel_booking.check_out else "N/A",
                        check_out_time="11:00",
                        adults=hotel_booking.adult_count or 1,
                        children=hotel_booking.child_count or 0,
                        guest_email=guest_email,
                        currency=hotel_booking.currency or "USD",
                        amount=payment_amount,
                        tax_amount=payment_tax,
                        total_amount=total_paid,
                        agent_email=agent_email or "",
                        hotel_map_url=hotel_map_url
                    )
            except Exception as email_error:
                frappe.log_error(
                    f"Failed to send booking confirmation email: {str(email_error)}",
                    "create_booking Email Error"
                )

        return {
                "success": True,
                "message": "Booking confirmation stored successfully",
                "data": {
                    "hotel_booking_id": hotel_booking.name,
                    "booking_id": hotel_booking.booking_id,
                    "external_booking_id": hotel_booking.external_booking_id,
                    "hotel_confirmation_no": hotel_booking.hotel_confirmation_no,
                    "request_booking_id": client_reference,
                    "employee": hotel_booking.employee,
                    "company": hotel_booking.company,
                    "hotel_id": hotel_booking.hotel_id,
                    "hotel_name": hotel_booking.hotel_name,
                    "city_code": hotel_booking.city_code,
                    "room_id": hotel_booking.room_id,
                    "room_type": hotel_booking.room_type,
                    "room_count": hotel_booking.room_count,
                    "check_in": str(hotel_booking.check_in) if hotel_booking.check_in else "",
                    "check_out": str(hotel_booking.check_out) if hotel_booking.check_out else "",
                    "total_amount": hotel_booking.total_amount,
                    "currency": hotel_booking.currency,
                    "booking_status": hotel_booking.booking_status,
                    "payment_mode": hotel_booking.payment_mode,
                    "make_my_trip": hotel_booking.make_my_trip,
                    "agoda": hotel_booking.agoda,
                    "booking_com": hotel_booking.booking_com,
                    "email_sent": email_sent,
                    "contact": {
                        "firstName": hotel_booking.contact_first_name,
                        "lastName": hotel_booking.contact_last_name,
                        "phone": hotel_booking.contact_phone,
                        "email": hotel_booking.contact_email
                    }
                }
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "create_booking API Error")
        return {
                "success": False,
                "error": str(e)
        }


@frappe.whitelist(allow_guest=False)
def get_all_bookings(employee=None, company=None, booking_status=None, booking_id=None, external_booking_id=None):
    """
    API to fetch all hotel bookings with optional filters.
    Returns all details stored via confirm_booking API.

    Args:
        employee (str, optional): Filter by employee ID
        company (str, optional): Filter by company
        booking_status (str, optional): Filter by booking status (confirmed, cancelled, pending, completed)
        booking_id (str, optional): Filter by specific booking_id (clientReference)
        external_booking_id (str, optional): Filter by external booking ID

    Returns:
        dict: Response with success status and list of bookings with full details
    """
    try:
        filters = {}

        if employee:
            filters["employee"] = employee

        if company:
            filters["company"] = company

        if booking_status:
            filters["booking_status"] = booking_status

        if booking_id:
            filters["booking_id"] = booking_id

        if external_booking_id:
            filters["external_booking_id"] = external_booking_id

        bookings = frappe.get_all(
            "Hotel Bookings",
            filters=filters,
            ignore_permissions=True,
            fields=[
                "name",
                "booking_id",
                "external_booking_id",
                "hotel_confirmation_no",
                "request_booking_link",
                "employee",
                "company",
                "agent",
                "hotel_id",
                "hotel_name",
                "city_code",
                "room_id",
                "room_type",
                "room_count",
                "check_in",
                "check_out",
                "occupancy",
                "adult_count",
                "child_count",
                "booking_status",
                "payment_status",
                "payment_mode",
                "total_amount",
                "tax",
                "currency",
                "contact_first_name",
                "contact_last_name",
                "contact_phone",
                "contact_email",
                "guest_list",
                "room_details",
                "cancellation_policy",
                "remark",
                "creation",
                "modified"
            ],
            order_by="creation desc"
        )

        # Process each booking to format the response
        for booking in bookings:
            # Convert date fields to strings for JSON serialization
            booking["check_in"] = str(booking["check_in"]) if booking.get("check_in") else ""
            booking["check_out"] = str(booking["check_out"]) if booking.get("check_out") else ""
            booking["creation"] = str(booking["creation"]) if booking.get("creation") else ""
            booking["modified"] = str(booking["modified"]) if booking.get("modified") else ""

            # Parse JSON fields back to objects
            if booking.get("guest_list"):
                try:
                    booking["guest_list"] = json.loads(booking["guest_list"])
                except (json.JSONDecodeError, TypeError):
                    booking["guest_list"] = []
            else:
                booking["guest_list"] = []

            if booking.get("room_details"):
                try:
                    booking["room_details"] = json.loads(booking["room_details"])
                except (json.JSONDecodeError, TypeError):
                    booking["room_details"] = []
            else:
                booking["room_details"] = []

            if booking.get("cancellation_policy"):
                try:
                    booking["cancellation_policy"] = json.loads(booking["cancellation_policy"])
                except (json.JSONDecodeError, TypeError):
                    booking["cancellation_policy"] = []
            else:
                booking["cancellation_policy"] = []

            # Structure contact info as nested object
            booking["contact"] = {
                "firstName": booking.pop("contact_first_name", "") or "",
                "lastName": booking.pop("contact_last_name", "") or "",
                "phone": booking.pop("contact_phone", "") or "",
                "email": booking.pop("contact_email", "") or ""
            }

            # Structure hotel info as nested object
            booking["hotel"] = {
                "id": booking.get("hotel_id", "") or "",
                "name": booking.get("hotel_name", "") or "",
                "cityCode": booking.pop("city_code", "") or ""
            }

        return {
                "success": True,
                "message": "Bookings fetched successfully",
                "data": {
                    "bookings": bookings,
                    "total_count": len(bookings)
                }
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "get_all_bookings API Error")
        return {
                "success": False,
                "error": str(e)
        }


@frappe.whitelist(allow_guest=False)
def update_booking(
    booking_id,
    booking_status=None,
    payment_status=None,
    external_booking_id=None,
    hotel_confirmation_no=None,
    hotel_id=None,
    hotel_name=None,
    city_code=None,
    room_id=None,
    room_type=None,
    room_count=None,
    check_in=None,
    check_out=None,
    occupancy=None,
    adult_count=None,
    child_count=None,
    total_amount=None,
    tax=None,
    currency=None,
    contact_first_name=None,
    contact_last_name=None,
    contact_phone=None,
    contact_email=None,
    guest_list=None,
    room_details=None,
    cancellation_policy=None,
    remark=None,
    make_my_trip=None,
    booking_com=None,
    agoda=None
):
    """
    API to update an existing hotel booking.

    Args:
        booking_id (str): Booking ID to identify the booking (required)
        booking_status (str, optional): Booking status (pending, confirmed, cancelled, completed)
        payment_status (str, optional): Payment status
        external_booking_id (str, optional): External booking ID
        hotel_confirmation_no (str, optional): Hotel confirmation number
        hotel_id (str, optional): Hotel ID
        hotel_name (str, optional): Hotel name
        city_code (str, optional): City code
        room_id (str, optional): Room ID
        room_type (str, optional): Room type
        room_count (int, optional): Number of rooms
        check_in (str, optional): Check-in date
        check_out (str, optional): Check-out date
        occupancy (int, optional): Occupancy
        adult_count (int, optional): Number of adults
        child_count (int, optional): Number of children
        total_amount (float, optional): Total amount
        tax (float, optional): Tax amount
        currency (str, optional): Currency code
        contact_first_name (str, optional): Contact first name
        contact_last_name (str, optional): Contact last name
        contact_phone (str, optional): Contact phone
        contact_email (str, optional): Contact email
        guest_list (list, optional): List of guests
        room_details (list, optional): Room details
        cancellation_policy (list, optional): Cancellation policy
        remark (str, optional): Remarks
        make_my_trip (str, optional): Make My Trip reference
        booking_com (str, optional): Booking.com reference
        agoda (str, optional): Agoda reference

    Returns:
        dict: Response with success status and updated booking data
    """
    try:
        # Find booking by booking_id
        booking_name = frappe.db.get_value("Hotel Bookings", {"booking_id": booking_id}, "name")

        if not booking_name:
            return {
                "success": False,
                "message": f"Booking with ID '{booking_id}' not found"
            }

        # Get the booking document
        booking_doc = frappe.get_doc("Hotel Bookings", booking_name)

        # Update fields if provided
        if booking_status is not None:
            booking_doc.booking_status = booking_status

        if payment_status is not None:
            booking_doc.payment_status = payment_status

        if external_booking_id is not None:
            booking_doc.external_booking_id = external_booking_id

        if hotel_confirmation_no is not None:
            booking_doc.hotel_confirmation_no = hotel_confirmation_no

        if hotel_id is not None:
            booking_doc.hotel_id = hotel_id

        if hotel_name is not None:
            booking_doc.hotel_name = hotel_name

        if city_code is not None:
            booking_doc.city_code = city_code

        if room_id is not None:
            booking_doc.room_id = room_id

        if room_type is not None:
            booking_doc.room_type = room_type

        if room_count is not None:
            booking_doc.room_count = int(room_count)

        if check_in is not None:
            booking_doc.check_in = check_in

        if check_out is not None:
            booking_doc.check_out = check_out

        if occupancy is not None:
            booking_doc.occupancy = occupancy

        if adult_count is not None:
            booking_doc.adult_count = int(adult_count)

        if child_count is not None:
            booking_doc.child_count = child_count

        if total_amount is not None:
            booking_doc.total_amount = total_amount

        if tax is not None:
            booking_doc.tax = tax

        if currency is not None:
            booking_doc.currency = currency

        if contact_first_name is not None:
            booking_doc.contact_first_name = contact_first_name

        if contact_last_name is not None:
            booking_doc.contact_last_name = contact_last_name

        if contact_phone is not None:
            booking_doc.contact_phone = contact_phone

        if contact_email is not None:
            booking_doc.contact_email = contact_email

        if guest_list is not None:
            if isinstance(guest_list, str):
                booking_doc.guest_list = guest_list
            else:
                booking_doc.guest_list = json.dumps(guest_list)

        if room_details is not None:
            if isinstance(room_details, str):
                booking_doc.room_details = room_details
            else:
                booking_doc.room_details = json.dumps(room_details)

        if cancellation_policy is not None:
            if isinstance(cancellation_policy, str):
                booking_doc.cancellation_policy = cancellation_policy
            else:
                booking_doc.cancellation_policy = json.dumps(cancellation_policy)

        if remark is not None:
            booking_doc.remark = remark

        if make_my_trip is not None:
            booking_doc.make_my_trip = make_my_trip

        if booking_com is not None:
            booking_doc.booking_com = booking_com

        if agoda is not None:
            booking_doc.agoda = agoda

        # Save the updated booking
        booking_doc.save(ignore_permissions=True)
        frappe.db.commit()

        return {
            "success": True,
            "message": "Booking updated successfully",
            "data": {
                "name": booking_doc.name,
                "booking_id": booking_doc.booking_id,
                "booking_status": booking_doc.booking_status,
                "payment_status": booking_doc.payment_status,
                "modified": str(booking_doc.modified)
            }
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "update_booking API Error")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=False)
def cancel_booking(**kwargs):
    """
    API to cancel a hotel booking.

    This API cancels an existing hotel booking, updates the booking status to 'cancelled',
    processes refunds for successful payments, and updates the refund status in Booking Payments.

    Request payload structure:
    {
        "booking_id": "external_booking_id"
    }

    Args:
        booking_id (str): The external booking ID to cancel (required)

    Returns:
        dict: Response with success status and refund details
    """
    try:
        # Extract data from kwargs
        data = kwargs

        # Validate booking_id (required)
        booking_id = data.get("booking_id")
        if not booking_id:
            return {
                "success": False,
                "error": "booking_id is required"
            }

        if not isinstance(booking_id, str) or not booking_id.strip():
            return {
                "success": False,
                "error": "booking_id must be a non-empty string"
            }
        booking_id = booking_id.strip()

        # Check if Hotel Booking exists
        hotel_booking = frappe.db.get_value(
            "Hotel Bookings",
            {"external_booking_id": booking_id},
            ["name", "booking_status"],
            as_dict=True
        )

        if not hotel_booking:
            return {
                "success": False,
                "error": f"Hotel booking not found with booking_id: {booking_id}"
            }

        # Check if booking is already cancelled
        if hotel_booking.booking_status == "cancelled":
            return {
                "success": False,
                "error": f"Booking is already cancelled. Booking ID: {booking_id}"
            }

        # Update Hotel Booking status to cancelled
        booking_doc = frappe.get_doc("Hotel Bookings", hotel_booking.name)
        booking_doc.booking_status = "cancelled"
        booking_doc.save(ignore_permissions=True)

        # Fetch payment records linked to this booking and process refunds
        refund_results = []
        payment_records = frappe.get_all(
            "Booking Payments",
            filters={
                "booking_id": hotel_booking.name,
                "payment_status": "payment_success"
            },
            fields=["name", "transaction_id", "total_amount", "currency"]
        )

        for payment in payment_records:
            if payment.transaction_id:
                # Call refund API
                refund_response = call_refund_api(
                    payment_id=payment.transaction_id,
                    amount=payment.total_amount or 0,
                    currency=payment.currency
                )

                # Update payment record refund_status to initialized
                payment_doc = frappe.get_doc("Booking Payments", payment.name)
                payment_doc.refund_status = "initialized"
                payment_doc.save(ignore_permissions=True)

                refund_results.append({
                    "payment_name": payment.name,
                    "transaction_id": payment.transaction_id,
                    "refund_api_success": refund_response.get("success"),
                    "refund_api_response": refund_response
                })

        frappe.db.commit()

        return {
            "success": True,
            "message": "Booking cancelled successfully",
            "data": {
                "hotel_booking_id": hotel_booking.name,
                "booking_id": booking_id,
                "booking_status": "cancelled",
                "refunds_processed": len(refund_results),
                "refund_results": refund_results
            }
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "cancel_booking API Error")
        return {
            "success": False,
            "error": str(e)
        }
