import frappe
import json
import requests
from frappe.utils import getdate


def get_next_agent_round_robin():
	"""
	Get the next agent using round-robin assignment.
	Fetches all active users with 'Agent' role and assigns based on least recent assignment.
	"""
	# Get all active users with Agent role
	agents = frappe.get_all(
		"Has Role",
		filters={"role": "Agent", "parenttype": "User"},
		fields=["parent"],
		pluck="parent"
	)

	if not agents:
		# Fallback: get all active users with System Manager role if no agents
		agents = frappe.get_all(
			"Has Role",
			filters={"role": "System Manager", "parenttype": "User"},
			fields=["parent"],
			pluck="parent"
		)

	if not agents:
		return None

	# Filter to only enabled users
	enabled_agents = frappe.get_all(
		"User",
		filters={"name": ["in", agents], "enabled": 1},
		fields=["name"],
		pluck="name"
	)

	if not enabled_agents:
		return None

	# Find the agent with the least recent assignment (round-robin)
	# Get the last assigned agent from Request Booking Details
	last_assignments = frappe.get_all(
		"Request Booking Details",
		filters={"agent": ["in", enabled_agents]},
		fields=["agent", "creation"],
		order_by="creation desc",
		limit=len(enabled_agents)
	)

	if not last_assignments:
		# No assignments yet, return first agent
		return enabled_agents[0]

	# Create a dict of agent -> last assignment time
	agent_last_assigned = {agent: None for agent in enabled_agents}
	for assignment in last_assignments:
		if agent_last_assigned[assignment.agent] is None:
			agent_last_assigned[assignment.agent] = assignment.creation

	# Find agents never assigned (highest priority)
	never_assigned = [agent for agent, time in agent_last_assigned.items() if time is None]
	if never_assigned:
		return never_assigned[0]

	# Return agent with oldest assignment (round-robin)
	sorted_agents = sorted(agent_last_assigned.items(), key=lambda x: x[1])
	return sorted_agents[0][0]


def get_ordinal_suffix(day):
	"""
	Get ordinal suffix for a day number (1st, 2nd, 3rd, 4th, etc.)
	"""
	if 11 <= day <= 13:
		return "th"
	suffix_map = {1: "st", 2: "nd", 3: "rd"}
	return suffix_map.get(day % 10, "th")


def format_date_with_ordinal(date_obj):
	"""
	Format date as '30th_Jan_2026'
	"""
	day = date_obj.day
	suffix = get_ordinal_suffix(day)
	month = date_obj.strftime("%b")
	year = date_obj.year
	return f"{day}{suffix}_{month}_{year}"


def generate_request_booking_id(employee_id, check_in, check_out):
	"""
	Generate unique request booking ID based on employee_id, check_in, and check_out.
	Format: {employee_id}_{check_in}-{check_out}
	Example: emp001_30th_Jan_2026-31st_Jan_2026
	"""
	check_in_date = getdate(check_in)
	check_out_date = getdate(check_out)
	check_in_str = format_date_with_ordinal(check_in_date)
	check_out_str = format_date_with_ordinal(check_out_date)
	return f"{employee_id}_{check_in_str}-{check_out_str}"


def get_default_company():
	"""
	Get the default company for new employees.
	Returns the first available company in the system.
	"""
	company = frappe.db.get_value(
		"Company",
		filters={"is_group": 0},
		fieldname="name",
		order_by="creation asc"
	)
	if not company:
		# Fallback: get any company
		company = frappe.db.get_value("Company", filters={}, fieldname="name")
	return company


