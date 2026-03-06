import frappe
from frappe.utils import nowdate, add_days, get_first_day_of_week, getdate
from datetime import datetime, timedelta
import csv
import io
import requests
import json
from destiin.destiin.constants import TASKS_HITPAY_CREATE_PAYMENT_URL, TASKS_EMAIL_API_URL


@frappe.whitelist()
def test_weekly_booking_report():
    """
    Test endpoint to manually trigger the weekly booking report.
    Can be called from browser or Postman.
    """
    if frappe.session.user == "Guest":
        frappe.throw("Authentication required")

    send_weekly_booking_report()
    return {"status": "success", "message": "Weekly booking report sent successfully"}


@frappe.whitelist()
def test_company_booking_report(company_name=None, start_date=None, end_date=None):
    """
    Test endpoint to send booking report for a specific company.

    Args:
        company_name: Company name (optional, will use first company if not provided)
        start_date: Start date in YYYY-MM-DD format (optional, defaults to Monday of current week)
        end_date: End date in YYYY-MM-DD format (optional, defaults to today)
    """
    if frappe.session.user == "Guest":
        frappe.throw("Authentication required")

    logger = frappe.logger("test_booking_report")

    # Default dates if not provided
    if not start_date or not end_date:
        from datetime import timedelta
        today = getdate(nowdate())
        start_date = start_date or str(today - timedelta(days=today.weekday()))
        end_date = end_date or str(today)

    # Get company if not provided
    if not company_name:
        companies = frappe.db.sql("""
            SELECT DISTINCT company
            FROM `tabHotel Bookings`
            WHERE company IS NOT NULL
            LIMIT 1
        """, as_dict=True)

        if not companies:
            return {"status": "error", "message": "No companies found with bookings"}

        company_name = companies[0].get("company")

    try:
        send_company_booking_report(company_name, start_date, end_date, logger)
        return {
            "status": "success",
            "message": f"Report sent successfully for {company_name}",
            "company": company_name,
            "start_date": start_date,
            "end_date": end_date
        }
    except Exception as e:
        frappe.log_error(message=str(e), title="Test Booking Report Error")
        return {"status": "error", "message": str(e)}


@frappe.whitelist()
def send_weekly_booking_report():
    """
    Scheduler task to send BTC payment request emails to companies.
    Frequency is determined per-company via btc_payment_link_frequency in Hotel Booking Config.
    This task should be scheduled to run daily; each company's send cadence is driven by config.
    """
    logger = frappe.logger("weekly_booking_report")
    logger.info("Starting BTC payment report generation...")

    try:
        today = getdate(nowdate())
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = today

        # Drive from Hotel Booking Config — covers all configured companies
        company_configs = frappe.get_all(
            "Hotel Booking Config",
            fields=["company", "btc_payment_type", "btc_payment_link_frequency"],
        )

        if not company_configs:
            logger.info("No company configurations found. Skipping report generation.")
            return

        logger.info(f"Found {len(company_configs)} company configuration(s)")

        for config in company_configs:
            company_name = config.get("company")
            if not company_name:
                continue

            frequency = config.get("btc_payment_link_frequency")
            if not _should_send_today(frequency):
                logger.info(
                    f"Skipping {company_name}: not scheduled for today "
                    f"(frequency: {frequency} days)"
                )
                continue

            try:
                send_company_booking_report(company_name, start_of_week, end_of_week, logger)
            except Exception as e:
                logger.error(f"Error sending report for company {company_name}: {str(e)}")
                frappe.log_error(
                    message=f"Error sending BTC payment report for company {company_name}: {str(e)}",
                    title="Weekly Booking Report Error"
                )
                continue

        logger.info("BTC payment report generation completed successfully")

    except Exception as e:
        logger.error(f"Error in weekly booking report: {str(e)}")
        frappe.log_error(
            message=f"Error in weekly booking report scheduler: {str(e)}",
            title="Weekly Booking Report Scheduler Error"
        )


