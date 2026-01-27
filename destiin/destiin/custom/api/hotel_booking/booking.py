import frappe
import json
from datetime import datetime


@frappe.whitelist(allow_guest=False)
def confirm_booking(request_booking_id, employee, selected_items):
    """
    API to create a hotel booking from an approved request booking.

    This API:
    1. Fetches the request booking details
    2. Creates Hotel Bookings and Booking Payments records ONLY for approved hotels/rooms from request
    3. Updates request_booking status to 'req_closed'

    Args:
        request_booking_id (str): The request booking ID (required)
        employee (str): The employee ID (required)
        selected_items (list/str): Array of approved hotels with rooms to book
            [
                {
                    "hotel_id": "...",
                    "room_ids": ["room_id_1", "room_id_2"]
                }
            ]

    Returns:
        dict: Response with success status and booking data
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

        # Fetch the request booking details
        request_booking = frappe.db.get_value(
            "Request Booking Details",
            {"request_booking_id": request_booking_id, "employee": employee},
            [
                "name", "request_booking_id", "employee", "company", "agent",
                "cart_hotel_item", "check_in", "check_out", "occupancy",
                "adult_count", "child_count", "room_count", "request_status"
            ],
            as_dict=True
        )

        if not request_booking:
            return {
                "response": {
                    "success": False,
                    "error": f"Request booking not found for ID: {request_booking_id} and employee: {employee}",
                    "data": None
                }
            }

        # Check if booking already exists with this request_booking_id
        existing_booking = frappe.db.exists(
            "Hotel Bookings",
            {"booking_id": request_booking_id}
        )

        if existing_booking:
            return {
                "response": {
                    "success": False,
                    "error": f"Booking already exists for request_booking_id: {request_booking_id}",
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

        # Fetch cart hotel item and filter by selected/approved items
        hotel_id = ""
        hotel_name = ""
        room_id = ""
        room_type = ""
        room_count = 0
        total_amount = 0.0
        tax_amount = 0.0
        currency = "INR"
        approved_rooms = []

        if not request_booking.cart_hotel_item:
            return {
                "response": {
                    "success": False,
                    "error": "No cart hotel item found for this request booking",
                    "data": None
                }
            }

        cart_hotel = frappe.get_doc("Cart Hotel Item", request_booking.cart_hotel_item)

        # Check if this hotel is in selected items
        if cart_hotel.hotel_id not in selected_hotel_map:
            return {
                "response": {
                    "success": False,
                    "error": f"Hotel ID {cart_hotel.hotel_id} not found in selected items",
                    "data": None
                }
            }

        selected_room_ids = selected_hotel_map[cart_hotel.hotel_id]
        hotel_id = cart_hotel.hotel_id or ""
        hotel_name = cart_hotel.hotel_name or ""

        # Get ONLY approved room details from cart hotel rooms
        room_ids = []
        room_types = []
        for room in cart_hotel.rooms:
            # Only include rooms that are in selected_room_ids AND have approved status
            if room.room_id in selected_room_ids and room.status == "approved":
                room_ids.append(room.room_id or "")
                room_types.append(room.room_name or "")
                total_amount += float(room.total_price or room.price or 0)
                tax_amount += float(room.tax or 0)
                if room.currency:
                    currency = room.currency
                approved_rooms.append(room)

        if not approved_rooms:
            return {
                "response": {
                    "success": False,
                    "error": "No approved rooms found for the selected items",
                    "data": None
                }
            }

        # Join multiple room IDs and types with comma
        room_id = ", ".join(filter(None, room_ids))
        room_type = ", ".join(filter(None, room_types))
        room_count = len(approved_rooms)

        # Create Hotel Bookings record
        hotel_booking = frappe.new_doc("Hotel Bookings")
        hotel_booking.booking_id = request_booking_id
        hotel_booking.request_booking_link = request_booking.name
        hotel_booking.employee = request_booking.employee
        hotel_booking.company = request_booking.company
        hotel_booking.agent = request_booking.agent
        hotel_booking.hotel_id = hotel_id
        hotel_booking.hotel_name = hotel_name
        hotel_booking.room_id = room_id
        hotel_booking.room_type = room_type
        hotel_booking.room_count = room_count
        hotel_booking.check_in = request_booking.check_in
        hotel_booking.check_out = request_booking.check_out
        hotel_booking.occupancy = str(request_booking.occupancy) if request_booking.occupancy else ""
        hotel_booking.adult_count = request_booking.adult_count
        hotel_booking.child_count = request_booking.child_count
        hotel_booking.booking_status = "pending"
        hotel_booking.payment_status = "payment_pending"
        hotel_booking.total_amount = total_amount
        hotel_booking.tax = tax_amount
        hotel_booking.currency = currency

        hotel_booking.insert(ignore_permissions=True)

        # Create Booking Payments record
        booking_payment = frappe.new_doc("Booking Payments")
        booking_payment.booking_id = hotel_booking.name
        booking_payment.request_booking_link = request_booking.name
        booking_payment.employee = request_booking.employee
        booking_payment.company = request_booking.company
        booking_payment.agent = request_booking.agent
        booking_payment.hotel_id = hotel_id
        booking_payment.hotel_name = hotel_name
        booking_payment.room_id = room_id
        booking_payment.room_type = room_type
        booking_payment.room_count = room_count
        booking_payment.check_in = request_booking.check_in
        booking_payment.check_out = request_booking.check_out
        booking_payment.occupancy = str(request_booking.occupancy) if request_booking.occupancy else ""
        booking_payment.adult_count = request_booking.adult_count
        booking_payment.child_count = request_booking.child_count
        booking_payment.booking_status = "pending"
        booking_payment.payment_status = "payment_pending"
        booking_payment.total_amount = total_amount
        booking_payment.tax = tax_amount
        booking_payment.currency = currency

        booking_payment.insert(ignore_permissions=True)

        # Update hotel booking with payment link
        hotel_booking.payment_link = booking_payment.name
        hotel_booking.save(ignore_permissions=True)

        # Update request booking status to req_closed
        frappe.db.set_value(
            "Request Booking Details",
            request_booking.name,
            "request_status",
            "req_closed"
        )

        # Update ONLY approved cart hotel rooms to link with hotel booking
        for room in cart_hotel.rooms:
            if room.room_id in selected_room_ids and room.status == "approved":
                room.hotel_bookings = hotel_booking.name
                room.request_booking_link = request_booking.name
        cart_hotel.save(ignore_permissions=True)

        frappe.db.commit()

        return {
            "response": {
                "success": True,
                "message": "Booking created successfully",
                "data": {
                    "hotel_booking_id": hotel_booking.name,
                    "booking_id": hotel_booking.booking_id,
                    "request_booking_id": request_booking_id,
                    "payment_id": booking_payment.name,
                    "hotel_id": hotel_id,
                    "hotel_name": hotel_name,
                    "room_id": room_id,
                    "room_type": room_type,
                    "room_count": room_count,
                    "check_in": str(request_booking.check_in) if request_booking.check_in else "",
                    "check_out": str(request_booking.check_out) if request_booking.check_out else "",
                    "total_amount": total_amount,
                    "tax": tax_amount,
                    "currency": currency,
                    "booking_status": "pending",
                    "payment_status": "payment_pending",
                    "request_status": "req_closed"
                }
            }
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "create_booking API Error")
        return {
            "response": {
                "success": False,
                "error": str(e),
                "data": None
            }
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
                "response": {
                    "success": False,
                    "error": "clientReference is required",
                    "data": None
                }
            }

        if not isinstance(client_reference, str) or not client_reference.strip():
            return {
                "response": {
                    "success": False,
                    "error": "clientReference must be a non-empty string",
                    "data": None
                }
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
        remark = data.get("remark", "")

        # Validate bookingId (required)
        if not external_booking_id:
            return {
                "response": {
                    "success": False,
                    "error": "bookingId is required",
                    "data": None
                }
            }
        external_booking_id = str(external_booking_id).strip()

        # Validate hotelConfirmationNo (required)
        if not hotel_confirmation_no:
            return {
                "response": {
                    "success": False,
                    "error": "hotelConfirmationNo is required",
                    "data": None
                }
            }
        hotel_confirmation_no = str(hotel_confirmation_no).strip()

        # Validate status (required)
        if not status:
            return {
                "response": {
                    "success": False,
                    "error": "status is required",
                    "data": None
                }
            }

        valid_statuses = ["confirmed", "cancelled", "pending", "completed"]
        if status.lower() not in valid_statuses:
            return {
                "response": {
                    "success": False,
                    "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
                    "data": None
                }
            }

        # Validate hotel object (required)
        if not hotel_data or not isinstance(hotel_data, dict):
            return {
                "response": {
                    "success": False,
                    "error": "hotel object is required",
                    "data": None
                }
            }

        if not hotel_data.get("id"):
            return {
                "response": {
                    "success": False,
                    "error": "hotel.id is required",
                    "data": None
                }
            }

        # Validate totalPrice (must be numeric and positive)
        try:
            total_price = float(total_price) if total_price else 0
            if total_price < 0:
                return {
                    "response": {
                        "success": False,
                        "error": "totalPrice must be a positive number",
                        "data": None
                    }
                }
        except (ValueError, TypeError):
            return {
                "response": {
                    "success": False,
                    "error": "totalPrice must be a valid number",
                    "data": None
                }
            }

        # Validate numOfRooms (must be positive integer)
        try:
            num_of_rooms = int(num_of_rooms) if num_of_rooms else 0
            if num_of_rooms < 0:
                return {
                    "response": {
                        "success": False,
                        "error": "numOfRooms must be a positive integer",
                        "data": None
                    }
                }
        except (ValueError, TypeError):
            return {
                "response": {
                    "success": False,
                    "error": "numOfRooms must be a valid integer",
                    "data": None
                }
            }

        # Validate contact object if provided
        if contact and not isinstance(contact, dict):
            return {
                "response": {
                    "success": False,
                    "error": "contact must be an object",
                    "data": None
                }
            }

        # Validate guestList if provided
        if guest_list and not isinstance(guest_list, list):
            return {
                "response": {
                    "success": False,
                    "error": "guestList must be an array",
                    "data": None
                }
            }

        # Validate roomList if provided
        if room_list and not isinstance(room_list, list):
            return {
                "response": {
                    "success": False,
                    "error": "roomList must be an array",
                    "data": None
                }
            }

        # Validate cancellation if provided
        if cancellation and not isinstance(cancellation, list):
            return {
                "response": {
                    "success": False,
                    "error": "cancellation must be an array",
                    "data": None
                }
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
                "response": {
                    "success": False,
                    "error": f"Duplicate booking: external bookingId '{external_booking_id}' already exists for booking '{duplicate_by_external_id.booking_id}'",
                    "data": None
                }
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
                "response": {
                    "success": False,
                    "error": f"Duplicate booking: hotelConfirmationNo '{hotel_confirmation_no}' already exists for booking '{duplicate_by_confirmation.booking_id}'",
                    "data": None
                }
            }

        # ==================== VALIDATION END ====================

        # Fetch the request booking details using clientReference
        request_booking = frappe.db.get_value(
            "Request Booking Details",
            {"request_booking_id": client_reference},
            [
                "name", "request_booking_id", "employee", "company", "agent",
                "check_in", "check_out", "occupancy", "adult_count", "child_count",
                "room_count", "request_status"
            ],
            as_dict=True
        )

        if not request_booking:
            return {
                "response": {
                    "success": False,
                    "error": f"Request booking not found for clientReference: {client_reference}",
                    "data": None
                }
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
                    "response": {
                        "success": False,
                        "error": f"Booking already confirmed with same details. Hotel Booking: {existing_booking.name}, External ID: {external_booking_id}",
                        "data": {
                            "hotel_booking_id": existing_booking.name,
                            "external_booking_id": existing_booking.external_booking_id,
                            "hotel_confirmation_no": existing_booking.hotel_confirmation_no
                        }
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
                    "response": {
                        "success": False,
                        "error": f"Invalid checkIn date format: '{check_in}'. Expected format: YYYY-MM-DD",
                        "data": None
                    }
                }

        if parsed_check_out:
            try:
                check_out_date = datetime.strptime(parsed_check_out, "%Y-%m-%d")
            except ValueError:
                return {
                    "response": {
                        "success": False,
                        "error": f"Invalid checkOut date format: '{check_out}'. Expected format: YYYY-MM-DD",
                        "data": None
                    }
                }

        # Validate checkIn is before checkOut
        if parsed_check_in and parsed_check_out:
            if check_in_date >= check_out_date:
                return {
                    "response": {
                        "success": False,
                        "error": "checkIn date must be before checkOut date",
                        "data": None
                    }
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
                hotel_booking.contact_first_name = contact.get("firstName", "")
                hotel_booking.contact_last_name = contact.get("lastName", "")
                hotel_booking.contact_phone = contact.get("phone", "")
                hotel_booking.contact_email = contact.get("email", "")

            # Store guest list, room details, and cancellation policy as JSON
            hotel_booking.guest_list = json.dumps(guest_list) if guest_list else None
            hotel_booking.room_details = json.dumps(room_list) if room_list else None
            hotel_booking.cancellation_policy = json.dumps(cancellation) if cancellation else None
            hotel_booking.remark = remark

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

            # Update Booking Payments if linked
            if hotel_booking.payment_link:
                booking_payment = frappe.get_doc("Booking Payments", hotel_booking.payment_link)
                booking_payment.booking_status = mapped_booking_status
                if total_price:
                    booking_payment.total_amount = total_price
                if currency:
                    booking_payment.currency = currency
                booking_payment.save(ignore_permissions=True)

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
            hotel_booking.payment_status = "payment_pending"

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
                hotel_booking.contact_first_name = contact.get("firstName", "")
                hotel_booking.contact_last_name = contact.get("lastName", "")
                hotel_booking.contact_phone = contact.get("phone", "")
                hotel_booking.contact_email = contact.get("email", "")

            # JSON fields
            hotel_booking.guest_list = json.dumps(guest_list) if guest_list else None
            hotel_booking.room_details = json.dumps(room_list) if room_list else None
            hotel_booking.cancellation_policy = json.dumps(cancellation) if cancellation else None
            hotel_booking.remark = remark

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

            # Create Booking Payments record
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

            # Update hotel booking with payment link
            hotel_booking.payment_link = booking_payment.name
            hotel_booking.save(ignore_permissions=True)

        frappe.db.commit()

        return {
            "response": {
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
                    "contact": {
                        "firstName": hotel_booking.contact_first_name,
                        "lastName": hotel_booking.contact_last_name,
                        "phone": hotel_booking.contact_phone,
                        "email": hotel_booking.contact_email
                    }
                }
            }
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "confirm_booking API Error")
        return {
            "response": {
                "success": False,
                "error": str(e),
                "data": None
            }
        }


@frappe.whitelist(allow_guest=False)
def get_all_bookings(employee=None, company=None, booking_status=None, booking_id=None):
    """
    API to fetch all hotel bookings with optional filters.
    Returns all details stored via confirm_booking API.

    Args:
        employee (str, optional): Filter by employee ID
        company (str, optional): Filter by company
        booking_status (str, optional): Filter by booking status (confirmed, cancelled, pending, completed)
        booking_id (str, optional): Filter by specific booking_id (clientReference)

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

        bookings = frappe.get_all(
            "Hotel Bookings",
            filters=filters,
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
                "total_amount",
                "tax",
                "currency",
                "payment_link",
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
            "response": {
                "success": True,
                "message": "Bookings fetched successfully",
                "data": {
                    "bookings": bookings,
                    "total_count": len(bookings)
                }
            }
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "get_all_bookings API Error")
        return {
            "response": {
                "success": False,
                "error": str(e),
                "data": None
            }
        }
