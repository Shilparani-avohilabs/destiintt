import frappe
import json
import requests
from frappe.utils import getdate


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
	employee_email=None
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
							"currency": "INR"
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
			booking_doc.child_ages = child_ages
		if room_count is not None:
			booking_doc.room_count = int(room_count)
		if destination:
			booking_doc.destination = destination
		if destination_code:
			booking_doc.destination_code = destination_code

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
						"currency": room.get("currency", "INR"),
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
			"child_ages": booking_doc.child_ages,
			"room_count": booking_doc.room_count,
			"destination": booking_doc.destination or "",
			"destination_code": booking_doc.destination_code or "",
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
def get_all_request_bookings(company=None, employee=None, status=None):
	"""
	API to get all request booking details with related hotel and room information

	Args:
		company (str, optional): Filter by company ID
		employee (str, optional): Filter by employee ID
		status (str, optional): Filter by request status. Supports multiple comma-separated values.
			Valid values: req_pending, req_sent_for_approval, req_approved,
			req_payment_pending, req_payment_success, req_closed
			Example: status=req_pending,req_sent_for_approval
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

		# Fetch all request booking details
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
				"destination_code"
			]
		)

		data = []
		for req in request_bookings:
			# Get employee details
			employee_name = ""
			employee_phone_number = ""
			if req.employee:
				employee_doc = frappe.get_value(
					"Employee",
					req.employee,
					["employee_name", "cell_number"],
					as_dict=True
				)
				if employee_doc:
					employee_name = employee_doc.get("employee_name", "")
					employee_phone_number = employee_doc.get("cell_number", "") or ""

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
				"check_in": str(req.check_in) if req.check_in else "",
				"check_out": str(req.check_out) if req.check_out else "",
				"amount": total_amount,
				"status": status,
				"status_code": status_code,
				"rooms_count": req.room_count or 0,
				"guests_count": req.adult_count or 0,
				"child_count": req.child_count or 0,
				"child_ages": req.child_ages or [],
				"company": {
					"id": req.company or "",
					"name": company_name
				},
				"employee": {
					"id": req.employee or "",
					"name": employee_name,
					"phone_number": employee_phone_number
				}
			}
			data.append(booking_data)

		return {
				"success": True,
				"data": data
		}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "get_all_request_bookings API Error")
		return {
				"success": False,
				"error": str(e),
				"data": []
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
				"destination_code"
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
		if req.employee:
			employee_doc = frappe.get_value(
				"Employee",
				req.employee,
				["employee_name", "cell_number"],
				as_dict=True
			)
			if employee_doc:
				employee_name = employee_doc.get("employee_name", "")
				employee_phone_number = employee_doc.get("cell_number", "") or ""

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
			"check_in": str(req.check_in) if req.check_in else "",
			"check_out": str(req.check_out) if req.check_out else "",
			"amount": total_amount,
			"status": status,
			"status_code": status_code,
			"rooms_count": req.room_count or 0,
			"guests_count": req.adult_count or 0,
			"child_count": req.child_count or 0,
			"child_ages": req.child_ages or [],
			"company": {
				"id": req.company or "",
				"name": company_name
			},
			"employee": {
				"id": req.employee or "",
				"name": employee_name,
				"phone_number": employee_phone_number
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
	url = "http://16.112.56.253/main/v1/email/send"
	headers = {
		"Content-Type": "application/json",
		"info": "true"
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


def generate_approval_email_body(employee_name, check_in, check_out, destination="", request_booking_id=""):
	"""
	Generate HTML email body for sent_for_approval notification.
	Uses a dark theme template with employee details and a review button.
	"""
	# Use destination if provided, otherwise use a generic message
	destination_text = f'<span style="color:#7ECDA5;font-weight:600;">{destination}</span>' if destination else "your selected destination"

	# Generate email action token
	token = ""
	try:
		token_response = requests.post(
			"http://16.112.56.253/crm/cbt/v1/utils/generateEmailActionToken",
			headers={"Content-Type": "application/json"},
			json={
				"source": "mail",
				"request_booking_id": request_booking_id
			},
			timeout=30
		)
		if token_response.status_code == 200:
			token_data = token_response.json()
			if token_data.get("success") and token_data.get("data", {}).get("token"):
				token = token_data["data"]["token"]
	except Exception as e:
		frappe.log_error(f"Failed to generate email action token: {str(e)}", "Email Token Generation Error")

	# Review link with token
	review_link = f"https://cbt-destiin-frontend.vercel.app/hotels/{request_booking_id}/review?token={token}"

	html_body = f"""<!DOCTYPE html
    PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">

<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Hotel Selection</title>

    <style type="text/css">
        body,
        table,
        td,
        a {{
            -webkit-text-size-adjust: 100%;
            -ms-text-size-adjust: 100%;
        }}

        table,
        td {{
            mso-table-lspace: 0pt;
            mso-table-rspace: 0pt;
        }}

        img {{
            border: 0;
            display: block;
            height: auto;
        }}

        table {{
            border-collapse: collapse !important;
        }}

        body {{
            margin: 0;
            padding: 0;
            width: 100%;
            background: #0E0F1D;
            font-family: 'Segoe UI', Helvetica, Arial, sans-serif;
        }}

        @media screen and (max-width:600px) {{
            .container {{
                width: 100% !important;
            }}

            .pad {{
                padding: 20px !important;
            }}
        }}
    </style>
</head>

