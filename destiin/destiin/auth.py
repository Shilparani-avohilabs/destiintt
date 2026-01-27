# Copyright (c) 2025, shilpa@avohilabs.com and contributors
# For license information, please see license.txt

import frappe
import json


@frappe.whitelist(allow_guest=True)
def user_login():
    """Custom login API that returns user details"""
    try:
        if frappe.form_dict.get("data"):
            data = json.loads(frappe.form_dict.data)
        elif frappe.request.data:
            data = json.loads(frappe.request.data)
        else:
            data = frappe.form_dict

        usr = data.get("usr")
        pwd = data.get("pwd")

        if not usr or not pwd:
            return {"success": False, "error": "Username and password are required"}

        login_manager = frappe.auth.LoginManager()
        login_manager.authenticate(usr, pwd)
        login_manager.post_login()

        user = frappe.get_doc("User", frappe.session.user)

        return {
            "success": True,
            "data": {
                "user_id": user.name,
                "email": user.email,
                # "full_name": user.full_name,
                # "first_name": user.first_name,
                # "last_name": user.last_name,
                "username": user.username,
                "sid": frappe.session.sid
            }
        }

    except frappe.AuthenticationError:
        return {"success": False, "error": "Invalid credentials"}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "user_login API Error")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_all_companies(company_id=None):
    """Fetch all companies with minimal data (id and name)

    Args:
        company_id: Optional filter to fetch a specific company
    """
    try:
        filters = {}
        if company_id:
            filters["name"] = company_id

        companies = frappe.get_all(
            "Company",
            filters=filters,
            fields=[
                "name as company_id",
                "company_name",
                "custom_platform_fee",
                "custom_platform_fee_type",
                "custom_commission",
                "custom_commission_type"
            ],
            order_by="company_name asc"
        )

        formatted_companies = []
        for company in companies:
            formatted_companies.append({
                "company_id": company.get("company_id"),
                "company_name": company.get("company_name"),
                "platform_fee": {
                    "type": company.get("custom_platform_fee_type") or "fixed",
                    "value": company.get("custom_platform_fee") or 0
                },
                "commission": {
                    "type": company.get("custom_commission_type") or "percentage",
                    "value": company.get("custom_commission") or 0
                }
            })

        # If company_id filter was provided, return single object instead of array
        if company_id:
            return {
                "success": True,
                "data": formatted_companies[0] if formatted_companies else None
            }

        return {
            "success": True,
            "data": formatted_companies
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "get_all_companies API Error")
        return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_employees_by_company(company):
    """Fetch all employees for a given company with basic details (id, name, email)"""
    try:
        if not company:
            return {"success": False, "error": "Company is required"}

        employees = frappe.get_all(
            "Employee",
            filters={"company": company},
            fields=["name as employee_id", "employee_name", "company_email"],
            order_by="employee_name asc"
        )

        return {
            "success": True,
            "data": employees
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "get_employees_by_company API Error")
        return {"success": False, "error": str(e)}


@frappe.whitelist(methods=["GET"])
def get_user_by_email(email=None):
    """Fetch user details by email ID

    Args:
        email: Email ID of the user to fetch (query param)

    Returns:
        User details including username, email, phone number, and full name
    """
    try:
        email = email or frappe.form_dict.get("email")

        if not email:
            return {"success": False, "error": "Email is required"}

        user = frappe.get_all(
            "User",
            filters={"email": email},
            fields=["username", "email", "mobile_no", "full_name"],
            limit=1
        )

        if not user:
            return {"success": False, "error": "User not found"}

        return {
            "success": True,
            "data": {
                "username": user[0].get("username"),
                "email": user[0].get("email"),
                "phone_number": user[0].get("mobile_no"),
                "full_name": user[0].get("full_name")
            }
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "get_user_by_email API Error")
        return {"success": False, "error": str(e)}


