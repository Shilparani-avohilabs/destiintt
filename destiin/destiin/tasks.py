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
    Weekly scheduler task to send booking reports to companies.
    Runs every Friday at 9 AM.
    Fetches all bookings from the current week (Monday to Friday) grouped by company
    and sends an Excel/CSV report to each company's email.
    """
    logger = frappe.logger("weekly_booking_report")
    logger.info("Starting weekly booking report generation...")

    try:
        # Get current week's date range (Monday to Friday)
        today = getdate(nowdate())
        # Calculate the start of the week (Monday)
        start_of_week = today - timedelta(days=today.weekday())
        # End of week is today (Friday when scheduler runs)
        end_of_week = today

        logger.info(f"Fetching bookings from {start_of_week} to {end_of_week}")

        # Get all unique companies that have bookings this week
        companies = frappe.db.sql("""
            SELECT DISTINCT company
            FROM `tabHotel Bookings`
            WHERE creation BETWEEN %s AND %s
            AND company IS NOT NULL
            AND company != ''
        """, (start_of_week, add_days(end_of_week, 1)), as_dict=True)

        if not companies:
            logger.info("No bookings found for this week. Skipping report generation.")
            return

        logger.info(f"Found bookings for {len(companies)} companies")

        for company_record in companies:
            company_name = company_record.get("company")
            if not company_name:
                continue

            try:
                send_company_booking_report(company_name, start_of_week, end_of_week, logger)
            except Exception as e:
                logger.error(f"Error sending report for company {company_name}: {str(e)}")
                frappe.log_error(
                    message=f"Error sending weekly booking report for company {company_name}: {str(e)}",
                    title="Weekly Booking Report Error"
                )
                continue

        logger.info("Weekly booking report generation completed successfully")

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
        "email": email,
        "name": name,
        "phone": phone,
        "purpose": purpose,
        "request_booking_id": request_booking_id,
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


def send_company_booking_report(company_name, start_of_week, end_of_week, logger):
    """
    Send booking report for a specific company.
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

    # Fetch all bookings for this company in the current week
    bookings = frappe.db.sql("""
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
        AND hb.creation BETWEEN %s AND %s
        ORDER BY hb.creation DESC
    """, (company_name, start_of_week, add_days(end_of_week, 1)), as_dict=True)

    if not bookings:
        logger.info(f"No bookings found for company {company_name} this week")
        return

    logger.info(f"Found {len(bookings)} bookings for company {company_name}")

    # Generate payment URLs for each booking
    for booking in bookings:
        try:
            payment_url = create_payment_link(booking, logger)
            booking['payment_url'] = payment_url
        except Exception as e:
            logger.error(f"Error creating payment link for booking {booking.get('booking_id')}: {str(e)}")
            booking['payment_url'] = "Error generating payment link"

    # Generate CSV content
    csv_content = generate_csv_report(bookings)

    # Generate report filename
    report_filename = f"Weekly_Booking_Report_{company_name}_{start_of_week}_to_{end_of_week}.csv"

    # Save CSV file and get URL
    csv_file_url = save_csv_file(csv_content, report_filename, company_name)
    logger.info(f"CSV file saved at: {csv_file_url}")

    # Create email content
    email_subject = f"Weekly Booking Report - {company_name} ({start_of_week} to {end_of_week})"
    email_body = generate_email_body(company_name, bookings, start_of_week, end_of_week, csv_file_url)

    # Send email via API
    try:
        send_email_via_api(
            to_emails=[company_email],
            subject=email_subject,
            body=email_body,
            csv_file_url=csv_file_url
        )
        logger.info(f"Successfully sent weekly booking report to {company_email} for company {company_name}")
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
