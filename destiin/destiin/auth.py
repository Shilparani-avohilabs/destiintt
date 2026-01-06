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
                "user_name": user.user_name
                # "sid": frappe.session.sid
            }
        }

    except frappe.AuthenticationError:
        return {"success": False, "error": "Invalid credentials"}
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "user_login API Error")
        return {"success": False, "error": str(e)}
