"""
Test cases for Request Booking APIs

Run tests with:
    bench --site <site-name> run-tests --module destiin.destiin.custom.api.request_booking.test_request

Or run specific test:
    bench --site <site-name> run-tests --module destiin.destiin.custom.api.request_booking.test_request --test TestStoreReqBooking
"""

import frappe
from frappe.tests import IntegrationTestCase
from unittest.mock import patch, MagicMock
import json


class TestGetAllRequestBookings(IntegrationTestCase):
    """Test cases for get_all_request_bookings API"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_company = cls._create_test_company()
        cls.test_employee = cls._create_test_employee(cls.test_company)
        cls.test_booking = cls._create_test_request_booking(
            cls.test_employee, cls.test_company
        )

    @classmethod
    def tearDownClass(cls):
        # Clean up test data
        frappe.db.rollback()
        super().tearDownClass()

    @classmethod
    def _create_test_company(cls):
        """Create a test company if not exists"""
        company_name = "_Test Company for Booking"
        if not frappe.db.exists("Company", company_name):
            company = frappe.get_doc({
                "doctype": "Company",
                "company_name": company_name,
                "default_currency": "INR",
                "country": "India"
            })
            company.insert(ignore_permissions=True)
            return company.name
        return company_name

    @classmethod
    def _create_test_employee(cls, company):
        """Create a test employee"""
        employee_id = "_Test-Employee-Booking"
        if not frappe.db.exists("Employee", {"employee_name": employee_id}):
            employee = frappe.get_doc({
                "doctype": "Employee",
                "employee_name": employee_id,
                "first_name": "Test",
                "last_name": "Employee",
                "company": company,
                "gender": "Male",
                "date_of_birth": "1990-01-01",
                "date_of_joining": "2020-01-01"
            })
            employee.insert(ignore_permissions=True)
            return employee.name
        return frappe.db.get_value("Employee", {"employee_name": employee_id}, "name")

    @classmethod
    def _create_test_request_booking(cls, employee, company):
        """Create a test request booking"""
        booking_id = f"{employee}_20260201_20260205"
        if not frappe.db.exists("Request Booking Details", {"request_booking_id": booking_id}):
            booking = frappe.get_doc({
                "doctype": "Request Booking Details",
                "request_booking_id": booking_id,
                "employee": employee,
                "company": company,
                "check_in": "2026-02-01",
                "check_out": "2026-02-05",
                "occupancy": 2,
                "adult_count": 2,
                "child_count": 0,
                "room_count": 1,
                "request_status": "req_pending"
            })
            booking.insert(ignore_permissions=True)
            return booking.name
        return frappe.db.get_value("Request Booking Details", {"request_booking_id": booking_id}, "name")

    def test_get_all_request_bookings_without_filters(self):
        """Test fetching all request bookings without any filters"""
        from destiin.destiin.custom.api.request_booking.request import get_all_request_bookings

        result = get_all_request_bookings()

        self.assertIn("response", result)
        self.assertTrue(result["response"]["success"])
        self.assertIsInstance(result["response"]["data"], list)

    def test_get_all_request_bookings_filter_by_company(self):
        """Test fetching request bookings filtered by company"""
        from destiin.destiin.custom.api.request_booking.request import get_all_request_bookings

        result = get_all_request_bookings(company=self.test_company)

        self.assertIn("response", result)
        self.assertTrue(result["response"]["success"])
        # All returned bookings should belong to the filtered company
        for booking in result["response"]["data"]:
            if booking.get("company"):
                self.assertEqual(booking["company"]["id"], self.test_company)

    def test_get_all_request_bookings_filter_by_employee(self):
        """Test fetching request bookings filtered by employee"""
        from destiin.destiin.custom.api.request_booking.request import get_all_request_bookings

        result = get_all_request_bookings(employee=self.test_employee)

        self.assertIn("response", result)
        self.assertTrue(result["response"]["success"])
        # All returned bookings should belong to the filtered employee
        for booking in result["response"]["data"]:
            if booking.get("employee"):
                self.assertEqual(booking["employee"]["id"], self.test_employee)

    def test_get_all_request_bookings_filter_by_status(self):
        """Test fetching request bookings filtered by status"""
        from destiin.destiin.custom.api.request_booking.request import get_all_request_bookings

        result = get_all_request_bookings(status="req_pending")

        self.assertIn("response", result)
        self.assertTrue(result["response"]["success"])

    def test_get_all_request_bookings_filter_by_company_and_employee(self):
        """Test fetching request bookings filtered by both company and employee"""
        from destiin.destiin.custom.api.request_booking.request import get_all_request_bookings

        result = get_all_request_bookings(
            company=self.test_company,
            employee=self.test_employee
        )

        self.assertIn("response", result)
        self.assertTrue(result["response"]["success"])

    def test_get_all_request_bookings_nonexistent_company(self):
        """Test fetching request bookings with non-existent company filter"""
        from destiin.destiin.custom.api.request_booking.request import get_all_request_bookings

        result = get_all_request_bookings(company="NonExistent Company XYZ")

        self.assertIn("response", result)
        self.assertTrue(result["response"]["success"])
        self.assertEqual(len(result["response"]["data"]), 0)

    def test_get_all_request_bookings_response_structure(self):
        """Test that response has correct structure with all expected fields"""
        from destiin.destiin.custom.api.request_booking.request import get_all_request_bookings

        result = get_all_request_bookings()

        self.assertIn("response", result)
        response = result["response"]
        self.assertIn("success", response)
        self.assertIn("data", response)

        if response["data"]:
            booking = response["data"][0]
            expected_fields = [
                "booking_id", "check_in", "check_out", "status",
                "status_code", "rooms_count", "guests_count"
            ]
            for field in expected_fields:
                self.assertIn(field, booking)


class TestStoreReqBooking(IntegrationTestCase):
    """Test cases for store_req_booking API"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_company = cls._create_test_company()
        cls.test_employee = cls._create_test_employee(cls.test_company)

    @classmethod
    def tearDownClass(cls):
        frappe.db.rollback()
        super().tearDownClass()

    @classmethod
    def _create_test_company(cls):
        """Create a test company"""
        company_name = "_Test Company Store Booking"
        if not frappe.db.exists("Company", company_name):
            company = frappe.get_doc({
                "doctype": "Company",
                "company_name": company_name,
                "default_currency": "INR",
                "country": "India"
            })
            company.insert(ignore_permissions=True)
            return company.name
        return company_name

    @classmethod
    def _create_test_employee(cls, company):
        """Create a test employee"""
        employee_id = "_Test-Employee-Store"
        if not frappe.db.exists("Employee", {"employee_name": employee_id}):
            employee = frappe.get_doc({
                "doctype": "Employee",
                "employee_name": employee_id,
                "first_name": "Test",
                "last_name": "Store",
                "company": company,
                "gender": "Male",
                "date_of_birth": "1990-01-01",
                "date_of_joining": "2020-01-01"
            })
            employee.insert(ignore_permissions=True)
            return employee.name
        return frappe.db.get_value("Employee", {"employee_name": employee_id}, "name")

    def test_store_req_booking_minimal_fields(self):
        """Test creating a request booking with minimal required fields"""
        from destiin.destiin.custom.api.request_booking.request import store_req_booking

        frappe.form_dict = frappe._dict({
            "employee": self.test_employee,
            "check_in": "2026-03-01",
            "check_out": "2026-03-05"
        })

        result = store_req_booking()

        self.assertIn("response", result)
        self.assertTrue(result["response"]["success"])
        self.assertIn("data", result["response"])
        self.assertIn("request_booking_id", result["response"]["data"])

    def test_store_req_booking_with_company(self):
        """Test creating a request booking with company"""
        from destiin.destiin.custom.api.request_booking.request import store_req_booking

        frappe.form_dict = frappe._dict({
            "employee": self.test_employee,
            "check_in": "2026-03-10",
            "check_out": "2026-03-15",
            "company": self.test_company
        })

        result = store_req_booking()

        self.assertIn("response", result)
        self.assertTrue(result["response"]["success"])

    def test_store_req_booking_with_occupancy_details(self):
        """Test creating a request booking with full occupancy details"""
        from destiin.destiin.custom.api.request_booking.request import store_req_booking

        frappe.form_dict = frappe._dict({
            "employee": self.test_employee,
            "check_in": "2026-03-20",
            "check_out": "2026-03-25",
            "company": self.test_company,
            "occupancy": 4,
            "adult_count": 2,
            "child_count": 2,
            "room_count": 2
        })

        result = store_req_booking()

        self.assertIn("response", result)
        self.assertTrue(result["response"]["success"])

    def test_store_req_booking_with_hotel_details(self):
        """Test creating a request booking with complete hotel details"""
        from destiin.destiin.custom.api.request_booking.request import store_req_booking

        hotel_details = {
            "hotel_id": "HTL001",
            "hotel_name": "Grand Hotel",
            "supplier": "Booking.com",
            "cancellation_policy": "Free cancellation until 24 hours before check-in",
            "meal_plan": "Breakfast Included",
            "rooms": [
                {
                    "room_id": "RM001",
                    "room_name": "Deluxe Room",
                    "price": 5000,
                    "total_price": 5500,
                    "tax": 500,
                    "currency": "INR"
                },
                {
                    "room_id": "RM002",
                    "room_name": "Suite Room",
                    "price": 8000,
                    "total_price": 8800,
                    "tax": 800,
                    "currency": "INR"
                }
            ]
        }

        frappe.form_dict = frappe._dict({
            "employee": self.test_employee,
            "check_in": "2026-04-01",
            "check_out": "2026-04-05",
            "company": self.test_company,
            "occupancy": 2,
            "adult_count": 2,
            "child_count": 0,
            "room_count": 1,
            "hotel_details": json.dumps(hotel_details)
        })

        result = store_req_booking()

        self.assertIn("response", result)
        self.assertTrue(result["response"]["success"])

    def test_store_req_booking_with_hotel_details_as_dict(self):
        """Test creating a request booking with hotel details as dict (not JSON string)"""
        from destiin.destiin.custom.api.request_booking.request import store_req_booking

        hotel_details = {
            "hotel_id": "HTL002",
            "hotel_name": "Test Hotel",
            "supplier": "Direct",
            "cancellation_policy": "Non-refundable",
            "meal_plan": "Room Only",
            "rooms": [
                {
                    "room_id": "RM003",
                    "room_name": "Standard Room",
                    "price": 3000,
                    "total_price": 3300,
                    "tax": 300,
                    "currency": "INR"
                }
            ]
        }

        frappe.form_dict = frappe._dict({
            "employee": self.test_employee,
            "check_in": "2026-04-10",
            "check_out": "2026-04-15",
            "company": self.test_company,
            "hotel_details": hotel_details
        })

        result = store_req_booking()

        self.assertIn("response", result)
        self.assertTrue(result["response"]["success"])

    def test_store_req_booking_update_existing(self):
        """Test updating an existing request booking"""
        from destiin.destiin.custom.api.request_booking.request import store_req_booking

        # First create a booking
        frappe.form_dict = frappe._dict({
            "employee": self.test_employee,
            "check_in": "2026-05-01",
            "check_out": "2026-05-05",
            "occupancy": 2
        })

        result1 = store_req_booking()
        self.assertTrue(result1["response"]["success"])

        # Update the same booking with new hotel details
        hotel_details = {
            "hotel_id": "HTL003",
            "hotel_name": "Updated Hotel",
            "supplier": "Expedia",
            "cancellation_policy": "Free cancellation",
            "meal_plan": "All Inclusive",
            "rooms": [
                {
                    "room_id": "RM004",
                    "room_name": "Premium Room",
                    "price": 7000,
                    "total_price": 7700,
                    "tax": 700,
                    "currency": "INR"
                }
            ]
        }

        frappe.form_dict = frappe._dict({
            "employee": self.test_employee,
            "check_in": "2026-05-01",
            "check_out": "2026-05-05",
            "occupancy": 3,
            "hotel_details": hotel_details
        })

        result2 = store_req_booking()

        self.assertIn("response", result2)
        self.assertTrue(result2["response"]["success"])
        # Should have the same booking ID
        self.assertEqual(
            result1["response"]["data"]["request_booking_id"],
            result2["response"]["data"]["request_booking_id"]
        )

    def test_store_req_booking_missing_employee(self):
        """Test that missing employee field is handled"""
        from destiin.destiin.custom.api.request_booking.request import store_req_booking

        frappe.form_dict = frappe._dict({
            "check_in": "2026-06-01",
            "check_out": "2026-06-05"
        })

        result = store_req_booking()

        # Should fail or handle gracefully
        self.assertIn("response", result)

    def test_store_req_booking_generates_unique_id(self):
        """Test that booking ID is generated correctly"""
        from destiin.destiin.custom.api.request_booking.request import store_req_booking

        frappe.form_dict = frappe._dict({
            "employee": self.test_employee,
            "check_in": "2026-07-15",
            "check_out": "2026-07-20"
        })

        result = store_req_booking()

        self.assertTrue(result["response"]["success"])
        booking_id = result["response"]["data"]["request_booking_id"]
        # Format should be: employee_id_YYYYMMDD_YYYYMMDD
        self.assertIn("20260715", booking_id)
        self.assertIn("20260720", booking_id)


