import frappe
import json
import requests
from frappe.utils import getdate

from threading import Thread
from urllib.parse import quote_plus
from destiin.destiin.constants import EMAIL_AUTH_TOKEN_URL, TASKS_EMAIL_API_URL, POLICY_DIEM_ACCOMMODATION_URL, CURRENCY_CONVERT_URL

TRIPADVISOR_URL_API = "http://18.60.41.154/ops/v1/tripAdvisorUrl"

EMAIL_AUTHENTICATION_API_URL = EMAIL_AUTH_TOKEN_URL


def get_hotel_reviews_url(hotel_reviews, hotel_name, destination):
	"""Return hotel_reviews if it has a value, otherwise construct a Google search URL."""
	if hotel_reviews:
		return hotel_reviews
	search_query = f"tripadvisor+{quote_plus(hotel_name or '')}+{quote_plus(destination or '')}"
	return f"https://www.google.com/search?q={search_query}"

# Mapping from Cart Details status to Request Booking status
CART_TO_REQUEST_STATUS_MAP = {
    "pending": "req_pending",
    "sent_for_approval": "req_sent_for_approval",
    "waiting_for_approval": "req_sent_for_approval",
    "approved": "req_approved",
    "declined": "req_cancelled",
    "booking_success": "req_closed",
    "booking_failure": "req_cancelled",
    "booking_unavailable": "req_cancelled",
    "payment_pending": "req_payment_pending",
    "payment_success": "req_payment_success",
    "payment_failure": "req_payment_pending",
    "payment_cancel": "req_cancelled"
}


def get_request_status_from_cart_status(cart_status):
    """
    Get the corresponding request booking status for a given cart/room status.

    Args:
        cart_status (str): The cart details status

    Returns:
        str: The corresponding request booking status
    """
    return CART_TO_REQUEST_STATUS_MAP.get(cart_status, "req_pending")


def update_request_status_from_rooms(request_booking_name, cart_hotel_item_name=None):
    """
    Update the request booking status based on the current room statuses across all linked hotels.

    The logic determines the request status based on the most significant room status:
    - If any room has payment_success → req_payment_success
    - If any room has payment_pending → req_payment_pending
    - If any room has approved → req_approved
    - If any room has sent_for_approval/waiting_for_approval → req_sent_for_approval
    - If all rooms are declined → req_cancelled
    - Otherwise → req_pending

    Args:
        request_booking_name (str): The Request Booking Details document name
        cart_hotel_item_name (str, optional): Deprecated - kept for backward compatibility

    Returns:
        str: The new request status that was set
    """
    if not request_booking_name:
        return None

    # Get all cart hotel items linked to this request booking
    cart_hotel_items = frappe.get_all(
        "Cart Hotel Item",
        filters={"request_booking": request_booking_name},
        pluck="name"
    )

    if not cart_hotel_items:
        return None

    # Collect all room statuses from all hotels
    room_statuses = []
    for cart_hotel_item in cart_hotel_items:
        cart_hotel = frappe.get_doc("Cart Hotel Item", cart_hotel_item)
        room_statuses.extend([room.status for room in cart_hotel.rooms if room.status])

    if not room_statuses:
        return None

    # Determine the request status based on room statuses (priority order)
    new_request_status = "req_pending"

    # Priority: payment_success > payment_pending > booking_success > approved > sent_for_approval > declined > pending
    status_priority = [
        ("payment_success", "req_payment_success"),
        ("payment_pending", "req_payment_pending"),
        ("booking_success", "req_closed"),
        ("approved", "req_approved"),
        ("sent_for_approval", "req_sent_for_approval"),
        ("waiting_for_approval", "req_sent_for_approval"),
    ]

    for cart_status, req_status in status_priority:
        if cart_status in room_statuses:
            new_request_status = req_status
            break
    else:
        # Check if all rooms are declined
        if all(status == "declined" for status in room_statuses):
            new_request_status = "req_cancelled"
        elif all(status == "booking_failure" for status in room_statuses):
            new_request_status = "req_cancelled"
        elif all(status == "booking_unavailable" for status in room_statuses):
            new_request_status = "req_cancelled"

    # Update the request booking status
    frappe.db.set_value(
        "Request Booking Details",
        request_booking_name,
        "request_status",
        new_request_status
    )

    return new_request_status


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


def generate_request_booking_id(custom_employee_id, check_in, check_out):
	"""
	Generate unique request booking ID based on custom_employee_id, check_in, and check_out.
	Format: {custom_employee_id}_{check_in}-{check_out}
	Example: emp001_30th_Jan_2026-31st_Jan_2026
	"""
	check_in_date = getdate(check_in)
	check_out_date = getdate(check_out)
	check_in_str = format_date_with_ordinal(check_in_date)
	check_out_str = format_date_with_ordinal(check_out_date)
	frappe.log_error(f"Request Booking Date Format: {check_in_str}-{check_out_str}")
	return f"{custom_employee_id}_{check_in_str}-{check_out_str}"


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


def get_or_create_employee(employee_id, company=None, employee_name=None, employee_email=None):
	"""
	Get an existing employee or create a new one if not exists.

	Args:
		employee_id (str): Employee ID or identifier (could be name, email, or ID)
		company (str, optional): Company to assign if creating new employee
		employee_name (str, optional): Employee name for new employee creation
		employee_email (str, optional): Employee email for lookup and new employee creation

	Returns:
		tuple: (employee_name, company_name, is_new_employee, custom_employee_id)
	"""
	# Check if employee exists by record ID (primary key)
	if frappe.db.exists("Employee", employee_id):
		employee_doc = frappe.get_doc("Employee", employee_id)
		custom_emp_id = employee_doc.custom_employee_id or employee_doc.name
		return employee_doc.name, employee_doc.company, False, custom_emp_id

	# Check if employee exists by email (if email provided)
	if employee_email:
		existing_by_email = frappe.db.get_value(
			"Employee",
			{"company_email": employee_email},
			["name", "company", "custom_employee_id"],
			as_dict=True
		)
		if not existing_by_email:
			# Also check personal_email field
			existing_by_email = frappe.db.get_value(
				"Employee",
				{"personal_email": employee_email},
				["name", "company", "custom_employee_id"],
				as_dict=True
			)
		if existing_by_email:
			custom_emp_id = existing_by_email.custom_employee_id or existing_by_email.name
			return existing_by_email.name, existing_by_email.company, False, custom_emp_id

	# Employee doesn't exist, create new one
	# Determine company to use
	if not company:
		company = get_default_company()

	if not company:
		frappe.throw("No company found in the system. Please create a company first.")

	# Create new employee
	new_employee = frappe.new_doc("Employee")

	# Use provided employee_name or fallback to employee_id
	name_to_use = employee_name if employee_name else employee_id
	new_employee.first_name = name_to_use
	new_employee.employee_name = name_to_use

	# Set email if provided
	if employee_email:
		new_employee.company_email = employee_email

	new_employee.company = company
	new_employee.date_of_joining = frappe.utils.today()
	new_employee.status = "Active"
	new_employee.gender = "Prefer not to say"
	new_employee.date_of_birth = frappe.utils.add_years(frappe.utils.today(), -18)

	# Store original employee_id in custom_employee_id field for new employees
	if employee_id:
		new_employee.custom_employee_id = employee_id

	new_employee.insert(ignore_permissions=True)
	frappe.db.commit()

	return new_employee.name, new_employee.company, True, employee_id


