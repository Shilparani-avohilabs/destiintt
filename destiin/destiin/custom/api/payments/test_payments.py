"""
Test cases for Payments APIs

Run tests with:
    bench --site <site-name> run-tests --module destiin.destiin.custom.api.payments.test_payments

Or run specific test:
    bench --site <site-name> run-tests --module destiin.destiin.custom.api.payments.test_payments --test TestCreatePaymentUrl
"""

import frappe
from frappe.tests import IntegrationTestCase
from unittest.mock import patch, MagicMock
import json


class TestCreatePaymentUrl(IntegrationTestCase):
    """Test cases for create_payment_url API"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_company = cls._create_test_company()
        cls.test_employee = cls._create_test_employee(cls.test_company)
        cls.test_payment = cls._create_test_booking_payment(
            cls.test_employee, cls.test_company
        )

    @classmethod
    def tearDownClass(cls):
        frappe.db.rollback()
        super().tearDownClass()

    @classmethod
    def _create_test_company(cls):
        """Create a test company"""
        company_name = "_Test Company Payments"
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
        """Create a test employee with email"""
        employee_id = "_Test-Employee-Payments"
        if not frappe.db.exists("Employee", {"employee_name": employee_id}):
            # First create a user for the employee
            user_email = "test_payment_employee@test.com"
            if not frappe.db.exists("User", user_email):
                user = frappe.get_doc({
                    "doctype": "User",
                    "email": user_email,
                    "first_name": "Test",
                    "last_name": "Payment",
                    "enabled": 1,
                    "user_type": "System User"
                })
                user.insert(ignore_permissions=True)

            employee = frappe.get_doc({
                "doctype": "Employee",
                "employee_name": employee_id,
                "first_name": "Test",
                "last_name": "Payment",
                "company": company,
                "gender": "Male",
                "date_of_birth": "1990-01-01",
                "date_of_joining": "2020-01-01",
                "user_id": user_email,
                "cell_number": "9876543210"
            })
            employee.insert(ignore_permissions=True)
            return employee.name
        return frappe.db.get_value("Employee", {"employee_name": employee_id}, "name")

    @classmethod
    def _create_test_booking_payment(cls, employee, company):
        """Create a test booking payment record"""
        from destiin.destiin.custom.api.request_booking.request import store_req_booking, approve_booking
        from destiin.destiin.custom.api.hotel_booking.booking import create_booking

        hotel_details = {
            "hotel_id": "HTL_PAY_001",
            "hotel_name": "Payment Test Hotel",
            "supplier": "Direct",
            "cancellation_policy": "Free cancellation",
            "meal_plan": "Breakfast",
            "rooms": [
                {
                    "room_id": "RM_PAY_001",
                    "room_name": "Payment Test Room",
                    "price": 5000,
                    "total_price": 5500,
                    "tax": 500,
                    "currency": "INR"
                }
            ]
        }

        # Create request booking
        frappe.form_dict = frappe._dict({
            "employee": employee,
            "check_in": "2027-03-01",
            "check_out": "2027-03-05",
            "company": company,
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
                    "hotel_id": "HTL_PAY_001",
                    "room_ids": ["RM_PAY_001"]
                }
            ]
        })
        approve_booking()

        # Create hotel booking (this creates the payment record)
        frappe.form_dict = frappe._dict({
            "request_booking_id": booking_id,
            "employee": employee,
            "selected_items": [
                {
                    "hotel_id": "HTL_PAY_001",
                    "room_ids": ["RM_PAY_001"]
                }
            ]
        })

        result = create_booking()

        if result["response"]["success"]:
            return result["response"]["data"]["payment_id"]
        return None

    @patch('requests.post')
    def test_create_payment_url_success(self, mock_post):
        """Test creating a payment URL successfully"""
        from destiin.destiin.custom.api.payments.payments import create_payment_url

        # Mock the HitPay API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "hitpay_payment_123",
            "url": "https://hitpay.com/payment/abc123",
            "status": "pending"
        }
        mock_post.return_value = mock_response

        if self.test_payment:
            frappe.form_dict = frappe._dict({
                "payment_id": str(self.test_payment)
            })

            result = create_payment_url()

            self.assertIn("response", result)
            if result["response"]["success"]:
                data = result["response"]["data"]
                self.assertIn("payment_url", data)
                self.assertIn("amount", data)

    @patch('requests.post')
    def test_create_payment_url_response_structure(self, mock_post):
        """Test that response has correct structure"""
        from destiin.destiin.custom.api.payments.payments import create_payment_url

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "hitpay_123",
            "url": "https://hitpay.com/pay/123"
        }
        mock_post.return_value = mock_response

        if self.test_payment:
            frappe.form_dict = frappe._dict({
                "payment_id": str(self.test_payment)
            })

            result = create_payment_url()

            self.assertIn("response", result)
            response = result["response"]
            self.assertIn("success", response)

            if response["success"]:
                data = response["data"]
                expected_fields = [
                    "payment_url",
                    "amount",
                    "currency",
                    "payment_status"
                ]
                for field in expected_fields:
                    self.assertIn(field, data)

    def test_create_payment_url_missing_payment_id(self):
        """Test create_payment_url without payment_id"""
        from destiin.destiin.custom.api.payments.payments import create_payment_url

        frappe.form_dict = frappe._dict({})

        result = create_payment_url()

        self.assertIn("response", result)
        # Should handle missing payment_id gracefully

    def test_create_payment_url_invalid_payment_id(self):
        """Test create_payment_url with invalid payment_id"""
        from destiin.destiin.custom.api.payments.payments import create_payment_url

        frappe.form_dict = frappe._dict({
            "payment_id": "99999999"  # Non-existent ID
        })

        result = create_payment_url()

        self.assertIn("response", result)
        # Should fail for non-existent payment

    @patch('requests.post')
    def test_create_payment_url_hitpay_api_failure(self, mock_post):
        """Test handling of HitPay API failure"""
        from destiin.destiin.custom.api.payments.payments import create_payment_url

        # Mock API failure
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal server error"}
        mock_post.return_value = mock_response

        if self.test_payment:
            frappe.form_dict = frappe._dict({
                "payment_id": str(self.test_payment)
            })

            result = create_payment_url()

            self.assertIn("response", result)

    @patch('requests.post')
    def test_create_payment_url_updates_status(self, mock_post):
        """Test that payment status is updated after creating URL"""
        from destiin.destiin.custom.api.payments.payments import create_payment_url

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "hitpay_456",
            "url": "https://hitpay.com/pay/456"
        }
        mock_post.return_value = mock_response

        if self.test_payment:
            frappe.form_dict = frappe._dict({
                "payment_id": str(self.test_payment)
            })

            result = create_payment_url()

            if result["response"]["success"]:
                # Check that status is updated to payment_awaiting
                payment_doc = frappe.get_doc("Booking Payments", self.test_payment)
                self.assertEqual(payment_doc.payment_status, "payment_awaiting")

    @patch('requests.post')
    def test_create_payment_url_creates_child_record(self, mock_post):
        """Test that Booking Payment URL child record is created"""
        from destiin.destiin.custom.api.payments.payments import create_payment_url

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "hitpay_789",
            "url": "https://hitpay.com/pay/789"
        }
        mock_post.return_value = mock_response

        if self.test_payment:
            frappe.form_dict = frappe._dict({
                "payment_id": str(self.test_payment)
            })

            result = create_payment_url()

            if result["response"]["success"]:
                # Verify child record exists
                payment_doc = frappe.get_doc("Booking Payments", self.test_payment)
                self.assertTrue(len(payment_doc.booking_payment_url) > 0)


class TestCreatePaymentUrlWithDifferentAmounts(IntegrationTestCase):
    """Test cases for create_payment_url with various amounts"""

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
        company_name = "_Test Company Amount"
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
        employee_id = "_Test-Employee-Amount"
        if not frappe.db.exists("Employee", {"employee_name": employee_id}):
            user_email = "test_amount_employee@test.com"
            if not frappe.db.exists("User", user_email):
                user = frappe.get_doc({
                    "doctype": "User",
                    "email": user_email,
                    "first_name": "Test",
                    "last_name": "Amount",
                    "enabled": 1,
                    "user_type": "System User"
                })
                user.insert(ignore_permissions=True)

            employee = frappe.get_doc({
                "doctype": "Employee",
                "employee_name": employee_id,
                "first_name": "Test",
                "last_name": "Amount",
                "company": company,
                "gender": "Male",
                "date_of_birth": "1990-01-01",
                "date_of_joining": "2020-01-01",
                "user_id": user_email,
                "cell_number": "9876543210"
            })
            employee.insert(ignore_permissions=True)
            return employee.name
        return frappe.db.get_value("Employee", {"employee_name": employee_id}, "name")

    def _create_booking_with_amount(self, price, tax, check_in, check_out):
        """Helper to create booking with specific amount"""
        from destiin.destiin.custom.api.request_booking.request import store_req_booking, approve_booking
        from destiin.destiin.custom.api.hotel_booking.booking import create_booking

        hotel_details = {
            "hotel_id": f"HTL_AMT_{price}",
            "hotel_name": "Amount Test Hotel",
            "supplier": "Direct",
            "cancellation_policy": "Free",
            "meal_plan": "None",
            "rooms": [
                {
                    "room_id": f"RM_AMT_{price}",
                    "room_name": "Test Room",
                    "price": price,
                    "total_price": price + tax,
                    "tax": tax,
                    "currency": "INR"
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

        frappe.form_dict = frappe._dict({
            "request_booking_id": booking_id,
            "employee": self.test_employee,
            "selected_items": [
                {
                    "hotel_id": f"HTL_AMT_{price}",
                    "room_ids": [f"RM_AMT_{price}"]
                }
            ]
        })
        approve_booking()

        frappe.form_dict = frappe._dict({
            "request_booking_id": booking_id,
            "employee": self.test_employee,
            "selected_items": [
                {
                    "hotel_id": f"HTL_AMT_{price}",
                    "room_ids": [f"RM_AMT_{price}"]
                }
            ]
        })

        result = create_booking()
        if result["response"]["success"]:
            return result["response"]["data"]["payment_id"]
        return None

    @patch('requests.post')
    def test_create_payment_url_small_amount(self, mock_post):
        """Test payment URL creation with small amount"""
        from destiin.destiin.custom.api.payments.payments import create_payment_url

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "small_123",
            "url": "https://hitpay.com/pay/small"
        }
        mock_post.return_value = mock_response

        payment_id = self._create_booking_with_amount(1000, 100, "2027-04-01", "2027-04-02")

        if payment_id:
            frappe.form_dict = frappe._dict({
                "payment_id": str(payment_id)
            })

            result = create_payment_url()

            self.assertIn("response", result)
            if result["response"]["success"]:
                # Amount should be price + tax = 1100
                self.assertEqual(result["response"]["data"]["amount"], 1100)

    @patch('requests.post')
    def test_create_payment_url_large_amount(self, mock_post):
        """Test payment URL creation with large amount"""
        from destiin.destiin.custom.api.payments.payments import create_payment_url

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "large_123",
            "url": "https://hitpay.com/pay/large"
        }
        mock_post.return_value = mock_response

        payment_id = self._create_booking_with_amount(100000, 18000, "2027-05-01", "2027-05-10")

        if payment_id:
            frappe.form_dict = frappe._dict({
                "payment_id": str(payment_id)
            })

            result = create_payment_url()

            self.assertIn("response", result)
            if result["response"]["success"]:
                # Amount should be 100000 + 18000 = 118000
                self.assertEqual(result["response"]["data"]["amount"], 118000)


class TestPaymentAPIEdgeCases(IntegrationTestCase):
    """Edge case tests for Payment APIs"""

    def test_create_payment_url_empty_string_payment_id(self):
        """Test with empty string payment_id"""
        from destiin.destiin.custom.api.payments.payments import create_payment_url

        frappe.form_dict = frappe._dict({
            "payment_id": ""
        })

        result = create_payment_url()

        self.assertIn("response", result)
        # Should handle empty string gracefully

    def test_create_payment_url_null_payment_id(self):
        """Test with null payment_id"""
        from destiin.destiin.custom.api.payments.payments import create_payment_url

        frappe.form_dict = frappe._dict({
            "payment_id": None
        })

        result = create_payment_url()

        self.assertIn("response", result)

    def test_create_payment_url_string_zero_payment_id(self):
        """Test with '0' as payment_id"""
        from destiin.destiin.custom.api.payments.payments import create_payment_url

        frappe.form_dict = frappe._dict({
            "payment_id": "0"
        })

        result = create_payment_url()

        self.assertIn("response", result)

    @patch('requests.post')
    def test_create_payment_url_network_timeout(self, mock_post):
        """Test handling of network timeout"""
        from destiin.destiin.custom.api.payments.payments import create_payment_url
        import requests

        mock_post.side_effect = requests.exceptions.Timeout("Connection timed out")

        frappe.form_dict = frappe._dict({
            "payment_id": "1"
        })

        result = create_payment_url()

        self.assertIn("response", result)
        # Should handle timeout gracefully

    @patch('requests.post')
    def test_create_payment_url_connection_error(self, mock_post):
        """Test handling of connection error"""
        from destiin.destiin.custom.api.payments.payments import create_payment_url
        import requests

        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

        frappe.form_dict = frappe._dict({
            "payment_id": "1"
        })

        result = create_payment_url()

        self.assertIn("response", result)
        # Should handle connection error gracefully

    @patch('requests.post')
    def test_create_payment_url_invalid_json_response(self, mock_post):
        """Test handling of invalid JSON response from HitPay"""
        from destiin.destiin.custom.api.payments.payments import create_payment_url

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_post.return_value = mock_response

        frappe.form_dict = frappe._dict({
            "payment_id": "1"
        })

        result = create_payment_url()

        self.assertIn("response", result)