def create_payment_link(booking, logger):
    """
    Create payment link for a booking using HitPay API.
    """
    url = TASKS_HITPAY_CREATE_PAYMENT_URL
    headers = {
        "Content-Type": "application/json"
    }

    # Prepare payment data
    amount = booking.get("total_amount") or 0
    email = booking.get("personal_email") or "no-email@example.com"
    name = booking.get("employee_name") or "Guest"
    phone = booking.get("cell_number") or "+6500000000"
    purpose = f"Hotel Booking - {booking.get('hotel_name')} ({booking.get('check_in')} to {booking.get('check_out')})"
    request_booking_id = booking.get("booking_id") or booking.get("name")

    payload = {
        "amount": float(amount),
        "currency":"USD",
        "email": email,
        "name": name,
        "phone": phone,
        "purpose": purpose,
        "request_booking_id": request_booking_id,
        "redirect_url": "https://cbt-dev-destiin.vercel.app/payment-success",
        "payment_methods": ["card"]
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)

        if response.status_code != 200:
            logger.error(f"Payment API returned status code {response.status_code}: {response.text}")
            return f"Error: API returned {response.status_code}"

        response_data = response.json()
        # Assuming the API returns a payment URL in the response
        # Adjust the key based on actual API response structure
        payment_url = response_data.get("payment_url") or response_data.get("url") or response_data.get("payment_link") or str(response_data)

        return payment_url
    except requests.exceptions.Timeout:
        logger.error("Payment API request timed out")
        return "Error: Request timeout"
    except Exception as e:
        logger.error(f"Error calling payment API: {str(e)}")
        return f"Error: {str(e)}"


def _get_company_config(company_name):
    """
    Fetch Hotel Booking Config for a given company.
    Returns a dict with config fields or an empty dict if not found.
    """
    configs = frappe.get_all(
        "Hotel Booking Config",
        filters={"company": company_name},
        fields=["btc_payment_type", "btc_payment_link_frequency"],
        limit=1
    )
    return configs[0] if configs else {}


def _should_send_today(frequency_days):
    """
    Determine if today falls on a scheduled send day for the given frequency (in days).
    Uses 2025-01-01 as a fixed reference epoch so the schedule is deterministic.
    Returns True if no frequency is set (always send) or if today is a send day.
    """
    if not frequency_days:
        return True
    try:
        freq = int(frequency_days)
        if freq <= 0:
            return True
        from datetime import date
        today = getdate(nowdate())
        ref = date(2025, 1, 1)
        delta = (today - ref).days
        return delta % freq == 0
    except (ValueError, TypeError):
        return True


