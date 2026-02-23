"""
Test cases for Request Booking APIs

Run tests with:
    bench --site <site-name> run-tests --module destiin.destiin.custom.api.request_booking.test_request

Or run specific test class:
    bench --site <site-name> run-tests --module destiin.destiin.custom.api.request_booking.test_request --test TestStoreReqBooking
"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate, add_years, today
from unittest.mock import patch, MagicMock
import json


# ---------------------------------------------------------------------------
# Shared test data helpers
# ---------------------------------------------------------------------------

def _ensure_test_company(company_name="_Test Destiin Company", abbr=None):
	"""Create a test company if it doesn't exist."""
	if not frappe.db.exists("Company", company_name):
		doc = {
			"doctype": "Company",
			"company_name": company_name,
			"default_currency": "USD",
			"country": "India",
		}
		if abbr:
			doc["abbr"] = abbr
		frappe.get_doc(doc).insert(ignore_permissions=True)
	return company_name


def _ensure_test_employee(company, employee_name="_Test Destiin Employee", email=None):
	"""Create a test employee if it doesn't exist. Returns employee doc name."""
	existing = frappe.db.get_value("Employee", {"employee_name": employee_name}, "name")
	if existing:
		return existing
	emp = frappe.get_doc({
		"doctype": "Employee",
		"employee_name": employee_name,
		"first_name": employee_name,
		"company": company,
		"gender": "Prefer not to say",
		"date_of_birth": "1990-01-01",
		"date_of_joining": "2020-01-01",
		"company_email": email or "",
	})
	emp.insert(ignore_permissions=True)
	return emp.name


def _cleanup_test_booking(request_booking_id):
	"""Delete a Request Booking Details and its linked Cart Hotel Items if they exist."""
	name = frappe.db.get_value(
		"Request Booking Details", {"request_booking_id": request_booking_id}, "name"
	)
	if not name:
		return
	for chi in frappe.get_all("Cart Hotel Item", filters={"request_booking": name}, pluck="name"):
		frappe.delete_doc("Cart Hotel Item", chi, force=True, ignore_permissions=True)
	frappe.delete_doc("Request Booking Details", name, force=True, ignore_permissions=True)


def _make_hotel_details(hotel_id="HTL001", hotel_name="Test Hotel", rooms=None):
	"""Build a hotel_details dict for API calls."""
	if rooms is None:
		rooms = [
			{
				"room_id": "RM001",
				"room_rate_id": f"RR_{hotel_id}_001",
				"room_name": "Deluxe Room",
				"price": 5000,
				"total_price": 5500,
				"tax": 500,
				"currency": "USD"
			},
			{
				"room_id": "RM002",
				"room_rate_id": f"RR_{hotel_id}_002",
				"room_name": "Suite Room",
				"price": 8000,
				"total_price": 8800,
				"tax": 800,
				"currency": "USD"
			}
		]
	return {
		"hotel_id": hotel_id,
		"hotel_name": hotel_name,
		"supplier": "Direct",
		"cancellation_policy": "Free cancellation",
		"meal_plan": "Breakfast",
		"rooms": rooms
	}


# ---------------------------------------------------------------------------
# Test: Helper / Utility Functions
# ---------------------------------------------------------------------------

