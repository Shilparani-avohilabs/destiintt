import frappe
import json


@frappe.whitelist(allow_guest=False)
def create_booking(request_booking_id, employee, selected_items):
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
