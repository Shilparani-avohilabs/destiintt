# Request Booking API Reference

Base URL pattern (Frappe):
```
POST /api/method/destiin.destiin.custom.api.request_booking.request.<function_name>
```

All endpoints require authentication (`allow_guest=False`) unless noted.
All responses are JSON with a top-level `success` boolean.

---

## Table of Contents

1. [store_req_booking](#1-store_req_booking)
2. [update_request_booking](#2-update_request_booking)
3. [get_all_request_bookings](#3-get_all_request_bookings)
4. [get_request_booking_details](#4-get_request_booking_details)
5. [search_request_bookings](#5-search_request_bookings)
6. [send_for_approval](#6-send_for_approval)
7. [approve_booking](#7-approve_booking)
8. [decline_booking](#8-decline_booking)

---

## 1. `store_req_booking`

Creates a new request booking. Returns an error if a booking with the same employee + check_in + check_out already exists.

### Request

| Parameter            | Type          | Required | Description |
|----------------------|---------------|----------|-------------|
| `employee`           | string        | Yes      | Employee ID (e.g. `EMP-0001`) |
| `check_in`           | string (date) | Yes      | Check-in date `YYYY-MM-DD` |
| `check_out`          | string (date) | Yes      | Check-out date `YYYY-MM-DD` |
| `company`            | string        | No       | Company ID |
| `employee_name`      | string        | No       | Employee full name (used if employee not found — creates new employee) |
| `employee_email`     | string        | No       | Employee email |
| `phone_number`       | string        | No       | Employee phone number |
| `employee_level`     | string        | No       | Employee level (e.g. `L1`, `L2`) |
| `employee_country`   | string        | No       | Employee's country. Defaults to `India` |
| `occupancy`          | integer       | No       | Total occupancy |
| `adult_count`        | integer       | No       | Number of adults |
| `child_count`        | integer       | No       | Number of children |
| `child_ages`         | array/string  | No       | List of child ages e.g. `[5, 8]` |
| `room_count`         | integer       | No       | Number of rooms |
| `destination`        | string        | No       | Destination name |
| `destination_code`   | string        | No       | Destination code |
| `destination_country`| string        | No       | Destination country |
| `budget_options`     | string        | No       | `fixed` or `actuals` |
| `budget_amount`      | string/float  | No       | Budget amount |
| `currency`           | string        | No       | Budget currency. Defaults to `USD` |
| `work_address`       | string        | No       | Work address |
| `agent_email`        | string        | No       | Agent email. Falls back to round-robin assignment |
| `request_source`     | string        | No       | Source of the request |
| `hotel_details`      | array/object/string | No  | Hotel and room details (see schema below) |

#### `hotel_details` Schema

```json
[
  {
    "hotel_id": "HTL-001",
    "hotel_name": "Grand Hotel",
    "supplier": "Hotelbeds",
    "latitude": "28.6139",
    "longitude": "77.2090",
    "hotel_reviews": "https://...",
    "images": ["https://img1.jpg", "https://img2.jpg"],
    "rooms": [
      {
        "room_id": "RM-001",
        "room_rate_id": "RR-001",
        "room_name": "Deluxe King",
        "room_code": "DLX",
        "price": 120.00,
        "total_price": 240.00,
        "tax": 20.00,
        "currency": "USD",
        "breakfast_type": "included",
        "cancellation_policy": [],
        "images": []
      }
    ]
  }
]
```

### Sample Request

```json
{
  "employee": "EMP-0001",
  "check_in": "2025-09-01",
  "check_out": "2025-09-05",
  "employee_name": "John Doe",
  "employee_email": "john.doe@example.com",
  "phone_number": "+91-9876543210",
  "employee_level": "L2",
  "company": "Acme Corp",
  "destination": "Mumbai, India",
  "destination_country": "India",
  "adult_count": 2,
  "room_count": 1,
  "budget_amount": "200",
  "currency": "USD",
  "request_source": "mobile_app",
  "hotel_details": [
    {
      "hotel_id": "HTL-001",
      "hotel_name": "Grand Hotel",
      "supplier": "Hotelbeds",
      "rooms": [
        {
          "room_id": "RM-001",
          "room_rate_id": "RR-001",
          "room_name": "Deluxe King",
          "price": 150.00,
          "total_price": 600.00,
          "tax": 50.00,
          "currency": "USD"
        }
      ]
    }
  ]
}
```

### Sample Response (Success)

```json
{
  "success": true,
  "message": "Request booking created successfully",
  "data": {
    "request_booking_id": "RB-EMP0001-20250901-20250905",
    "name": "RBD-0001",
    "employee": "EMP-0001",
    "company": "Acme Corp",
    "check_in": "2025-09-01",
    "check_out": "2025-09-05",
    "request_status": "offer_pending",
    "agent": "agent@example.com",
    "occupancy": null,
    "adult_count": 2,
    "child_count": null,
    "child_ages": [],
    "room_count": 1,
    "destination": "Mumbai, India",
    "destination_code": "",
    "budget_options": "",
    "employee_budget": 200.0,
    "work_address": "",
    "budget_amount": "200",
    "perdiem_amount": 180.0,
    "perdiem_currency": "USD",
    "cart_hotel_item": [],
    "cart_hotel_items": ["CHI-0001"],
    "hotel_count": 1,
    "is_new": true,
    "is_new_employee": false,
    "request_source": "mobile_app",
    "phone_number": "+91-9876543210"
  }
}
```

### Sample Response (Duplicate)

```json
{
  "success": false,
  "message": "Request already exists for this employee with same checkin checkout"
}
```

### Sample Response (Error)

```json
{
  "success": false,
  "error": "<exception message>",
  "data": null
}
```

---

## 2. `update_request_booking`

Updates an existing request booking. Only fields explicitly passed are updated.

### Request

| Parameter              | Type          | Required     | Description |
|------------------------|---------------|--------------|-------------|
| `request_booking_id`   | string        | Yes (or `name`) | The request booking ID |
| `name`                 | string        | Yes (or `request_booking_id`) | Document name (alternative identifier) |
| `employee`             | string        | No           | Employee ID (Link → Employee) |
| `employee_email`       | string        | No           | Employee email |
| `phone_number`         | string        | No           | Employee phone number |
| `company`              | string        | No           | Company ID |
| `agent`                | string        | No           | Agent user email (Link → User) |
| `request_status`       | string        | No           | See valid values below |
| `payment_status`       | string        | No           | See valid values below |
| `request_source`       | string        | No           | Source of the request |
| `request_reference`    | string        | No           | External reference ID |
| `check_in`             | string (date) | No           | `YYYY-MM-DD` |
| `check_out`            | string (date) | No           | `YYYY-MM-DD` |
| `destination`          | string        | No           | Destination name |
| `destination_code`     | string        | No           | Destination code |
| `destination_country`  | string        | No           | Destination country |
| `employee_country`     | string        | No           | Employee's country |
| `work_address`         | string        | No           | Work address |
| `room_count`           | integer ≥ 0   | No           | Number of rooms |
| `occupancy`            | integer ≥ 0   | No           | Total occupancy |
| `adult_count`          | integer ≥ 0   | No           | Number of adults |
| `child_count`          | integer ≥ 0   | No           | Number of children |
| `child_ages`           | array/string  | No           | List of child ages |
| `budget_amount`        | string        | No           | Budget amount |
| `budget_options`       | string        | No           | `fixed` or `actuals` |
| `currency`             | string        | No           | Budget currency |
| `employee_budget`      | string/float  | No           | Employee budget (converted) |
| `employee_currency`    | string        | No           | Employee budget currency |
| `perdiem_amount`       | float ≥ 0     | No           | Per diem amount |
| `perdiem_currency`     | string        | No           | Per diem currency |
| `booking`              | string        | No           | Linked Hotel Booking document name |
| `itravel_approved`     | 0 or 1        | No           | iTravel approved flag |
| `void`                 | 0 or 1        | No           | Void flag |
| `hotel_details`        | array/object/string | No     | Hotel and room details (same schema as store) |

#### Valid `request_status` values
`open_request` · `offer_pending` · `offer_sent` · `approval_received` · `request_closed` · `void`

#### Valid `payment_status` values
`payment_pending` · `payment_failure` · `payment_success` · `payment_declined` · `payment_awaiting` · `payment_cancel` · `payment_expired` · `payment_refunded`

### Sample Request

```json
{
  "request_booking_id": "RB-EMP0001-20250901-20250905",
  "phone_number": "+91-9999999999",
  "request_status": "offer_sent",
  "destination": "Delhi, India",
  "adult_count": 3,
  "hotel_details": [
    {
      "hotel_id": "HTL-002",
      "hotel_name": "New Hotel",
      "supplier": "Expedia",
      "rooms": [
        {
          "room_id": "RM-002",
          "room_rate_id": "RR-002",
          "room_name": "Standard Twin",
          "price": 100.00,
          "total_price": 400.00,
          "tax": 30.00,
          "currency": "USD"
        }
      ]
    }
  ]
}
```

### Sample Response (Success)

```json
{
  "success": true,
  "message": "Request booking updated successfully",
  "data": {
    "request_booking_id": "RB-EMP0001-20250901-20250905",
    "name": "RBD-0001",
    "employee": "EMP-0001",
    "employee_email": "john.doe@example.com",
    "phone_number": "+91-9999999999",
    "company": "Acme Corp",
    "agent": "agent@example.com",
    "request_status": "offer_sent",
    "payment_status": "",
    "request_source": "mobile_app",
    "request_reference": "",
    "check_in": "2025-09-01",
    "check_out": "2025-09-05",
    "destination": "Delhi, India",
    "destination_code": "",
    "destination_country": "India",
    "employee_country": "India",
    "work_address": "",
    "room_count": 1,
    "occupancy": 0,
    "adult_count": 3,
    "child_count": 0,
    "child_ages": [],
    "budget_amount": "200",
    "budget_options": "",
    "currency": "USD",
    "employee_budget": 200.0,
    "employee_currency": "USD",
    "perdiem_amount": 180.0,
    "perdiem_currency": "USD",
    "booking": "",
    "itravel_approved": 0,
    "void": 0,
    "cart_hotel_item": []
  }
}
```

### Sample Response (Not Found)

```json
{
  "success": false,
  "error": "Request booking not found: RB-EMP0001-20250901-20250905"
}
```

### Sample Response (Validation Error)

```json
{
  "success": false,
  "error": "Invalid request_status 'xyz'. Valid values: approval_received, offer_pending, offer_sent, open_request, request_closed, void"
}
```

---

## 3. `get_all_request_bookings`

Returns a paginated list of request bookings (future check-in dates only).

### Request

| Parameter    | Type         | Required | Description |
|--------------|--------------|----------|-------------|
| `company`    | string       | No       | Filter by company ID |
| `employee`   | string       | No       | Filter by employee ID |
| `status`     | string       | No       | Comma-separated status values e.g. `offer_pending,offer_sent` |
| `page`       | integer      | No       | Page number (1-indexed). Default: `1` |
| `page_size`  | integer      | No       | Records per page. Default: `20`, Max: `100` |
| `res_payload`| array/string | No       | List of response keys to include. Omit for all fields |

### Sample Request

```json
{
  "company": "Acme Corp",
  "status": "offer_pending,offer_sent",
  "page": 1,
  "page_size": 10
}
```

### Sample Response (Success)

```json
{
  "success": true,
  "data": [
    {
      "name": "RBD-0001",
      "request_booking_id": "RB-EMP0001-20250901-20250905",
      "company": "Acme Corp",
      "company_name": "Acme Corporation",
      "employee": "EMP-0001",
      "employee_email": "john.doe@example.com",
      "employee_name": "John Doe",
      "employee_phone": "+91-9876543210",
      "employee_level": "L2",
      "booking": "",
      "booking_id": "",
      "request_status": "offer_pending",
      "check_in": "2025-09-01",
      "check_out": "2025-09-05",
      "occupancy": 0,
      "adult_count": 2,
      "child_count": 0,
      "child_ages": [],
      "room_count": 1,
      "destination": "Mumbai, India",
      "destination_code": "",
      "destination_country": "India",
      "budget_options": "",
      "employee_budget": 200.0,
      "work_address": "",
      "request_source": "mobile_app",
      "request_reference": "",
      "itravel_approved": 0,
      "void": 0,
      "creation": "2025-08-01 10:30:00",
      "hotels": [
        {
          "hotel_id": "HTL-001",
          "hotel_name": "Grand Hotel",
          "supplier": "Hotelbeds",
          "hotel_reviews": "https://...",
          "status": "pending",
          "approver_level": 0,
          "images": ["https://img1.jpg"],
          "rooms": [
            {
              "room_id": "RM-001",
              "room_rate_id": "RR-001",
              "room_code": "DLX",
              "room_type": "Deluxe King",
              "price": 150.0,
              "room_count": 1,
              "breakfast_type": "included",
              "cancellation_policy": [],
              "status": "pending",
              "approver_level": 0,
              "images": []
            }
          ]
        }
      ],
      "total_amount": 150.0
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 10,
    "total_count": 1,
    "total_pages": 1,
    "has_next": false,
    "has_previous": false
  }
}
```

---

## 4. `get_request_booking_details`

Returns full details for a single request booking including hotels, rooms, and converted total amount.

### Request

| Parameter            | Type   | Required | Description |
|----------------------|--------|----------|-------------|
| `request_booking_id` | string | Yes      | The request booking ID |
| `status`             | string | No       | Filter rooms by status (e.g. `sent_for_approval`, `approved`) |

### Sample Request

```json
{
  "request_booking_id": "RB-EMP0001-20250901-20250905",
  "status": "sent_for_approval"
}
```

### Sample Response (Success)

```json
{
  "success": true,
  "data": {
    "name": "RBD-0001",
    "request_booking_id": "RB-EMP0001-20250901-20250905",
    "company": "Acme Corp",
    "company_name": "Acme Corporation",
    "employee": "EMP-0001",
    "employee_email": "john.doe@example.com",
    "employee_name": "John Doe",
    "employee_phone": "+91-9876543210",
    "employee_level": "L2",
    "booking": "",
    "booking_id": "",
    "request_status": "offer_sent",
    "check_in": "2025-09-01",
    "check_out": "2025-09-05",
    "occupancy": 0,
    "adult_count": 2,
    "child_count": 0,
    "child_ages": [],
    "room_count": 1,
    "destination": "Mumbai, India",
    "destination_code": "",
    "destination_country": "India",
    "budget_options": "",
    "employee_budget": 200.0,
    "work_address": "",
    "request_source": "mobile_app",
    "request_reference": "",
    "itravel_approved": 0,
    "void": 0,
    "creation": "2025-08-01 10:30:00",
    "hotels": [
      {
        "hotel_id": "HTL-001",
        "hotel_name": "Grand Hotel",
        "supplier": "Hotelbeds",
        "hotel_reviews": "https://...",
        "approver_level": 0,
        "images": ["https://img1.jpg"],
        "rooms": [
          {
            "room_id": "RM-001",
            "room_rate_id": "RR-001",
            "room_code": "DLX",
            "room_type": "Deluxe King",
            "price": 150.0,
            "room_count": 1,
            "breakfast_type": "included",
            "cancellation_policy": [],
            "status": "sent_for_approval",
            "approver_level": 0,
            "images": []
          }
        ]
      }
    ],
    "total_amount": 150.0,
    "converted_amount": 12450.0,
    "converted_currency": "INR"
  }
}
```

### Sample Response (Not Found)

```json
{
  "success": false,
  "error": "Request booking not found: RB-EMP0001-20250901-20250905"
}
```

---

## 5. `search_request_bookings`

Global search / auto-suggestion across bookings. Requires at least one of `query`, `company`, or `status`.

Searchable fields: `request_booking_id`, `employee_email`, employee name, `destination`, `destination_code`, `request_reference`, `request_source`.

### Request

| Parameter    | Type         | Required          | Description |
|--------------|--------------|-------------------|-------------|
| `query`      | string       | Yes (or company/status) | Search string (min 1 char) |
| `company`    | string       | No                | Filter by company |
| `status`     | string       | No                | Filter by request_status |
| `limit`      | integer      | No                | Max results. Default: `10`, Max: `50` |
| `res_payload`| array/string | No                | List of response keys to include |

### Sample Request

```json
{
  "query": "Mumbai",
  "company": "Acme Corp",
  "limit": 5
}
```

### Sample Response (Success)

```json
{
  "success": true,
  "query": "Mumbai",
  "count": 1,
  "data": [
    {
      "request_booking_id": "RB-EMP0001-20250901-20250905",
      "employee": {
        "id": "EMP-0001",
        "name": "John Doe",
        "email": "john.doe@example.com"
      },
      "company": "Acme Corp",
      "destination": "Mumbai, India",
      "destination_code": "",
      "request_status": "offer_sent",
      "check_in": "2025-09-01",
      "check_out": "2025-09-05",
      "request_reference": "",
      "request_source": "mobile_app",
      "itravel_approved": 0,
      "void": 0
    }
  ]
}
```

### Sample Response (Error)

```json
{
  "success": false,
  "error": "Provide at least one of: query, company, or status",
  "data": []
}
```

---

## 6. `send_for_approval`

Marks selected hotels/rooms as `sent_for_approval` and sends an email notification to the employee and agent.

### Request

| Parameter            | Type         | Required | Description |
|----------------------|--------------|----------|-------------|
| `request_booking_id` | string       | Yes      | The request booking ID |
| `selected_items`     | array/string | Yes      | Hotels and room_rate_ids to send for approval |

#### `selected_items` Schema

```json
[
  {
    "hotel_id": "HTL-001",
    "room_rate_ids": ["RR-001", "RR-002"]
  }
]
```

> **Note:** Use `room_rate_id` (unique) not `room_id` to identify rooms.

### Sample Request

```json
{
  "request_booking_id": "RB-EMP0001-20250901-20250905",
  "selected_items": [
    {
      "hotel_id": "HTL-001",
      "room_rate_ids": ["RR-001"]
    }
  ]
}
```

### Sample Response (Success)

```json
{
  "success": true,
  "message": "Successfully sent 1 room(s) for approval",
  "data": {
    "request_booking_id": "RB-EMP0001-20250901-20250905",
    "updated_count": 1,
    "email_sent": true,
    "email_recipients": ["john.doe@example.com", "agent@example.com"],
    "updated_hotels": [
      {
        "hotel_id": "HTL-001",
        "hotel_name": "Grand Hotel",
        "supplier": "Hotelbeds",
        "rooms": [
          {
            "room_id": "RM-001",
            "room_rate_id": "RR-001",
            "room_name": "Deluxe King",
            "price": 150.0,
            "total_price": 600.0,
            "tax": 50.0,
            "currency": "USD"
          }
        ]
      }
    ]
  }
}
```

### Sample Response (Not Found)

```json
{
  "success": false,
  "error": "Request booking not found for ID: RB-EMP0001-20250901-20250905"
}
```

---

## 7. `approve_booking`

Approves selected rooms (sets status to `approved`) and automatically declines all other rooms in the same hotels.

### Request

| Parameter            | Type         | Required | Description |
|----------------------|--------------|----------|-------------|
| `request_booking_id` | string       | Yes      | The request booking ID |
| `employee`           | string       | Yes      | Employee ID (booking must belong to this employee) |
| `selected_items`     | array/string | Yes      | Hotels and room_rate_ids to approve |

#### `selected_items` Schema

```json
[
  {
    "hotel_id": "HTL-001",
    "room_rate_ids": ["RR-001"]
  }
]
```

### Sample Request

```json
{
  "request_booking_id": "RB-EMP0001-20250901-20250905",
  "employee": "EMP-0001",
  "selected_items": [
    {
      "hotel_id": "HTL-001",
      "room_rate_ids": ["RR-001"]
    }
  ]
}
```

### Sample Response (Success)

```json
{
  "success": true,
  "message": "Successfully approved 1 room(s) and declined 0 room(s)",
  "data": {
    "request_booking_id": "RB-EMP0001-20250901-20250905",
    "employee": "EMP-0001",
    "approved_count": 1,
    "declined_count": 0,
    "request_status": "approval_received",
    "approved_hotels": [
      {
        "hotel_id": "HTL-001",
        "hotel_name": "Grand Hotel",
        "supplier": "Hotelbeds",
        "rooms": [
          {
            "room_id": "RM-001",
            "room_rate_id": "RR-001",
            "room_name": "Deluxe King",
            "price": 150.0,
            "status": "approved"
          }
        ]
      }
    ],
    "declined_hotels": []
  }
}
```

### Sample Response (Not Found)

```json
{
  "success": false,
  "error": "Request booking not found for ID: RB-EMP0001-20250901-20250905 and employee: EMP-0001"
}
```

---

## 8. `decline_booking`

Declines selected hotels/rooms (sets status to `declined`).

### Request

| Parameter            | Type         | Required | Description |
|----------------------|--------------|----------|-------------|
| `request_booking_id` | string       | Yes      | The request booking ID |
| `employee`           | string       | Yes      | Employee ID (booking must belong to this employee) |
| `selected_items`     | array/string | Yes      | Hotels and room_rate_ids to decline |

#### `selected_items` Schema

```json
[
  {
    "hotel_id": "HTL-001",
    "room_rate_ids": ["RR-001"]
  }
]
```

### Sample Request

```json
{
  "request_booking_id": "RB-EMP0001-20250901-20250905",
  "employee": "EMP-0001",
  "selected_items": [
    {
      "hotel_id": "HTL-001",
      "room_rate_ids": ["RR-001"]
    }
  ]
}
```

### Sample Response (Success)

```json
{
  "success": true,
  "message": "Successfully declined 1 room(s)",
  "data": {
    "request_booking_id": "RB-EMP0001-20250901-20250905",
    "employee": "EMP-0001",
    "declined_count": 1,
    "request_status": "req_cancelled",
    "declined_hotels": [
      {
        "hotel_id": "HTL-001",
        "hotel_name": "Grand Hotel",
        "supplier": "Hotelbeds",
        "rooms": [
          {
            "room_id": "RM-001",
            "room_rate_id": "RR-001",
            "room_name": "Deluxe King",
            "price": 150.0,
            "status": "declined"
          }
        ]
      }
    ]
  }
}
```

### Sample Response (Not Found)

```json
{
  "success": false,
  "error": "Request booking not found for ID: RB-EMP0001-20250901-20250905 and employee: EMP-0001"
}
```

---

## Common Error Responses

All endpoints return this shape on unhandled exceptions:

```json
{
  "success": false,
  "error": "<exception message>"
}
```

---

## Room & Request Status Reference

### Room Status Values
| Status              | Description |
|---------------------|-------------|
| `pending`           | Room added, not yet sent |
| `sent_for_approval` | Sent to employee for approval |
| `approved`          | Employee approved this room |
| `declined`          | Employee declined this room |

### Request Status Values
| Status               | Description |
|----------------------|-------------|
| `open_request`       | Request opened |
| `offer_pending`      | Agent yet to send offers |
| `offer_sent`         | Offers sent to employee |
| `approval_received`  | Employee approved a selection |
| `request_closed`     | Booking completed |
| `void`               | Cancelled/voided |

### Payment Status Values
| Status               | Description |
|----------------------|-------------|
| `payment_pending`    | Awaiting payment |
| `payment_success`    | Payment completed |
| `payment_failure`    | Payment failed |
| `payment_declined`   | Payment declined |
| `payment_awaiting`   | Awaiting confirmation |
| `payment_cancel`     | Payment cancelled |
| `payment_expired`    | Payment link expired |
| `payment_refunded`   | Payment refunded |
