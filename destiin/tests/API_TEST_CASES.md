# API Test Cases - Booking and Payment APIs

This document contains comprehensive test cases for all Booking and Payment APIs including positive and negative scenarios.

---

## Table of Contents

1. [Confirm Booking API](#1-confirm-booking-api)
2. [Create Booking API](#2-create-booking-api)
3. [Get All Bookings API](#3-get-all-bookings-api)
4. [Store Request Booking API](#4-store-request-booking-api)
5. [Get All Request Bookings API](#5-get-all-request-bookings-api)
6. [Send For Approval API](#6-send-for-approval-api)
7. [Approve Booking API](#7-approve-booking-api)
8. [Decline Booking API](#8-decline-booking-api)
9. [Update Request Booking API](#9-update-request-booking-api)
10. [Create Payment URL API](#10-create-payment-url-api)
11. [Payment Callback API](#11-payment-callback-api)

---

## 1. Confirm Booking API

**Endpoint:** `POST /api/method/destiin.custom.api.hotel_booking.booking.confirm_booking`

### Positive Test Cases

| TC ID | Test Case | Request Body | Expected Result |
|-------|-----------|--------------|-----------------|
| CB_P01 | Valid booking confirmation with all required fields | `{"clientReference": "REQ-001", "bookingId": "BK-001", "hotelConfirmationNo": "HC-001", "status": "confirmed", "hotel": {"id": "H001", "name": "Test Hotel", "cityCode": "NYC"}, "checkIn": "2025-03-01", "checkOut": "2025-03-05", "totalPrice": 500, "currency": "USD", "numOfRooms": 2}` | Success: 200, booking created |
| CB_P02 | Valid booking with guest list | `{"clientReference": "REQ-002", "bookingId": "BK-002", "hotelConfirmationNo": "HC-002", "status": "confirmed", "hotel": {"id": "H001"}, "checkIn": "2025-03-01", "checkOut": "2025-03-05", "totalPrice": 500, "numOfRooms": 1, "guestList": [{"firstName": "John", "lastName": "Doe"}]}` | Success: 200, booking created with guest list |
| CB_P03 | Valid booking with room list | `{"clientReference": "REQ-003", "bookingId": "BK-003", "hotelConfirmationNo": "HC-003", "status": "pending", "hotel": {"id": "H001"}, "checkIn": "2025-03-01", "checkOut": "2025-03-05", "totalPrice": 300, "numOfRooms": 1, "roomList": [{"roomId": "R001", "roomName": "Deluxe"}]}` | Success: 200, booking created with room details |
| CB_P04 | Valid booking with contact info | `{"clientReference": "REQ-004", "bookingId": "BK-004", "hotelConfirmationNo": "HC-004", "status": "confirmed", "hotel": {"id": "H001"}, "checkIn": "2025-03-01", "checkOut": "2025-03-05", "totalPrice": 400, "numOfRooms": 1, "contact": {"firstName": "Jane", "lastName": "Doe", "phone": "1234567890", "email": "jane@test.com"}}` | Success: 200, booking created with contact |
| CB_P05 | Valid booking with cancellation policy | `{"clientReference": "REQ-005", "bookingId": "BK-005", "hotelConfirmationNo": "HC-005", "status": "confirmed", "hotel": {"id": "H001"}, "checkIn": "2025-03-01", "checkOut": "2025-03-05", "totalPrice": 600, "numOfRooms": 1, "cancellation": [{"deadline": "2025-02-28", "penalty": 100}]}` | Success: 200, booking created with cancellation policy |
| CB_P06 | Valid booking with status "cancelled" | `{"clientReference": "REQ-006", "bookingId": "BK-006", "hotelConfirmationNo": "HC-006", "status": "cancelled", "hotel": {"id": "H001"}, "checkIn": "2025-03-01", "checkOut": "2025-03-05", "totalPrice": 0, "numOfRooms": 1}` | Success: 200, booking created with cancelled status |
| CB_P07 | Valid booking with status "completed" | `{"clientReference": "REQ-007", "bookingId": "BK-007", "hotelConfirmationNo": "HC-007", "status": "completed", "hotel": {"id": "H001"}, "checkIn": "2025-02-01", "checkOut": "2025-02-05", "totalPrice": 800, "numOfRooms": 2}` | Success: 200, booking created with completed status |
| CB_P08 | Update existing booking (same clientReference) | `{"clientReference": "REQ-001", "bookingId": "BK-001-UPD", "hotelConfirmationNo": "HC-001-UPD", "status": "confirmed", "hotel": {"id": "H001"}, "checkIn": "2025-03-01", "checkOut": "2025-03-05", "totalPrice": 550, "numOfRooms": 2}` | Success: 200, existing booking updated |

### Negative Test Cases

| TC ID | Test Case | Request Body | Expected Result |
|-------|-----------|--------------|-----------------|
| CB_N01 | Missing clientReference | `{"bookingId": "BK-N01", "hotelConfirmationNo": "HC-N01", "status": "confirmed", "hotel": {"id": "H001"}, "checkIn": "2025-03-01", "checkOut": "2025-03-05", "totalPrice": 500, "numOfRooms": 1}` | Error: 400, "clientReference is required" |
| CB_N02 | Empty clientReference | `{"clientReference": "", "bookingId": "BK-N02", ...}` | Error: 400, "clientReference cannot be empty" |
| CB_N03 | Missing bookingId | `{"clientReference": "REQ-N03", "hotelConfirmationNo": "HC-N03", "status": "confirmed", "hotel": {"id": "H001"}, "checkIn": "2025-03-01", "checkOut": "2025-03-05", "totalPrice": 500, "numOfRooms": 1}` | Error: 400, "bookingId is required" |
| CB_N04 | Missing hotelConfirmationNo | `{"clientReference": "REQ-N04", "bookingId": "BK-N04", "status": "confirmed", "hotel": {"id": "H001"}, "checkIn": "2025-03-01", "checkOut": "2025-03-05", "totalPrice": 500, "numOfRooms": 1}` | Error: 400, "hotelConfirmationNo is required" |
| CB_N05 | Missing status | `{"clientReference": "REQ-N05", "bookingId": "BK-N05", "hotelConfirmationNo": "HC-N05", "hotel": {"id": "H001"}, "checkIn": "2025-03-01", "checkOut": "2025-03-05", "totalPrice": 500, "numOfRooms": 1}` | Error: 400, "status is required" |
| CB_N06 | Invalid status value | `{"clientReference": "REQ-N06", "bookingId": "BK-N06", "hotelConfirmationNo": "HC-N06", "status": "invalid_status", "hotel": {"id": "H001"}, "checkIn": "2025-03-01", "checkOut": "2025-03-05", "totalPrice": 500, "numOfRooms": 1}` | Error: 400, "Invalid status. Must be one of: confirmed, cancelled, pending, completed" |
| CB_N07 | Missing hotel object | `{"clientReference": "REQ-N07", "bookingId": "BK-N07", "hotelConfirmationNo": "HC-N07", "status": "confirmed", "checkIn": "2025-03-01", "checkOut": "2025-03-05", "totalPrice": 500, "numOfRooms": 1}` | Error: 400, "hotel is required" |
| CB_N08 | Missing hotel.id | `{"clientReference": "REQ-N08", "bookingId": "BK-N08", "hotelConfirmationNo": "HC-N08", "status": "confirmed", "hotel": {"name": "Test Hotel"}, "checkIn": "2025-03-01", "checkOut": "2025-03-05", "totalPrice": 500, "numOfRooms": 1}` | Error: 400, "hotel.id is required" |
| CB_N09 | Missing checkIn | `{"clientReference": "REQ-N09", "bookingId": "BK-N09", "hotelConfirmationNo": "HC-N09", "status": "confirmed", "hotel": {"id": "H001"}, "checkOut": "2025-03-05", "totalPrice": 500, "numOfRooms": 1}` | Error: 400, "checkIn is required" |
| CB_N10 | Missing checkOut | `{"clientReference": "REQ-N10", "bookingId": "BK-N10", "hotelConfirmationNo": "HC-N10", "status": "confirmed", "hotel": {"id": "H001"}, "checkIn": "2025-03-01", "totalPrice": 500, "numOfRooms": 1}` | Error: 400, "checkOut is required" |
| CB_N11 | Invalid date format for checkIn | `{"clientReference": "REQ-N11", "bookingId": "BK-N11", "hotelConfirmationNo": "HC-N11", "status": "confirmed", "hotel": {"id": "H001"}, "checkIn": "01-03-2025", "checkOut": "2025-03-05", "totalPrice": 500, "numOfRooms": 1}` | Error: 400, "Invalid date format for checkIn" |
| CB_N12 | checkOut before checkIn | `{"clientReference": "REQ-N12", "bookingId": "BK-N12", "hotelConfirmationNo": "HC-N12", "status": "confirmed", "hotel": {"id": "H001"}, "checkIn": "2025-03-10", "checkOut": "2025-03-05", "totalPrice": 500, "numOfRooms": 1}` | Error: 400, "checkOut must be after checkIn" |
| CB_N13 | Negative totalPrice | `{"clientReference": "REQ-N13", "bookingId": "BK-N13", "hotelConfirmationNo": "HC-N13", "status": "confirmed", "hotel": {"id": "H001"}, "checkIn": "2025-03-01", "checkOut": "2025-03-05", "totalPrice": -100, "numOfRooms": 1}` | Error: 400, "totalPrice must be non-negative" |
| CB_N14 | Non-numeric totalPrice | `{"clientReference": "REQ-N14", "bookingId": "BK-N14", "hotelConfirmationNo": "HC-N14", "status": "confirmed", "hotel": {"id": "H001"}, "checkIn": "2025-03-01", "checkOut": "2025-03-05", "totalPrice": "abc", "numOfRooms": 1}` | Error: 400, "totalPrice must be numeric" |
| CB_N15 | Zero numOfRooms | `{"clientReference": "REQ-N15", "bookingId": "BK-N15", "hotelConfirmationNo": "HC-N15", "status": "confirmed", "hotel": {"id": "H001"}, "checkIn": "2025-03-01", "checkOut": "2025-03-05", "totalPrice": 500, "numOfRooms": 0}` | Error: 400, "numOfRooms must be positive" |
| CB_N16 | Negative numOfRooms | `{"clientReference": "REQ-N16", "bookingId": "BK-N16", "hotelConfirmationNo": "HC-N16", "status": "confirmed", "hotel": {"id": "H001"}, "checkIn": "2025-03-01", "checkOut": "2025-03-05", "totalPrice": 500, "numOfRooms": -1}` | Error: 400, "numOfRooms must be positive" |
| CB_N17 | Duplicate bookingId (different clientReference) | `{"clientReference": "REQ-N17", "bookingId": "BK-001", "hotelConfirmationNo": "HC-N17", "status": "confirmed", "hotel": {"id": "H001"}, "checkIn": "2025-03-01", "checkOut": "2025-03-05", "totalPrice": 500, "numOfRooms": 1}` | Error: 400, "Duplicate bookingId exists" |
| CB_N18 | Duplicate hotelConfirmationNo (different clientReference) | `{"clientReference": "REQ-N18", "bookingId": "BK-N18", "hotelConfirmationNo": "HC-001", "status": "confirmed", "hotel": {"id": "H001"}, "checkIn": "2025-03-01", "checkOut": "2025-03-05", "totalPrice": 500, "numOfRooms": 1}` | Error: 400, "Duplicate hotelConfirmationNo exists" |
| CB_N19 | Unauthorized request (no auth token) | Valid payload without Authorization header | Error: 401/403, "Authentication required" |
| CB_N20 | Empty request body | `{}` | Error: 400, "Request body cannot be empty" |
| CB_N21 | Invalid JSON format | `{invalid json}` | Error: 400, "Invalid JSON format" |
| CB_N22 | Invalid hotel object type | `{"clientReference": "REQ-N22", "bookingId": "BK-N22", "hotelConfirmationNo": "HC-N22", "status": "confirmed", "hotel": "not_an_object", ...}` | Error: 400, "hotel must be an object" |

---

## 2. Create Booking API

**Endpoint:** `POST /api/method/destiin.custom.api.hotel_booking.booking.create_booking`

*This API has the same structure as Confirm Booking API. Test cases are identical.*

---

## 3. Get All Bookings API

**Endpoint:** `GET /api/method/destiin.custom.api.hotel_booking.booking.get_all_bookings`

### Positive Test Cases

| TC ID | Test Case | Query Parameters | Expected Result |
|-------|-----------|------------------|-----------------|
| GAB_P01 | Get all bookings without filters | None | Success: 200, list of all bookings |
| GAB_P02 | Filter by employee | `?employee=EMP-001` | Success: 200, bookings for specific employee |
| GAB_P03 | Filter by company | `?company=COMP-001` | Success: 200, bookings for specific company |
| GAB_P04 | Filter by booking_status "confirmed" | `?booking_status=confirmed` | Success: 200, only confirmed bookings |
| GAB_P05 | Filter by booking_status "cancelled" | `?booking_status=cancelled` | Success: 200, only cancelled bookings |
| GAB_P06 | Filter by booking_status "pending" | `?booking_status=pending` | Success: 200, only pending bookings |
| GAB_P07 | Filter by booking_status "completed" | `?booking_status=completed` | Success: 200, only completed bookings |
| GAB_P08 | Filter by booking_id | `?booking_id=REQ-001` | Success: 200, specific booking |
| GAB_P09 | Combined filters | `?employee=EMP-001&booking_status=confirmed` | Success: 200, filtered results |

### Negative Test Cases

| TC ID | Test Case | Query Parameters | Expected Result |
|-------|-----------|------------------|-----------------|
| GAB_N01 | Invalid booking_status | `?booking_status=invalid` | Error: 400, "Invalid booking_status" |
| GAB_N02 | Non-existent employee | `?employee=NON_EXISTENT` | Success: 200, empty list |
| GAB_N03 | Non-existent company | `?company=NON_EXISTENT` | Success: 200, empty list |
| GAB_N04 | Non-existent booking_id | `?booking_id=NON_EXISTENT` | Success: 200, empty list |
| GAB_N05 | Unauthorized request | No Authorization header | Error: 401/403, "Authentication required" |
| GAB_N06 | SQL injection attempt | `?employee=' OR '1'='1` | Error: 400 or sanitized response |

---

## 4. Store Request Booking API

**Endpoint:** `POST /api/method/destiin.custom.api.request_booking.request.store_req_booking`

### Positive Test Cases

| TC ID | Test Case | Request Body | Expected Result |
|-------|-----------|--------------|-----------------|
| SRB_P01 | Valid request with required fields only | `{"employee": "EMP-001", "check_in": "2025-03-01", "check_out": "2025-03-05"}` | Success: 200, request booking created |
| SRB_P02 | Valid request with company | `{"employee": "EMP-001", "company": "COMP-001", "check_in": "2025-03-01", "check_out": "2025-03-05"}` | Success: 200 |
| SRB_P03 | Valid request with occupancy details | `{"employee": "EMP-001", "check_in": "2025-03-01", "check_out": "2025-03-05", "occupancy": 4, "adult_count": 2, "child_count": 2, "room_count": 2}` | Success: 200 |
| SRB_P04 | Valid request with destination | `{"employee": "EMP-001", "check_in": "2025-03-01", "check_out": "2025-03-05", "destination": "New York", "destination_code": "NYC"}` | Success: 200 |
| SRB_P05 | Valid request with hotel_details | `{"employee": "EMP-001", "check_in": "2025-03-01", "check_out": "2025-03-05", "hotel_details": {"hotel_id": "H001", "hotel_name": "Test Hotel", "rooms": [{"room_id": "R001", "room_name": "Deluxe", "price": 100, "total_price": 400, "tax": 40, "currency": "USD"}]}}` | Success: 200, booking with hotel details |
| SRB_P06 | Valid request with multiple rooms | `{"employee": "EMP-001", "check_in": "2025-03-01", "check_out": "2025-03-05", "hotel_details": {"hotel_id": "H001", "rooms": [{"room_id": "R001", "price": 100}, {"room_id": "R002", "price": 150}]}}` | Success: 200 |
| SRB_P07 | Update existing request booking | `{"employee": "EMP-001", "check_in": "2025-03-01", "check_out": "2025-03-05", "request_booking_id": "existing_id"}` | Success: 200, existing booking updated |

### Negative Test Cases

| TC ID | Test Case | Request Body | Expected Result |
|-------|-----------|--------------|-----------------|
| SRB_N01 | Missing employee | `{"check_in": "2025-03-01", "check_out": "2025-03-05"}` | Error: 400, "employee is required" |
| SRB_N02 | Empty employee | `{"employee": "", "check_in": "2025-03-01", "check_out": "2025-03-05"}` | Error: 400, "employee cannot be empty" |
| SRB_N03 | Non-existent employee | `{"employee": "NON_EXISTENT", "check_in": "2025-03-01", "check_out": "2025-03-05"}` | Error: 400, "Employee not found" |
| SRB_N04 | Missing check_in | `{"employee": "EMP-001", "check_out": "2025-03-05"}` | Error: 400, "check_in is required" |
| SRB_N05 | Missing check_out | `{"employee": "EMP-001", "check_in": "2025-03-01"}` | Error: 400, "check_out is required" |
| SRB_N06 | Invalid check_in date format | `{"employee": "EMP-001", "check_in": "01/03/2025", "check_out": "2025-03-05"}` | Error: 400, "Invalid date format" |
| SRB_N07 | check_out before check_in | `{"employee": "EMP-001", "check_in": "2025-03-10", "check_out": "2025-03-05"}` | Error: 400, "check_out must be after check_in" |
| SRB_N08 | check_in in the past | `{"employee": "EMP-001", "check_in": "2020-01-01", "check_out": "2020-01-05"}` | Error: 400, "check_in cannot be in the past" |
| SRB_N09 | Negative occupancy | `{"employee": "EMP-001", "check_in": "2025-03-01", "check_out": "2025-03-05", "occupancy": -1}` | Error: 400, "occupancy must be positive" |
| SRB_N10 | Negative adult_count | `{"employee": "EMP-001", "check_in": "2025-03-01", "check_out": "2025-03-05", "adult_count": -1}` | Error: 400, "adult_count must be non-negative" |
| SRB_N11 | Negative child_count | `{"employee": "EMP-001", "check_in": "2025-03-01", "check_out": "2025-03-05", "child_count": -2}` | Error: 400, "child_count must be non-negative" |
| SRB_N12 | Negative room_count | `{"employee": "EMP-001", "check_in": "2025-03-01", "check_out": "2025-03-05", "room_count": -1}` | Error: 400, "room_count must be positive" |
| SRB_N13 | Invalid hotel_details format | `{"employee": "EMP-001", "check_in": "2025-03-01", "check_out": "2025-03-05", "hotel_details": "invalid"}` | Error: 400, "hotel_details must be an object" |
| SRB_N14 | hotel_details without hotel_id | `{"employee": "EMP-001", "check_in": "2025-03-01", "check_out": "2025-03-05", "hotel_details": {"hotel_name": "Test"}}` | Error: 400, "hotel_id is required in hotel_details" |
| SRB_N15 | Empty rooms array in hotel_details | `{"employee": "EMP-001", "check_in": "2025-03-01", "check_out": "2025-03-05", "hotel_details": {"hotel_id": "H001", "rooms": []}}` | Error: 400, "rooms cannot be empty" |
| SRB_N16 | Room without room_id | `{"employee": "EMP-001", "check_in": "2025-03-01", "check_out": "2025-03-05", "hotel_details": {"hotel_id": "H001", "rooms": [{"room_name": "Deluxe"}]}}` | Error: 400, "room_id is required" |
| SRB_N17 | Negative room price | `{"employee": "EMP-001", "check_in": "2025-03-01", "check_out": "2025-03-05", "hotel_details": {"hotel_id": "H001", "rooms": [{"room_id": "R001", "price": -100}]}}` | Error: 400, "price must be non-negative" |
| SRB_N18 | Unauthorized request | Valid payload without auth | Error: 401/403 |
| SRB_N19 | Empty request body | `{}` | Error: 400, "Missing required fields" |

---

## 5. Get All Request Bookings API

**Endpoint:** `GET /api/method/destiin.custom.api.request_booking.request.get_all_request_bookings`

### Positive Test Cases

| TC ID | Test Case | Query Parameters | Expected Result |
|-------|-----------|------------------|-----------------|
| GARB_P01 | Get all request bookings | None | Success: 200, list of all request bookings |
| GARB_P02 | Filter by company | `?company=COMP-001` | Success: 200, filtered results |
| GARB_P03 | Filter by employee | `?employee=EMP-001` | Success: 200, filtered results |
| GARB_P04 | Filter by status req_pending | `?status=req_pending` | Success: 200 |
| GARB_P05 | Filter by status req_send_for_approval | `?status=req_send_for_approval` | Success: 200 |
| GARB_P06 | Filter by status req_approved | `?status=req_approved` | Success: 200 |
| GARB_P07 | Filter by status req_payment_pending | `?status=req_payment_pending` | Success: 200 |
| GARB_P08 | Filter by status req_payment_success | `?status=req_payment_success` | Success: 200 |
| GARB_P09 | Filter by status req_closed | `?status=req_closed` | Success: 200 |
| GARB_P10 | Filter by multiple statuses | `?status=req_pending,req_approved` | Success: 200 |
| GARB_P11 | Combined filters | `?company=COMP-001&employee=EMP-001&status=req_pending` | Success: 200 |

### Negative Test Cases

| TC ID | Test Case | Query Parameters | Expected Result |
|-------|-----------|------------------|-----------------|
| GARB_N01 | Invalid status | `?status=invalid_status` | Error: 400 or empty results |
| GARB_N02 | Non-existent company | `?company=NON_EXISTENT` | Success: 200, empty list |
| GARB_N03 | Non-existent employee | `?employee=NON_EXISTENT` | Success: 200, empty list |
| GARB_N04 | SQL injection attempt | `?company=' OR '1'='1` | Error: 400 or sanitized |

---

## 6. Send For Approval API

**Endpoint:** `POST /api/method/destiin.custom.api.request_booking.request.send_for_approval`

### Positive Test Cases

| TC ID | Test Case | Request Body | Expected Result |
|-------|-----------|--------------|-----------------|
| SFA_P01 | Valid send for approval with one hotel | `{"request_booking_id": "REQ-001", "selected_items": [{"hotel_id": "H001", "room_ids": ["R001"]}]}` | Success: 200, items sent for approval |
| SFA_P02 | Valid send with multiple rooms | `{"request_booking_id": "REQ-001", "selected_items": [{"hotel_id": "H001", "room_ids": ["R001", "R002"]}]}` | Success: 200 |
| SFA_P03 | Valid send with multiple hotels | `{"request_booking_id": "REQ-001", "selected_items": [{"hotel_id": "H001", "room_ids": ["R001"]}, {"hotel_id": "H002", "room_ids": ["R003"]}]}` | Success: 200 |

### Negative Test Cases

| TC ID | Test Case | Request Body | Expected Result |
|-------|-----------|--------------|-----------------|
| SFA_N01 | Missing request_booking_id | `{"selected_items": [{"hotel_id": "H001", "room_ids": ["R001"]}]}` | Error: 400, "request_booking_id is required" |
| SFA_N02 | Empty request_booking_id | `{"request_booking_id": "", "selected_items": [...]}` | Error: 400, "request_booking_id cannot be empty" |
| SFA_N03 | Non-existent request_booking_id | `{"request_booking_id": "NON_EXISTENT", "selected_items": [...]}` | Error: 404, "Request booking not found" |
| SFA_N04 | Missing selected_items | `{"request_booking_id": "REQ-001"}` | Error: 400, "selected_items is required" |
| SFA_N05 | Empty selected_items array | `{"request_booking_id": "REQ-001", "selected_items": []}` | Error: 400, "selected_items cannot be empty" |
| SFA_N06 | selected_items without hotel_id | `{"request_booking_id": "REQ-001", "selected_items": [{"room_ids": ["R001"]}]}` | Error: 400, "hotel_id is required" |
| SFA_N07 | selected_items without room_ids | `{"request_booking_id": "REQ-001", "selected_items": [{"hotel_id": "H001"}]}` | Error: 400, "room_ids is required" |
| SFA_N08 | Empty room_ids array | `{"request_booking_id": "REQ-001", "selected_items": [{"hotel_id": "H001", "room_ids": []}]}` | Error: 400, "room_ids cannot be empty" |
| SFA_N09 | Non-existent hotel_id | `{"request_booking_id": "REQ-001", "selected_items": [{"hotel_id": "NON_EXISTENT", "room_ids": ["R001"]}]}` | Error: 404, "Hotel not found" |
| SFA_N10 | Non-existent room_id | `{"request_booking_id": "REQ-001", "selected_items": [{"hotel_id": "H001", "room_ids": ["NON_EXISTENT"]}]}` | Error: 404, "Room not found" |
| SFA_N11 | Invalid status transition (already approved) | Send for already approved booking | Error: 400, "Cannot send for approval" |
| SFA_N12 | Unauthorized request | Valid payload without auth | Error: 401/403 |

---

## 7. Approve Booking API

**Endpoint:** `POST /api/method/destiin.custom.api.request_booking.request.approve_booking`

### Positive Test Cases

| TC ID | Test Case | Request Body | Expected Result |
|-------|-----------|--------------|-----------------|
| AB_P01 | Valid approval with one hotel | `{"request_booking_id": "REQ-001", "employee": "EMP-001", "selected_items": [{"hotel_id": "H001", "room_ids": ["R001"]}]}` | Success: 200, booking approved |
| AB_P02 | Valid approval with multiple rooms | `{"request_booking_id": "REQ-001", "employee": "EMP-001", "selected_items": [{"hotel_id": "H001", "room_ids": ["R001", "R002"]}]}` | Success: 200 |
| AB_P03 | Partial approval (some hotels approved) | `{"request_booking_id": "REQ-001", "employee": "EMP-001", "selected_items": [{"hotel_id": "H001", "room_ids": ["R001"]}]}` (when H002 also exists) | Success: 200, partial approval |

### Negative Test Cases

| TC ID | Test Case | Request Body | Expected Result |
|-------|-----------|--------------|-----------------|
| AB_N01 | Missing request_booking_id | `{"employee": "EMP-001", "selected_items": [...]}` | Error: 400, "request_booking_id is required" |
| AB_N02 | Missing employee | `{"request_booking_id": "REQ-001", "selected_items": [...]}` | Error: 400, "employee is required" |
| AB_N03 | Missing selected_items | `{"request_booking_id": "REQ-001", "employee": "EMP-001"}` | Error: 400, "selected_items is required" |
| AB_N04 | Empty selected_items | `{"request_booking_id": "REQ-001", "employee": "EMP-001", "selected_items": []}` | Error: 400, "selected_items cannot be empty" |
| AB_N05 | Non-existent request_booking_id | `{"request_booking_id": "NON_EXISTENT", "employee": "EMP-001", "selected_items": [...]}` | Error: 404, "Request booking not found" |
| AB_N06 | Non-existent employee | `{"request_booking_id": "REQ-001", "employee": "NON_EXISTENT", "selected_items": [...]}` | Error: 404, "Employee not found" |
| AB_N07 | Booking not in approval pending state | Approve booking that's not sent for approval | Error: 400, "Booking not in approval pending state" |
| AB_N08 | Unauthorized employee (not approver) | Employee without approval rights | Error: 403, "Not authorized to approve" |
| AB_N09 | Already approved booking | Approve already approved booking | Error: 400, "Booking already approved" |
| AB_N10 | Unauthorized request | Valid payload without auth | Error: 401/403 |

---

## 8. Decline Booking API

**Endpoint:** `POST /api/method/destiin.custom.api.request_booking.request.decline_booking`

### Positive Test Cases

| TC ID | Test Case | Request Body | Expected Result |
|-------|-----------|--------------|-----------------|
| DB_P01 | Valid decline with one hotel | `{"request_booking_id": "REQ-001", "employee": "EMP-001", "selected_items": [{"hotel_id": "H001", "room_ids": ["R001"]}]}` | Success: 200, booking declined |
| DB_P02 | Valid decline with multiple rooms | `{"request_booking_id": "REQ-001", "employee": "EMP-001", "selected_items": [{"hotel_id": "H001", "room_ids": ["R001", "R002"]}]}` | Success: 200 |

### Negative Test Cases

| TC ID | Test Case | Request Body | Expected Result |
|-------|-----------|--------------|-----------------|
| DB_N01 | Missing request_booking_id | `{"employee": "EMP-001", "selected_items": [...]}` | Error: 400, "request_booking_id is required" |
| DB_N02 | Missing employee | `{"request_booking_id": "REQ-001", "selected_items": [...]}` | Error: 400, "employee is required" |
| DB_N03 | Missing selected_items | `{"request_booking_id": "REQ-001", "employee": "EMP-001"}` | Error: 400, "selected_items is required" |
| DB_N04 | Empty selected_items | `{"request_booking_id": "REQ-001", "employee": "EMP-001", "selected_items": []}` | Error: 400, "selected_items cannot be empty" |
| DB_N05 | Non-existent request_booking_id | `{"request_booking_id": "NON_EXISTENT", ...}` | Error: 404, "Request booking not found" |
| DB_N06 | Booking not in correct state | Decline already completed booking | Error: 400, "Cannot decline booking" |
| DB_N07 | Unauthorized employee | Employee without decline rights | Error: 403, "Not authorized" |
| DB_N08 | Unauthorized request | Valid payload without auth | Error: 401/403 |

---

## 9. Update Request Booking API

**Endpoint:** `POST /api/method/destiin.custom.api.request_booking.request.update_request_booking`

### Positive Test Cases

| TC ID | Test Case | Request Body | Expected Result |
|-------|-----------|--------------|-----------------|
| URB_P01 | Update occupancy details | `{"request_booking_id": "REQ-001", "occupancy": 4, "adult_count": 3, "child_count": 1}` | Success: 200 |
| URB_P02 | Update room_count | `{"request_booking_id": "REQ-001", "room_count": 3}` | Success: 200 |
| URB_P03 | Add hotel_details | `{"request_booking_id": "REQ-001", "hotel_details": {"hotel_id": "H002", "rooms": [{"room_id": "R003"}]}}` | Success: 200 |

### Negative Test Cases

| TC ID | Test Case | Request Body | Expected Result |
|-------|-----------|--------------|-----------------|
| URB_N01 | Missing request_booking_id | `{"occupancy": 4}` | Error: 400, "request_booking_id is required" |
| URB_N02 | Non-existent request_booking_id | `{"request_booking_id": "NON_EXISTENT", "occupancy": 4}` | Error: 404, "Request booking not found" |
| URB_N03 | Change destination (not allowed) | `{"request_booking_id": "REQ-001", "destination": "New Destination"}` | Error: 400, "Cannot change destination" |
| URB_N04 | Change check_in date (not allowed) | `{"request_booking_id": "REQ-001", "check_in": "2025-04-01"}` | Error: 400, "Cannot change check_in" |
| URB_N05 | Change check_out date (not allowed) | `{"request_booking_id": "REQ-001", "check_out": "2025-04-10"}` | Error: 400, "Cannot change check_out" |
| URB_N06 | Negative occupancy | `{"request_booking_id": "REQ-001", "occupancy": -1}` | Error: 400, "occupancy must be positive" |
| URB_N07 | Update after approval | Update approved booking | Error: 400, "Cannot update approved booking" |
| URB_N08 | Unauthorized request | Valid payload without auth | Error: 401/403 |

---

## 10. Create Payment URL API

**Endpoint:** `POST /api/method/destiin.custom.api.payments.payments.create_payment_url`

### Positive Test Cases

| TC ID | Test Case | Request Body | Expected Result |
|-------|-----------|--------------|-----------------|
| CPU_P01 | Create payment URL with direct_pay mode | `{"request_booking_id": "REQ-001", "mode": "direct_pay"}` | Success: 200, payment URL generated |
| CPU_P02 | Create payment URL with bill_to_company mode | `{"request_booking_id": "REQ-001", "mode": "bill_to_company"}` | Success: 200, payment URL generated |

### Negative Test Cases

| TC ID | Test Case | Request Body | Expected Result |
|-------|-----------|--------------|-----------------|
| CPU_N01 | Missing request_booking_id | `{"mode": "direct_pay"}` | Error: 400, "request_booking_id is required" |
| CPU_N02 | Empty request_booking_id | `{"request_booking_id": "", "mode": "direct_pay"}` | Error: 400, "request_booking_id cannot be empty" |
| CPU_N03 | Non-existent request_booking_id | `{"request_booking_id": "NON_EXISTENT", "mode": "direct_pay"}` | Error: 404, "Request booking not found" |
| CPU_N04 | Missing mode | `{"request_booking_id": "REQ-001"}` | Error: 400, "mode is required" |
| CPU_N05 | Invalid mode | `{"request_booking_id": "REQ-001", "mode": "invalid_mode"}` | Error: 400, "Invalid mode. Must be direct_pay or bill_to_company" |
| CPU_N06 | Empty mode | `{"request_booking_id": "REQ-001", "mode": ""}` | Error: 400, "mode cannot be empty" |
| CPU_N07 | No approved rooms | Create payment for booking without approved rooms | Error: 400, "No approved rooms found" |
| CPU_N08 | Zero payment amount | Create payment when total is 0 | Error: 400, "Payment amount must be greater than 0" |
| CPU_N09 | Booking not in correct status | Create payment for pending booking | Error: 400, "Booking not approved for payment" |
| CPU_N10 | Payment already created | Create duplicate payment | Error: 400, "Payment already exists" |
| CPU_N11 | Unauthorized request | Valid payload without auth | Error: 401/403 |
| CPU_N12 | HitPay API failure | Valid request but HitPay fails | Error: 500, "Payment gateway error" |

---

## 11. Payment Callback API

**Endpoint:** `POST /api/method/destiin.custom.api.payments.payments.payment_callback`

### Positive Test Cases

| TC ID | Test Case | Request Body | Expected Result |
|-------|-----------|--------------|-----------------|
| PC_P01 | Payment success callback | `{"payment_id": "PAY-001", "status": "success", "transaction_id": "TXN-001"}` | Success: 200, payment marked successful |
| PC_P02 | Payment failure callback | `{"payment_id": "PAY-001", "status": "failure", "error_message": "Card declined"}` | Success: 200, payment marked failed |
| PC_P03 | Payment cancel callback | `{"payment_id": "PAY-001", "status": "cancel"}` | Success: 200, payment marked cancelled |
| PC_P04 | Success with transaction details | `{"payment_id": "PAY-001", "status": "success", "transaction_id": "TXN-001", "payment_method": "credit_card"}` | Success: 200 |

### Negative Test Cases

| TC ID | Test Case | Request Body | Expected Result |
|-------|-----------|--------------|-----------------|
| PC_N01 | Missing payment_id | `{"status": "success"}` | Error: 400, "payment_id is required" |
| PC_N02 | Empty payment_id | `{"payment_id": "", "status": "success"}` | Error: 400, "payment_id cannot be empty" |
| PC_N03 | Non-existent payment_id | `{"payment_id": "NON_EXISTENT", "status": "success"}` | Error: 404, "Payment not found" |
| PC_N04 | Missing status | `{"payment_id": "PAY-001"}` | Error: 400, "status is required" |
| PC_N05 | Invalid status | `{"payment_id": "PAY-001", "status": "invalid_status"}` | Error: 400, "Invalid status. Must be success, failure, or cancel" |
| PC_N06 | Empty status | `{"payment_id": "PAY-001", "status": ""}` | Error: 400, "status cannot be empty" |
| PC_N07 | Already processed payment | Callback for already successful payment | Error: 400, "Payment already processed" |
| PC_N08 | Expired payment | Callback for expired payment session | Error: 400, "Payment session expired" |
| PC_N09 | Unauthorized request | Valid payload without auth | Error: 401/403 |
| PC_N10 | Invalid signature (webhook verification) | Invalid HMAC signature | Error: 401, "Invalid signature" |
| PC_N11 | Duplicate callback | Same callback sent twice | Error: 400 or idempotent success |

---

## Test Data Requirements

### Prerequisites
1. Valid Employee ID (e.g., `EMP-001`)
2. Valid Company ID (e.g., `COMP-001`)
3. Valid User/Agent ID for authentication
4. API authentication token/credentials

### Test Data Setup
1. Create test employees in the system
2. Create test companies
3. Create test request bookings in various states
4. Set up test payment records

### Environment Variables for Postman
```
{{base_url}} = Your Frappe/ERPNext instance URL
{{api_key}} = API Key for authentication
{{api_secret}} = API Secret for authentication
{{employee_id}} = Test employee ID
{{company_id}} = Test company ID
```

---

## Test Execution Notes

1. **Authentication**: Most APIs require authentication. Include proper headers:
   ```
   Authorization: token {{api_key}}:{{api_secret}}
   Content-Type: application/json
   ```

2. **Order of Execution**: Some tests depend on data created by previous tests. Execute in order:
   - Store Request Booking
   - Send for Approval
   - Approve/Decline Booking
   - Create Payment URL
   - Payment Callback

3. **Cleanup**: After running tests, clean up test data to maintain a clean test environment.

4. **Environment**: Run tests on a staging/development environment, not production.