def get_or_create_employee(employee_id, company=None):
	"""
	Get an existing employee or create a new one if not exists.

	Args:
		employee_id (str): Employee ID or identifier (could be name, email, or ID)
		company (str, optional): Company to assign if creating new employee

	Returns:
		tuple: (employee_name, company_name, is_new_employee)
	"""
	# Check if employee exists by name (primary key)
	if frappe.db.exists("Employee", employee_id):
		employee_doc = frappe.get_doc("Employee", employee_id)
		return employee_doc.name, employee_doc.company, False

	# Check if employee exists by employee_name field
	existing_by_name = frappe.db.get_value(
		"Employee",
		{"employee_name": employee_id},
		["name", "company"],
		as_dict=True
	)
	if existing_by_name:
		return existing_by_name.name, existing_by_name.company, False

	# Employee doesn't exist, create new one
	# Determine company to use
	if not company:
		company = get_default_company()

	if not company:
		frappe.throw("No company found in the system. Please create a company first.")

	# Create new employee
	new_employee = frappe.new_doc("Employee")
	new_employee.first_name = employee_id
	new_employee.employee_name = employee_id
	new_employee.company = company
	new_employee.date_of_joining = frappe.utils.today()
	new_employee.status = "Active"

	new_employee.insert(ignore_permissions=True)
	frappe.db.commit()

	return new_employee.name, new_employee.company, True


@frappe.whitelist(allow_guest=False)
def store_req_booking(
	employee,
	check_in,
	check_out,
	company=None,
	occupancy=None,
	adult_count=None,
	child_count=None,
	room_count=None,
	hotel_details=None
):
	"""
	API to store or update a request booking.

	If a booking with the same employee, check_in, and check_out exists, it updates the record.
	Otherwise, creates a new record with round-robin agent assignment.

	Args:
		employee (str): Employee ID (required)
		check_in (str): Check-in date (required)
		check_out (str): Check-out date (required)
		company (str, optional): Company ID
		occupancy (int, optional): Total occupancy
		adult_count (int, optional): Number of adults
		child_count (int, optional): Number of children
		room_count (int, optional): Number of rooms
		hotel_details (dict/str, optional): Hotel and room details
			{
				"hotel_id": "...",
				"hotel_name": "...",
				"supplier": "...",
				"cancellation_policy": "...",
				"meal_plan": "...",
				"rooms": [
					{
						"room_id": "...",
						"room_name": "...",
						"price": 0,
						"total_price": 0,
						"tax": 0,
						"currency": "INR"
					}
				]
			}

	Returns:
		dict: Response with success status and booking data
	"""
	try:
		# Parse hotel_details if it's a string
		if isinstance(hotel_details, str):
			import json
			hotel_details = json.loads(hotel_details) if hotel_details else None

		# Get or create employee if not exists
		employee_name, employee_company, is_new_employee = get_or_create_employee(employee, company)

		# Use the employee's company if no company was provided
		if not company:
			company = employee_company

		# Generate request booking ID using the actual employee name
		request_booking_id = generate_request_booking_id(employee_name, check_in, check_out)

		# Check if booking already exists
		existing_booking = frappe.db.exists(
			"Request Booking Details",
			{"request_booking_id": request_booking_id}
		)

		if existing_booking:
			# Update existing booking
			booking_doc = frappe.get_doc("Request Booking Details", existing_booking)
			is_new = False
		else:
			# Create new booking
			booking_doc = frappe.new_doc("Request Booking Details")
			booking_doc.request_booking_id = request_booking_id
			booking_doc.request_status = "req_pending"
			# Assign agent using round-robin
			booking_doc.agent = get_next_agent_round_robin()
			is_new = True

		# Update fields
		booking_doc.employee = employee_name
		booking_doc.company = company
		booking_doc.check_in = getdate(check_in)
		booking_doc.check_out = getdate(check_out)

		if occupancy is not None:
			booking_doc.occupancy = int(occupancy)
		if adult_count is not None:
			booking_doc.adult_count = int(adult_count)
		if child_count is not None:
			booking_doc.child_count = int(child_count)
		if room_count is not None:
			booking_doc.room_count = int(room_count)

		# Handle hotel and room details
		if hotel_details:
			cart_hotel_item = None

			if booking_doc.cart_hotel_item:
				# Update existing cart hotel item
				cart_hotel_item = frappe.get_doc("Cart Hotel Item", booking_doc.cart_hotel_item)
			else:
				# Create new cart hotel item
				cart_hotel_item = frappe.new_doc("Cart Hotel Item")

			# Update hotel details
			cart_hotel_item.hotel_id = hotel_details.get("hotel_id", "")
			cart_hotel_item.hotel_name = hotel_details.get("hotel_name", "")
			cart_hotel_item.supplier = hotel_details.get("supplier", "")
			cart_hotel_item.cancellation_policy = hotel_details.get("cancellation_policy", "")
			cart_hotel_item.meal_plan = hotel_details.get("meal_plan", "")

			# Clear existing rooms and add new ones
			cart_hotel_item.rooms = []
			rooms_data = hotel_details.get("rooms", [])

			for room in rooms_data:
				cart_hotel_item.append("rooms", {
					"room_id": room.get("room_id", ""),
					"room_name": room.get("room_name", ""),
					"price": room.get("price", 0),
					"total_price": room.get("total_price", 0),
					"tax": room.get("tax", 0),
					"currency": room.get("currency", "INR"),
					"status": "pending"
				})

			cart_hotel_item.room_count = len(rooms_data)
			cart_hotel_item.save(ignore_permissions=True)

			# Link cart hotel item to booking
			booking_doc.cart_hotel_item = cart_hotel_item.name

		# Save the booking
		booking_doc.save(ignore_permissions=True)
		frappe.db.commit()

		# Prepare response data
		response_data = {
			"request_booking_id": booking_doc.request_booking_id,
			"name": booking_doc.name,
			"employee": booking_doc.employee,
			"company": booking_doc.company,
			"check_in": str(booking_doc.check_in) if booking_doc.check_in else "",
			"check_out": str(booking_doc.check_out) if booking_doc.check_out else "",
			"request_status": booking_doc.request_status,
			"agent": booking_doc.agent,
			"occupancy": booking_doc.occupancy,
			"adult_count": booking_doc.adult_count,
			"child_count": booking_doc.child_count,
			"room_count": booking_doc.room_count,
			"cart_hotel_item": booking_doc.cart_hotel_item,
			"is_new": is_new,
			"is_new_employee": is_new_employee
		}

		# Build message
		message = "Request booking created successfully" if is_new else "Request booking updated successfully"
		if is_new_employee:
			message += " (new employee created)"

		return {
			"response": {
				"success": True,
				"message": message,
				"data": response_data
			}
		}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "store_req_booking API Error")
		return {
			"response": {
				"success": False,
				"error": str(e),
				"data": None
			}
		}