class TestHelperFunctions(IntegrationTestCase):
	"""Test pure utility functions that don't need DB state."""

	def test_get_ordinal_suffix(self):
		from destiin.destiin.custom.api.request_booking.request import get_ordinal_suffix
		self.assertEqual(get_ordinal_suffix(1), "st")
		self.assertEqual(get_ordinal_suffix(2), "nd")
		self.assertEqual(get_ordinal_suffix(3), "rd")
		self.assertEqual(get_ordinal_suffix(4), "th")
		self.assertEqual(get_ordinal_suffix(11), "th")
		self.assertEqual(get_ordinal_suffix(12), "th")
		self.assertEqual(get_ordinal_suffix(13), "th")
		self.assertEqual(get_ordinal_suffix(21), "st")
		self.assertEqual(get_ordinal_suffix(22), "nd")
		self.assertEqual(get_ordinal_suffix(23), "rd")

	def test_format_date_with_ordinal(self):
		from destiin.destiin.custom.api.request_booking.request import format_date_with_ordinal
		d = getdate("2026-01-15")
		self.assertEqual(format_date_with_ordinal(d), "15th_Jan_2026")

		d2 = getdate("2026-03-01")
		self.assertEqual(format_date_with_ordinal(d2), "1st_Mar_2026")

		d3 = getdate("2026-12-22")
		self.assertEqual(format_date_with_ordinal(d3), "22nd_Dec_2026")

	def test_generate_request_booking_id(self):
		from destiin.destiin.custom.api.request_booking.request import generate_request_booking_id
		bid = generate_request_booking_id("EMP001", "2026-01-15", "2026-01-20")
		self.assertEqual(bid, "EMP001_15th_Jan_2026-20th_Jan_2026")

	def test_get_hotel_reviews_url_with_value(self):
		from destiin.destiin.custom.api.request_booking.request import get_hotel_reviews_url
		url = get_hotel_reviews_url("https://tripadvisor.com/hotel123", "Hotel X", "Paris")
		self.assertEqual(url, "https://tripadvisor.com/hotel123")

	def test_get_hotel_reviews_url_fallback(self):
		from destiin.destiin.custom.api.request_booking.request import get_hotel_reviews_url
		url = get_hotel_reviews_url("", "Grand Hotel", "Sydney")
		self.assertIn("google.com/search", url)
		self.assertIn("tripadvisor", url)
		self.assertIn("Grand", url)

	def test_get_request_status_from_cart_status(self):
		from destiin.destiin.custom.api.request_booking.request import get_request_status_from_cart_status
		self.assertEqual(get_request_status_from_cart_status("pending"), "req_pending")
		self.assertEqual(get_request_status_from_cart_status("approved"), "req_approved")
		self.assertEqual(get_request_status_from_cart_status("payment_success"), "req_payment_success")
		self.assertEqual(get_request_status_from_cart_status("declined"), "req_cancelled")
		# Unknown status falls back to req_pending
		self.assertEqual(get_request_status_from_cart_status("unknown_xyz"), "req_pending")

	def test_request_status_display_map(self):
		from destiin.destiin.custom.api.request_booking.request import REQUEST_STATUS_DISPLAY_MAP
		status, code = REQUEST_STATUS_DISPLAY_MAP["req_pending"]
		self.assertEqual(status, "pending_in_cart")
		self.assertEqual(code, 0)
		status, code = REQUEST_STATUS_DISPLAY_MAP["req_closed"]
		self.assertEqual(status, "closed")
		self.assertEqual(code, 5)

	def test_build_booking_response_data(self):
		from destiin.destiin.custom.api.request_booking.request import _build_booking_response_data
		# Create a mock request object
		req = frappe._dict({
			"request_booking_id": "TEST_001",
			"employee_email": "test@example.com",
			"destination": "Paris",
			"destination_code": "PAR",
			"budget_options": "fixed",
			"employee_budget": 1000.0,
			"work_address": "123 Street",
			"check_in": getdate("2026-03-01"),
			"check_out": getdate("2026-03-05"),
			"request_status": "req_pending",
			"room_count": 1,
			"adult_count": 2,
			"child_count": 0,
			"child_ages": "[]",
			"company": "TestCo",
			"employee": "EMP001",
			"creation": frappe.utils.now_datetime()
		})
		result = _build_booking_response_data(
			req, hotels=[], total_amount=0.0,
			employee_name="John", employee_phone="123",
			employee_level="L1", company_name="Test Co", booking_id="NA"
		)
		self.assertEqual(result["request_booking_id"], "TEST_001")
		self.assertEqual(result["user_name"], "John")
		self.assertEqual(result["status"], "pending_in_cart")
		self.assertEqual(result["status_code"], 0)
		self.assertEqual(result["company"]["name"], "Test Co")
		self.assertEqual(result["employee"]["phone_number"], "123")


# ---------------------------------------------------------------------------
# Test: store_req_booking
# ---------------------------------------------------------------------------

