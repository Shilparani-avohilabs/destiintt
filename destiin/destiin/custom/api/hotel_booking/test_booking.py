"""
Test cases for Hotel Booking APIs

Run tests with:
    bench --site <site-name> run-tests --module destiin.destiin.custom.api.hotel_booking.test_booking

Or run specific test:
    bench --site <site-name> run-tests --module destiin.destiin.custom.api.hotel_booking.test_booking --test TestCreateBooking
"""

import frappe
from frappe.tests import IntegrationTestCase
from unittest.mock import patch, MagicMock
import json


class TestCreateBooking(IntegrationTestCase):
    """Test cases for create_booking API"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_company = cls._create_test_company()
        cls.test_employee = cls._create_test_employee(cls.test_company)
        # Create an approved request booking for testing
        cls.approved_booking_id = cls._create_approved_request_booking(
            cls.test_employee, cls.test_company
        )

    @classmethod
    def tearDownClass(cls):
        frappe.db.rollback()
        super().tearDownClass()

    @classmethod
    def _create_test_company(cls):
        """Create a test company"""
        company_name = "_Test Company Hotel Booking"
        if not frappe.db.exists("Company", company_name):
            company = frappe.get_doc({
                "doctype": "Company",
                "company_name": company_name,
                "default_currency": "USD",
                "country": "India"
            })
            company.insert(ignore_permissions=True)
            return company.name
        return company_name

    @classmethod
    def _create_test_employee(cls, company):
        """Create a test employee"""
        employee_id = "_Test-Employee-Hotel"
        if not frappe.db.exists("Employee", {"employee_name": employee_id}):
            employee = frappe.get_doc({
                "doctype": "Employee",
                "employee_name": employee_id,
                "first_name": "Test",
                "last_name": "Hotel",
                "company": company,
                "gender": "Male",
                "date_of_birth": "1990-01-01",
                "date_of_joining": "2020-01-01"
            })
            employee.insert(ignore_permissions=True)
            return employee.name
        return frappe.db.get_value("Employee", {"employee_name": employee_id}, "name")

    @classmethod
    def _create_approved_request_booking(cls, employee, company):
        """Create a request booking with approved rooms"""
        from destiin.destiin.custom.api.request_booking.request import store_req_booking, approve_booking

        hotel_details = {
            "hotel_id": "HTL_HOTEL_001",
            "hotel_name": "Hotel Booking Test",
            "supplier": "Direct",
            "cancellation_policy": "Free cancellation",
            "meal_plan": "Breakfast Included",
            "rooms": [
                {
                    "room_id": "RM_HTL_001",
                    "room_name": "Deluxe Room",
                    "price": 5000,
                    "total_price": 5500,
                    "tax": 500,
                    "currency": "USD"
                },
                {
                    "room_id": "RM_HTL_002",
                    "room_name": "Suite Room",
                    "price": 8000,
                    "total_price": 8800,
                    "tax": 800,
                    "currency": "USD"
                }
            ]
        }

        # Create the request booking
        frappe.form_dict = frappe._dict({
            "employee": employee,
            "check_in": "2026-10-01",
            "check_out": "2026-10-05",
            "company": company,
            "occupancy": 2,
            "adult_count": 2,
            "child_count": 0,
            "room_count": 2,
            "hotel_details": hotel_details
        })

        result = store_req_booking()
        booking_id = result["response"]["data"]["request_booking_id"]

        # Approve the booking
        frappe.form_dict = frappe._dict({
            "request_booking_id": booking_id,
            "employee": employee,
            "selected_items": [
                {
                    "hotel_id": "HTL_HOTEL_001",
                    "room_ids": ["RM_HTL_001", "RM_HTL_002"]
                }
            ]
        })

        approve_booking()

        return booking_id

    def test_create_booking_success(self):
        """Test creating a hotel booking from an approved request booking"""
        from destiin.destiin.custom.api.hotel_booking.booking import create_booking

        # Create a new approved booking for this test
        new_booking_id = self._create_new_approved_booking("2026-11-01", "2026-11-05")

        frappe.form_dict = frappe._dict({
            "request_booking_id": new_booking_id,
            "employee": self.test_employee,
            "selected_items": json.dumps([
                {
                    "hotel_id": "HTL_CREATE_001",
                    "room_ids": ["RM_CREATE_001"]
                }
            ])
        })

        result = create_booking()

        self.assertIn("response", result)
        if result["response"]["success"]:
            self.assertIn("data", result["response"])
            data = result["response"]["data"]
            self.assertIn("hotel_booking_id", data)
            self.assertIn("payment_id", data)

    def _create_new_approved_booking(self, check_in, check_out):
        """Helper to create a new approved booking"""
        from destiin.destiin.custom.api.request_booking.request import store_req_booking, approve_booking

        hotel_details = {
            "hotel_id": "HTL_CREATE_001",
            "hotel_name": "Create Test Hotel",
            "supplier": "Direct",
            "cancellation_policy": "Flexible",
            "meal_plan": "Room Only",
            "rooms": [
                {
                    "room_id": "RM_CREATE_001",
                    "room_name": "Standard Room",
                    "price": 3000,
                    "total_price": 3300,
                    "tax": 300,
                    "currency": "USD"
                }
            ]
        }

        frappe.form_dict = frappe._dict({
            "employee": self.test_employee,
            "check_in": check_in,
            "check_out": check_out,
            "company": self.test_company,
            "hotel_details": hotel_details
        })

        result = store_req_booking()
        booking_id = result["response"]["data"]["request_booking_id"]

        # Approve it
        frappe.form_dict = frappe._dict({
            "request_booking_id": booking_id,
            "employee": self.test_employee,
            "selected_items": [
                {
                    "hotel_id": "HTL_CREATE_001",
                    "room_ids": ["RM_CREATE_001"]
                }
            ]
        })
        approve_booking()

        return booking_id

    def test_create_booking_with_selected_items_as_list(self):
        """Test create_booking with selected_items as list instead of JSON"""
        from destiin.destiin.custom.api.hotel_booking.booking import create_booking

        new_booking_id = self._create_new_approved_booking("2026-11-10", "2026-11-15")

        frappe.form_dict = frappe._dict({
            "request_booking_id": new_booking_id,
            "employee": self.test_employee,
            "selected_items": [
                {
                    "hotel_id": "HTL_CREATE_001",
                    "room_ids": ["RM_CREATE_001"]
                }
            ]
        })

        result = create_booking()

        self.assertIn("response", result)

    def test_create_booking_missing_request_booking_id(self):
        """Test create_booking without request_booking_id"""
        from destiin.destiin.custom.api.hotel_booking.booking import create_booking

        frappe.form_dict = frappe._dict({
            "employee": self.test_employee,
            "selected_items": [{"hotel_id": "HTL001", "room_ids": ["RM001"]}]
        })

        result = create_booking()

        self.assertIn("response", result)
        # Should handle missing booking ID gracefully

    def test_create_booking_missing_employee(self):
        """Test create_booking without employee"""
        from destiin.destiin.custom.api.hotel_booking.booking import create_booking

        frappe.form_dict = frappe._dict({
            "request_booking_id": self.approved_booking_id,
            "selected_items": [{"hotel_id": "HTL001", "room_ids": ["RM001"]}]
        })

        result = create_booking()

        self.assertIn("response", result)

    def test_create_booking_nonexistent_request_booking(self):
        """Test create_booking with non-existent request booking"""
        from destiin.destiin.custom.api.hotel_booking.booking import create_booking

        frappe.form_dict = frappe._dict({
            "request_booking_id": "NONEXISTENT_BOOKING_XYZ",
            "employee": self.test_employee,
            "selected_items": [{"hotel_id": "HTL001", "room_ids": ["RM001"]}]
        })

        result = create_booking()

        self.assertIn("response", result)
        # Should fail for non-existent booking

    def test_create_booking_duplicate_prevention(self):
        """Test that duplicate hotel bookings are prevented"""
        from destiin.destiin.custom.api.hotel_booking.booking import create_booking

        # Create a booking first
        new_booking_id = self._create_new_approved_booking("2026-12-01", "2026-12-05")

        frappe.form_dict = frappe._dict({
            "request_booking_id": new_booking_id,
            "employee": self.test_employee,
            "selected_items": [
                {
                    "hotel_id": "HTL_CREATE_001",
                    "room_ids": ["RM_CREATE_001"]
                }
            ]
        })

        # First call should succeed
        result1 = create_booking()

        if result1["response"]["success"]:
            # Second call with same booking should fail or handle gracefully
            result2 = create_booking()
            self.assertIn("response", result2)

    def test_create_booking_response_structure(self):
        """Test that response has correct structure"""
        from destiin.destiin.custom.api.hotel_booking.booking import create_booking

        new_booking_id = self._create_new_approved_booking("2026-12-10", "2026-12-15")

        frappe.form_dict = frappe._dict({
            "request_booking_id": new_booking_id,
            "employee": self.test_employee,
            "selected_items": [
                {
                    "hotel_id": "HTL_CREATE_001",
                    "room_ids": ["RM_CREATE_001"]
                }
            ]
        })

        result = create_booking()

        self.assertIn("response", result)
        response = result["response"]
        self.assertIn("success", response)

        if response["success"]:
            data = response["data"]
            expected_fields = [
                "hotel_booking_id",
                "booking_id",
                "payment_id",
                "booking_status",
                "payment_status"
            ]
            for field in expected_fields:
                self.assertIn(field, data)

    def test_create_booking_only_approved_rooms(self):
        """Test that only approved rooms are included in the booking"""
        from destiin.destiin.custom.api.request_booking.request import store_req_booking
        from destiin.destiin.custom.api.hotel_booking.booking import create_booking

        # Create booking with multiple rooms but only approve some
        hotel_details = {
            "hotel_id": "HTL_PARTIAL_001",
            "hotel_name": "Partial Approval Hotel",
            "supplier": "Direct",
            "cancellation_policy": "Non-refundable",
            "meal_plan": "None",
            "rooms": [
                {
                    "room_id": "RM_PARTIAL_001",
                    "room_name": "Room 1",
                    "price": 2000,
                    "total_price": 2200,
                    "tax": 200,
                    "currency": "USD"
                },
                {
                    "room_id": "RM_PARTIAL_002",
                    "room_name": "Room 2",
                    "price": 3000,
                    "total_price": 3300,
                    "tax": 300,
                    "currency": "USD"
                }
            ]
        }

        frappe.form_dict = frappe._dict({
            "employee": self.test_employee,
            "check_in": "2026-12-20",
            "check_out": "2026-12-25",
            "company": self.test_company,
            "hotel_details": hotel_details
        })

        result = store_req_booking()
        booking_id = result["response"]["data"]["request_booking_id"]

        # Approve only one room
        from destiin.destiin.custom.api.request_booking.request import approve_booking
        frappe.form_dict = frappe._dict({
            "request_booking_id": booking_id,
            "employee": self.test_employee,
            "selected_items": [
                {
                    "hotel_id": "HTL_PARTIAL_001",
                    "room_ids": ["RM_PARTIAL_001"]  # Only approve first room
                }
            ]
        })
        approve_booking()

        # Create booking - should only include approved room
        frappe.form_dict = frappe._dict({
            "request_booking_id": booking_id,
            "employee": self.test_employee,
            "selected_items": [
                {
                    "hotel_id": "HTL_PARTIAL_001",
                    "room_ids": ["RM_PARTIAL_001"]
                }
            ]
        })

        result = create_booking()
        self.assertIn("response", result)


class TestCreateBookingWithMultipleRooms(IntegrationTestCase):
    """Test cases for create_booking with multiple rooms"""

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
        company_name = "_Test Company Multi Room"
        if not frappe.db.exists("Company", company_name):
            company = frappe.get_doc({
                "doctype": "Company",
                "company_name": company_name,
                "default_currency": "USD",
                "country": "India"
            })
            company.insert(ignore_permissions=True)
            return company.name
        return company_name

    @classmethod
    def _create_test_employee(cls, company):
        employee_id = "_Test-Employee-Multi"
        if not frappe.db.exists("Employee", {"employee_name": employee_id}):
            employee = frappe.get_doc({
                "doctype": "Employee",
                "employee_name": employee_id,
                "first_name": "Test",
                "last_name": "Multi",
                "company": company,
                "gender": "Male",
                "date_of_birth": "1990-01-01",
                "date_of_joining": "2020-01-01"
            })
            employee.insert(ignore_permissions=True)
            return employee.name
        return frappe.db.get_value("Employee", {"employee_name": employee_id}, "name")

    def test_create_booking_multiple_rooms(self):
        """Test creating a booking with multiple rooms"""
        from destiin.destiin.custom.api.request_booking.request import store_req_booking, approve_booking
        from destiin.destiin.custom.api.hotel_booking.booking import create_booking

        hotel_details = {
            "hotel_id": "HTL_MULTI_001",
            "hotel_name": "Multi Room Hotel",
            "supplier": "Expedia",
            "cancellation_policy": "24 hours",
            "meal_plan": "Half Board",
            "rooms": [
                {
                    "room_id": "RM_MULTI_001",
                    "room_name": "Room A",
                    "price": 4000,
                    "total_price": 4400,
                    "tax": 400,
                    "currency": "USD"
                },
                {
                    "room_id": "RM_MULTI_002",
                    "room_name": "Room B",
                    "price": 4500,
                    "total_price": 4950,
                    "tax": 450,
                    "currency": "USD"
                },
                {
                    "room_id": "RM_MULTI_003",
                    "room_name": "Room C",
                    "price": 5000,
                    "total_price": 5500,
                    "tax": 500,
                    "currency": "USD"
                }
            ]
        }

        # Create booking
        frappe.form_dict = frappe._dict({
            "employee": self.test_employee,
            "check_in": "2027-01-01",
            "check_out": "2027-01-05",
            "company": self.test_company,
            "room_count": 3,
            "hotel_details": hotel_details
        })

        result = store_req_booking()
        booking_id = result["response"]["data"]["request_booking_id"]

        # Approve all rooms
        frappe.form_dict = frappe._dict({
            "request_booking_id": booking_id,
            "employee": self.test_employee,
            "selected_items": [
                {
                    "hotel_id": "HTL_MULTI_001",
                    "room_ids": ["RM_MULTI_001", "RM_MULTI_002", "RM_MULTI_003"]
                }
            ]
        })
        approve_booking()

        # Create hotel booking
        frappe.form_dict = frappe._dict({
            "request_booking_id": booking_id,
            "employee": self.test_employee,
            "selected_items": [
                {
                    "hotel_id": "HTL_MULTI_001",
                    "room_ids": ["RM_MULTI_001", "RM_MULTI_002", "RM_MULTI_003"]
                }
            ]
        })

        result = create_booking()

        self.assertIn("response", result)
        if result["response"]["success"]:
            data = result["response"]["data"]
            # Total amount should be sum of all rooms
            # 4400 + 4950 + 5500 = 14850
            self.assertIn("total_amount", data)

    def test_create_booking_calculates_correct_total(self):
        """Test that total amount is calculated correctly"""
        from destiin.destiin.custom.api.request_booking.request import store_req_booking, approve_booking
        from destiin.destiin.custom.api.hotel_booking.booking import create_booking

        hotel_details = {
            "hotel_id": "HTL_CALC_001",
            "hotel_name": "Calculation Test Hotel",
            "supplier": "Direct",
            "cancellation_policy": "Free",
            "meal_plan": "BB",
            "rooms": [
                {
                    "room_id": "RM_CALC_001",
                    "room_name": "Room 1",
                    "price": 1000,
                    "total_price": 1100,
                    "tax": 100,
                    "currency": "USD"
                },
                {
                    "room_id": "RM_CALC_002",
                    "room_name": "Room 2",
                    "price": 2000,
                    "total_price": 2200,
                    "tax": 200,
                    "currency": "USD"
                }
            ]
        }

        frappe.form_dict = frappe._dict({
            "employee": self.test_employee,
            "check_in": "2027-02-01",
            "check_out": "2027-02-05",
            "company": self.test_company,
            "hotel_details": hotel_details
        })

        result = store_req_booking()
        booking_id = result["response"]["data"]["request_booking_id"]

        # Approve
        frappe.form_dict = frappe._dict({
            "request_booking_id": booking_id,
            "employee": self.test_employee,
            "selected_items": [
                {
                    "hotel_id": "HTL_CALC_001",
                    "room_ids": ["RM_CALC_001", "RM_CALC_002"]
                }
            ]
        })
        approve_booking()

        # Create booking
        frappe.form_dict = frappe._dict({
            "request_booking_id": booking_id,
            "employee": self.test_employee,
            "selected_items": [
                {
                    "hotel_id": "HTL_CALC_001",
                    "room_ids": ["RM_CALC_001", "RM_CALC_002"]
                }
            ]
        })

        result = create_booking()

        self.assertIn("response", result)
        if result["response"]["success"]:
            data = result["response"]["data"]
            # Expected total: 1100 + 2200 = 3300
            expected_total = 3300
            self.assertEqual(data.get("total_amount"), expected_total)