@frappe.whitelist()
def get_all_request_bookings(company=None, employee=None, status=None):
	"""
	API to get all request booking details with related hotel and room information

	Args:
		company (str, optional): Filter by company ID
		employee (str, optional): Filter by employee ID
		status (str, optional): Filter by request status
			Valid values: req_pending, req_send_for_approval, req_approved,
			req_payment_pending, req_payment_success, req_closed
	"""
	try:
		# Build filters based on query params
		filters = {}
		if company:
			filters["company"] = company
		if employee:
			filters["employee"] = employee
		if status:
			filters["request_status"] = status

		# Fetch all request booking details
		request_bookings = frappe.get_all(
			"Request Booking Details",
			filters=filters,
			fields=[
				"name",
				"request_booking_id",
				"company",
				"employee",
				"cart_hotel_item",
				"booking",
				"request_status",
				"check_in",
				"check_out",
				"occupancy",
				"adult_count",
				"child_count",
				"room_count"
			]
		)

		data = []
		for req in request_bookings:
			# Get employee details
			employee_name = ""
			if req.employee:
				employee_doc = frappe.get_value(
					"Employee",
					req.employee,
					["employee_name"],
					as_dict=True
				)
				if employee_doc:
					employee_name = employee_doc.get("employee_name", "")

			# Get company details
			company_name = ""
			if req.company:
				company_doc = frappe.get_value(
					"Company",
					req.company,
					["company_name"],
					as_dict=True
				)
				if company_doc:
					company_name = company_doc.get("company_name", "")

			# Get booking details for booking_id and destination
			booking_id = "NA"
			destination = ""
			if req.booking:
				booking_doc = frappe.get_value(
					"Hotel Bookings",
					req.booking,
					["booking_id", "destination"],
					as_dict=True
				)
				if booking_doc:
					booking_id = booking_doc.get("booking_id") or "NA"
					destination = booking_doc.get("destination") or ""

			# Get hotel items linked to this request booking
			hotels = []
			total_amount = 0.0

			if req.cart_hotel_item:
				cart_hotel = frappe.get_doc("Cart Hotel Item", req.cart_hotel_item)

				# Get rooms for this hotel
				rooms = []
				for room in cart_hotel.rooms:
					room_data = {
						"room_id": room.room_id or "",
						"room_type": room.room_name or "",
						"price": float(room.price or 0),
						"room_count": 1,
						"meal_plan": cart_hotel.meal_plan or "",
						"cancellation_policy": cart_hotel.cancellation_policy or "",
						"status": room.status or "pending",
						"approver_level": 0
					}
					rooms.append(room_data)
					total_amount += float(room.price or 0)

				hotel_data = {
					"hotel_id": cart_hotel.hotel_id or "",
					"hotel_name": cart_hotel.hotel_name or "",
					"supplier": cart_hotel.supplier or "",
					"status": "pending",
					"approver_level": 0,
					"rooms": rooms
				}
				hotels.append(hotel_data)

			# Map request_status to status and status_code
			status_mapping = {
				"req_pending": ("pending_in_cart", 0),
				"req_send_for_approval": ("sent_for_approval", 1),
				"req_approved": ("approved", 2),
				"req_payment_pending": ("payment_pending", 3),
				"req_payment_success": ("payment_success", 4),
				"req_closed": ("closed", 5)
			}
			status, status_code = status_mapping.get(
				req.request_status or "req_pending",
				("pending_in_cart", 0)
			)

			booking_data = {
				"request_booking_id": req.request_booking_id or "",
				"booking_id": booking_id,
				"user_name": employee_name,
				"hotels": hotels,
				"destination": destination,
				"check_in": str(req.check_in) if req.check_in else "",
				"check_out": str(req.check_out) if req.check_out else "",
				"amount": total_amount,
				"status": status,
				"status_code": status_code,
				"rooms_count": req.room_count or 0,
				"guests_count": req.adult_count or 0,
				"child_count": req.child_count or 0,
				"company": {
					"id": req.company or "",
					"name": company_name
				},
				"employee": {
					"id": req.employee or "",
					"name": employee_name
				}
			}
			data.append(booking_data)

		return {
			"response": {
				"success": True,
				"data": data
			}
		}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "get_all_request_bookings API Error")
		return {
			"response": {
				"success": False,
				"error": str(e),
				"data": []
			}
		}


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