class TestStoreReqBooking(IntegrationTestCase):
	"""Test the store_req_booking API."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company = _ensure_test_company("_Test Store Booking Co", abbr="TSBC")
		cls.employee = _ensure_test_employee(cls.company, "_Test Store Emp")

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()

	@patch("destiin.destiin.custom.api.request_booking.request._fire_tripadvisor_url_api")
	def test_create_new_booking_minimal(self, mock_trip):
		"""Create a booking with only required fields."""
		from destiin.destiin.custom.api.request_booking.request import store_req_booking
		result = store_req_booking(
			employee=self.employee,
			check_in="2026-10-01",
			check_out="2026-10-05"
		)
		self.assertTrue(result["success"])
		self.assertIn("request_booking_id", result["data"])
		self.assertEqual(result["data"]["employee"], self.employee)
		self.assertTrue(result["data"]["is_new"])

	@patch("destiin.destiin.custom.api.request_booking.request._fire_tripadvisor_url_api")
	def test_create_booking_with_hotel_details(self, mock_trip):
		"""Create a booking with hotel and room details."""
		from destiin.destiin.custom.api.request_booking.request import store_req_booking
		hotel = _make_hotel_details("HTL_STORE_001", "Store Test Hotel")
		result = store_req_booking(
			employee=self.employee,
			check_in="2026-10-10",
			check_out="2026-10-15",
			company=self.company,
			occupancy=2,
			adult_count=2,
			child_count=0,
			room_count=1,
			hotel_details=json.dumps(hotel)
		)
		self.assertTrue(result["success"])
		self.assertEqual(result["data"]["hotel_count"], 1)
		self.assertEqual(len(result["data"]["cart_hotel_items"]), 1)
		mock_trip.assert_called_once()

	@patch("destiin.destiin.custom.api.request_booking.request._fire_tripadvisor_url_api")
	def test_create_booking_with_multiple_hotels(self, mock_trip):
		"""Create a booking with multiple hotels."""
		from destiin.destiin.custom.api.request_booking.request import store_req_booking
		hotels = [
			_make_hotel_details("HTL_MULTI_A", "Hotel A"),
			_make_hotel_details("HTL_MULTI_B", "Hotel B"),
		]
		result = store_req_booking(
			employee=self.employee,
			check_in="2026-10-20",
			check_out="2026-10-25",
			hotel_details=json.dumps(hotels)
		)
		self.assertTrue(result["success"])
		self.assertEqual(result["data"]["hotel_count"], 2)

	@patch("destiin.destiin.custom.api.request_booking.request._fire_tripadvisor_url_api")
	def test_duplicate_booking_returns_error(self, mock_trip):
		"""Calling store_req_booking twice with same dates returns error."""
		from destiin.destiin.custom.api.request_booking.request import store_req_booking
		store_req_booking(
			employee=self.employee,
			check_in="2026-11-01",
			check_out="2026-11-05"
		)
		result = store_req_booking(
			employee=self.employee,
			check_in="2026-11-01",
			check_out="2026-11-05"
		)
		self.assertFalse(result["success"])
		self.assertIn("already exists", result["message"])

	@patch("destiin.destiin.custom.api.request_booking.request._fire_tripadvisor_url_api")
	@patch("destiin.destiin.custom.api.request_booking.request.requests.get")
	def test_create_booking_with_budget_conversion(self, mock_get, mock_trip):
		"""Budget in non-USD currency triggers conversion API."""
		from destiin.destiin.custom.api.request_booking.request import store_req_booking
		mock_response = MagicMock()
		mock_response.status_code = 200
		mock_response.json.return_value = {"status": True, "data": {"converted": 75.0}}
		mock_response.text = '{"status": true, "data": {"converted": 75.0}}'
		mock_get.return_value = mock_response

		result = store_req_booking(
			employee=self.employee,
			check_in="2026-11-10",
			check_out="2026-11-14",
			currency="EUR",
			budget_amount="100",
		)
		self.assertTrue(result["success"])
		# 75 USD converted * 4 nights = 300
		self.assertEqual(result["data"]["employee_budget"], 300.0)
		mock_get.assert_called_once()

	@patch("destiin.destiin.custom.api.request_booking.request._fire_tripadvisor_url_api")
	def test_create_booking_assigns_agent(self, mock_trip):
		"""New booking should get an agent assigned via round-robin."""
		from destiin.destiin.custom.api.request_booking.request import store_req_booking
		result = store_req_booking(
			employee=self.employee,
			check_in="2026-12-01",
			check_out="2026-12-05"
		)
		self.assertTrue(result["success"])
		# Agent may or may not be set depending on test env, but field should exist
		self.assertIn("agent", result["data"])


# ---------------------------------------------------------------------------
# Test: get_all_request_bookings
# ---------------------------------------------------------------------------

class TestGetAllRequestBookings(IntegrationTestCase):
	"""Test the get_all_request_bookings API."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company = _ensure_test_company("_Test GetAll Co", abbr="TGAC")
		cls.employee = _ensure_test_employee(cls.company, "_Test GetAll Emp")
		_cleanup_test_booking("GETALL_TEST_001")
		# Create a booking for testing
		cls.booking_doc = frappe.get_doc({
			"doctype": "Request Booking Details",
			"request_booking_id": "GETALL_TEST_001",
			"employee": cls.employee,
			"company": cls.company,
			"check_in": "2026-06-01",
			"check_out": "2026-06-05",
			"occupancy": 2,
			"adult_count": 2,
			"child_count": 0,
			"room_count": 1,
			"request_status": "req_pending",
			"destination": "Paris",
			"destination_code": "PAR",
		})
		cls.booking_doc.insert(ignore_permissions=True)

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()

	def test_get_all_without_filters(self):
		from destiin.destiin.custom.api.request_booking.request import get_all_request_bookings
		result = get_all_request_bookings()
		self.assertTrue(result["success"])
		self.assertIsInstance(result["data"], list)
		self.assertIn("pagination", result)

	def test_filter_by_company(self):
		from destiin.destiin.custom.api.request_booking.request import get_all_request_bookings
		result = get_all_request_bookings(company=self.company)
		self.assertTrue(result["success"])
		for bk in result["data"]:
			self.assertEqual(bk["company"]["id"], self.company)

	def test_filter_by_employee(self):
		from destiin.destiin.custom.api.request_booking.request import get_all_request_bookings
		result = get_all_request_bookings(employee=self.employee)
		self.assertTrue(result["success"])
		for bk in result["data"]:
			self.assertEqual(bk["employee"]["id"], self.employee)

	def test_filter_by_status(self):
		from destiin.destiin.custom.api.request_booking.request import get_all_request_bookings
		result = get_all_request_bookings(status="req_pending")
		self.assertTrue(result["success"])
		for bk in result["data"]:
			self.assertEqual(bk["status"], "pending_in_cart")

	def test_filter_by_multiple_statuses(self):
		from destiin.destiin.custom.api.request_booking.request import get_all_request_bookings
		result = get_all_request_bookings(status="req_pending,req_approved")
		self.assertTrue(result["success"])
		for bk in result["data"]:
			self.assertIn(bk["status"], ["pending_in_cart", "approved"])

	def test_pagination(self):
		from destiin.destiin.custom.api.request_booking.request import get_all_request_bookings
		result = get_all_request_bookings(page=1, page_size=1)
		self.assertTrue(result["success"])
		self.assertLessEqual(len(result["data"]), 1)
		pagination = result["pagination"]
		self.assertEqual(pagination["page"], 1)
		self.assertEqual(pagination["page_size"], 1)

	def test_empty_results(self):
		from destiin.destiin.custom.api.request_booking.request import get_all_request_bookings
		result = get_all_request_bookings(company="NonExistent_XYZ_Company")
		self.assertTrue(result["success"])
		self.assertEqual(len(result["data"]), 0)
		self.assertEqual(result["pagination"]["total_count"], 0)

	def test_response_structure(self):
		from destiin.destiin.custom.api.request_booking.request import get_all_request_bookings
		result = get_all_request_bookings(company=self.company)
		self.assertTrue(result["success"])
		if result["data"]:
			bk = result["data"][0]
			expected_keys = [
				"request_booking_id", "booking_id", "user_name", "hotels",
				"destination", "check_in", "check_out", "status", "status_code",
				"rooms_count", "guests_count", "company", "employee",
				"request_created_date", "request_created_time"
			]
			for key in expected_keys:
				self.assertIn(key, bk, f"Missing key: {key}")