class TestSendForApproval(IntegrationTestCase):
    """Test cases for send_for_approval API"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_company = cls._create_test_company()
        cls.test_employee = cls._create_test_employee(cls.test_company)
        cls.test_booking = cls._create_test_booking_with_rooms(
            cls.test_employee, cls.test_company
        )

    @classmethod
    def tearDownClass(cls):
        frappe.db.rollback()
        super().tearDownClass()

    @classmethod
    def _create_test_company(cls):
        company_name = "_Test Company Approval"
        if not frappe.db.exists("Company", company_name):
            company = frappe.get_doc({
                "doctype": "Company",
                "company_name": company_name,
                "default_currency": "INR",
                "country": "India"
            })
            company.insert(ignore_permissions=True)
            return company.name
        return company_name

    @classmethod
    def _create_test_employee(cls, company):
        employee_id = "_Test-Employee-Approval"
        if not frappe.db.exists("Employee", {"employee_name": employee_id}):
            employee = frappe.get_doc({
                "doctype": "Employee",
                "employee_name": employee_id,
                "first_name": "Test",
                "last_name": "Approval",
                "company": company,
                "gender": "Male",
                "date_of_birth": "1990-01-01",
                "date_of_joining": "2020-01-01"
            })
            employee.insert(ignore_permissions=True)
            return employee.name
        return frappe.db.get_value("Employee", {"employee_name": employee_id}, "name")

    @classmethod
    def _create_test_booking_with_rooms(cls, employee, company):
        """Create a test booking with cart hotel items and rooms"""
        from destiin.destiin.custom.api.request_booking.request import store_req_booking

        hotel_details = {
            "hotel_id": "HTL_APPROVAL_001",
            "hotel_name": "Approval Test Hotel",
            "supplier": "Direct",
            "cancellation_policy": "Free cancellation",
            "meal_plan": "Breakfast",
            "rooms": [
                {
                    "room_id": "RM_APP_001",
                    "room_name": "Test Room 1",
                    "price": 5000,
                    "total_price": 5500,
                    "tax": 500,
                    "currency": "INR"
                },
                {
                    "room_id": "RM_APP_002",
                    "room_name": "Test Room 2",
                    "price": 6000,
                    "total_price": 6600,
                    "tax": 600,
                    "currency": "INR"
                }
            ]
        }

        frappe.form_dict = frappe._dict({
            "employee": employee,
            "check_in": "2026-08-01",
            "check_out": "2026-08-05",
            "company": company,
            "hotel_details": hotel_details
        })

        result = store_req_booking()
        return result["response"]["data"]["request_booking_id"]

    @patch('destiin.destiin.custom.api.request_booking.request.send_email_via_api')
    def test_send_for_approval_success(self, mock_email):
        """Test sending a booking for approval"""
        from destiin.destiin.custom.api.request_booking.request import send_for_approval

        mock_email.return_value = {"success": True}

        frappe.form_dict = frappe._dict({
            "request_booking_id": self.test_booking,
            "selected_items": json.dumps([
                {
                    "hotel_id": "HTL_APPROVAL_001",
                    "room_ids": ["RM_APP_001", "RM_APP_002"]
                }
            ])
        })

        result = send_for_approval()

        self.assertIn("response", result)

    @patch('destiin.destiin.custom.api.request_booking.request.send_email_via_api')
    def test_send_for_approval_with_selected_items_as_list(self, mock_email):
        """Test send_for_approval with selected_items as list instead of JSON string"""
        from destiin.destiin.custom.api.request_booking.request import send_for_approval

        mock_email.return_value = {"success": True}

        frappe.form_dict = frappe._dict({
            "request_booking_id": self.test_booking,
            "selected_items": [
                {
                    "hotel_id": "HTL_APPROVAL_001",
                    "room_ids": ["RM_APP_001"]
                }
            ]
        })

        result = send_for_approval()

        self.assertIn("response", result)

    def test_send_for_approval_missing_booking_id(self):
        """Test send_for_approval without request_booking_id"""
        from destiin.destiin.custom.api.request_booking.request import send_for_approval

        frappe.form_dict = frappe._dict({
            "selected_items": [{"hotel_id": "HTL001", "room_ids": ["RM001"]}]
        })

        result = send_for_approval()

        self.assertIn("response", result)
        # Should handle missing booking ID gracefully

    def test_send_for_approval_nonexistent_booking(self):
        """Test send_for_approval with non-existent booking ID"""
        from destiin.destiin.custom.api.request_booking.request import send_for_approval

        frappe.form_dict = frappe._dict({
            "request_booking_id": "NONEXISTENT_BOOKING_123",
            "selected_items": [{"hotel_id": "HTL001", "room_ids": ["RM001"]}]
        })

        result = send_for_approval()

        self.assertIn("response", result)
        # Should fail gracefully for non-existent booking


class TestApproveBooking(IntegrationTestCase):
    """Test cases for approve_booking API"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_company = cls._create_test_company()
        cls.test_employee = cls._create_test_employee(cls.test_company)
        cls.test_booking = cls._create_test_booking_for_approval(
            cls.test_employee, cls.test_company
        )

    @classmethod
    def tearDownClass(cls):
        frappe.db.rollback()
        super().tearDownClass()

    @classmethod
    def _create_test_company(cls):
        company_name = "_Test Company Approve"
        if not frappe.db.exists("Company", company_name):
            company = frappe.get_doc({
                "doctype": "Company",
                "company_name": company_name,
                "default_currency": "INR",
                "country": "India"
            })
            company.insert(ignore_permissions=True)
            return company.name
        return company_name

    @classmethod
    def _create_test_employee(cls, company):
        employee_id = "_Test-Employee-Approve"
        if not frappe.db.exists("Employee", {"employee_name": employee_id}):
            employee = frappe.get_doc({
                "doctype": "Employee",
                "employee_name": employee_id,
                "first_name": "Test",
                "last_name": "Approve",
                "company": company,
                "gender": "Male",
                "date_of_birth": "1990-01-01",
                "date_of_joining": "2020-01-01"
            })
            employee.insert(ignore_permissions=True)
            return employee.name
        return frappe.db.get_value("Employee", {"employee_name": employee_id}, "name")

    @classmethod
    def _create_test_booking_for_approval(cls, employee, company):
        """Create a test booking with rooms ready for approval"""
        from destiin.destiin.custom.api.request_booking.request import store_req_booking

        hotel_details = {
            "hotel_id": "HTL_APPROVE_001",
            "hotel_name": "Approve Test Hotel",
            "supplier": "Direct",
            "cancellation_policy": "Free",
            "meal_plan": "BB",
            "rooms": [
                {
                    "room_id": "RM_APR_001",
                    "room_name": "Approve Room 1",
                    "price": 4000,
                    "total_price": 4400,
                    "tax": 400,
                    "currency": "INR"
                }
            ]
        }

        frappe.form_dict = frappe._dict({
            "employee": employee,
            "check_in": "2026-09-01",
            "check_out": "2026-09-05",
            "company": company,
            "hotel_details": hotel_details
        })

        result = store_req_booking()
        return result["response"]["data"]["request_booking_id"]

    def test_approve_booking_success(self):
        """Test approving a booking"""
        from destiin.destiin.custom.api.request_booking.request import approve_booking

        frappe.form_dict = frappe._dict({
            "request_booking_id": self.test_booking,
            "employee": self.test_employee,
            "selected_items": json.dumps([
                {
                    "hotel_id": "HTL_APPROVE_001",
                    "room_ids": ["RM_APR_001"]
                }
            ])
        })

        result = approve_booking()

        self.assertIn("response", result)

    def test_approve_booking_with_list_items(self):
        """Test approve_booking with selected_items as list"""
        from destiin.destiin.custom.api.request_booking.request import approve_booking

        frappe.form_dict = frappe._dict({
            "request_booking_id": self.test_booking,
            "employee": self.test_employee,
            "selected_items": [
                {
                    "hotel_id": "HTL_APPROVE_001",
                    "room_ids": ["RM_APR_001"]
                }
            ]
        })

        result = approve_booking()

        self.assertIn("response", result)

    def test_approve_booking_missing_employee(self):
        """Test approve_booking without employee field"""
        from destiin.destiin.custom.api.request_booking.request import approve_booking

        frappe.form_dict = frappe._dict({
            "request_booking_id": self.test_booking,
            "selected_items": [{"hotel_id": "HTL001", "room_ids": ["RM001"]}]
        })

        result = approve_booking()

        self.assertIn("response", result)

    def test_approve_booking_nonexistent_booking(self):
        """Test approve_booking with non-existent booking"""
        from destiin.destiin.custom.api.request_booking.request import approve_booking

        frappe.form_dict = frappe._dict({
            "request_booking_id": "NONEXISTENT_123",
            "employee": self.test_employee,
            "selected_items": [{"hotel_id": "HTL001", "room_ids": ["RM001"]}]
        })

        result = approve_booking()

        self.assertIn("response", result)


class TestHelperFunctions(IntegrationTestCase):
    """Test cases for helper functions"""

    def test_generate_request_booking_id(self):
        """Test request booking ID generation"""
        from destiin.destiin.custom.api.request_booking.request import generate_request_booking_id

        booking_id = generate_request_booking_id("EMP001", "2026-01-15", "2026-01-20")

        self.assertEqual(booking_id, "EMP001_20260115_20260120")

    def test_generate_request_booking_id_different_dates(self):
        """Test booking ID generation with different date formats"""
        from destiin.destiin.custom.api.request_booking.request import generate_request_booking_id

        booking_id = generate_request_booking_id("HR-EMP-00001", "2026-12-25", "2027-01-02")

        self.assertEqual(booking_id, "HR-EMP-00001_20261225_20270102")

    def test_get_next_agent_round_robin(self):
        """Test round robin agent assignment"""
        from destiin.destiin.custom.api.request_booking.request import get_next_agent_round_robin

        # This test may return None if no agents exist
        agent = get_next_agent_round_robin()

        # Agent should be either a valid user or None
        if agent:
            self.assertTrue(frappe.db.exists("User", agent))