def generate_approval_email_body(employee_name, check_in, check_out, hotels_data):
	"""
	Generate HTML email body for send_for_approval notification.
	"""
	# Build hotels and rooms HTML
	hotels_html = ""
	total_amount = 0.0

	for hotel in hotels_data:
		rooms_html = ""
		hotel_total = 0.0

		for room in hotel.get("rooms", []):
			room_price = float(room.get("price", 0))
			hotel_total += room_price
			rooms_html += f"""
				<tr>
					<td style="padding: 8px; border: 1px solid #ddd;">{room.get("room_name", "N/A")}</td>
					<td style="padding: 8px; border: 1px solid #ddd;">{room.get("room_id", "N/A")}</td>
					<td style="padding: 8px; border: 1px solid #ddd; text-align: right;">{room.get("currency", "INR")} {room_price:,.2f}</td>
				</tr>
			"""

		total_amount += hotel_total

		hotels_html += f"""
			<div style="margin-bottom: 20px; padding: 15px; border: 1px solid #e0e0e0; border-radius: 8px; background-color: #f9f9f9;">
				<h3 style="margin: 0 0 10px 0; color: #333;">{hotel.get("hotel_name", "N/A")}</h3>
				<p style="margin: 5px 0; color: #666;"><strong>Hotel ID:</strong> {hotel.get("hotel_id", "N/A")}</p>
				<p style="margin: 5px 0; color: #666;"><strong>Supplier:</strong> {hotel.get("supplier", "N/A")}</p>
				<p style="margin: 5px 0; color: #666;"><strong>Meal Plan:</strong> {hotel.get("meal_plan", "N/A")}</p>
				<p style="margin: 5px 0; color: #666;"><strong>Cancellation Policy:</strong> {hotel.get("cancellation_policy", "N/A")}</p>

				<table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
					<thead>
						<tr style="background-color: #4CAF50; color: white;">
							<th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Room Type</th>
							<th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Room ID</th>
							<th style="padding: 10px; border: 1px solid #ddd; text-align: right;">Price</th>
						</tr>
					</thead>
					<tbody>
						{rooms_html}
					</tbody>
				</table>
				<p style="margin-top: 10px; text-align: right; font-weight: bold;">Hotel Subtotal: INR {hotel_total:,.2f}</p>
			</div>
		"""

	html_body = f"""
	<html>
	<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px;">
		<div style="background-color: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0;">
			<h1 style="margin: 0;">Booking Approval Request</h1>
		</div>

		<div style="padding: 20px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 8px 8px;">
			<p>Dear Team,</p>
			<p>A booking request has been submitted for approval. Please review the details below:</p>

			<div style="background-color: #f0f0f0; padding: 15px; border-radius: 8px; margin: 20px 0;">
				<h3 style="margin: 0 0 10px 0; color: #4CAF50;">Booking Summary</h3>
				<p style="margin: 5px 0;"><strong>Employee:</strong> {employee_name}</p>
				<p style="margin: 5px 0;"><strong>Check-in:</strong> {check_in}</p>
				<p style="margin: 5px 0;"><strong>Check-out:</strong> {check_out}</p>
			</div>

			<h2 style="color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px;">Selected Hotels & Rooms</h2>
			{hotels_html}

			<div style="background-color: #4CAF50; color: white; padding: 15px; border-radius: 8px; margin-top: 20px; text-align: right;">
				<h3 style="margin: 0;">Total Amount: INR {total_amount:,.2f}</h3>
			</div>

			<p style="margin-top: 30px;">Please review and take appropriate action on this booking request.</p>

			<p style="margin-top: 20px;">
				Best regards,<br>
				<strong>Hotel Bookings System</strong>
			</p>
		</div>

		<div style="text-align: center; padding: 10px; color: #666; font-size: 12px;">
			<p>This is an automated email. Please do not reply directly to this message.</p>
		</div>
	</body>
	</html>
	"""

	return html_body