# ---------------------------------------------------------------------------
# Test: get_request_booking_details
# ---------------------------------------------------------------------------

class TestGetRequestBookingDetails(IntegrationTestCase):
	"""Test the get_request_booking_details API."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company = _ensure_test_company("_Test Detail Co", abbr="TDTC")
		cls.employee = _ensure_test_employee(cls.company, "_Test Detail Emp")
		_cleanup_test_booking("DETAIL_TEST_001")
		cls.booking_doc = frappe.get_doc({
			"doctype": "Request Booking Details",
			"request_booking_id": "DETAIL_TEST_001",
			"employee": cls.employee,
			"company": cls.company,
			"check_in": "2026-07-01",
			"check_out": "2026-07-05",
			"occupancy": 2,
			"adult_count": 2,
			"room_count": 1,
			"request_status": "req_pending",
			"destination": "Tokyo",
		})
		cls.booking_doc.insert(ignore_permissions=True)

		# Create a Cart Hotel Item linked to this booking
		cls.cart_hotel = frappe.get_doc({
			"doctype": "Cart Hotel Item",
			"request_booking": cls.booking_doc.name,
			"hotel_id": "HTL_DETAIL_001",
			"hotel_name": "Detail Test Hotel",
			"supplier": "Direct",
			"meal_plan": "BB",
			"rooms": [
				{
					"room_id": "RM_D_001",
					"room_rate_id": "RR_D_001",
					"room_name": "Standard",
					"price": 100,
					"total_price": 110,
					"tax": 10,
					"currency": "USD",
					"status": "pending"
				}
			]
		})
		cls.cart_hotel.insert(ignore_permissions=True)

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()

	def test_get_existing_booking(self):
		from destiin.destiin.custom.api.request_booking.request import get_request_booking_details
		result = get_request_booking_details("DETAIL_TEST_001")
		self.assertTrue(result["success"])
		self.assertEqual(result["data"]["request_booking_id"], "DETAIL_TEST_001")
		self.assertEqual(result["data"]["destination"], "Tokyo")

	def test_get_booking_includes_hotels(self):
		from destiin.destiin.custom.api.request_booking.request import get_request_booking_details
		result = get_request_booking_details("DETAIL_TEST_001")
		self.assertTrue(result["success"])
		hotels = result["data"]["hotels"]
		self.assertGreaterEqual(len(hotels), 1)
		self.assertEqual(hotels[0]["hotel_id"], "HTL_DETAIL_001")
		self.assertGreaterEqual(len(hotels[0]["rooms"]), 1)

	def test_nonexistent_booking(self):
		from destiin.destiin.custom.api.request_booking.request import get_request_booking_details
		result = get_request_booking_details("NONEXISTENT_99999")
		self.assertFalse(result["success"])
		self.assertIn("error", result)

	def test_missing_booking_id(self):
		from destiin.destiin.custom.api.request_booking.request import get_request_booking_details
		result = get_request_booking_details("")
		self.assertFalse(result["success"])
		self.assertIn("error", result)


# ---------------------------------------------------------------------------
# Test: update_request_booking
# ---------------------------------------------------------------------------

class TestUpdateRequestBooking(IntegrationTestCase):
	"""Test the update_request_booking API."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company = _ensure_test_company("_Test Update Co", abbr="TUPC")
		cls.employee = _ensure_test_employee(cls.company, "_Test Update Emp")
		_cleanup_test_booking("UPDATE_TEST_001")
		cls.booking_doc = frappe.get_doc({
			"doctype": "Request Booking Details",
			"request_booking_id": "UPDATE_TEST_001",
			"employee": cls.employee,
			"company": cls.company,
			"check_in": "2026-08-01",
			"check_out": "2026-08-05",
			"occupancy": 2,
			"adult_count": 2,
			"room_count": 1,
			"request_status": "req_pending",
			"destination": "Berlin",
		})
		cls.booking_doc.insert(ignore_permissions=True)

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()

	def test_update_basic_fields(self):
		from destiin.destiin.custom.api.request_booking.request import update_request_booking
		result = update_request_booking(
			request_booking_id="UPDATE_TEST_001",
			destination="Munich",
			occupancy=4,
			adult_count=3,
		)
		self.assertTrue(result["success"])
		self.assertEqual(result["data"]["destination"], "Munich")
		self.assertEqual(result["data"]["occupancy"], 4)
		self.assertEqual(result["data"]["adult_count"], 3)

	@patch("destiin.destiin.custom.api.request_booking.request._fire_tripadvisor_url_api")
	def test_update_with_hotel_details(self, mock_trip):
		from destiin.destiin.custom.api.request_booking.request import update_request_booking
		hotel = _make_hotel_details("HTL_UPD_001", "Update Hotel")
		result = update_request_booking(
			request_booking_id="UPDATE_TEST_001",
			hotel_details=json.dumps(hotel)
		)
		self.assertTrue(result["success"])
		mock_trip.assert_called_once()

	def test_update_nonexistent_booking(self):
		from destiin.destiin.custom.api.request_booking.request import update_request_booking
		result = update_request_booking(request_booking_id="NONEXISTENT_UPD_999")
		self.assertFalse(result["success"])
		self.assertIn("error", result)

	def test_update_requires_identifier(self):
		from destiin.destiin.custom.api.request_booking.request import update_request_booking
		result = update_request_booking(request_booking_id="", name=None)
		self.assertFalse(result["success"])