def create_bulk_payment_link(company_name, company_email, bookings, total_amount, currency, logger):
    """
    Create a single consolidated HitPay payment link for all pending BTC bookings.
    The amount is the sum of all booking totals.
    """
    url = TASKS_HITPAY_CREATE_PAYMENT_URL
    headers = {"Content-Type": "application/json"}

    booking_ids = [str(b.get("booking_id") or b.get("name")) for b in bookings if b.get("booking_id") or b.get("name")]
    purpose = f"BTC Consolidated Payment - {company_name} ({len(bookings)} booking(s))"

    payload = {
        "amount": float(total_amount),
        "currency": currency or "USD",
        "email": company_email,
        "name": company_name,
        "purpose": purpose,
        "request_booking_id": ",".join(booking_ids),
        "redirect_url": "https://cbt-dev-destiin.vercel.app/payment-success",
        "payment_methods": ["card"]
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
        if response.status_code != 200:
            logger.error(f"Bulk payment API returned {response.status_code}: {response.text}")
            return f"Error: API returned {response.status_code}"
        response_data = response.json()
        return (
            response_data.get("payment_url")
            or response_data.get("url")
            or response_data.get("payment_link")
            or str(response_data)
        )
    except requests.exceptions.Timeout:
        logger.error("Bulk payment API request timed out")
        return "Error: Request timeout"
    except Exception as e:
        logger.error(f"Error calling bulk payment API: {str(e)}")
        return f"Error: {str(e)}"


def generate_btc_email_body(company_name, bookings, total_amount, currency,
                             btc_payment_type="Individual", bulk_payment_url=None):
    """
    Generate HTML email body for BTC payment requests.
    - Bulk: summary table + single consolidated 'Pay Now' button.
    - Individual: table with per-booking payment links.
    """
    booking_rows = ""
    for b in bookings:
        booking_id = b.get("booking_id") or b.get("name") or "-"
        employee_name = b.get("employee_name") or "-"
        hotel_name = b.get("hotel_name") or "-"
        check_in = str(b.get("check_in") or "-")
        check_out = str(b.get("check_out") or "-")
        amount = b.get("total_amount") or 0
        curr = b.get("currency") or currency

        if btc_payment_type == "Individual":
            pay_url = b.get("payment_url") or "#"
            pay_cell = (
                f'<td style="padding:8px 12px;border-bottom:1px solid #e0e0e0;text-align:center;">'
                f'<a href="{pay_url}" style="background:#667eea;color:#fff;padding:6px 14px;'
                f'border-radius:4px;text-decoration:none;font-size:12px;font-weight:600;">Pay</a>'
                f'</td>'
            )
        else:
            pay_cell = ""

        booking_rows += (
            f'<tr>'
            f'<td style="padding:8px 12px;border-bottom:1px solid #e0e0e0;">{booking_id}</td>'
            f'<td style="padding:8px 12px;border-bottom:1px solid #e0e0e0;">{employee_name}</td>'
            f'<td style="padding:8px 12px;border-bottom:1px solid #e0e0e0;">{hotel_name}</td>'
            f'<td style="padding:8px 12px;border-bottom:1px solid #e0e0e0;">{check_in}</td>'
            f'<td style="padding:8px 12px;border-bottom:1px solid #e0e0e0;">{check_out}</td>'
            f'<td style="padding:8px 12px;border-bottom:1px solid #e0e0e0;text-align:right;">'
            f'{curr} {float(amount):,.2f}</td>'
            f'{pay_cell}'
            f'</tr>'
        )

    pay_col_header = (
        '<th style="padding:10px 12px;text-align:center;font-size:12px;color:#666;font-weight:600;">Pay</th>'
        if btc_payment_type == "Individual" else ""
    )

    bulk_payment_section = ""
    if btc_payment_type == "Bulk" and bulk_payment_url:
        bulk_payment_section = f"""
        <tr>
            <td style="padding:20px 40px 30px 40px;text-align:center;">
                <p style="margin:0 0 8px 0;color:#555;font-size:14px;">
                    All <strong>{len(bookings)}</strong> pending bookings are consolidated into a single payment.
                </p>
                <p style="margin:0 0 20px 0;color:#333;font-size:22px;font-weight:700;">
                    Total: {currency} {total_amount:,.2f}
                </p>
                <a href="{bulk_payment_url}"
                   style="display:inline-block;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
                          color:#ffffff;text-decoration:none;padding:16px 36px;border-radius:6px;
                          font-size:16px;font-weight:700;">
                    Pay Now — {currency} {total_amount:,.2f}
                </a>
                <p style="margin:12px 0 0 0;color:#999;font-size:11px;">
                    Click the button above to complete the consolidated payment via HitPay.
                </p>
            </td>
        </tr>"""

    mode_label = "Consolidated (Bulk)" if btc_payment_type == "Bulk" else "Individual Payment Links"

    return f"""
    <html>
    <body style="margin:0;padding:0;background-color:#f4f4f4;font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f4f4;padding:20px 0;">
            <tr>
                <td align="center">
                    <table width="650" cellpadding="0" cellspacing="0"
                           style="background-color:#ffffff;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1);">

                        <!-- Header -->
                        <tr>
                            <td style="background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);
                                        padding:30px 40px;border-radius:8px 8px 0 0;">
                                <h1 style="color:#ffffff;margin:0;font-size:22px;font-weight:600;">
                                    BTC Payment Request
                                </h1>
                                <p style="color:rgba(255,255,255,0.85);margin:8px 0 0 0;font-size:13px;">
                                    Destiin Travel Management &nbsp;|&nbsp; {mode_label}
                                </p>
                            </td>
                        </tr>

                        <!-- Company + Summary -->
                        <tr>
                            <td style="padding:28px 40px 20px 40px;">
                                <table width="100%" cellpadding="0" cellspacing="0"
                                       style="background-color:#f8f9fa;border-radius:6px;padding:18px 20px;">
                                    <tr>
                                        <td>
                                            <p style="margin:0 0 4px 0;color:#6c757d;font-size:11px;
                                                       text-transform:uppercase;letter-spacing:1px;">Company</p>
                                            <p style="margin:0;color:#333;font-size:18px;font-weight:600;">
                                                {company_name}
                                            </p>
                                        </td>
                                        <td style="text-align:right;">
                                            <p style="margin:0 0 4px 0;color:#6c757d;font-size:11px;
                                                       text-transform:uppercase;letter-spacing:1px;">Pending Bookings</p>
                                            <p style="margin:0;color:#333;font-size:18px;font-weight:600;">
                                                {len(bookings)}
                                            </p>
                                        </td>
                                        <td style="text-align:right;padding-left:30px;">
                                            <p style="margin:0 0 4px 0;color:#6c757d;font-size:11px;
                                                       text-transform:uppercase;letter-spacing:1px;">Total Amount</p>
                                            <p style="margin:0;color:#388e3c;font-size:18px;font-weight:700;">
                                                {currency} {total_amount:,.2f}
                                            </p>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <!-- Bulk Pay Button (Bulk mode only) -->
                        {bulk_payment_section}

                        <!-- Bookings Table -->
                        <tr>
                            <td style="padding:0 40px 30px 40px;">
                                <h3 style="color:#333;font-size:15px;margin:0 0 12px 0;font-weight:600;">
                                    Pending Booking Details
                                </h3>
                                <table width="100%" cellpadding="0" cellspacing="0"
                                       style="border:1px solid #e0e0e0;border-radius:6px;overflow:hidden;font-size:12px;">
                                    <tr style="background-color:#f5f5f5;">
                                        <th style="padding:10px 12px;text-align:left;color:#666;font-weight:600;">Booking ID</th>
                                        <th style="padding:10px 12px;text-align:left;color:#666;font-weight:600;">Employee</th>
                                        <th style="padding:10px 12px;text-align:left;color:#666;font-weight:600;">Hotel</th>
                                        <th style="padding:10px 12px;text-align:left;color:#666;font-weight:600;">Check-in</th>
                                        <th style="padding:10px 12px;text-align:left;color:#666;font-weight:600;">Check-out</th>
                                        <th style="padding:10px 12px;text-align:right;color:#666;font-weight:600;">Amount</th>
                                        {pay_col_header}
                                    </tr>
                                    {booking_rows}
                                </table>
                            </td>
                        </tr>

                        <!-- Footer -->
                        <tr>
                            <td style="background-color:#f8f9fa;padding:22px 40px;
                                        border-radius:0 0 8px 8px;border-top:1px solid #e0e0e0;">
                                <p style="margin:0;color:#666;font-size:12px;line-height:1.6;">
                                    This is an automated payment request from Destiin Travel Management.
                                    Please do not reply to this email.
                                </p>
                                <p style="margin:12px 0 0 0;color:#999;font-size:11px;">
                                    &copy; {datetime.now().year} Destiin. All rights reserved.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


def send_company_booking_report(company_name, start_of_week, end_of_week, logger):
    """
    Send BTC payment request email for a specific company.
    Fetches Hotel Booking Config to determine btc_payment_type (Bulk / Individual)
    and generates payment links accordingly for all pending BTC bookings.
    """
    # Get company email
    try:
        company = frappe.get_doc("Company", company_name)
        company_email = company.email
    except frappe.DoesNotExistError:
        logger.warning(f"Company {company_name} not found in Company doctype. Skipping.")
        return

    if not company_email:
        logger.warning(f"No email configured for company {company_name}. Skipping.")
        return

    # Fetch Hotel Booking Config for this company
    config = _get_company_config(company_name)
    btc_payment_type = config.get("btc_payment_type") or "Individual"

    logger.info(f"Company {company_name} — BTC payment type: {btc_payment_type}")

    # Fetch ALL pending BTC bookings (no date restriction — collect all outstanding dues)
    pending_bookings = frappe.db.sql("""
        SELECT
            hb.name,
            hb.booking_id,
            hb.employee,
            hb.hotel_name,
            hb.check_in,
            hb.check_out,
            hb.room_count,
            hb.adult_count,
            hb.child_count,
            hb.room_type,
            hb.booking_status,
            hb.payment_status,
            hb.payment_mode,
            hb.tax,
            hb.total_amount,
            hb.currency,
            hb.creation,
            emp.employee_name,
            emp.personal_email,
            emp.cell_number
        FROM `tabHotel Bookings` hb
        LEFT JOIN `tabEmployee` emp ON hb.employee = emp.name
        WHERE hb.company = %s
        AND hb.payment_mode = 'BTC'
        AND hb.payment_status = 'Pending'
        ORDER BY hb.creation DESC
    """, (company_name,), as_dict=True)

    if not pending_bookings:
        logger.info(f"No pending BTC bookings for company {company_name}. Skipping.")
        return

    logger.info(f"Found {len(pending_bookings)} pending BTC booking(s) for {company_name}")

    total_amount = sum(float(b.get("total_amount") or 0) for b in pending_bookings)
    currency = pending_bookings[0].get("currency") or "USD"
    email_subject = (
        f"BTC Payment Request - {company_name} "
        f"({len(pending_bookings)} booking(s) | {currency} {total_amount:,.2f})"
    )

    if btc_payment_type == "Bulk":
        # Consolidate all pending amounts into a single payment link
        bulk_payment_url = create_bulk_payment_link(
            company_name, company_email, pending_bookings, total_amount, currency, logger
        )
        email_body = generate_btc_email_body(
            company_name, pending_bookings, total_amount, currency,
            btc_payment_type="Bulk",
            bulk_payment_url=bulk_payment_url
        )
    else:
        # Create a separate payment link for each pending booking
        for booking in pending_bookings:
            try:
                booking["payment_url"] = create_payment_link(booking, logger)
            except Exception as e:
                logger.error(
                    f"Error creating payment link for booking "
                    f"{booking.get('booking_id')}: {str(e)}"
                )
                booking["payment_url"] = "Error generating payment link"

        email_body = generate_btc_email_body(
            company_name, pending_bookings, total_amount, currency,
            btc_payment_type="Individual"
        )

    try:
        send_email_via_api(
            to_emails=[company_email],
            subject=email_subject,
            body=email_body
        )
        logger.info(
            f"Successfully sent BTC payment request to {company_email} "
            f"for company {company_name}"
        )
    except Exception as e:
        logger.error(f"Failed to send email to {company_email}: {str(e)}")
        raise


def generate_csv_report(bookings):
    """
    Generate CSV content from bookings data.
    """
    output = io.StringIO()

    # Define CSV columns
    fieldnames = [
        "Booking ID",
        "Employee ID",
        "Employee Name",
        "Hotel Name",
        "Check-in Date",
        "Check-out Date",
        "Room Count",
        "Adult Count",
        "Child Count",
        "Room Type",
        "Booking Status",
        "Payment Status",
        "Tax",
        "Total Amount",
        "Currency",
        "Booking Created On",
        "Payment URL"
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for booking in bookings:
        writer.writerow({
            "Booking ID": booking.get("booking_id") or booking.get("name") or "",
            "Employee ID": booking.get("employee") or "",
            "Employee Name": booking.get("employee_name") or "",
            "Hotel Name": booking.get("hotel_name") or "",
            "Check-in Date": str(booking.get("check_in") or ""),
            "Check-out Date": str(booking.get("check_out") or ""),
            "Room Count": booking.get("room_count") or "",
            "Adult Count": booking.get("adult_count") or "",
            "Child Count": booking.get("child_count") or "",
            "Room Type": booking.get("room_type") or "",
            "Booking Status": booking.get("booking_status") or "",
            "Payment Status": booking.get("payment_status") or "",
            "Tax": booking.get("tax") or "",
            "Total Amount": booking.get("total_amount") or "",
            "Currency": booking.get("currency") or "",
            "Booking Created On": str(booking.get("creation") or ""),
            "Payment URL": booking.get("payment_url") or ""
        })

    return output.getvalue()


def save_csv_file(csv_content, filename, company_name):
    """
    Save CSV content as a Frappe file and return the file URL.
    """
    # Create file document in Frappe
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": filename,
        "content": csv_content,
        "is_private": 0,  # Make it publicly accessible
        "folder": "Home"
    })
    file_doc.save(ignore_permissions=True)
    frappe.db.commit()

    # Get the site URL and construct full file URL
    site_url = frappe.utils.get_url()
    file_url = f"{site_url}{file_doc.file_url}"

    return file_url


def send_email_via_api(to_emails, subject, body, csv_file_url=None):
    """
    Send email using the external email API.
    """
    url = TASKS_EMAIL_API_URL
    headers = {
        "Content-Type": "application/json",
        "info": "true"
    }
    payload = {
        "toEmails": to_emails,
        "subject": subject,
        "body": body
    }

    if csv_file_url:
        payload["csvFileUrl"] = csv_file_url

    response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)

    if response.status_code != 200:
        raise Exception(f"Email API returned status code {response.status_code}: {response.text}")

    return response.json()


def generate_email_body(company_name, bookings, start_of_week, end_of_week, csv_file_url=None):
    """
    Generate HTML email body with booking summary using custom template.
    """
    total_bookings = len(bookings)

    # Count booking statuses
    status_counts = {}
    for booking in bookings:
        status = booking.get("booking_status") or "Unknown"
        status_counts[status] = status_counts.get(status, 0) + 1

    # Calculate total revenue
    total_revenue = 0
    for booking in bookings:
        try:
            price = float(booking.get("total_amount") or 0)
            total_revenue += price
        except (ValueError, TypeError):
            pass

    # Generate status summary rows
    status_rows = "".join([
        f'<tr><td style="padding: 8px 12px; border-bottom: 1px solid #e0e0e0;">{status}</td>'
        f'<td style="padding: 8px 12px; border-bottom: 1px solid #e0e0e0; text-align: center;">{count}</td></tr>'
        for status, count in status_counts.items()
    ])

    email_body = f"""
    <html>
    <body style="margin: 0; padding: 0; background-color: #f4f4f4; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px 0;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                        <!-- Header -->
                        <tr>
                            <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px 40px; border-radius: 8px 8px 0 0;">
                                <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: 600;">Weekly Booking Report</h1>
                                <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0; font-size: 14px;">Destiin Travel Management System</p>
                            </td>
                        </tr>

                        <!-- Company Info -->
                        <tr>
                            <td style="padding: 30px 40px 20px 40px;">
                                <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f8f9fa; border-radius: 6px; padding: 20px;">
                                    <tr>
                                        <td>
                                            <p style="margin: 0 0 8px 0; color: #6c757d; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">Company</p>
                                            <p style="margin: 0; color: #333; font-size: 18px; font-weight: 600;">{company_name}</p>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding-top: 15px;">
                                            <p style="margin: 0 0 8px 0; color: #6c757d; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">Report Period</p>
                                            <p style="margin: 0; color: #333; font-size: 16px;">{start_of_week} to {end_of_week}</p>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <!-- Summary Cards -->
                        <tr>
                            <td style="padding: 0 40px 20px 40px;">
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td width="48%" style="background-color: #e3f2fd; border-radius: 6px; padding: 20px; text-align: center;">
                                            <p style="margin: 0; color: #1976d2; font-size: 32px; font-weight: 700;">{total_bookings}</p>
                                            <p style="margin: 8px 0 0 0; color: #1976d2; font-size: 14px;">Total Bookings</p>
                                        </td>
                                        <td width="4%"></td>
                                        <td width="48%" style="background-color: #e8f5e9; border-radius: 6px; padding: 20px; text-align: center;">
                                            <p style="margin: 0; color: #388e3c; font-size: 32px; font-weight: 700;">{total_revenue:,.2f}</p>
                                            <p style="margin: 8px 0 0 0; color: #388e3c; font-size: 14px;">Total Bookings value</p>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <!-- Status Breakdown -->
                        <tr>
                            <td style="padding: 0 40px 30px 40px;">
                                <h3 style="color: #333; font-size: 16px; margin: 0 0 15px 0; font-weight: 600;">Booking Status Breakdown</h3>
                                <table width="100%" cellpadding="0" cellspacing="0" style="border: 1px solid #e0e0e0; border-radius: 6px; overflow: hidden;">
                                    <tr style="background-color: #f5f5f5;">
                                        <th style="padding: 12px; text-align: left; font-size: 13px; color: #666; font-weight: 600;">Status</th>
                                        <th style="padding: 12px; text-align: center; font-size: 13px; color: #666; font-weight: 600;">Count</th>
                                    </tr>
                                    {status_rows}
                                </table>
                            </td>
                        </tr>

                        <!-- Download Report Button -->
                        {f'''<tr>
                            <td style="padding: 0 40px 30px 40px; text-align: center;">
                                <a href="{csv_file_url}" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #ffffff; text-decoration: none; padding: 14px 28px; border-radius: 6px; font-size: 14px; font-weight: 600;">
                                    Download Full Report (CSV)
                                </a>
                                <p style="margin: 12px 0 0 0; color: #666; font-size: 12px;">Click the button above to download the detailed booking report</p>
                            </td>
                        </tr>''' if csv_file_url else ''}

                        <!-- Footer -->
                        <tr>
                            <td style="background-color: #f8f9fa; padding: 25px 40px; border-radius: 0 0 8px 8px; border-top: 1px solid #e0e0e0;">
                                <p style="margin: 0; color: #666; font-size: 13px; line-height: 1.6;">
                                    This is an automated email from Destiin Travel Management System. Please do not reply to this email.
                                </p>
                                <p style="margin: 15px 0 0 0; color: #999; font-size: 11px;">
                                    &copy; {datetime.now().year} Destiin. All rights reserved.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    return email_body