@frappe.whitelist(allow_guest=False)
def send_for_approval(request_booking_id, selected_items):
	"""
	API to send selected hotels and rooms for approval.

	Updates the status of selected hotels and rooms to 'sending_for_approval'
	and sends an email notification to the employee and agent.

	Args:
		request_booking_id (str): The request booking ID (required)
		selected_items (list/str): Array of selected hotels with rooms to send for approval
			[
				{
					"hotel_id": "...",
					"room_ids": ["room_id_1", "room_id_2"]
				}
			]

	Returns:
		dict: Response with success status and updated data
	"""
	try:
		# Parse selected_items if it's a string
		if isinstance(selected_items, str):
			selected_items = json.loads(selected_items) if selected_items else []

		if not request_booking_id:
			return {
				"response": {
					"success": False,
					"error": "request_booking_id is required",
					"data": None
				}
			}

		if not selected_items:
			return {
				"response": {
					"success": False,
					"error": "selected_items is required and cannot be empty",
					"data": None
				}
			}

		# Check if booking exists
		booking_doc = frappe.db.get_value(
			"Request Booking Details",
			{"request_booking_id": request_booking_id},
			["name", "employee", "agent", "check_in", "check_out", "cart_hotel_item"],
			as_dict=True
		)

		if not booking_doc:
			return {
				"response": {
					"success": False,
					"error": f"Request booking not found for ID: {request_booking_id}",
					"data": None
				}
			}

		# Get employee details
		employee_name = ""
		employee_email = ""
		if booking_doc.employee:
			employee_doc = frappe.get_value(
				"Employee",
				booking_doc.employee,
				["employee_name", "company_email", "personal_email"],
				as_dict=True
			)
			if employee_doc:
				employee_name = employee_doc.get("employee_name", "")
				employee_email = employee_doc.get("company_email") or employee_doc.get("personal_email") or ""

		# Get agent email
		agent_email = ""
		if booking_doc.agent:
			agent_doc = frappe.get_value(
				"User",
				booking_doc.agent,
				["email"],
				as_dict=True
			)
			if agent_doc:
				agent_email = agent_doc.get("email", "")

		# Build a mapping of selected hotel_ids to room_ids
		selected_hotel_map = {}
		for item in selected_items:
			hotel_id = item.get("hotel_id")
			room_ids = item.get("room_ids", [])
			if hotel_id:
				selected_hotel_map[hotel_id] = room_ids

		# Track updated hotels data for email
		updated_hotels_data = []
		updated_count = 0

		# Get the cart hotel item linked to this booking
		if booking_doc.cart_hotel_item:
			cart_hotel = frappe.get_doc("Cart Hotel Item", booking_doc.cart_hotel_item)

			# Check if this hotel is in selected items
			if cart_hotel.hotel_id in selected_hotel_map:
				selected_room_ids = selected_hotel_map[cart_hotel.hotel_id]

				hotel_data = {
					"hotel_id": cart_hotel.hotel_id,
					"hotel_name": cart_hotel.hotel_name,
					"supplier": cart_hotel.supplier,
					"meal_plan": cart_hotel.meal_plan,
					"cancellation_policy": cart_hotel.cancellation_policy,
					"rooms": []
				}

				# Update status for selected rooms
				for room in cart_hotel.rooms:
					if room.room_id in selected_room_ids:
						room.status = "sending_for_approval"
						updated_count += 1

						hotel_data["rooms"].append({
							"room_id": room.room_id,
							"room_name": room.room_name,
							"price": float(room.price or 0),
							"total_price": float(room.total_price or 0),
							"tax": float(room.tax or 0),
							"currency": room.currency or "INR"
						})

				# Save the cart hotel item
				cart_hotel.save(ignore_permissions=True)

				if hotel_data["rooms"]:
					updated_hotels_data.append(hotel_data)

		# Update the request booking status
		frappe.db.set_value(
			"Request Booking Details",
			booking_doc.name,
			"request_status",
			"req_send_for_approval"
		)

		frappe.db.commit()

		# Prepare email recipients
		to_emails = []
		if employee_email:
			to_emails.append(employee_email)
		if agent_email and agent_email != employee_email:
			to_emails.append(agent_email)

		# Send email notification
		email_sent = False
		if to_emails and updated_hotels_data:
			try:
				subject = f"Booking Approval Request - {employee_name} ({str(booking_doc.check_in)} to {str(booking_doc.check_out)})"
				body = generate_approval_email_body(
					employee_name=employee_name,
					check_in=str(booking_doc.check_in) if booking_doc.check_in else "",
					check_out=str(booking_doc.check_out) if booking_doc.check_out else "",
					hotels_data=updated_hotels_data
				)
				send_email_via_api(to_emails, subject, body)
				email_sent = True
			except Exception as email_error:
				frappe.log_error(
					f"Failed to send approval email: {str(email_error)}",
					"send_for_approval Email Error"
				)

		return {
			"response": {
				"success": True,
				"message": f"Successfully sent {updated_count} room(s) for approval",
				"data": {
					"request_booking_id": request_booking_id,
					"updated_count": updated_count,
					"email_sent": email_sent,
					"email_recipients": to_emails,
					"updated_hotels": updated_hotels_data
				}
			}
		}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "send_for_approval API Error")
		return {
			"response": {
				"success": False,
				"error": str(e),
				"data": None
			}
		}