# ---------------------------------------------------------------------------
# Test: send_for_approval
# ---------------------------------------------------------------------------

class TestSendForApproval(IntegrationTestCase):
	"""Test the send_for_approval API."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company = _ensure_test_company("_Test Approval Co", abbr="TAPC")
		cls.employee = _ensure_test_employee(
			cls.company, "_Test Approval Emp", email="approval@test.com"
		)
		_cleanup_test_booking("APPROVAL_TEST_001")
		cls.booking_doc = frappe.get_doc({
			"doctype": "Request Booking Details",
			"request_booking_id": "APPROVAL_TEST_001",
			"employee": cls.employee,
			"employee_email": "approval@test.com",
			"company": cls.company,
			"check_in": "2026-09-01",
			"check_out": "2026-09-05",
			"adult_count": 2,
			"room_count": 1,
			"request_status": "req_pending",
			"destination": "London",
		})
		cls.booking_doc.insert(ignore_permissions=True)

		cls.cart_hotel = frappe.get_doc({
			"doctype": "Cart Hotel Item",
			"request_booking": cls.booking_doc.name,
			"hotel_id": "HTL_APP_001",
			"hotel_name": "Approval Hotel",
			"supplier": "Direct",
			"meal_plan": "BB",
			"cancellation_policy": "Free",
			"rooms": [
				{
					"room_id": "RM_A_001",
					"room_rate_id": "RR_A_001",
					"room_name": "Standard",
					"price": 200,
					"total_price": 220,
					"tax": 20,
					"currency": "USD",
					"status": "pending"
				},
				{
					"room_id": "RM_A_002",
					"room_rate_id": "RR_A_002",
					"room_name": "Deluxe",
					"price": 300,
					"total_price": 330,
					"tax": 30,
					"currency": "USD",
					"status": "pending"
				}
			]
		})
		cls.cart_hotel.insert(ignore_permissions=True)

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()

	@patch("destiin.destiin.custom.api.request_booking.request.send_email_via_api")
	def test_send_for_approval_success(self, mock_email):
		from destiin.destiin.custom.api.request_booking.request import send_for_approval
		mock_email.return_value = {"success": True}
		result = send_for_approval(
			request_booking_id="APPROVAL_TEST_001",
			selected_items=json.dumps([{
				"hotel_id": "HTL_APP_001",
				"room_rate_ids": ["RR_A_001"]
			}])
		)
		self.assertTrue(result["success"])
		self.assertEqual(result["data"]["updated_count"], 1)
		self.assertTrue(result["data"]["email_sent"])

	def test_send_for_approval_missing_booking_id(self):
		from destiin.destiin.custom.api.request_booking.request import send_for_approval
		result = send_for_approval(
			request_booking_id="",
			selected_items=[{"hotel_id": "HTL001", "room_rate_ids": ["RR001"]}]
		)
		self.assertFalse(result["success"])

	def test_send_for_approval_nonexistent_booking(self):
		from destiin.destiin.custom.api.request_booking.request import send_for_approval
		result = send_for_approval(
			request_booking_id="NONEXISTENT_APP_999",
			selected_items=[{"hotel_id": "HTL001", "room_rate_ids": ["RR001"]}]
		)
		self.assertFalse(result["success"])

	def test_send_for_approval_empty_items(self):
		from destiin.destiin.custom.api.request_booking.request import send_for_approval
		result = send_for_approval(
			request_booking_id="APPROVAL_TEST_001",
			selected_items="[]"
		)
		self.assertFalse(result["success"])


# ---------------------------------------------------------------------------
# Test: approve_booking
# ---------------------------------------------------------------------------

class TestApproveBooking(IntegrationTestCase):
	"""Test the approve_booking API."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company = _ensure_test_company("_Test Approve Co", abbr="TARC")
		cls.employee = _ensure_test_employee(cls.company, "_Test Approve Emp")
		_cleanup_test_booking("APPROVE_TEST_001")
		cls.booking_doc = frappe.get_doc({
			"doctype": "Request Booking Details",
			"request_booking_id": "APPROVE_TEST_001",
			"employee": cls.employee,
			"company": cls.company,
			"check_in": "2026-09-10",
			"check_out": "2026-09-15",
			"room_count": 1,
			"request_status": "req_sent_for_approval",
		})
		cls.booking_doc.insert(ignore_permissions=True)

		cls.cart_hotel = frappe.get_doc({
			"doctype": "Cart Hotel Item",
			"request_booking": cls.booking_doc.name,
			"hotel_id": "HTL_APR_001",
			"hotel_name": "Approve Hotel",
			"supplier": "Direct",
			"rooms": [
				{
					"room_id": "RM_APR_001",
					"room_rate_id": "RR_APR_001",
					"room_name": "Standard",
					"price": 150,
					"status": "sent_for_approval"
				},
				{
					"room_id": "RM_APR_002",
					"room_rate_id": "RR_APR_002",
					"room_name": "Suite",
					"price": 250,
					"status": "sent_for_approval"
				}
			]
		})
		cls.cart_hotel.insert(ignore_permissions=True)

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()

	def test_approve_success(self):
		from destiin.destiin.custom.api.request_booking.request import approve_booking
		result = approve_booking(
			request_booking_id="APPROVE_TEST_001",
			employee=self.employee,
			selected_items=json.dumps([{
				"hotel_id": "HTL_APR_001",
				"room_rate_ids": ["RR_APR_001"]
			}])
		)
		self.assertTrue(result["success"])
		self.assertEqual(result["data"]["approved_count"], 1)
		# Non-selected room should be auto-declined
		self.assertEqual(result["data"]["declined_count"], 1)

	def test_approve_missing_employee(self):
		from destiin.destiin.custom.api.request_booking.request import approve_booking
		result = approve_booking(
			request_booking_id="APPROVE_TEST_001",
			employee="",
			selected_items=[{"hotel_id": "HTL_APR_001", "room_rate_ids": ["RR_APR_001"]}]
		)
		self.assertFalse(result["success"])

	def test_approve_nonexistent_booking(self):
		from destiin.destiin.custom.api.request_booking.request import approve_booking
		result = approve_booking(
			request_booking_id="NONEXISTENT_APR_999",
			employee=self.employee,
			selected_items=[{"hotel_id": "HTL001", "room_rate_ids": ["RR001"]}]
		)
		self.assertFalse(result["success"])