def _fire_tripadvisor_url_api(request_booking_id, hotels_data, destination, destination_country):
	"""
	Fire-and-forget POST to TripAdvisor URL API for newly added hotels.
	Runs in a background thread so the main request is not blocked.
	"""
	def _call():
		try:
			# Extract city from destination (e.g., "Sydney, Australia" -> "Sydney")
			city = ""
			if destination:
				city = destination.split(",")[0].strip() if "," in destination else destination

			country = destination_country or ""

			hotels_payload = []
			for h in hotels_data:
				hotels_payload.append({
					"hotel_id": h.get("hotel_id", ""),
					"hotel_name": h.get("hotel_name", ""),
					"city": city,
					"country": country
				})

			payload = {
				"request_booking_id": request_booking_id,
				"hotels": hotels_payload
			}

			frappe.log_error(
				message=f"URL: {TRIPADVISOR_URL_API}\nPayload: {json.dumps(payload, indent=2)}",
				title="[TripAdvisor URL API] REQUEST"
			)
			resp = requests.post(
				TRIPADVISOR_URL_API,
				headers={"Content-Type": "application/json"},
				data=json.dumps(payload),
				timeout=30
			)
			frappe.log_error(
				message=f"Status: {resp.status_code}\nBody: {resp.text}",
				title="[TripAdvisor URL API] RESPONSE"
			)
		except Exception as e:
			frappe.log_error(
				f"Failed to call TripAdvisor URL API: {str(e)}",
				"TripAdvisor URL API Error"
			)

	thread = Thread(target=_call)
	thread.daemon = True
	thread.start()