@frappe.whitelist(allow_guest=False)
def approve_booking(request_booking_id, employee, selected_items):
	"""
	API to approve selected hotels and rooms.

	Updates the status of selected hotels and rooms to 'approved'
	and updates the request booking status to 'req_approved'.

	Args:
		request_booking_id (str): The request booking ID (required)
		employee (str): The employee ID (required)
		selected_items (list/str): Array of selected hotels with rooms to approve
			[
				{
					"hotel_id": "...",
					"room_ids": ["room_id_1", "room_id_2"]
				}
			]

	Returns:
		dict: Response with success status and updated data
	"""
	try:
		# Parse selected_items if it's a string
		if isinstance(selected_items, str):
			selected_items = json.loads(selected_items) if selected_items else []

		if not request_booking_id:
			return {
				"response": {
					"success": False,
					"error": "request_booking_id is required",
					"data": None
				}
			}

		if not employee:
			return {
				"response": {
					"success": False,
					"error": "employee is required",
					"data": None
				}
			}

		if not selected_items:
			return {
				"response": {
					"success": False,
					"error": "selected_items is required and cannot be empty",
					"data": None
				}
			}

		# Check if booking exists and belongs to the employee
		booking_doc = frappe.db.get_value(
			"Request Booking Details",
			{"request_booking_id": request_booking_id, "employee": employee},
			["name", "employee", "agent", "check_in", "check_out", "cart_hotel_item", "request_status"],
			as_dict=True
		)

		if not booking_doc:
			return {
				"response": {
					"success": False,
					"error": f"Request booking not found for ID: {request_booking_id} and employee: {employee}",
					"data": None
				}
			}

		# Build a mapping of selected hotel_ids to room_ids
		selected_hotel_map = {}
		for item in selected_items:
			hotel_id = item.get("hotel_id")
			room_ids = item.get("room_ids", [])
			if hotel_id:
				selected_hotel_map[hotel_id] = room_ids

		# Track updated hotels data
		updated_hotels_data = []
		declined_hotels_data = []
		updated_count = 0
		declined_count = 0

		# Get the cart hotel item linked to this booking
		if booking_doc.cart_hotel_item:
			cart_hotel = frappe.get_doc("Cart Hotel Item", booking_doc.cart_hotel_item)

			# Check if this hotel is in selected items
			if cart_hotel.hotel_id in selected_hotel_map:
				selected_room_ids = selected_hotel_map[cart_hotel.hotel_id]

				hotel_data = {
					"hotel_id": cart_hotel.hotel_id,
					"hotel_name": cart_hotel.hotel_name,
					"supplier": cart_hotel.supplier,
					"rooms": []
				}

				declined_hotel_data = {
					"hotel_id": cart_hotel.hotel_id,
					"hotel_name": cart_hotel.hotel_name,
					"supplier": cart_hotel.supplier,
					"rooms": []
				}

				# Update status for selected rooms to approved, decline all others
				for room in cart_hotel.rooms:
					if room.room_id in selected_room_ids:
						room.status = "approved"
						updated_count += 1

						hotel_data["rooms"].append({
							"room_id": room.room_id,
							"room_name": room.room_name,
							"price": float(room.price or 0),
							"status": "approved"
						})
					else:
						# Automatically decline non-selected rooms
						room.status = "declined"
						declined_count += 1

						declined_hotel_data["rooms"].append({
							"room_id": room.room_id,
							"room_name": room.room_name,
							"price": float(room.price or 0),
							"status": "declined"
						})

				# Save the cart hotel item
				cart_hotel.save(ignore_permissions=True)

				if hotel_data["rooms"]:
					updated_hotels_data.append(hotel_data)
				if declined_hotel_data["rooms"]:
					declined_hotels_data.append(declined_hotel_data)

		# Update the request booking status to approved
		frappe.db.set_value(
			"Request Booking Details",
			booking_doc.name,
			"request_status",
			"req_approved"
		)

		frappe.db.commit()

		return {
			"response": {
				"success": True,
				"message": f"Successfully approved {updated_count} room(s) and declined {declined_count} room(s)",
				"data": {
					"request_booking_id": request_booking_id,
					"employee": employee,
					"approved_count": updated_count,
					"declined_count": declined_count,
					"request_status": "req_approved",
					"approved_hotels": updated_hotels_data,
					"declined_hotels": declined_hotels_data
				}
			}
		}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "approve_booking API Error")
		return {
			"response": {
				"success": False,
				"error": str(e),
				"data": None
			}
		}