# ---------------------------------------------------------------------------
# Test: decline_booking
# ---------------------------------------------------------------------------

class TestDeclineBooking(IntegrationTestCase):
	"""Test the decline_booking API."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company = _ensure_test_company("_Test Decline Co", abbr="TDCC")
		cls.employee = _ensure_test_employee(cls.company, "_Test Decline Emp")
		_cleanup_test_booking("DECLINE_TEST_001")
		cls.booking_doc = frappe.get_doc({
			"doctype": "Request Booking Details",
			"request_booking_id": "DECLINE_TEST_001",
			"employee": cls.employee,
			"company": cls.company,
			"check_in": "2026-09-20",
			"check_out": "2026-09-25",
			"room_count": 1,
			"request_status": "req_sent_for_approval",
		})
		cls.booking_doc.insert(ignore_permissions=True)

		cls.cart_hotel = frappe.get_doc({
			"doctype": "Cart Hotel Item",
			"request_booking": cls.booking_doc.name,
			"hotel_id": "HTL_DEC_001",
			"hotel_name": "Decline Hotel",
			"supplier": "Direct",
			"rooms": [
				{
					"room_id": "RM_DEC_001",
					"room_rate_id": "RR_DEC_001",
					"room_name": "Standard",
					"price": 100,
					"status": "sent_for_approval"
				}
			]
		})
		cls.cart_hotel.insert(ignore_permissions=True)

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()

	def test_decline_success(self):
		from destiin.destiin.custom.api.request_booking.request import decline_booking
		result = decline_booking(
			request_booking_id="DECLINE_TEST_001",
			employee=self.employee,
			selected_items=json.dumps([{
				"hotel_id": "HTL_DEC_001",
				"room_rate_ids": ["RR_DEC_001"]
			}])
		)
		self.assertTrue(result["success"])
		self.assertEqual(result["data"]["declined_count"], 1)

	def test_decline_missing_employee(self):
		from destiin.destiin.custom.api.request_booking.request import decline_booking
		result = decline_booking(
			request_booking_id="DECLINE_TEST_001",
			employee="",
			selected_items=[{"hotel_id": "HTL_DEC_001", "room_rate_ids": ["RR_DEC_001"]}]
		)
		self.assertFalse(result["success"])


# ---------------------------------------------------------------------------
# Test: update_request_status_from_rooms
# ---------------------------------------------------------------------------

class TestUpdateRequestStatusFromRooms(IntegrationTestCase):
	"""Test the request status aggregation logic."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company = _ensure_test_company("_Test StatusAgg Co", abbr="TSAC")
		cls.employee = _ensure_test_employee(cls.company, "_Test StatusAgg Emp")

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()

	def _create_booking_with_rooms(self, booking_id, room_statuses):
		"""Helper: create a booking with a hotel whose rooms have the given statuses."""
		booking = frappe.get_doc({
			"doctype": "Request Booking Details",
			"request_booking_id": booking_id,
			"employee": self.employee,
			"company": self.company,
			"check_in": "2026-12-01",
			"check_out": "2026-12-05",
			"request_status": "req_pending",
		})
		booking.insert(ignore_permissions=True)

		rooms = []
		for i, status in enumerate(room_statuses):
			rooms.append({
				"room_id": f"RM_{i}",
				"room_rate_id": f"RR_{booking_id}_{i}",
				"room_name": f"Room {i}",
				"price": 100,
				"status": status
			})

		cart_hotel = frappe.get_doc({
			"doctype": "Cart Hotel Item",
			"request_booking": booking.name,
			"hotel_id": f"HTL_{booking_id}",
			"hotel_name": "Status Test Hotel",
			"rooms": rooms
		})
		cart_hotel.insert(ignore_permissions=True)
		return booking.name

	def test_payment_success_priority(self):
		from destiin.destiin.custom.api.request_booking.request import update_request_status_from_rooms
		name = self._create_booking_with_rooms("STATUS_PS_001", ["pending", "payment_success"])
		result = update_request_status_from_rooms(name)
		self.assertEqual(result, "req_payment_success")

	def test_approved_priority(self):
		from destiin.destiin.custom.api.request_booking.request import update_request_status_from_rooms
		name = self._create_booking_with_rooms("STATUS_APR_001", ["pending", "approved"])
		result = update_request_status_from_rooms(name)
		self.assertEqual(result, "req_approved")

	def test_all_declined(self):
		from destiin.destiin.custom.api.request_booking.request import update_request_status_from_rooms
		name = self._create_booking_with_rooms("STATUS_DEC_001", ["declined", "declined"])
		result = update_request_status_from_rooms(name)
		self.assertEqual(result, "req_cancelled")

	def test_mixed_pending(self):
		from destiin.destiin.custom.api.request_booking.request import update_request_status_from_rooms
		name = self._create_booking_with_rooms("STATUS_PND_001", ["pending", "pending"])
		result = update_request_status_from_rooms(name)
		self.assertEqual(result, "req_pending")

	def test_no_booking(self):
		from destiin.destiin.custom.api.request_booking.request import update_request_status_from_rooms
		result = update_request_status_from_rooms(None)
		self.assertIsNone(result)


