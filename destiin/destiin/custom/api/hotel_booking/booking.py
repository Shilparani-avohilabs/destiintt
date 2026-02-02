import frappe
import json
import requests
from datetime import datetime
from destiin.destiin.custom.api.request_booking.request import update_request_status_from_rooms


PRICE_COMPARISON_API_URL = "http://16.112.56.253/ops/v1/priceComparison"


def call_price_comparison_api(hotel_booking):
    """
    Call the price comparison API and store the prices from different sites.

    Args:
        hotel_booking: The Hotel Booking document
    """
    try:
        # Try to get room_rate_id from room_details
        room_rate_id = ""
        room_id = hotel_booking.room_id or ""
        frappe.log_error(f" call_price_comparison_api Room ID: {room_id}")

        if hotel_booking.room_details:
            try:
                room_list = json.loads(hotel_booking.room_details)
                if room_list and len(room_list) > 0:
                    first_room = room_list[0]
                    room_rate_id = str(first_room.get("rateId", first_room.get("roomRateId", "")))
                    if not room_id:
                        room_id = str(first_room.get("roomId", ""))
            except (json.JSONDecodeError, TypeError):
                pass

        payload = {
            "hotel_name": hotel_booking.hotel_name or "",
            "city": hotel_booking.city_code or "",
            "check_in": str(hotel_booking.check_in) if hotel_booking.check_in else "",
            "check_out": str(hotel_booking.check_out) if hotel_booking.check_out else "",
            "adults": hotel_booking.adult_count or 2,
            "children": hotel_booking.child_count or 0,
            "rooms": hotel_booking.room_count or 1,
            "room_type": hotel_booking.room_type or "",
            "hotel_id": hotel_booking.hotel_id or "",
            "room_id": room_id,
            "room_rate_id": room_rate_id,
            "sites": ["makemytrip", "agoda", "booking_com"]
        }

        response = requests.post(
            PRICE_COMPARISON_API_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        frappe.log_error(f" call_price_comparison_api Response: {response}")

        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])

            for result in results:
                site = result.get("site", "")
                if result.get("success"):
                    price_breakdown = result.get("price_breakdown", {})
                    total_with_tax = price_breakdown.get("total_with_tax")

                    if site == "makemytrip" and total_with_tax is not None:
                        hotel_booking.make_my_trip = total_with_tax
                    elif site == "agoda" and total_with_tax is not None:
                        hotel_booking.agoda = total_with_tax
                    elif site == "booking_com" and total_with_tax is not None:
                        hotel_booking.booking_com = total_with_tax

            hotel_booking.save(ignore_permissions=True)

    except Exception as e:
        frappe.log_error(f"Price comparison API error: {str(e)}", "Price Comparison API Error")


