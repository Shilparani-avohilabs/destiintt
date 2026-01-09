import frappe
from frappe.utils import nowdate, add_days, get_first_day_of_week, getdate
from datetime import datetime, timedelta
import csv
import io
import requests
import json


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
            FROM `tabTravel Bookings`
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
            name,
            booking_id,
            employee_id,
            employee_name,
            hotel_name,
            destination,
            check_in_date,
            check_out_date,
            room_count,
            guest_count,
            child_count,
            room_type,
            supplier,
            booking_status,
            payment_status,
            payment_method,
            price,
            tax,
            total_price,
            currency,
            creation
        FROM `tabTravel Bookings`
        WHERE company = %s
        AND creation BETWEEN %s AND %s
        ORDER BY creation DESC
    """, (company_name, start_of_week, add_days(end_of_week, 1)), as_dict=True)

    if not bookings:
        logger.info(f"No bookings found for company {company_name} this week")
        return

    logger.info(f"Found {len(bookings)} bookings for company {company_name}")

    # Generate CSV content
    csv_content = generate_csv_report(bookings)

    # Generate report filename
    report_filename = f"Weekly_Booking_Report_{company_name}_{start_of_week}_to_{end_of_week}.csv"

    # Create email content
    email_subject = f"Weekly Booking Report - {company_name} ({start_of_week} to {end_of_week})"
    email_body = generate_email_body(company_name, bookings, start_of_week, end_of_week)

    # Send email via API
    try:
        send_email_via_api(
            to_emails=[company_email],
            subject=email_subject,
            body=email_body
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
        "Destination",
        "Check-in Date",
        "Check-out Date",
        "Room Count",
        "Guest Count",
        "Child Count",
        "Room Type",
        "Supplier",
        "Booking Status",
        "Payment Status",
        "Payment Method",
        "Price (Without Tax)",
        "Tax",
        "Total Price (inc Tax)",
        "Currency",
        "Booking Created On"
    ]

    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for booking in bookings:
        writer.writerow({
            "Booking ID": booking.get("booking_id") or booking.get("name") or "",
            "Employee ID": booking.get("employee_id") or "",
            "Employee Name": booking.get("employee_name") or "",
            "Hotel Name": booking.get("hotel_name") or "",
            "Destination": booking.get("destination") or "",
            "Check-in Date": str(booking.get("check_in_date") or ""),
            "Check-out Date": str(booking.get("check_out_date") or ""),
            "Room Count": booking.get("room_count") or "",
            "Guest Count": booking.get("guest_count") or "",
            "Child Count": booking.get("child_count") or "",
            "Room Type": booking.get("room_type") or "",
            "Supplier": booking.get("supplier") or "",
            "Booking Status": booking.get("booking_status") or "",
            "Payment Status": booking.get("payment_status") or "",
            "Payment Method": booking.get("payment_method") or "",
            "Price (Without Tax)": booking.get("price") or "",
            "Tax": booking.get("tax") or "",
            "Total Price (inc Tax)": booking.get("total_price") or "",
            "Currency": booking.get("currency") or "",
            "Booking Created On": str(booking.get("creation") or "")
        })

    return output.getvalue()


def send_email_via_api(to_emails, subject, body):
    """
    Send email using the external email API.
    """
    url = "http://16.112.129.113/v1/email/send"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "toEmails": to_emails,
        "subject": subject,
        "body": body
    }

    response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)

    if response.status_code != 200:
        raise Exception(f"Email API returned status code {response.status_code}: {response.text}")

    return response.json()


def generate_email_body(company_name, bookings, start_of_week, end_of_week):
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
            price = float(booking.get("total_price") or 0)
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
                                            <p style="margin: 8px 0 0 0; color: #388e3c; font-size: 14px;">Total Revenue</p>
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