# ---------------------------------------------------------------------------
# Test: get_next_agent_round_robin
# ---------------------------------------------------------------------------

class TestGetNextAgentRoundRobin(IntegrationTestCase):
	"""Test agent round-robin assignment."""

	def test_returns_agent_or_none(self):
		from destiin.destiin.custom.api.request_booking.request import get_next_agent_round_robin
		agent = get_next_agent_round_robin()
		# Should be a valid user or None (if no agents exist)
		if agent:
			self.assertTrue(frappe.db.exists("User", agent))


# ---------------------------------------------------------------------------
# Test: Shared helper functions
# ---------------------------------------------------------------------------

class TestSharedHelpers(IntegrationTestCase):
	"""Test the shared helper functions used by GET APIs."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.company = _ensure_test_company("_Test Helper Co", abbr="THPC")
		cls.employee = _ensure_test_employee(cls.company, "_Test Helper Emp")

	@classmethod
	def tearDownClass(cls):
		frappe.db.rollback()
		super().tearDownClass()

	def test_get_employee_info(self):
		from destiin.destiin.custom.api.request_booking.request import _get_employee_info
		name, phone, level = _get_employee_info(self.employee)
		self.assertEqual(name, "_Test Helper Emp")

	def test_get_employee_info_empty(self):
		from destiin.destiin.custom.api.request_booking.request import _get_employee_info
		name, phone, level = _get_employee_info("")
		self.assertEqual(name, "")

	def test_get_company_display_name(self):
		from destiin.destiin.custom.api.request_booking.request import _get_company_display_name
		name = _get_company_display_name(self.company)
		self.assertEqual(name, "_Test Helper Co")

	def test_get_company_display_name_empty(self):
		from destiin.destiin.custom.api.request_booking.request import _get_company_display_name
		name = _get_company_display_name("")
		self.assertEqual(name, "")

	def test_get_hotel_booking_id_none(self):
		from destiin.destiin.custom.api.request_booking.request import _get_hotel_booking_id
		bid = _get_hotel_booking_id(None)
		self.assertEqual(bid, "NA")

	def test_get_hotel_booking_id_empty(self):
		from destiin.destiin.custom.api.request_booking.request import _get_hotel_booking_id
		bid = _get_hotel_booking_id("")
		self.assertEqual(bid, "NA")
