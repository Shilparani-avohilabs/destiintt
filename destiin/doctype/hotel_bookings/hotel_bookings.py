# Copyright (c) 2026, Destiin and contributors
# For license information, please see license.txt

import frappe
import json
import csv
import io
import requests
from frappe.model.document import Document
from frappe.utils import nowdate, add_days, getdate
from datetime import datetime, timedelta
from destiin.destiin.constants import TASKS_HITPAY_CREATE_PAYMENT_URL, TASKS_EMAIL_API_URL


class HotelBookings(Document):
	pass


@frappe.whitelist()
def send_bill_to_company_report():
	"""
	Generate a report for Hotel Bookings where:
	- payment_mode = 'bill_to_company'
	- payment_status = 'payment_pending'

	Groups bookings by company, creates payment links for each,
	generates a CSV report, and sends it to each company's email.
	"""
	frappe.log_error(
		message="Step 1: Starting bill-to-company booking report generation",
		title="BTC Report - Started"
	)

	try:
		# Get all bill_to_company bookings with payment_pending, grouped by company
		companies = frappe.db.sql("""
			SELECT DISTINCT company
			FROM `tabHotel Bookings`
			WHERE payment_mode = 'bill_to_company'
			AND payment_status = 'payment_pending'
			AND company IS NOT NULL
			AND company != ''
		""", as_dict=True)

		frappe.log_error(
			message=f"Step 2: Company query result - Found {len(companies)} companies: {[c.get('company') for c in companies]}",
			title="BTC Report - Companies Found"
		)

		if not companies:
			frappe.log_error(
				message="Step 2: No companies found with bill_to_company + payment_pending bookings. Check if Hotel Bookings have payment_mode='bill_to_company' AND payment_status='payment_pending'",
				title="BTC Report - No Companies"
			)
			return {
				"success": False,
				"error": "No pending bill-to-company bookings found"
			}

		total_bookings = 0
		emails_sent = 0
		companies_processed = 0
		skipped_companies = []

		for company_record in companies:
			company_name = company_record.get("company")
			if not company_name:
				continue

			frappe.log_error(
				message=f"Step 3: Processing company: {company_name}",
				title="BTC Report - Processing Company"
			)

			try:
				result = _send_company_btc_report(company_name)
				if result:
					companies_processed += 1
					total_bookings += result.get("booking_count", 0)
					if result.get("email_sent"):
						emails_sent += 1
					frappe.log_error(
						message=f"Step 3: Company {company_name} processed successfully - {result}",
						title="BTC Report - Company Done"
					)
				else:
					skipped_companies.append(company_name)
					frappe.log_error(
						message=f"Step 3: Company {company_name} returned None (skipped - check company email or bookings)",
						title="BTC Report - Company Skipped"
					)
			except Exception as e:
				frappe.log_error(
					message=f"Step 3: Error for company {company_name}: {str(e)}\n{frappe.get_traceback()}",
					title="BTC Report - Company Error"
				)
				continue

		frappe.log_error(
			message=f"Step 4: Report complete - Companies processed: {companies_processed}, Total bookings: {total_bookings}, Emails sent: {emails_sent}, Skipped: {skipped_companies}",
			title="BTC Report - Completed"
		)

		return {
			"success": True,
			"message": "Bill-to-company booking report generated and sent successfully",
			"data": {
				"companies_processed": companies_processed,
				"total_bookings": total_bookings,
				"emails_sent": emails_sent
			}
		}

	except Exception as e:
		frappe.log_error(
			message=f"Fatal error in bill-to-company report: {str(e)}\n{frappe.get_traceback()}",
			title="BTC Report - Fatal Error"
		)
		return {
			"success": False,
			"error": str(e)
		}


