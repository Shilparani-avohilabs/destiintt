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
def get_all_companies():
    """Fetch all companies with minimal data (id and name)"""
    try:
        companies = frappe.get_all(
            "Company",
            fields=["name as company_id", "company_name","custom_platform_fee as platform_fee","custom_commission as commission"],
            order_by="company_name asc"
        )

        return {
            "success": True,
            "data": companies
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
