import frappe
from frappe.utils import nowdate, add_days, get_first_day_of_week, getdate
from datetime import datetime, timedelta
import csv
import io


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

    # Send email with attachment
    try:
        frappe.sendmail(
            recipients=[company_email],
            subject=email_subject,
            message=email_body,
            attachments=[{
                "fname": report_filename,
                "fcontent": csv_content.encode('utf-8')
            }],
            now=True
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


def generate_email_body(company_name, bookings, start_of_week, end_of_week):
    """
    Generate HTML email body with booking summary.
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

    status_summary = "<br>".join([f"&nbsp;&nbsp;• {status}: {count}" for status, count in status_counts.items()])

    email_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #333;">Weekly Booking Report</h2>
        <p><strong>Company:</strong> {company_name}</p>
        <p><strong>Report Period:</strong> {start_of_week} to {end_of_week}</p>

        <hr style="border: 1px solid #eee;">

        <h3 style="color: #555;">Summary</h3>
        <p><strong>Total Bookings:</strong> {total_bookings}</p>
        <p><strong>Total Revenue:</strong> {total_revenue:,.2f}</p>

        <p><strong>Booking Status Breakdown:</strong><br>
        {status_summary}
        </p>

        <hr style="border: 1px solid #eee;">

        <p style="color: #666; font-size: 12px;">
            Please find the detailed booking report attached as a CSV file.
            You can open this file in Excel or Google Sheets for further analysis.
        </p>

        <p style="color: #888; font-size: 11px; margin-top: 20px;">
            This is an automated email from Destiin Travel Management System.
        </p>
    </div>
    """

    return email_body