def _send_company_btc_report(company_name):
	"""
	Send bill-to-company pending payment report for a specific company.
	Returns dict with booking_count and email_sent status.
	"""
	# Get company email
	try:
		company_doc = frappe.get_doc("Company", company_name)
		company_email = company_doc.email
		frappe.log_error(
			message=f"Company '{company_name}' found - email: {company_email}",
			title="BTC Report - Company Email Lookup"
		)
	except frappe.DoesNotExistError:
		frappe.log_error(
			message=f"Company '{company_name}' does NOT exist in Company doctype. Skipping.",
			title="BTC Report - Company Not Found"
		)
		return None

	if not company_email:
		frappe.log_error(
			message=f"Company '{company_name}' has no email configured. Skipping.",
			title="BTC Report - No Company Email"
		)
		return None

	# Fetch all bill_to_company + payment_pending bookings for this company
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
		AND hb.payment_mode = 'bill_to_company'
		AND hb.payment_status = 'payment_pending'
		ORDER BY hb.creation DESC
	""", (company_name,), as_dict=True)

	frappe.log_error(
		message=f"Bookings query for '{company_name}' returned {len(bookings)} results. Booking IDs: {[b.get('booking_id') or b.get('name') for b in bookings]}",
		title="BTC Report - Bookings Fetched"
	)

	if not bookings:
		return None

	# Generate payment links for each booking
	for booking in bookings:
		booking_id = booking.get("booking_id") or booking.get("name")
		try:
			frappe.log_error(
				message=f"Creating payment link for booking {booking_id} - amount: {booking.get('total_amount')}, employee: {booking.get('employee_name')}",
				title="BTC Report - Payment Link Start"
			)
			payment_url = _create_payment_link(booking)
			booking["payment_url"] = payment_url
			frappe.log_error(
				message=f"Payment link for booking {booking_id}: {payment_url}",
				title="BTC Report - Payment Link Result"
			)
		except Exception as e:
			frappe.log_error(
				message=f"Error creating payment link for booking {booking_id}: {str(e)}\n{frappe.get_traceback()}",
				title="BTC Report - Payment Link Error"
			)
			booking["payment_url"] = "Error generating payment link"

	# Generate CSV report
	frappe.log_error(
		message=f"Generating CSV report for '{company_name}' with {len(bookings)} bookings",
		title="BTC Report - CSV Generation"
	)
	csv_content = _generate_btc_csv_report(bookings)
	today = getdate(nowdate())
	report_filename = f"BillToCompany_Pending_Report_{company_name}_{today}.csv"

	# Save CSV and get URL
	csv_file_url = _save_csv_file(csv_content, report_filename)
	frappe.log_error(
		message=f"CSV saved for '{company_name}': {csv_file_url}",
		title="BTC Report - CSV Saved"
	)

	# Build and send email
	email_subject = f"Pending Payment Report - Bill to Company - {company_name}"
	email_body = _generate_btc_email_body(company_name, bookings, csv_file_url)

	frappe.log_error(
		message=f"Sending email to {company_email} for '{company_name}' - Subject: {email_subject}",
		title="BTC Report - Sending Email"
	)

	try:
		email_response = _send_email(
			to_emails=[company_email],
			subject=email_subject,
			body=email_body,
			csv_file_url=csv_file_url
		)
		frappe.log_error(
			message=f"Email sent successfully to {company_email} for '{company_name}'. API response: {email_response}",
			title="BTC Report - Email Sent"
		)
		return {"booking_count": len(bookings), "email_sent": True}
	except Exception as e:
		frappe.log_error(
			message=f"Failed to send email to {company_email} for '{company_name}': {str(e)}\n{frappe.get_traceback()}",
			title="BTC Report - Email Failed"
		)
		raise


def _create_payment_link(booking):
	"""
	Create a payment link for a booking using HitPay API.
	"""
	headers = {"Content-Type": "application/json"}

	amount = float(booking.get("total_amount") or 0)
	booking_id = booking.get("booking_id") or booking.get("name")

	if amount <= 0:
		frappe.log_error(
			message=f"Booking {booking_id} has amount {amount} <= 0. Skipping payment link.",
			title="BTC Report - Zero Amount"
		)
		return "No amount to pay"

	payload = {
		"amount": amount,
		"currency": "USD",
		"email": booking.get("personal_email") or "no-email@example.com",
		"name": booking.get("employee_name") or "Guest",
		"phone": booking.get("cell_number") or "",
		"purpose": f"Hotel Booking - {booking.get('hotel_name')} ({booking.get('check_in')} to {booking.get('check_out')})",
		"request_booking_id": booking_id,
		"redirect_url": "https://cbt-destiin-frontend.vercel.app/payment-success",
		"payment_methods": ["card"]
	}

	frappe.log_error(
		message=f"Payment API request for {booking_id}: URL={TASKS_HITPAY_CREATE_PAYMENT_URL}, Payload={json.dumps(payload)}",
		title="BTC Report - Payment API Request"
	)

	try:
		response = requests.post(
			TASKS_HITPAY_CREATE_PAYMENT_URL,
			headers=headers,
			data=json.dumps(payload),
			timeout=30
		)

		frappe.log_error(
			message=f"Payment API response for {booking_id}: status={response.status_code}, body={response.text[:500]}",
			title="BTC Report - Payment API Response"
		)

		if response.status_code != 200:
			return f"Error: API returned {response.status_code}"

		response_data = response.json()
		payment_url = (
			response_data.get("payment_url")
			or response_data.get("url")
			or response_data.get("data", {}).get("payment_url")
			or str(response_data)
		)
		return payment_url

	except requests.exceptions.Timeout:
		frappe.log_error(
			message=f"Payment API timed out for booking {booking_id}",
			title="BTC Report - Payment Timeout"
		)
		return "Error: Request timeout"
	except Exception as e:
		frappe.log_error(
			message=f"Payment API exception for booking {booking_id}: {str(e)}\n{frappe.get_traceback()}",
			title="BTC Report - Payment Exception"
		)
		return f"Error: {str(e)}"


def _generate_btc_csv_report(bookings):
	"""
	Generate CSV content from bill-to-company bookings.
	"""
	output = io.StringIO()

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
		"Payment Mode",
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
			"Payment Mode": booking.get("payment_mode") or "",
			"Tax": booking.get("tax") or "",
			"Total Amount": booking.get("total_amount") or "",
			"Currency": booking.get("currency") or "",
			"Booking Created On": str(booking.get("creation") or ""),
			"Payment URL": booking.get("payment_url") or ""
		})

	return output.getvalue()


def _save_csv_file(csv_content, filename):
	"""
	Save CSV content as a Frappe file and return the full URL.
	"""
	file_doc = frappe.get_doc({
		"doctype": "File",
		"file_name": filename,
		"content": csv_content,
		"is_private": 0,
		"folder": "Home"
	})
	file_doc.save(ignore_permissions=True)
	frappe.db.commit()

	site_url = frappe.utils.get_url()
	file_url = f"{site_url}{file_doc.file_url}"

	frappe.log_error(
		message=f"CSV file saved: {filename} -> {file_url}",
		title="BTC Report - File Saved"
	)

	return file_url


def _send_email(to_emails, subject, body, csv_file_url=None):
	"""
	Send email using the external email API.
	"""
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

	frappe.log_error(
		message=f"Email API request: URL={TASKS_EMAIL_API_URL}, To={to_emails}, Subject={subject}",
		title="BTC Report - Email API Request"
	)

	response = requests.post(
		TASKS_EMAIL_API_URL,
		headers=headers,
		data=json.dumps(payload),
		timeout=30
	)

	frappe.log_error(
		message=f"Email API response: status={response.status_code}, body={response.text[:500]}",
		title="BTC Report - Email API Response"
	)

	if response.status_code != 200:
		raise Exception(f"Email API returned status code {response.status_code}: {response.text}")

	return response.json()


def _generate_btc_email_body(company_name, bookings, csv_file_url=None):
	"""
	Generate HTML email body for the bill-to-company pending payment report.
	"""
	total_bookings = len(bookings)

	# Calculate totals
	total_revenue = 0
	total_tax = 0
	for booking in bookings:
		try:
			total_revenue += float(booking.get("total_amount") or 0)
			total_tax += float(booking.get("tax") or 0)
		except (ValueError, TypeError):
			pass

	grand_total = total_revenue + total_tax

	# Generate booking rows for the table
	booking_rows = ""
	for idx, booking in enumerate(bookings, 1):
		amount = float(booking.get("total_amount") or 0)
		tax = float(booking.get("tax") or 0)
		payment_url = booking.get("payment_url") or ""
		is_error = payment_url.startswith("Error") or payment_url == "No amount to pay"

		payment_link_html = (
			f'<span style="color: #dc3545; font-size: 12px;">{payment_url}</span>'
			if is_error
			else f'<a href="{payment_url}" style="display: inline-block; background-color: #7ecda5; color: #0e0f1d; text-decoration: none; padding: 6px 14px; border-radius: 4px; font-size: 12px; font-weight: 600;">Pay Now</a>'
		)

		bg_color = "#ffffff" if idx % 2 == 1 else "#f8f9fa"

		booking_rows += f"""
		<tr style="background-color: {bg_color};">
			<td style="padding: 10px 12px; border-bottom: 1px solid #e0e0e0; font-size: 13px; color: #333;">{idx}</td>
			<td style="padding: 10px 12px; border-bottom: 1px solid #e0e0e0; font-size: 13px; color: #333;">{booking.get("booking_id") or booking.get("name") or ""}</td>
			<td style="padding: 10px 12px; border-bottom: 1px solid #e0e0e0; font-size: 13px; color: #333;">{booking.get("employee_name") or ""}</td>
			<td style="padding: 10px 12px; border-bottom: 1px solid #e0e0e0; font-size: 13px; color: #333;">{booking.get("hotel_name") or ""}</td>
			<td style="padding: 10px 12px; border-bottom: 1px solid #e0e0e0; font-size: 13px; color: #333;">{booking.get("check_in") or ""}</td>
			<td style="padding: 10px 12px; border-bottom: 1px solid #e0e0e0; font-size: 13px; color: #333;">{booking.get("check_out") or ""}</td>
			<td style="padding: 10px 12px; border-bottom: 1px solid #e0e0e0; font-size: 13px; color: #333; text-align: right;">{amount:,.2f}</td>
			<td style="padding: 10px 12px; border-bottom: 1px solid #e0e0e0; font-size: 13px; color: #333; text-align: right;">{tax:,.2f}</td>
			<td style="padding: 10px 12px; border-bottom: 1px solid #e0e0e0; text-align: center;">{payment_link_html}</td>
		</tr>"""

	today = getdate(nowdate())
	current_year = datetime.now().year

	# Build download button HTML separately to avoid nested f-string issues
	download_button_html = ""
	if csv_file_url:
		download_button_html = (
			'<tr>'
			'<td style="padding: 0 40px 30px 40px; text-align: center;">'
			'<a href="' + csv_file_url + '" style="display: inline-block; background: linear-gradient(135deg, #0e0f1d 0%, #1a1d35 100%); color: #7ecda5; text-decoration: none; padding: 14px 28px; border-radius: 6px; font-size: 14px; font-weight: 600;">'
			'Download Full Report (CSV)'
			'</a>'
			'<p style="margin: 12px 0 0 0; color: #666; font-size: 12px;">Click the button above to download the detailed report with all booking information</p>'
			'</td>'
			'</tr>'
		)

	email_body = f"""
	<html>
	<body style="margin: 0; padding: 0; background-color: #f4f4f4; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
		<table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px 0;">
			<tr>
				<td align="center">
					<table width="900" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
						<!-- Header -->
						<tr>
							<td style="background: linear-gradient(135deg, #0e0f1d 0%, #1a1d35 100%); padding: 30px 40px; border-radius: 8px 8px 0 0;">
								<h1 style="color: #7ecda5; margin: 0; font-size: 24px; font-weight: 600;">Pending Payment Report</h1>
								<p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0; font-size: 14px;">Bill to Company - Destiin Travel Management</p>
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
										<td style="text-align: right;">
											<p style="margin: 0 0 8px 0; color: #6c757d; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">Report Date</p>
											<p style="margin: 0; color: #333; font-size: 16px;">{today}</p>
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
										<td width="30%" style="background-color: #fff3e0; border-radius: 6px; padding: 20px; text-align: center;">
											<p style="margin: 0; color: #e65100; font-size: 32px; font-weight: 700;">{total_bookings}</p>
											<p style="margin: 8px 0 0 0; color: #e65100; font-size: 13px;">Pending Bookings</p>
										</td>
										<td width="3%"></td>
										<td width="30%" style="background-color: #e3f2fd; border-radius: 6px; padding: 20px; text-align: center;">
											<p style="margin: 0; color: #1565c0; font-size: 32px; font-weight: 700;">{total_revenue:,.2f}</p>
											<p style="margin: 8px 0 0 0; color: #1565c0; font-size: 13px;">Total Amount</p>
										</td>
										<td width="3%"></td>
										<td width="34%" style="background-color: #fce4ec; border-radius: 6px; padding: 20px; text-align: center;">
											<p style="margin: 0; color: #c62828; font-size: 32px; font-weight: 700;">{grand_total:,.2f}</p>
											<p style="margin: 8px 0 0 0; color: #c62828; font-size: 13px;">Grand Total (incl. Tax)</p>
										</td>
									</tr>
								</table>
							</td>
						</tr>

						<!-- Booking Details Table -->
						<tr>
							<td style="padding: 0 40px 30px 40px;">
								<h3 style="color: #333; font-size: 16px; margin: 0 0 15px 0; font-weight: 600;">Booking Details</h3>
								<table width="100%" cellpadding="0" cellspacing="0" style="border: 1px solid #e0e0e0; border-radius: 6px; overflow: hidden;">
									<tr style="background-color: #0e0f1d;">
										<th style="padding: 12px; text-align: left; font-size: 12px; color: #7ecda5; font-weight: 600;">#</th>
										<th style="padding: 12px; text-align: left; font-size: 12px; color: #7ecda5; font-weight: 600;">Booking ID</th>
										<th style="padding: 12px; text-align: left; font-size: 12px; color: #7ecda5; font-weight: 600;">Employee</th>
										<th style="padding: 12px; text-align: left; font-size: 12px; color: #7ecda5; font-weight: 600;">Hotel</th>
										<th style="padding: 12px; text-align: left; font-size: 12px; color: #7ecda5; font-weight: 600;">Check-in</th>
										<th style="padding: 12px; text-align: left; font-size: 12px; color: #7ecda5; font-weight: 600;">Check-out</th>
										<th style="padding: 12px; text-align: right; font-size: 12px; color: #7ecda5; font-weight: 600;">Amount</th>
										<th style="padding: 12px; text-align: right; font-size: 12px; color: #7ecda5; font-weight: 600;">Tax</th>
										<th style="padding: 12px; text-align: center; font-size: 12px; color: #7ecda5; font-weight: 600;">Payment</th>
									</tr>
									{booking_rows}
									<!-- Total Row -->
									<tr style="background-color: #f0f0f0; font-weight: 700;">
										<td colspan="6" style="padding: 12px; border-top: 2px solid #333; font-size: 14px; color: #333; text-align: right;">TOTAL</td>
										<td style="padding: 12px; border-top: 2px solid #333; font-size: 14px; color: #333; text-align: right;">{total_revenue:,.2f}</td>
										<td style="padding: 12px; border-top: 2px solid #333; font-size: 14px; color: #333; text-align: right;">{total_tax:,.2f}</td>
										<td style="padding: 12px; border-top: 2px solid #333;"></td>
									</tr>
								</table>
							</td>
						</tr>

						<!-- Download Report Button -->
						{download_button_html}

						<!-- Note -->
						<tr>
							<td style="padding: 0 40px 30px 40px;">
								<table width="100%" cellpadding="0" cellspacing="0" style="background-color: #fff8e1; border-left: 4px solid #ff8f00; border-radius: 4px;">
									<tr>
										<td style="padding: 16px 20px;">
											<p style="margin: 0 0 4px 0; font-size: 13px; color: #e65100; font-weight: 600;">Action Required</p>
											<p style="margin: 0; font-size: 13px; color: #555; line-height: 1.6;">
												The above bookings have pending payments under the Bill-to-Company arrangement.
												Please click the respective "Pay Now" buttons to complete the payment for each booking,
												or download the CSV report for your records.
											</p>
										</td>
									</tr>
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
									&copy; {current_year} Destiin. All rights reserved.
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