@frappe.whitelist(allow_guest=False)
def decline_booking(request_booking_id, employee, selected_items):
	"""
	API to decline selected hotels and rooms.

	Updates the status of selected hotels and rooms to 'declined'
	and updates the request booking status to 'req_declined'.

	Args:
		request_booking_id (str): The request booking ID (required)
		employee (str): The employee ID (required)
		selected_items (list/str): Array of selected hotels with rooms to decline
			[
				{
					"hotel_id": "...",
					"room_ids": ["room_id_1", "room_id_2"]
				}
			]

	Returns:
		dict: Response with success status and updated data
	"""
	try:
		# Parse selected_items if it's a string
		if isinstance(selected_items, str):
			selected_items = json.loads(selected_items) if selected_items else []

		if not request_booking_id:
			return {
				"response": {
					"success": False,
					"error": "request_booking_id is required",
					"data": None
				}
			}

		if not employee:
			return {
				"response": {
					"success": False,
					"error": "employee is required",
					"data": None
				}
			}

		if not selected_items:
			return {
				"response": {
					"success": False,
					"error": "selected_items is required and cannot be empty",
					"data": None
				}
			}

		# Check if booking exists and belongs to the employee
		booking_doc = frappe.db.get_value(
			"Request Booking Details",
			{"request_booking_id": request_booking_id, "employee": employee},
			["name", "employee", "agent", "check_in", "check_out", "cart_hotel_item", "request_status"],
			as_dict=True
		)

		if not booking_doc:
			return {
				"response": {
					"success": False,
					"error": f"Request booking not found for ID: {request_booking_id} and employee: {employee}",
					"data": None
				}
			}

		# Build a mapping of selected hotel_ids to room_ids
		selected_hotel_map = {}
		for item in selected_items:
			hotel_id = item.get("hotel_id")
			room_ids = item.get("room_ids", [])
			if hotel_id:
				selected_hotel_map[hotel_id] = room_ids

		# Track declined hotels data
		declined_hotels_data = []
		declined_count = 0

		# Get the cart hotel item linked to this booking
		if booking_doc.cart_hotel_item:
			cart_hotel = frappe.get_doc("Cart Hotel Item", booking_doc.cart_hotel_item)

			# Check if this hotel is in selected items
			if cart_hotel.hotel_id in selected_hotel_map:
				selected_room_ids = selected_hotel_map[cart_hotel.hotel_id]

				hotel_data = {
					"hotel_id": cart_hotel.hotel_id,
					"hotel_name": cart_hotel.hotel_name,
					"supplier": cart_hotel.supplier,
					"rooms": []
				}

				# Update status for selected rooms to declined
				for room in cart_hotel.rooms:
					if room.room_id in selected_room_ids:
						room.status = "declined"
						declined_count += 1

						hotel_data["rooms"].append({
							"room_id": room.room_id,
							"room_name": room.room_name,
							"price": float(room.price or 0),
							"status": "declined"
						})

				# Save the cart hotel item
				cart_hotel.save(ignore_permissions=True)

				if hotel_data["rooms"]:
					declined_hotels_data.append(hotel_data)

		# Update the request booking status to declined
		frappe.db.set_value(
			"Request Booking Details",
			booking_doc.name,
			"request_status",
			"req_declined"
		)

		frappe.db.commit()

		return {
			"response": {
				"success": True,
				"message": f"Successfully declined {declined_count} room(s)",
				"data": {
					"request_booking_id": request_booking_id,
					"employee": employee,
					"declined_count": declined_count,
					"request_status": "req_declined",
					"declined_hotels": declined_hotels_data
				}
			}
		}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "decline_booking API Error")
		return {
			"response": {
				"success": False,
				"error": str(e),
				"data": None
			}
		}