<body>

    <table width="100%" cellpadding="0" cellspacing="0" style="background:#0E0F1D;">
        <tr>
            <td align="center" style="padding:40px 10px;">

                <!-- MAIN CONTAINER -->
                <table width="500" class="container" cellpadding="0" cellspacing="0" style="background:#161B22;border-radius:16px;overflow:hidden;
box-shadow:0 20px 40px rgba(0,0,0,0.45);">

                    <!-- HEADER -->
                    <tr>
                        <td align="center" style="padding:26px;
background:linear-gradient(90deg,#7ECDA5,#5B8FD6,#7A63A8);">
                            <h2 style="margin:0;color:#FFFFFF;font-size:22px;font-weight:600;">
                                Hotel Selection Request
                            </h2>
                        </td>
                    </tr>

                    <!-- INTRO -->
                    <tr>
                        <td class="pad" style="padding:30px 40px;color:#E5E7EB;font-size:15px;line-height:1.5;">
                            <p style="margin:0 0 16px;">
                                Dear <strong>{employee_name}</strong>,
                            </p>
                            <p style="margin:0 0 24px;">
                                Please review and select your preferred hotel for your upcoming trip.
                            </p>
                        </td>
                    </tr>

                    <!-- BOOKING DETAILS CARD -->
                    <tr>
                        <td style="padding:0 40px 30px 40px;">
                            <table width="100%" cellpadding="0" cellspacing="0" style="
background:#0F1F33;
border:1px solid #1F3B4D;
border-radius:16px;
overflow:hidden;
">
                                <tr>
                                    <td style="padding:22px;">
                                        <!-- DESTINATION -->
                                        <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:16px;">
                                            <tr>
                                                <td style="color:#9CA3AF;font-size:13px;padding-bottom:4px;">
                                                    Destination
                                                </td>
                                            </tr>
                                            <tr>
                                                <td style="color:#FFFFFF;font-size:18px;font-weight:600;">
                                                    {destination_text}
                                                </td>
                                            </tr>
                                        </table>

                                        <!-- DATES -->
                                        <table width="100%" cellpadding="0" cellspacing="0" style="
background:rgba(255,255,255,0.05);
border:1px solid #1F3B4D;
border-radius:12px;
">
                                            <tr>
                                                <td style="padding:14px;width:50%;border-right:1px solid #1F3B4D;">
                                                    <p style="margin:0;font-size:12px;color:#9CA3AF;">
                                                        Check-in
                                                    </p>
                                                    <p style="margin:4px 0 0 0;font-size:16px;font-weight:600;color:#FFFFFF;">
                                                        {check_in}
                                                    </p>
                                                </td>
                                                <td style="padding:14px;width:50%;">
                                                    <p style="margin:0;font-size:12px;color:#9CA3AF;">
                                                        Check-out
                                                    </p>
                                                    <p style="margin:4px 0 0 0;font-size:16px;font-weight:600;color:#FFFFFF;">
                                                        {check_out}
                                                    </p>
                                                </td>
                                            </tr>
                                        </table>

                                        <!-- CTA BUTTON -->
                                        <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:20px;">
                                            <tr>
                                                <td align="center">
                                                    <a href="{review_link}" style="
display:block;
background:#10B981;
color:#FFFFFF;
padding:16px;
border-radius:999px;
text-decoration:none;
font-size:15px;
font-weight:600;
">
                                                        Review Hotels
                                                    </a>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- FOOTER -->
                    <tr>
                        <td align="center" style="padding:26px;background:#0A0B14;border-top:1px solid #1F2937;">
                            <p style="margin:0;color:#6B7280;font-size:12px;">
                                © 2026 DESTIIN TRAVEL
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
			["name", "employee", "agent", "check_in", "check_out", "destination", "employee_email"],
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
							"currency": room.currency or "INR"
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
					request_booking_id=request_booking_id
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
						"currency": "INR",
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
			for hotel_data in hotels_list:
				hotel_id = hotel_data.get("hotel_id", "")
				cart_hotel_item = None

				# Check if hotel already exists
				if hotel_id and hotel_id in existing_hotels_map:
					cart_hotel_item = existing_hotels_map[hotel_id]
				else:
					# Create new cart hotel item
					cart_hotel_item = frappe.new_doc("Cart Hotel Item")
					cart_hotel_item.request_booking = request_booking.name

				# Update hotel details
				cart_hotel_item.hotel_id = hotel_data.get("hotel_id", cart_hotel_item.hotel_id or "")
				cart_hotel_item.hotel_name = hotel_data.get("hotel_name", cart_hotel_item.hotel_name or "")
				cart_hotel_item.supplier = hotel_data.get("supplier", cart_hotel_item.supplier or "")
				cart_hotel_item.cancellation_policy = hotel_data.get("cancellation_policy", cart_hotel_item.cancellation_policy or "")
				cart_hotel_item.meal_plan = hotel_data.get("meal_plan", cart_hotel_item.meal_plan or "")
				cart_hotel_item.images = json.dumps(hotel_data.get("images", []))

				# Clear existing rooms and add new ones
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
						"currency": room.get("currency", "INR"),
						"status": room.get("status", "pending"),
						"images": json.dumps(room.get("images", []))
					})

				cart_hotel_item.room_count = len(rooms_data)
				cart_hotel_item.save(ignore_permissions=True)
				created_hotel_items.append(cart_hotel_item.name)

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