@frappe.whitelist(allow_guest=False)
def store_req_booking(
	employee,
	check_in,
	check_out,
	company=None,
	occupancy=None,
	adult_count=None,
	child_count=None,
	child_ages=None,
	room_count=None,
	destination=None,
	destination_code=None,
	hotel_details=None,
	employee_name=None,
	employee_email=None,
	employee_level=None,
	budget_options=None,
	employee_country=None,
	destination_country=None,
	currency=None,
	work_address=None,
	budget_amount=None
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
		child_ages (list, optional): List of child ages
		room_count (int, optional): Number of rooms
		destination (str, optional): Destination name
		destination_code (str, optional): Destination code
		hotel_details (list/dict/str, optional): Hotel and room details. Can be a single hotel dict or array of hotels.
		employee_name (str, optional): Employee name for new employee creation
		employee_email (str, optional): Employee email for lookup (if employee ID not found) and new employee creation
			Single hotel:
			{
				"hotel_id": "...",
				"hotel_name": "...",
				"supplier": "...",
				"cancellation_policy": "...",
				"meal_plan": "...",
				"rooms": [...]
			}
			Multiple hotels:
			[
				{
					"hotel_id": "...",
					"hotel_name": "...",
					"supplier": "...",
					"cancellation_policy": "...",
					"meal_plan": "...",
					"rooms": [
						{
							"room_id": "...",
							"room_rate_id": "...",
							"room_name": "...",
							"price": 0,
							"total_price": 0,
							"tax": 0,
							"currency": "USD"
						}
					]
				},
				...
			]

	Returns:
		dict: Response with success status and booking data
	"""
	try:
		# Parse hotel_details if it's a string
		if isinstance(hotel_details, str):
			hotel_details = json.loads(hotel_details) if hotel_details else None

		# Normalize hotel_details to always be a list
		hotels_list = []
		if hotel_details:
			if isinstance(hotel_details, dict):
				# Single hotel passed as dict - convert to list
				hotels_list = [hotel_details]
			elif isinstance(hotel_details, list):
				hotels_list = hotel_details

		# Get or create employee if not exists
		employee_name_result, employee_company, is_new_employee, custom_employee_id = get_or_create_employee(
			employee, company, employee_name, employee_email
		)

		# If employee_level provided, store it; otherwise fetch from existing employee
		if employee_level and employee_name_result:
			frappe.db.set_value("Employee", employee_name_result, "custom_employee_level", employee_level)
		elif not employee_level and employee_name_result and not is_new_employee:
			employee_level = frappe.db.get_value("Employee", employee_name_result, "custom_employee_level") or ""

		# Use the employee's company if no company was provided
		if not company:
			company = employee_company

		# Generate request booking ID using custom_employee_id
		request_booking_id = generate_request_booking_id(custom_employee_id, check_in, check_out)
		frappe.log_error(f"Request Booking ID: {request_booking_id}")

		# Check if booking already exists
		existing_booking = frappe.db.exists(
			"Request Booking Details",
			{"request_booking_id": request_booking_id}
		)
		if existing_booking:
			# Update existing booking
			booking_doc = frappe.get_doc("Request Booking Details", existing_booking)
			is_new = False

			return {
					"success": False,
					"message": "Request already exists for this employee with same checkin checkout",
			}

		# Create new booking
		booking_doc = frappe.new_doc("Request Booking Details")
		booking_doc.request_booking_id = request_booking_id
		booking_doc.request_status = "req_pending"
		# Assign agent using round-robin
		booking_doc.agent = get_next_agent_round_robin()
		is_new = True
		booking_doc.employee = employee_name_result
		booking_doc.company = company
		if employee_email:
			booking_doc.employee_email = employee_email
		booking_doc.check_in = getdate(check_in)
		booking_doc.check_out = getdate(check_out)

		if occupancy is not None:
			booking_doc.occupancy = int(occupancy)
		if adult_count is not None:
			booking_doc.adult_count = int(adult_count)
		if child_count is not None:
			booking_doc.child_count = int(child_count)
		if child_ages:
			# Parse child_ages if it's a string and store as JSON
			if isinstance(child_ages, str):
				child_ages = json.loads(child_ages) if child_ages else []
			booking_doc.child_ages = json.dumps(child_ages) if isinstance(child_ages, list) else child_ages
		if room_count is not None:
			booking_doc.room_count = int(room_count)
		if destination:
			booking_doc.destination = destination
		if destination_code:
			booking_doc.destination_code = destination_code
		if budget_options:
			booking_doc.budget_options = budget_options

		# Store country and currency details
		emp_country = employee_country if employee_country else "India"
		dest_country = destination_country if destination_country else ""
		budget_currency = currency if currency else "USD"
		booking_doc.employee_country = emp_country
		booking_doc.destination_country = dest_country
		booking_doc.currency = budget_currency
		if work_address:
			booking_doc.work_address = work_address
		if budget_amount:
			booking_doc.budget_amount = budget_amount

		# Call currency conversion API to get employee budget in USD
		employee_budget = 0

		if budget_amount and budget_currency:
			# Calculate number of nights
			check_in_date = getdate(check_in)
			check_out_date = getdate(check_out)
			num_nights = (check_out_date - check_in_date).days
			if num_nights < 1:
				num_nights = 1

			if budget_currency == "USD":
				employee_budget = float(budget_amount) * num_nights
			else:
				try:
					currency_convert_url = f"{CURRENCY_CONVERT_URL}?amount={budget_amount}&from={budget_currency}&to=USD"
					frappe.log_error(
						message=f"URL: {currency_convert_url}",
						title="[Currency Convert API] REQUEST"
					)
					currency_response = requests.get(
						currency_convert_url,
						timeout=30
					)
					frappe.log_error(
						message=f"Status: {currency_response.status_code}\nBody: {currency_response.text}",
						title="[Currency Convert API] RESPONSE"
					)
					if currency_response.status_code == 200:
						currency_data = currency_response.json()
						if currency_data.get("status"):
							converted_value = float(currency_data.get("data", {}).get("converted", 0))
							employee_budget = converted_value * num_nights
					else:
						frappe.log_error(
							f"Currency Convert API returned status {currency_response.status_code}: {currency_response.text}",
							"Currency Convert API Error"
						)
				except Exception as convert_error:
					frappe.log_error(
						f"Failed to call currency convert API: {str(convert_error)}",
						"Currency Convert API Error"
					)

		booking_doc.employee_budget = employee_budget

		# Save the booking first to get the name for linking hotels
		booking_doc.save(ignore_permissions=True)

		# Handle hotel and room details - create multiple Cart Hotel Items
		created_hotel_items = []
		if hotels_list:
			for hotel_data in hotels_list:
				# Create new cart hotel item for each hotel
				cart_hotel_item = frappe.new_doc("Cart Hotel Item")

				# Link to the request booking
				cart_hotel_item.request_booking = booking_doc.name

				# Update hotel details
				cart_hotel_item.hotel_id = hotel_data.get("hotel_id", "")
				cart_hotel_item.hotel_name = hotel_data.get("hotel_name", "")
				cart_hotel_item.supplier = hotel_data.get("supplier", "")
				cart_hotel_item.cancellation_policy = hotel_data.get("cancellation_policy", "")
				cart_hotel_item.meal_plan = hotel_data.get("meal_plan", "")
				cart_hotel_item.latitude = hotel_data.get("latitude", "")
				cart_hotel_item.longitude = hotel_data.get("longitude", "")
				cart_hotel_item.hotel_reviews = hotel_data.get("hotel_reviews", "")
				cart_hotel_item.images = json.dumps(hotel_data.get("images", []))

				# Add rooms
				cart_hotel_item.rooms = []
				rooms_data = hotel_data.get("rooms", [])

				for room in rooms_data:
					cart_hotel_item.append("rooms", {
						"room_id": room.get("room_id", ""),
						"room_rate_id": room.get("room_rate_id", ""),
						"room_name": room.get("room_name", ""),
						"price": room.get("price", 0),
						"total_price": room.get("total_price", 0),
						"tax": room.get("tax", 0),
						"currency": room.get("currency", "USD"),
						"status": "pending",
						"images": json.dumps(room.get("images", []))
					})

				cart_hotel_item.room_count = len(rooms_data)
				cart_hotel_item.save(ignore_permissions=True)
				created_hotel_items.append(cart_hotel_item.name)

			# Link all cart hotel items to the Table MultiSelect field
			if created_hotel_items:
				booking_doc.cart_hotel_item = []  # Clear existing entries
				for item_name in created_hotel_items:
					booking_doc.append("cart_hotel_item", {
						"cart_hotel_item": item_name
					})
				booking_doc.save(ignore_permissions=True)

		frappe.db.commit()

		# Fire-and-forget TripAdvisor URL API call for new hotels
		if hotels_list:
			_fire_tripadvisor_url_api(
				request_booking_id=booking_doc.request_booking_id,
				hotels_data=hotels_list,
				destination=destination or "",
				destination_country=dest_country
			)

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
			"child_ages": json.loads(booking_doc.child_ages) if isinstance(booking_doc.child_ages, str) else (booking_doc.child_ages or []),
			"room_count": booking_doc.room_count,
			"destination": booking_doc.destination or "",
			"destination_code": booking_doc.destination_code or "",
			"budget_options": booking_doc.budget_options or "",
			"employee_budget": booking_doc.employee_budget or 0,
			"work_address": booking_doc.work_address or "",
			"budget_amount": booking_doc.budget_amount or "",
			"cart_hotel_item": booking_doc.cart_hotel_item,
			"cart_hotel_items": created_hotel_items,
			"hotel_count": len(created_hotel_items),
			"is_new": is_new,
			"is_new_employee": is_new_employee
		}

		# Build message
		message = "Request booking created successfully" if is_new else "Request booking updated successfully"
		if is_new_employee:
			message += " (new employee created)"

		return {		
				"success": True,
				"message": message,
				"data": response_data	
		}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "store_req_booking API Error")
		return {		
				"success": False,
				"error": str(e),
				"data": None	
		}


@frappe.whitelist()
def get_all_request_bookings(company=None, employee=None, status=None, page=None, page_size=None):
	"""
	API to get all request booking details with related hotel and room information

	Args:
		company (str, optional): Filter by company ID
		employee (str, optional): Filter by employee ID
		status (str, optional): Filter by request status. Supports multiple comma-separated values.
			Valid values: req_pending, req_sent_for_approval, req_approved,
			req_payment_pending, req_payment_success, req_closed
			Example: status=req_pending,req_sent_for_approval
		page (int, optional): Page number (1-indexed). Defaults to 1.
		page_size (int, optional): Number of records per page. Defaults to 20. Max 100.
	"""
	try:
		# Build filters based on query params
		filters = {}
		if company:
			filters["company"] = company
		if employee:
			filters["employee"] = employee
		if status:
			# Support multiple comma-separated status values
			if "," in status:
				status_list = [s.strip() for s in status.split(",")]
				filters["request_status"] = ["in", status_list]
			else:
				filters["request_status"] = status

		# Pagination defaults
		page = int(page) if page else 1
		page_size = int(page_size) if page_size else 20
		# Ensure valid values
		if page < 1:
			page = 1
		if page_size < 1:
			page_size = 20
		if page_size > 100:
			page_size = 100

		# Calculate offset
		offset = (page - 1) * page_size

		# Get total count for pagination metadata
		total_count = frappe.db.count("Request Booking Details", filters=filters)

		# Fetch request booking details with pagination
		request_bookings = frappe.get_all(
			"Request Booking Details",
			filters=filters,
			fields=[
				"name",
				"request_booking_id",
				"company",
				"employee",
				"employee_email",
				"booking",
				"request_status",
				"check_in",
				"check_out",
				"occupancy",
				"adult_count",
				"child_count",
				"child_ages",
				"room_count",
				"destination",
				"destination_code",
				"budget_options",
				"employee_budget",
				"work_address"
			],
			order_by="creation desc",
			start=offset,
			page_length=page_size
		)

		data = []
		for req in request_bookings:
			# Get employee details
			employee_name = ""
			employee_phone_number = ""
			employee_level = ""
			if req.employee:
				employee_doc = frappe.get_value(
					"Employee",
					req.employee,
					["employee_name", "cell_number", "custom_employee_level"],
					as_dict=True
				)
				if employee_doc:
					employee_name = employee_doc.get("employee_name", "")
					employee_phone_number = employee_doc.get("cell_number", "") or ""
					employee_level = employee_doc.get("custom_employee_level", "") or ""

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

			# Get booking details for booking_id
			booking_id = "NA"
			if req.booking:
				booking_doc = frappe.get_value(
					"Hotel Bookings",
					req.booking,
					["booking_id"],
					as_dict=True
				)
				if booking_doc:
					booking_id = booking_doc.get("booking_id") or "NA"

			# Get all hotel items linked to this request booking
			hotels = []
			total_amount = 0.0
			# Get destination from Request Booking Details
			destination = req.destination or ""
			destination_code = req.destination_code or ""

			# Get hotels via the request_booking link
			cart_hotel_items = frappe.get_all(
				"Cart Hotel Item",
				filters={"request_booking": req.name},
				pluck="name"
			)

			# Map request status to the expected room status for filtering
			expected_room_status = {
				"req_approved": "approved",
				"req_payment_pending": "payment_pending",
				"req_payment_success": "payment_success",
			}.get(req.request_status)

			for cart_hotel_name in cart_hotel_items:
				cart_hotel = frappe.get_doc("Cart Hotel Item", cart_hotel_name)

				# Get rooms for this hotel
				rooms = []
				for room in cart_hotel.rooms:
					if expected_room_status and (room.status or "pending") != expected_room_status:
						continue

					room_data = {
						"room_id": room.room_id or "",
						"room_rate_id": room.room_rate_id or "",
						"room_type": room.room_name or "",
						"price": float(room.price or 0),
						"room_count": 1,
						"meal_plan": cart_hotel.meal_plan or "",
						"cancellation_policy": cart_hotel.cancellation_policy or "",
						"status": room.status or "pending",
						"approver_level": 0,
						"images": json.loads(room.images) if isinstance(room.images, str) else (room.images or [])
					}
					rooms.append(room_data)
					total_amount += float(room.price or 0)

				# Skip hotel entirely if no rooms passed the filter
				if not rooms:
					continue

				hotel_data = {
					"hotel_id": cart_hotel.hotel_id or "",
					"hotel_name": cart_hotel.hotel_name or "",
					"supplier": cart_hotel.supplier or "",
					"hotel_reviews": get_hotel_reviews_url(cart_hotel.hotel_reviews, cart_hotel.hotel_name, destination),
					"status": "pending",
					"approver_level": 0,
					"images": json.loads(cart_hotel.images) if isinstance(cart_hotel.images, str) else (cart_hotel.images or []),
					"rooms": rooms
				}
				hotels.append(hotel_data)

			# Map request_status to status and status_code
			status_mapping = {
				"req_pending": ("pending_in_cart", 0),
				"req_sent_for_approval": ("sent_for_approval", 1),
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
				"req_email":req.employee_email or "",
				"hotels": hotels,
				"destination": destination,
				"destination_code": destination_code,
				"budget_options": req.budget_options or "",
				"employee_budget": float(req.employee_budget or 0),
				"work_address": req.work_address or "",
				"check_in": str(req.check_in) if req.check_in else "",
				"check_out": str(req.check_out) if req.check_out else "",
				"amount": total_amount,
				"status": status,
				"status_code": status_code,
				"rooms_count": req.room_count or 0,
				"guests_count": req.adult_count or 0,
				"child_count": req.child_count or 0,
				"child_ages": json.loads(req.child_ages) if isinstance(req.child_ages, str) else (req.child_ages or []),
				"company": {
					"id": req.company or "",
					"name": company_name
				},
				"employee": {
					"id": req.employee or "",
					"name": employee_name,
					"phone_number": employee_phone_number,
					"employee_level": employee_level
				}
			}
			data.append(booking_data)

		# Calculate pagination metadata
		total_pages = (total_count + page_size - 1) // page_size  # Ceiling division
		has_next = page < total_pages
		has_previous = page > 1

		return {
				"success": True,
				"data": data,
				"pagination": {
					"page": page,
					"page_size": page_size,
					"total_count": total_count,
					"total_pages": total_pages,
					"has_next": has_next,
					"has_previous": has_previous
				}
		}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "get_all_request_bookings API Error")
		return {
				"success": False,
				"error": str(e),
				"data": [],
				"pagination": None
		}


@frappe.whitelist()
def get_request_booking_details(request_booking_id, status=None):
	"""
	API to get full details of a specific request booking including all cart hotel items and rooms.

	Args:
		request_booking_id (str): The request booking ID (required)
		status (str): Optional status filter for rooms (e.g., "sent_for_approval", "approved")
		              If not provided, uses the request's own status for filtering.

	Returns:
		dict: Response with success status and full booking data including hotels and rooms
	"""
	try:
		if not request_booking_id:
			return {
				"success": False,
				"error": "request_booking_id is required"
			}

		# Check if booking exists
		req = frappe.db.get_value(
			"Request Booking Details",
			{"request_booking_id": request_booking_id},
			[
				"name",
				"request_booking_id",
				"company",
				"employee",
				"employee_email",
				"booking",
				"request_status",
				"check_in",
				"check_out",
				"occupancy",
				"adult_count",
				"child_count",
				"child_ages",
				"room_count",
				"destination",
				"destination_code",
				"budget_options",
				"employee_budget",
				"work_address"
			],
			as_dict=True
		)

		if not req:
			return {
				"success": False,
				"error": f"Request booking not found for ID: {request_booking_id}"
			}

		# Get employee details
		employee_name = ""
		employee_phone_number = ""
		employee_level = ""
		if req.employee:
			employee_doc = frappe.get_value(
				"Employee",
				req.employee,
				["employee_name", "cell_number", "custom_employee_level"],
				as_dict=True
			)
			if employee_doc:
				employee_name = employee_doc.get("employee_name", "")
				employee_phone_number = employee_doc.get("cell_number", "") or ""
				employee_level = employee_doc.get("custom_employee_level", "") or ""

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

		# Get booking details for booking_id
		booking_id = "NA"
		if req.booking:
			booking_doc = frappe.get_value(
				"Hotel Bookings",
				req.booking,
				["booking_id"],
				as_dict=True
			)
			if booking_doc:
				booking_id = booking_doc.get("booking_id") or "NA"

		# Get all hotel items linked to this request booking
		hotels = []
		total_amount = 0.0

		# Get hotels via the request_booking link
		cart_hotel_items = frappe.get_all(
			"Cart Hotel Item",
			filters={"request_booking": req.name},
			pluck="name"
		)

		# Define status filter mapping based on request status
		room_status_filter = {
			"req_sent_for_approval": "sent_for_approval",
			"req_approved": "approved",
			"req_payment_pending": "payment_pending",
			"req_payment_success": "payment_success"
		}

		# Use status from query param if provided, otherwise use request's own status
		if status:
			required_room_status = status
		else:
			required_room_status = room_status_filter.get(req.request_status)

		for cart_hotel_name in cart_hotel_items:
			cart_hotel = frappe.get_doc("Cart Hotel Item", cart_hotel_name)

			# Get rooms for this hotel
			rooms = []
			for room in cart_hotel.rooms:
				# Filter rooms based on request status
				if required_room_status and (room.status or "pending") != required_room_status:
					continue

				room_data = {
					"room_id": room.room_id or "",
					"room_rate_id": room.room_rate_id or "",
					"room_type": room.room_name or "",
					"price": float(room.price or 0),
					"room_count": 1,
					"meal_plan": cart_hotel.meal_plan or "",
					"cancellation_policy": cart_hotel.cancellation_policy or "",
					"status": room.status or "pending",
					"approver_level": 0,
					"images": json.loads(room.images) if isinstance(room.images, str) else (room.images or [])
				}
				rooms.append(room_data)
				total_amount += float(room.price or 0)

			# Skip hotel entirely if no rooms passed the filter
			if required_room_status and not rooms:
				continue

			hotel_data = {
				"hotel_id": cart_hotel.hotel_id or "",
				"hotel_name": cart_hotel.hotel_name or "",
				"supplier": cart_hotel.supplier or "",
				"hotel_reviews": get_hotel_reviews_url(cart_hotel.hotel_reviews, cart_hotel.hotel_name, req.destination or ""),
				"approver_level": 0,
				"images": json.loads(cart_hotel.images) if isinstance(cart_hotel.images, str) else (cart_hotel.images or []),
				"rooms": rooms
			}
			hotels.append(hotel_data)

		# Map request_status to status and status_code
		status_mapping = {
			"req_pending": ("pending_in_cart", 0),
			"req_sent_for_approval": ("sent_for_approval", 1),
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
			"req_email":req.employee_email or "",
			"hotels": hotels,
			"destination": req.destination or "",
			"destination_code": req.destination_code or "",
			"budget_options": req.budget_options or "",
			"employee_budget": float(req.employee_budget or 0),
			"work_address": req.work_address or "",
			"check_in": str(req.check_in) if req.check_in else "",
			"check_out": str(req.check_out) if req.check_out else "",
			"amount": total_amount,
			"status": status,
			"status_code": status_code,
			"rooms_count": req.room_count or 0,
			"guests_count": req.adult_count or 0,
			"child_count": req.child_count or 0,
			"child_ages": json.loads(req.child_ages) if isinstance(req.child_ages, str) else (req.child_ages or []),
			"company": {
				"id": req.company or "",
				"name": company_name
			},
			"employee": {
				"id": req.employee or "",
				"name": employee_name,
				"phone_number": employee_phone_number,
				"employee_level": employee_level
			}
		}

		return {
			"success": True,
			"data": booking_data
		}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "get_request_booking_details API Error")
		return {
			"success": False,
			"error": str(e)
		}


def send_email_via_api(to_emails, subject, body):
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

	frappe.log_error(
		message=f"URL: {url}\nTo: {to_emails}\nSubject: {subject}",
		title="[Email Send API] REQUEST"
	)
	response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
	frappe.log_error(
		message=f"Status: {response.status_code}\nBody: {response.text}",
		title="[Email Send API] RESPONSE"
	)

	if response.status_code != 200:
		raise Exception(f"Email API returned status code {response.status_code}: {response.text}")

	return response.json()


def generate_approval_email_body(employee_name, check_in, check_out, destination="", request_booking_id="", number_of_guests=0, number_of_hotel_options=0, agent_email=""):
	"""
	Generate HTML email body for sent_for_approval notification.
	Uses a dark theme template with employee details and a review button.
	"""
	# Generate email action token
	token = ""
	try:
		token_payload = {"source": "mail", "request_booking_id": request_booking_id}
		frappe.log_error(
			message=f"URL: {EMAIL_AUTHENTICATION_API_URL}\nPayload: {json.dumps(token_payload, indent=2)}",
			title="[Email Auth Token API] REQUEST"
		)
		token_response = requests.post(
			EMAIL_AUTHENTICATION_API_URL,
			headers={"Content-Type": "application/json"},
			json=token_payload,
			timeout=30
		)
		frappe.log_error(
			message=f"Status: {token_response.status_code}\nBody: {token_response.text}",
			title="[Email Auth Token API] RESPONSE"
		)
		if token_response.status_code == 200:
			token_data = token_response.json()
			if token_data.get("success") and token_data.get("data", {}).get("token"):
				token = token_data["data"]["token"]
	except Exception as e:
		frappe.log_error(f"Failed to generate email action token: {str(e)}", "Email Token Generation Error")

	# Review link with token
	review_link = f"https://cbt-dev-destiin.vercel.app/hotels/{request_booking_id}/review?token={token}"

	html_body = f"""<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml"
    xmlns:o="urn:schemas-microsoft-com:office:office">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="x-apple-disable-message-reformatting">
    <title>Hotel Approval Request - Destiin</title>
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
            /* background-color: #050a14 !important; */
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
                                            {employee_name},</p>
                                    </td>
                                </tr>

                                <!-- Message -->
                                <tr>
                                    <td style="padding-bottom: 24px;">
                                        <p style="margin: 0; font-size: 15px; color: #a0a0a0; line-height: 1.7;">
                                            We have carefully reviewed your travel requirements and are pleased to
                                            present our recommended hotel options for your upcoming trip.
                                        </p>
                                    </td>
                                </tr>

                                <!-- Hotel Summary Card -->
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
                                                                    📍 TRIP SUMMARY</p>
                                                            </td>
                                                        </tr>

                                                        <!-- Destination -->
                                                        <tr>
                                                            <td
                                                                style="padding: 8px 16px 8px 0; font-size: 13px; color: #a0a0a0; font-weight: 500; width: 40%;">
                                                                Destination:</td>
                                                            <td
                                                                style="padding: 8px 0; font-size: 14px; color: #ededed; font-weight: 500;">
                                                                {destination}</td>
                                                        </tr>

                                                        <!-- Check-in -->
                                                        <tr>
                                                            <td
                                                                style="padding: 8px 16px 8px 0; font-size: 13px; color: #a0a0a0; font-weight: 500;">
                                                                Check-in:</td>
                                                            <td
                                                                style="padding: 8px 0; font-size: 14px; color: #ededed; font-weight: 500;">
                                                                {check_in}</td>
                                                        </tr>

                                                        <!-- Check-out -->
                                                        <tr>
                                                            <td
                                                                style="padding: 8px 16px 8px 0; font-size: 13px; color: #a0a0a0; font-weight: 500;">
                                                                Check-out:</td>
                                                            <td
                                                                style="padding: 8px 0; font-size: 14px; color: #ededed; font-weight: 500;">
                                                                {check_out}</td>
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

                                                        <!-- Hotels Suggested -->
                                                        <tr>
                                                            <td
                                                                style="padding: 8px 16px 8px 0; font-size: 13px; color: #a0a0a0; font-weight: 500;">
                                                                Hotels Suggested:</td>
                                                            <td
                                                                style="padding: 8px 0; font-size: 14px; color: #ededed; font-weight: 500;">
                                                                {number_of_hotel_options} Options</td>
                                                        </tr>
                                                    </table>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>

                                <!-- Message 2 -->
                                <tr>
                                    <td style="padding-bottom: 24px;">
                                        <p style="margin: 0; font-size: 15px; color: #a0a0a0; line-height: 1.7;">
                                            Our travel team has handpicked hotels that match your preferences, budget,
                                            and company policies. Click the button below to review all available options
                                            and make your selection.
                                        </p>
                                    </td>
                                </tr>

                                <!-- CTA Button -->
                                <tr>
                                    <td align="center" style="padding: 32px 0;">
                                        <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                                            <tr>
                                                <td align="center"
                                                    style="border-radius: 12px; background-color: #7ecda5;">
                                                    <a href="{review_link}" target="_blank" class="cta-button"
                                                        style="display: inline-block; padding: 16px 48px; font-size: 16px; font-weight: 600; color: #0e0f1d; text-decoration: none; border-radius: 12px; font-family: 'Outfit', Arial, sans-serif;">
                                                        View Hotel Options
                                                    </a>
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
                                            Have questions or need different options?
                                        </p>
                                        <p style="margin: 0; font-size: 14px; color: #a0a0a0; line-height: 1.6;">
                                            Reply to this email or contact your travel agent at <a
                                                href="mailto:{agent_email}"
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
                                            This is an automated notification regarding your travel booking request.
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

	return html_body


@frappe.whitelist(allow_guest=False)
def send_for_approval(request_booking_id, selected_items):
	"""
	API to send selected hotels and rooms for approval.

	Updates the status of selected hotels and rooms to 'sent_for_approval'
	and sends an email notification to the employee and agent.

	Args:
		request_booking_id (str): The request booking ID (required)
		selected_items (list/str): Array of selected hotels with rooms to send for approval.
			Rooms are identified by room_rate_id (unique) instead of room_id (not unique).
			[
				{
					"hotel_id": "...",
					"room_rate_ids": ["room_rate_id_1", "room_rate_id_2"]
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
					"success": False,
					"error": "request_booking_id is required"
			}

		if not selected_items:
			return {
					"success": False,
					"error": "selected_items is required and cannot be empty"
			}

		# Check if booking exists
		booking_doc = frappe.db.get_value(
			"Request Booking Details",
			{"request_booking_id": request_booking_id},
			["name", "employee", "agent", "check_in", "check_out", "destination", "employee_email", "adult_count"],
			as_dict=True
		)

		if not booking_doc:
			return {
					"success": False,
					"error": f"Request booking not found for ID: {request_booking_id}"
			}

		# Get employee details — prefer employee_email stored on the request booking
		employee_name = ""
		employee_email = booking_doc.employee_email or ""
		if booking_doc.employee:
			employee_doc = frappe.get_value(
				"Employee",
				booking_doc.employee,
				["employee_name", "company_email", "personal_email"],
				as_dict=True
			)
			if employee_doc:
				employee_name = employee_doc.get("employee_name", "")
				if not employee_email:
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

		# Build a mapping of selected hotel_ids to room_rate_ids
		selected_hotel_map = {}
		for item in selected_items:
			hotel_id = item.get("hotel_id")
			room_rate_ids = item.get("room_rate_ids", [])
			if hotel_id:
				selected_hotel_map[hotel_id] = room_rate_ids

		# Track updated hotels data for email
		updated_hotels_data = []
		updated_count = 0

		# Get all cart hotel items linked to this booking
		cart_hotel_items = frappe.get_all(
			"Cart Hotel Item",
			filters={"request_booking": booking_doc.name},
			pluck="name"
		)

		for cart_hotel_name in cart_hotel_items:
			cart_hotel = frappe.get_doc("Cart Hotel Item", cart_hotel_name)

			# Check if this hotel is in selected items
			if cart_hotel.hotel_id in selected_hotel_map:
				selected_room_rate_ids = selected_hotel_map[cart_hotel.hotel_id]

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
					if room.room_rate_id in selected_room_rate_ids:
						room.status = "sent_for_approval"
						updated_count += 1

						hotel_data["rooms"].append({
							"room_id": room.room_id,
							"room_rate_id": room.room_rate_id,
							"room_name": room.room_name,
							"price": float(room.price or 0),
							"total_price": float(room.total_price or 0),
							"tax": float(room.tax or 0),
							"currency": room.currency or "USD"
						})

				# Save the cart hotel item
				cart_hotel.save(ignore_permissions=True)

				if hotel_data["rooms"]:
					updated_hotels_data.append(hotel_data)

		# Update the request booking status based on room statuses
		new_request_status = update_request_status_from_rooms(booking_doc.name)

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
					destination=booking_doc.destination or "",
					request_booking_id=request_booking_id,
					number_of_guests=booking_doc.adult_count or 0,
					number_of_hotel_options=len(updated_hotels_data),
					agent_email=agent_email or ""
				)
				send_email_via_api(to_emails, subject, body)
				email_sent = True
			except Exception as email_error:
				frappe.log_error(
					f"Failed to send approval email: {str(email_error)}",
					"sent_for_approval Email Error"
				)

		return {
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

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "sent_for_approval API Error")
		return {
				"success": False,
				"error": str(e)
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
		selected_items (list/str): Array of selected hotels with rooms to approve.
			Rooms are identified by room_rate_id (unique) instead of room_id (not unique).
			[
				{
					"hotel_id": "...",
					"room_rate_ids": ["room_rate_id_1", "room_rate_id_2"]
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
					"success": False,
					"error": "request_booking_id is required"
			}

		if not employee:
			return {
					"success": False,
					"error": "employee is required"
			}

		if not selected_items:
			return {
					"success": False,
					"error": "selected_items is required and cannot be empty"
			}

		# Check if booking exists and belongs to the employee
		booking_doc = frappe.db.get_value(
			"Request Booking Details",
			{"request_booking_id": request_booking_id, "employee": employee},
			["name", "employee", "agent", "check_in", "check_out", "request_status"],
			as_dict=True
		)

		if not booking_doc:
			return {
					"success": False,
					"error": f"Request booking not found for ID: {request_booking_id} and employee: {employee}"
			}

		# Build a mapping of selected hotel_ids to room_rate_ids
		selected_hotel_map = {}
		for item in selected_items:
			hotel_id = item.get("hotel_id")
			room_rate_ids = item.get("room_rate_ids", [])
			if hotel_id:
				selected_hotel_map[hotel_id] = room_rate_ids

		# Track updated hotels data
		updated_hotels_data = []
		declined_hotels_data = []
		updated_count = 0
		declined_count = 0

		# Get all cart hotel items linked to this booking
		cart_hotel_items = frappe.get_all(
			"Cart Hotel Item",
			filters={"request_booking": booking_doc.name},
			pluck="name"
		)

		for cart_hotel_name in cart_hotel_items:
			cart_hotel = frappe.get_doc("Cart Hotel Item", cart_hotel_name)

			# Check if this hotel is in selected items
			if cart_hotel.hotel_id in selected_hotel_map:
				selected_room_rate_ids = selected_hotel_map[cart_hotel.hotel_id]

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
					if room.room_rate_id in selected_room_rate_ids:
						room.status = "approved"
						updated_count += 1

						hotel_data["rooms"].append({
							"room_id": room.room_id,
							"room_rate_id": room.room_rate_id,
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
							"room_rate_id": room.room_rate_id,
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

		# Update the request booking status based on room statuses
		new_request_status = update_request_status_from_rooms(booking_doc.name)

		frappe.db.commit()

		return {
				"success": True,
				"message": f"Successfully approved {updated_count} room(s) and declined {declined_count} room(s)",
				"data": {
					"request_booking_id": request_booking_id,
					"employee": employee,
					"approved_count": updated_count,
					"declined_count": declined_count,
					"request_status": new_request_status or "req_approved",
					"approved_hotels": updated_hotels_data,
					"declined_hotels": declined_hotels_data
				}
		}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "approve_booking API Error")
		return {
				"success": False,
				"error": str(e)
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
		selected_items (list/str): Array of selected hotels with rooms to decline.
			Rooms are identified by room_rate_id (unique) instead of room_id (not unique).
			[
				{
					"hotel_id": "...",
					"room_rate_ids": ["room_rate_id_1", "room_rate_id_2"]
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
					"success": False,
					"error": "request_booking_id is required"
			}

		if not employee:
			return {
					"success": False,
					"error": "employee is required"
			}

		if not selected_items:
			return {
					"success": False,
					"error": "selected_items is required and cannot be empty"
			}

		# Check if booking exists and belongs to the employee
		booking_doc = frappe.db.get_value(
			"Request Booking Details",
			{"request_booking_id": request_booking_id, "employee": employee},
			["name", "employee", "agent", "check_in", "check_out", "request_status"],
			as_dict=True
		)

		if not booking_doc:
			return {
					"success": False,
					"error": f"Request booking not found for ID: {request_booking_id} and employee: {employee}"
			}

		# Build a mapping of selected hotel_ids to room_rate_ids
		selected_hotel_map = {}
		for item in selected_items:
			hotel_id = item.get("hotel_id")
			room_rate_ids = item.get("room_rate_ids", [])
			if hotel_id:
				selected_hotel_map[hotel_id] = room_rate_ids

		# Track declined hotels data
		declined_hotels_data = []
		declined_count = 0

		# Get all cart hotel items linked to this booking
		cart_hotel_items = frappe.get_all(
			"Cart Hotel Item",
			filters={"request_booking": booking_doc.name},
			pluck="name"
		)

		for cart_hotel_name in cart_hotel_items:
			cart_hotel = frappe.get_doc("Cart Hotel Item", cart_hotel_name)

			# Check if this hotel is in selected items
			if cart_hotel.hotel_id in selected_hotel_map:
				selected_room_rate_ids = selected_hotel_map[cart_hotel.hotel_id]

				hotel_data = {
					"hotel_id": cart_hotel.hotel_id,
					"hotel_name": cart_hotel.hotel_name,
					"supplier": cart_hotel.supplier,
					"rooms": []
				}

				# Update status for selected rooms to declined
				for room in cart_hotel.rooms:
					if room.room_rate_id in selected_room_rate_ids:
						room.status = "declined"
						declined_count += 1

						hotel_data["rooms"].append({
							"room_id": room.room_id,
							"room_rate_id": room.room_rate_id,
							"room_name": room.room_name,
							"price": float(room.price or 0),
							"status": "declined"
						})

				# Save the cart hotel item
				cart_hotel.save(ignore_permissions=True)

				if hotel_data["rooms"]:
					declined_hotels_data.append(hotel_data)

		# Update the request booking status based on room statuses
		new_request_status = update_request_status_from_rooms(booking_doc.name)

		frappe.db.commit()

		return {
				"success": True,
				"message": f"Successfully declined {declined_count} room(s)",
				"data": {
					"request_booking_id": request_booking_id,
					"employee": employee,
					"declined_count": declined_count,
					"request_status": new_request_status or "req_cancelled",
					"declined_hotels": declined_hotels_data
				}
		}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "decline_booking API Error")
		return {
				"success": False,
				"error": str(e)
		}


@frappe.whitelist(allow_guest=False)
def update_request_booking(
	request_booking_id,
	name=None,
	destination=None,
	destination_code=None,
	check_in=None,
	check_out=None,
	occupancy=None,
	adult_count=None,
	child_count=None,
	child_ages=None,
	room_count=None,
	hotel_details=None,
	employee=None,
	company=None,
	request_status=None,
	agent=None
):
	"""
	API to update an existing request booking.

	All parameters are optional. The booking can be identified by either
	request_booking_id or name (document name).

	Args:
		request_booking_id (str, optional): The request booking ID
		name (str, optional): The document name (alternative identifier)
		destination (str, optional): Destination name to update
		destination_code (str, optional): Destination code to update
		check_in (str, optional): Check-in date to update
		check_out (str, optional): Check-out date to update
		occupancy (int, optional): Total occupancy to update
		adult_count (int, optional): Number of adults to update
		child_count (int, optional): Number of children to update
		child_ages (list, optional): List of child ages to update
		room_count (int, optional): Number of rooms to update
		employee (str, optional): Employee ID to update
		company (str, optional): Company ID to update
		request_status (str, optional): Request status to update
		agent (str, optional): Agent to update
		hotel_details (dict/list/str, optional): Hotel and room details to update
			{
				"hotel_id": "...",
				"hotel_name": "...",
				"supplier": "...",
				"cancellation_policy": "...",
				"meal_plan": "...",
				"rooms": [
					{
						"room_id": "...",
						"room_rate_id": "...",
						"room_name": "...",
						"price": 0,
						"total_price": 0,
						"tax": 0,
						"currency": "USD",
						"status": "pending"
					}
				]
			}

	Returns:
		dict: Response with success status and updated booking data
	"""
	try:
		# Parse hotel_details if it's a string
		if isinstance(hotel_details, str):
			hotel_details = json.loads(hotel_details) if hotel_details else None

		# Need at least one identifier
		if not request_booking_id and not name:
			return {
					"success": False,
					"error": "Either request_booking_id or name is required to identify the booking"
			}

		# Check if booking exists - try by request_booking_id first, then by name
		booking_doc = None
		if request_booking_id:
			booking_doc = frappe.db.get_value(
				"Request Booking Details",
				{"request_booking_id": request_booking_id},
				["name", "employee", "company", "check_in", "check_out", "booking", "request_status", "destination", "destination_code"],
				as_dict=True
			)

		if not booking_doc and name:
			booking_doc = frappe.db.get_value(
				"Request Booking Details",
				name,
				["name", "employee", "company", "check_in", "check_out", "booking", "request_status", "destination", "destination_code"],
				as_dict=True
			)

		if not booking_doc:
			identifier = request_booking_id or name
			return {
					"success": False,
					"error": f"Request booking not found for identifier: {identifier}"
			}

		# Get the full booking document for updates
		request_booking = frappe.get_doc("Request Booking Details", booking_doc.name)

		# Update fields if provided
		if occupancy is not None:
			request_booking.occupancy = int(occupancy)
		if adult_count is not None:
			request_booking.adult_count = int(adult_count)
		if child_count is not None:
			request_booking.child_count = int(child_count)
		if child_ages is not None:
			# Parse child_ages if it's a string and store as JSON
			if isinstance(child_ages, str):
				child_ages = json.loads(child_ages) if child_ages else []
			request_booking.child_ages = json.dumps(child_ages) if isinstance(child_ages, list) else child_ages
		if room_count is not None:
			request_booking.room_count = int(room_count)
		if destination is not None:
			request_booking.destination = destination
		if destination_code is not None:
			request_booking.destination_code = destination_code
		if check_in is not None:
			request_booking.check_in = getdate(check_in)
		if check_out is not None:
			request_booking.check_out = getdate(check_out)
		if employee is not None:
			request_booking.employee = employee
		if company is not None:
			request_booking.company = company
		if request_status is not None:
			request_booking.request_status = request_status
		if agent is not None:
			request_booking.agent = agent

		# Handle hotel and room details update
		new_hotels_data = []
		if hotel_details:
			# Parse hotel_details if it's a string
			if isinstance(hotel_details, str):
				hotel_details = json.loads(hotel_details) if hotel_details else None

			# Normalize to list
			hotels_list = []
			if isinstance(hotel_details, dict):
				hotels_list = [hotel_details]
			elif isinstance(hotel_details, list):
				hotels_list = hotel_details

			# Get existing cart hotel items linked to this booking
			existing_hotel_items = frappe.get_all(
				"Cart Hotel Item",
				filters={"request_booking": request_booking.name},
				pluck="name"
			)

			# Create a map of existing hotels by hotel_id
			existing_hotels_map = {}
			for item_name in existing_hotel_items:
				hotel_doc = frappe.get_doc("Cart Hotel Item", item_name)
				existing_hotels_map[hotel_doc.hotel_id] = hotel_doc

			created_hotel_items = []
			new_hotels_data = []
			for hotel_data in hotels_list:
				hotel_id = hotel_data.get("hotel_id", "")
				cart_hotel_item = None
				is_new_hotel = False

				# Check if hotel already exists
				if hotel_id and hotel_id in existing_hotels_map:
					cart_hotel_item = existing_hotels_map[hotel_id]
				else:
					# Create new cart hotel item
					cart_hotel_item = frappe.new_doc("Cart Hotel Item")
					cart_hotel_item.request_booking = request_booking.name
					is_new_hotel = True

				# Update only provided hotel details
				if "hotel_id" in hotel_data:
					cart_hotel_item.hotel_id = hotel_data["hotel_id"]
				if "hotel_name" in hotel_data:
					cart_hotel_item.hotel_name = hotel_data["hotel_name"]
				if "supplier" in hotel_data:
					cart_hotel_item.supplier = hotel_data["supplier"]
				if "cancellation_policy" in hotel_data:
					cart_hotel_item.cancellation_policy = hotel_data["cancellation_policy"]
				if "meal_plan" in hotel_data:
					cart_hotel_item.meal_plan = hotel_data["meal_plan"]
				if "latitude" in hotel_data:
					cart_hotel_item.latitude = hotel_data["latitude"]
				if "longitude" in hotel_data:
					cart_hotel_item.longitude = hotel_data["longitude"]
				if "hotel_reviews" in hotel_data:
					cart_hotel_item.hotel_reviews = hotel_data["hotel_reviews"]
				if "images" in hotel_data:
					cart_hotel_item.images = json.dumps(hotel_data["images"])

				# Only update rooms if explicitly provided in the payload
				if "rooms" in hotel_data:
					cart_hotel_item.rooms = []
					rooms_data = hotel_data["rooms"]

					for room in rooms_data:
						cart_hotel_item.append("rooms", {
							"room_id": room.get("room_id", ""),
							"room_rate_id": room.get("room_rate_id", ""),
							"room_name": room.get("room_name", ""),
							"price": room.get("price", 0),
							"total_price": room.get("total_price", 0),
							"tax": room.get("tax", 0),
							"currency": room.get("currency", "USD"),
							"status": room.get("status", "pending"),
							"images": json.dumps(room.get("images", []))
						})

					cart_hotel_item.room_count = len(rooms_data)
				cart_hotel_item.save(ignore_permissions=True)
				created_hotel_items.append(cart_hotel_item.name)

				if is_new_hotel:
					new_hotels_data.append(hotel_data)

			# Update the request booking status based on room statuses
			update_request_status_from_rooms(request_booking.name)
			# Reload the document to get the updated modified timestamp
			request_booking.reload()

			# Link all cart hotel items to the Table MultiSelect field (after reload to preserve changes)
			if created_hotel_items:
				request_booking.cart_hotel_item = []  # Clear existing entries
				for item_name in created_hotel_items:
					request_booking.append("cart_hotel_item", {
						"cart_hotel_item": item_name
					})

		# Save the booking
		request_booking.save(ignore_permissions=True)
		frappe.db.commit()

		# Fire-and-forget TripAdvisor URL API call for newly added hotels
		if hotel_details and new_hotels_data:
			dest = destination if destination is not None else (booking_doc.destination or "")
			dest_cntry = booking_doc.get("destination_country") or ""
			_fire_tripadvisor_url_api(
				request_booking_id=request_booking.request_booking_id,
				hotels_data=new_hotels_data,
				destination=dest,
				destination_country=dest_cntry
			)

		# Prepare response data
		response_data = {
			"request_booking_id": request_booking.request_booking_id,
			"name": request_booking.name,
			"employee": request_booking.employee,
			"company": request_booking.company,
			"check_in": str(request_booking.check_in) if request_booking.check_in else "",
			"check_out": str(request_booking.check_out) if request_booking.check_out else "",
			"request_status": request_booking.request_status,
			"agent": request_booking.agent,
			"occupancy": request_booking.occupancy,
			"adult_count": request_booking.adult_count,
			"child_count": request_booking.child_count,
			"child_ages": json.loads(request_booking.child_ages) if isinstance(request_booking.child_ages, str) else (request_booking.child_ages or []),
			"room_count": request_booking.room_count,
			"cart_hotel_item": request_booking.cart_hotel_item,
			"destination": request_booking.destination or "",
			"destination_code": request_booking.destination_code or ""
		}

		return {
				"success": True,
				"message": "Request booking updated successfully",
				"data": response_data
		}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "update_request_booking API Error")
		return {
				"success": False,
				"error": str(e)
		}