@frappe.whitelist(allow_guest=False)
def confirm_booking(**kwargs):
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
                    "success": False,
                    "error": "clientReference is required"
            }

        if not isinstance(client_reference, str) or not client_reference.strip():
            return {
                    "success": False,
                    "error": "clientReference must be a non-empty string"
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
                    "success": False,
                    "error": "bookingId is required"
            }
        external_booking_id = str(external_booking_id).strip()

        # Validate hotelConfirmationNo (required)
        if not hotel_confirmation_no:
            return {
                    "success": False,
                    "error": "hotelConfirmationNo is required"
            }
        hotel_confirmation_no = str(hotel_confirmation_no).strip()

        # Validate status (required)
        if not status:
            return {
                    "success": False,
                    "error": "status is required"
            }

        # Convert status to string if it's not already
        status = str(status) if status else ""

        valid_statuses = ["confirmed", "cancelled", "pending", "completed"]
        if status.lower() not in valid_statuses:
            return {
                    "success": False,
                    "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            }

        # Validate hotel object (required)
        if not hotel_data or not isinstance(hotel_data, dict):
            return {
                    "success": False,
                    "error": "hotel object is required"
            }

        if not hotel_data.get("id"):
            return {
                    "success": False,
                    "error": "hotel.id is required"
            }

        # Validate totalPrice (must be numeric and positive)
        try:
            total_price = float(total_price) if total_price else 0
            if total_price < 0:
                return {
                        "success": False,
                        "error": "totalPrice must be a positive number"
                }
        except (ValueError, TypeError):
            return {
                    "success": False,
                    "error": "totalPrice must be a valid number"
            }

        # Validate numOfRooms (must be positive integer)
        try:
            num_of_rooms = int(num_of_rooms) if num_of_rooms else 0
            if num_of_rooms < 0:
                return {
                        "success": False,
                        "error": "numOfRooms must be a positive integer"
                }
        except (ValueError, TypeError):
            return {
                    "success": False,
                    "error": "numOfRooms must be a valid integer"
            }

        # Validate contact object if provided
        if contact and not isinstance(contact, dict):
            return {
                    "success": False,
                    "error": "contact must be an object"
            }

        # Validate guestList if provided
        if guest_list and not isinstance(guest_list, list):
            return {
                    "success": False,
                    "error": "guestList must be an array"
            }

        # Validate roomList if provided
        if room_list and not isinstance(room_list, list):
            return {
                    "success": False,
                    "error": "roomList must be an array"
            }

        # Validate cancellation if provided
        if cancellation and not isinstance(cancellation, list):
            return {
                    "success": False,
                    "error": "cancellation must be an array"
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
                    "success": False,
                    "error": f"Duplicate booking: external bookingId '{external_booking_id}' already exists for booking '{duplicate_by_external_id.booking_id}'"
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
                    "success": False,
                    "error": f"Duplicate booking: hotelConfirmationNo '{hotel_confirmation_no}' already exists for booking '{duplicate_by_confirmation.booking_id}'"
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
                    "success": False,
                    "error": f"Request booking not found for clientReference: {client_reference}"
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
                        "success": False,
                        "error": f"Booking already confirmed with same details. Hotel Booking: {existing_booking.name}, External ID: {external_booking_id}",
                        "data": {
                            "hotel_booking_id": existing_booking.name,
                            "external_booking_id": existing_booking.external_booking_id,
                            "hotel_confirmation_no": existing_booking.hotel_confirmation_no
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
                        "success": False,
                        "error": f"Invalid checkIn date format: '{check_in}'. Expected format: YYYY-MM-DD"
                }

        if parsed_check_out:
            try:
                check_out_date = datetime.strptime(parsed_check_out, "%Y-%m-%d")
            except ValueError:
                return {
                        "success": False,
                        "error": f"Invalid checkOut date format: '{check_out}'. Expected format: YYYY-MM-DD"
                }

        # Validate checkIn is before checkOut
        if parsed_check_in and parsed_check_out:
            if check_in_date >= check_out_date:
                return {
                        "success": False,
                        "error": "checkIn date must be before checkOut date"
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

            # Update cart hotel room statuses based on booking status for existing booking
            cart_hotel_item_name = frappe.db.get_value(
                "Request Booking Details",
                request_booking.name,
                "cart_hotel_item"
            )

            if cart_hotel_item_name:
                cart_hotel = frappe.get_doc("Cart Hotel Item", cart_hotel_item_name)

                # Map booking status to room status
                room_status_map = {
                    "confirmed": "booking_success",
                    "cancelled": "booking_failure",
                    "pending": "payment_pending",
                    "completed": "booking_success"
                }
                new_room_status = room_status_map.get(mapped_booking_status, "payment_pending")

                # Update room statuses
                for room in cart_hotel.rooms:
                    if room.status in ["approved", "payment_pending"]:
                        room.status = new_room_status
                cart_hotel.save(ignore_permissions=True)

                # Update request booking status based on room statuses
                update_request_status_from_rooms(request_booking.name, cart_hotel_item_name)

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

            # Update request_booking status to req_closed
            frappe.db.set_value(
                "Request Booking Details",
                request_booking.name,
                "request_status",
                "req_closed"
            )

            # Find and link existing payments from request_booking_details to this booking
            existing_payments = frappe.get_all(
                "Booking Payments",
                filters={"request_booking_link": request_booking.name},
                fields=["name"]
            )

            # Update existing payments to link to the new Hotel Booking
            for payment in existing_payments:
                frappe.db.set_value(
                    "Booking Payments",
                    payment.name,
                    "booking_id",
                    hotel_booking.name
                )

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

        # Update cart hotel room statuses based on booking status
        cart_hotel_item_name = frappe.db.get_value(
            "Request Booking Details",
            request_booking.name,
            "cart_hotel_item"
        )

        if cart_hotel_item_name:
            cart_hotel = frappe.get_doc("Cart Hotel Item", cart_hotel_item_name)

            # Map booking status to room status
            room_status_map = {
                "confirmed": "booking_success",
                "cancelled": "booking_failure",
                "pending": "payment_pending",
                "completed": "booking_success"
            }
            new_room_status = room_status_map.get(mapped_booking_status, "payment_pending")

            # Update room statuses
            for room in cart_hotel.rooms:
                if room.status in ["approved", "payment_pending"]:
                    room.status = new_room_status
            cart_hotel.save(ignore_permissions=True)

            # Update request booking status based on room statuses
            update_request_status_from_rooms(request_booking.name, cart_hotel_item_name)

        # Call price comparison API to get prices from different sites
        call_price_comparison_api(hotel_booking)

        frappe.db.commit()

        return {
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
                    "make_my_trip": hotel_booking.make_my_trip,
                    "agoda": hotel_booking.agoda,
                    "booking_com": hotel_booking.booking_com,
                    "contact": {
                        "firstName": hotel_booking.contact_first_name,
                        "lastName": hotel_booking.contact_last_name,
                        "phone": hotel_booking.contact_phone,
                        "email": hotel_booking.contact_email
                    }
                }
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "confirm_booking API Error")
        return {
                "success": False,
                "error": str(e)
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
                    "success": False,
                    "error": "clientReference is required"
            }

        if not isinstance(client_reference, str) or not client_reference.strip():
            return {
                    "success": False,
                    "error": "clientReference must be a non-empty string"
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
                    "success": False,
                    "error": "bookingId is required"
            }
        external_booking_id = str(external_booking_id).strip()

        # Validate hotelConfirmationNo (required)
        # if not hotel_confirmation_no:
        #     return {
        #             "success": False,
        #             "error": "hotelConfirmationNo is required"
        #     }
        # hotel_confirmation_no = str(hotel_confirmation_no).strip()

        # Validate status (required)
        if not status:
            return {
                    "success": False,
                    "error": "status is required"
            }

        # Convert status to string if it's not already
        status = str(status) if status else ""

        valid_statuses = ["confirmed", "cancelled", "pending", "completed"]
        if status.lower() not in valid_statuses:
            return {
                    "success": False,
                    "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            }

        # Validate hotel object (required)
        if not hotel_data or not isinstance(hotel_data, dict):
            return {
                    "success": False,
                    "error": "hotel object is required"
            }

        if not hotel_data.get("id"):
            return {
                    "success": False,
                    "error": "hotel.id is required"
            }

        # Validate totalPrice (must be numeric and positive)
        try:
            total_price = float(total_price) if total_price else 0
            if total_price < 0:
                return {
                        "success": False,
                        "error": "totalPrice must be a positive number"
                }
        except (ValueError, TypeError):
            return {
                    "success": False,
                    "error": "totalPrice must be a valid number"
            }

        # Validate numOfRooms (must be positive integer)
        try:
            num_of_rooms = int(num_of_rooms) if num_of_rooms else 0
            if num_of_rooms < 0:
                return {
                        "success": False,
                        "error": "numOfRooms must be a positive integer"
                }
        except (ValueError, TypeError):
            return {
                    "success": False,
                    "error": "numOfRooms must be a valid integer"
            }

        # Validate contact object if provided
        if contact and not isinstance(contact, dict):
            return {
                    "success": False,
                    "error": "contact must be an object"
            }

        # Validate guestList if provided
        if guest_list and not isinstance(guest_list, list):
            return {
                    "success": False,
                    "error": "guestList must be an array"
            }

        # Validate roomList if provided
        if room_list and not isinstance(room_list, list):
            return {
                    "success": False,
                    "error": "roomList must be an array"
            }

        # Validate cancellation if provided
        if cancellation and not isinstance(cancellation, list):
            return {
                    "success": False,
                    "error": "cancellation must be an array"
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
                    "success": False,
                    "error": f"Duplicate booking: external bookingId '{external_booking_id}' already exists for booking '{duplicate_by_external_id.booking_id}'"
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
                    "success": False,
                    "error": f"Duplicate booking: hotelConfirmationNo '{hotel_confirmation_no}' already exists for booking '{duplicate_by_confirmation.booking_id}'"
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
                    "success": False,
                    "error": f"Request booking not found for clientReference: {client_reference}"
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
                        "success": False,
                        "error": f"Booking already confirmed with same details. Hotel Booking: {existing_booking.name}, External ID: {external_booking_id}",
                        "data": {
                            "hotel_booking_id": existing_booking.name,
                            "external_booking_id": existing_booking.external_booking_id,
                            "hotel_confirmation_no": existing_booking.hotel_confirmation_no
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
                        "success": False,
                        "error": f"Invalid checkIn date format: '{check_in}'. Expected format: YYYY-MM-DD"
                }

        if parsed_check_out:
            try:
                check_out_date = datetime.strptime(parsed_check_out, "%Y-%m-%d")
            except ValueError:
                return {
                        "success": False,
                        "error": f"Invalid checkOut date format: '{check_out}'. Expected format: YYYY-MM-DD"
                }

        # Validate checkIn is before checkOut
        if parsed_check_in and parsed_check_out:
            if check_in_date >= check_out_date:
                return {
                        "success": False,
                        "error": "checkIn date must be before checkOut date"
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

            # Update cart hotel room statuses based on booking status for existing booking
            cart_hotel_item_name = frappe.db.get_value(
                "Request Booking Details",
                request_booking.name,
                "cart_hotel_item"
            )

            if cart_hotel_item_name:
                cart_hotel = frappe.get_doc("Cart Hotel Item", cart_hotel_item_name)

                # Map booking status to room status
                room_status_map = {
                    "confirmed": "booking_success",
                    "cancelled": "booking_failure",
                    "pending": "payment_pending",
                    "completed": "booking_success"
                }
                new_room_status = room_status_map.get(mapped_booking_status, "payment_pending")

                # Update room statuses
                for room in cart_hotel.rooms:
                    if room.status in ["approved", "payment_pending"]:
                        room.status = new_room_status
                cart_hotel.save(ignore_permissions=True)

                # Update request booking status based on room statuses
                update_request_status_from_rooms(request_booking.name, cart_hotel_item_name)

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

            # Update request_booking status to req_closed
            frappe.db.set_value(
                "Request Booking Details",
                request_booking.name,
                "request_status",
                "req_closed"
            )

            # Find and link existing payments from request_booking_details to this booking
            existing_payments = frappe.get_all(
                "Booking Payments",
                filters={"request_booking_link": request_booking.name},
                fields=["name"]
            )

            # Update existing payments to link to the new Hotel Booking
            for payment in existing_payments:
                frappe.db.set_value(
                    "Booking Payments",
                    payment.name,
                    "booking_id",
                    hotel_booking.name
                )

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

        # Update cart hotel room statuses based on booking status
        cart_hotel_item_name = frappe.db.get_value(
            "Request Booking Details",
            request_booking.name,
            "cart_hotel_item"
        )

        if cart_hotel_item_name:
            cart_hotel = frappe.get_doc("Cart Hotel Item", cart_hotel_item_name)

            # Map booking status to room status
            room_status_map = {
                "confirmed": "booking_success",
                "cancelled": "booking_failure",
                "pending": "payment_pending",
                "completed": "booking_success"
            }
            new_room_status = room_status_map.get(mapped_booking_status, "payment_pending")

            # Update room statuses
            for room in cart_hotel.rooms:
                if room.status in ["approved", "payment_pending"]:
                    room.status = new_room_status
            cart_hotel.save(ignore_permissions=True)

            # Update request booking status based on room statuses
            update_request_status_from_rooms(request_booking.name, cart_hotel_item_name)

        # Call price comparison API to get prices from different sites
        call_price_comparison_api(hotel_booking)

        frappe.db.commit()

        return {
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
                    "make_my_trip": hotel_booking.make_my_trip,
                    "agoda": hotel_booking.agoda,
                    "booking_com": hotel_booking.booking_com,
                    "contact": {
                        "firstName": hotel_booking.contact_first_name,
                        "lastName": hotel_booking.contact_last_name,
                        "phone": hotel_booking.contact_phone,
                        "email": hotel_booking.contact_email
                    }
                }
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "confirm_booking API Error")
        return {
                "success": False,
                "error": str(e)
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
            ignore_permissions=True,
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
                "success": True,
                "message": "Bookings fetched successfully",
                "data": {
                    "bookings": bookings,
                    "total_count": len(bookings)
                }
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "get_all_bookings API Error")
        return {
                "success": False,
                "error": str(e)
        }


@frappe.whitelist(allow_guest=False)
def update_booking(
    booking_id,
    booking_status=None,
    payment_status=None,
    external_booking_id=None,
    hotel_confirmation_no=None,
    hotel_id=None,
    hotel_name=None,
    city_code=None,
    room_id=None,
    room_type=None,
    room_count=None,
    check_in=None,
    check_out=None,
    occupancy=None,
    adult_count=None,
    child_count=None,
    total_amount=None,
    tax=None,
    currency=None,
    contact_first_name=None,
    contact_last_name=None,
    contact_phone=None,
    contact_email=None,
    guest_list=None,
    room_details=None,
    cancellation_policy=None,
    remark=None,
    make_my_trip=None,
    booking_com=None,
    agoda=None
):
    """
    API to update an existing hotel booking.

    Args:
        booking_id (str): Booking ID to identify the booking (required)
        booking_status (str, optional): Booking status (pending, confirmed, cancelled, completed)
        payment_status (str, optional): Payment status
        external_booking_id (str, optional): External booking ID
        hotel_confirmation_no (str, optional): Hotel confirmation number
        hotel_id (str, optional): Hotel ID
        hotel_name (str, optional): Hotel name
        city_code (str, optional): City code
        room_id (str, optional): Room ID
        room_type (str, optional): Room type
        room_count (int, optional): Number of rooms
        check_in (str, optional): Check-in date
        check_out (str, optional): Check-out date
        occupancy (int, optional): Occupancy
        adult_count (int, optional): Number of adults
        child_count (int, optional): Number of children
        total_amount (float, optional): Total amount
        tax (float, optional): Tax amount
        currency (str, optional): Currency code
        contact_first_name (str, optional): Contact first name
        contact_last_name (str, optional): Contact last name
        contact_phone (str, optional): Contact phone
        contact_email (str, optional): Contact email
        guest_list (list, optional): List of guests
        room_details (list, optional): Room details
        cancellation_policy (list, optional): Cancellation policy
        remark (str, optional): Remarks
        make_my_trip (str, optional): Make My Trip reference
        booking_com (str, optional): Booking.com reference
        agoda (str, optional): Agoda reference

    Returns:
        dict: Response with success status and updated booking data
    """
    try:
        # Find booking by booking_id
        booking_name = frappe.db.get_value("Hotel Bookings", {"booking_id": booking_id}, "name")

        if not booking_name:
            return {
                "success": False,
                "message": f"Booking with ID '{booking_id}' not found"
            }

        # Get the booking document
        booking_doc = frappe.get_doc("Hotel Bookings", booking_name)

        # Update fields if provided
        if booking_status is not None:
            booking_doc.booking_status = booking_status

        if payment_status is not None:
            booking_doc.payment_status = payment_status

        if external_booking_id is not None:
            booking_doc.external_booking_id = external_booking_id

        if hotel_confirmation_no is not None:
            booking_doc.hotel_confirmation_no = hotel_confirmation_no

        if hotel_id is not None:
            booking_doc.hotel_id = hotel_id

        if hotel_name is not None:
            booking_doc.hotel_name = hotel_name

        if city_code is not None:
            booking_doc.city_code = city_code

        if room_id is not None:
            booking_doc.room_id = room_id

        if room_type is not None:
            booking_doc.room_type = room_type

        if room_count is not None:
            booking_doc.room_count = int(room_count)

        if check_in is not None:
            booking_doc.check_in = check_in

        if check_out is not None:
            booking_doc.check_out = check_out

        if occupancy is not None:
            booking_doc.occupancy = occupancy

        if adult_count is not None:
            booking_doc.adult_count = int(adult_count)

        if child_count is not None:
            booking_doc.child_count = child_count

        if total_amount is not None:
            booking_doc.total_amount = total_amount

        if tax is not None:
            booking_doc.tax = tax

        if currency is not None:
            booking_doc.currency = currency

        if contact_first_name is not None:
            booking_doc.contact_first_name = contact_first_name

        if contact_last_name is not None:
            booking_doc.contact_last_name = contact_last_name

        if contact_phone is not None:
            booking_doc.contact_phone = contact_phone

        if contact_email is not None:
            booking_doc.contact_email = contact_email

        if guest_list is not None:
            if isinstance(guest_list, str):
                booking_doc.guest_list = guest_list
            else:
                booking_doc.guest_list = json.dumps(guest_list)

        if room_details is not None:
            if isinstance(room_details, str):
                booking_doc.room_details = room_details
            else:
                booking_doc.room_details = json.dumps(room_details)

        if cancellation_policy is not None:
            if isinstance(cancellation_policy, str):
                booking_doc.cancellation_policy = cancellation_policy
            else:
                booking_doc.cancellation_policy = json.dumps(cancellation_policy)

        if remark is not None:
            booking_doc.remark = remark

        if make_my_trip is not None:
            booking_doc.make_my_trip = make_my_trip

        if booking_com is not None:
            booking_doc.booking_com = booking_com

        if agoda is not None:
            booking_doc.agoda = agoda

        # Save the updated booking
        booking_doc.save(ignore_permissions=True)
        frappe.db.commit()

        return {
            "success": True,
            "message": "Booking updated successfully",
            "data": {
                "name": booking_doc.name,
                "booking_id": booking_doc.booking_id,
                "booking_status": booking_doc.booking_status,
                "payment_status": booking_doc.payment_status,
                "modified": str(booking_doc.modified)
            }
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "update_booking API Error")
        return {
            "success": False,
            "error": str(e)
        }


@frappe.whitelist(allow_guest=False)
def cancel_booking(**kwargs):
    """
    API to cancel a hotel booking.

    This API cancels an existing hotel booking, updates the booking status to 'cancelled',
    and creates a cancel record in the Cancel Booking doctype.

    Request payload structure:
    {
        "booking_id": "request_booking_id",
        "cancellation_reason": "User requested cancellation",
        "status": "Pending",  (optional: Pending, Approved, Rejected, Processed)
        "refund_status": "Not Initiated",  (optional: Not Initiated, Initiated, Processing, Completed, Failed, Not Applicable)
        "refund_amount": 100.00,  (optional)
        "refund_date": "2026-02-02",  (optional)
        "remarks": "Additional details about the cancellation"  (optional)
    }

    Args:
        booking_id (str): The booking ID to cancel (required)
        cancellation_reason (str, optional): Reason for cancellation
        status (str, optional): Cancel status (Pending, Approved, Rejected, Processed)
        refund_status (str, optional): Refund status
        refund_amount (float, optional): Refund amount
        refund_date (str, optional): Refund date
        remarks (str, optional): Additional remarks

    Returns:
        dict: Response with success status and cancellation details
    """
    try:
        # Extract data from kwargs
        data = kwargs

        # ==================== VALIDATION START ====================

        # Validate booking_id (required)
        booking_id = data.get("booking_id")
        if not booking_id:
            return {
                "success": False,
                "error": "booking_id is required"
            }

        if not isinstance(booking_id, str) or not booking_id.strip():
            return {
                "success": False,
                "error": "booking_id must be a non-empty string"
            }
        booking_id = booking_id.strip()

        # Extract optional parameters
        cancellation_reason = data.get("cancellation_reason", "")
        cancel_status = data.get("status", "Pending")
        refund_status = data.get("refund_status", "Not Initiated")
        refund_amount = data.get("refund_amount")
        refund_date = data.get("refund_date")
        remarks = data.get("remarks", "")

        # Validate cancel_status
        valid_cancel_statuses = ["Pending", "Approved", "Rejected", "Processed"]
        if cancel_status and cancel_status not in valid_cancel_statuses:
            return {
                "success": False,
                "error": f"Invalid status. Must be one of: {', '.join(valid_cancel_statuses)}"
            }

        # Validate refund_status
        valid_refund_statuses = ["Not Initiated", "Initiated", "Processing", "Completed", "Failed", "Not Applicable"]
        if refund_status and refund_status not in valid_refund_statuses:
            return {
                "success": False,
                "error": f"Invalid refund_status. Must be one of: {', '.join(valid_refund_statuses)}"
            }

        # Validate refund_amount if provided
        if refund_amount is not None:
            try:
                refund_amount = float(refund_amount)
                if refund_amount < 0:
                    return {
                        "success": False,
                        "error": "refund_amount must be a positive number"
                    }
            except (ValueError, TypeError):
                return {
                    "success": False,
                    "error": "refund_amount must be a valid number"
                }

        # Validate refund_date format if provided
        if refund_date:
            try:
                datetime.strptime(refund_date, "%Y-%m-%d")
            except ValueError:
                return {
                    "success": False,
                    "error": f"Invalid refund_date format: '{refund_date}'. Expected format: YYYY-MM-DD"
                }

        # ==================== VALIDATION END ====================

        # Check if Hotel Booking exists
        hotel_booking = frappe.db.get_value(
            "Hotel Bookings",
            {"external_booking_id": booking_id},
            [
                "name", "booking_id", "booking_status", "employee", "company",
                "hotel_id", "hotel_name", "total_amount", "currency"
            ],
            as_dict=True
        )

        if not hotel_booking:
            return {
                "success": False,
                "error": f"Hotel booking not found with booking_id: {booking_id}"
            }

        # Check if a cancel booking record already exists
        existing_cancel = frappe.db.get_value(
            "Cancel Booking",
            {"hotel_booking": hotel_booking.name},
            "name"
        )

        if existing_cancel:
            # Update existing Cancel Booking record
            cancel_booking = frappe.get_doc("Cancel Booking", existing_cancel)

            # Update status fields
            if cancel_status:
                cancel_booking.status = cancel_status
            if refund_status:
                cancel_booking.refund_status = refund_status

            # Update cancellation reason if provided
            if cancellation_reason:
                cancel_booking.cancellation_reason = cancellation_reason

            # Update refund details
            if refund_amount is not None:
                cancel_booking.refund_amount = refund_amount

            if refund_date:
                cancel_booking.refund_date = refund_date

            # Update remarks - combine old and new if both exist
            remarks_list = []

            # Keep existing remarks if any
            if cancel_booking.remarks:
                remarks_list.append(f"Previous Remarks:\n{cancel_booking.remarks}")

            # Add new remarks
            if remarks:
                remarks_list.append(f"Updated Remarks:\n{remarks}")

            # Add any additional fields that were passed but not explicitly handled
            extra_fields = {k: v for k, v in data.items() if k not in [
                "booking_id", "cancellation_reason", "status", "refund_status",
                "refund_amount", "refund_date", "remarks"
            ]}

            if extra_fields:
                remarks_list.append(f"Additional Details:\n{json.dumps(extra_fields, indent=2)}")

            if remarks_list:
                cancel_booking.remarks = "\n\n".join(remarks_list)

            cancel_booking.save(ignore_permissions=True)

            action_message = "Cancel booking record updated successfully"
        else:
            # Update Hotel Booking status to cancelled if not already
            if hotel_booking.booking_status != "cancelled":
                booking_doc = frappe.get_doc("Hotel Bookings", hotel_booking.name)
                booking_doc.booking_status = "cancelled"
                booking_doc.save(ignore_permissions=True)

            # Create new Cancel Booking record
            cancel_booking = frappe.new_doc("Cancel Booking")
            cancel_booking.hotel_booking = hotel_booking.name
            cancel_booking.employee = hotel_booking.employee
            cancel_booking.company = hotel_booking.company
            cancel_booking.cancellation_date = datetime.now().strftime("%Y-%m-%d")
            cancel_booking.status = cancel_status or "Pending"
            cancel_booking.refund_status = refund_status or "Not Initiated"

            if cancellation_reason:
                cancel_booking.cancellation_reason = cancellation_reason

            if refund_amount is not None:
                cancel_booking.refund_amount = refund_amount

            if refund_date:
                cancel_booking.refund_date = refund_date

            # Combine any extra details into remarks
            remarks_list = []
            if remarks:
                remarks_list.append(remarks)

            # Add any additional fields that were passed but not explicitly handled
            extra_fields = {k: v for k, v in data.items() if k not in [
                "booking_id", "cancellation_reason", "status", "refund_status",
                "refund_amount", "refund_date", "remarks"
            ]}

            if extra_fields:
                remarks_list.append(f"Additional Details: {json.dumps(extra_fields, indent=2)}")

            if remarks_list:
                cancel_booking.remarks = "\n\n".join(remarks_list)

            cancel_booking.insert(ignore_permissions=True)

            action_message = "Booking cancelled successfully"

        frappe.db.commit()

        return {
            "success": True,
            "message": action_message,
            "data": {
                "cancel_booking_id": cancel_booking.name,
                "hotel_booking_id": hotel_booking.name,
                "booking_id": booking_id,
                "booking_status": "cancelled",
                "cancellation_date": cancel_booking.cancellation_date,
                "status": cancel_booking.status,
                "refund_status": cancel_booking.refund_status,
                "refund_amount": cancel_booking.refund_amount,
                "refund_date": str(cancel_booking.refund_date) if cancel_booking.refund_date else None,
                "cancellation_reason": cancel_booking.cancellation_reason,
                "remarks": cancel_booking.remarks
            }
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "cancel_booking API Error")
        return {
            "success": False,
            "error": str(e)
        }
