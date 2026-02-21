import frappe
from frappe import _


@frappe.whitelist(allow_guest=True)
def login(usr, pwd):
    """
    Employee login API.
    1. Logs in using Frappe auth
    2. Checks if user is an active Employee
    3. Returns employee details + travel policy

    API: POST /api/method/destiin.destiin.custom.sbt.employee.login
    Body: { "usr": "emp@company.com", "pwd": "password123" }
    """
    try:
        # Step 1: Frappe login
        frappe.local.login_manager.authenticate(usr, pwd)
        frappe.local.login_manager.post_login()

    except frappe.AuthenticationError:
        frappe.clear_messages()
        frappe.throw(_("Invalid email or password"), frappe.AuthenticationError)

    # Step 2: Check if this user is an active Employee
    employee = frappe.db.get_value("Employee",
        {"user_id": frappe.session.user, "status": "Active"},
        ["name", "employee_name", "designation", "department",
         "company", "reports_to", "cell_phone", "image"],
        as_dict=True
    )

    if not employee:
        frappe.local.login_manager.logout()
        frappe.throw(
            _("You are not registered as an employee. Please contact HR."),
            frappe.PermissionError
        )

    # Step 3: Get travel policy
    travel_policy = get_travel_policy(employee.designation, employee.company)

    # Step 4: Get manager name
    manager_name = None
    if employee.reports_to:
        manager_name = frappe.db.get_value("Employee",
            employee.reports_to, "employee_name")

    return {
        "message": "Login successful",
        "employee": {
            "employee_id": employee.name,
            "employee_name": employee.employee_name,
            "designation": employee.designation,
            "department": employee.department,
            "company": employee.company,
            "reports_to": employee.reports_to,
            "manager_name": manager_name,
            "cell_phone": employee.cell_phone,
            "image": employee.image,
        },
        "travel_policy": travel_policy,
        "sid": frappe.session.sid,
        "api_key": frappe.generate_hash(length=15),
    }


def get_travel_policy(designation, company):
    """
    Fetch travel policy from Company Config for this designation.
    """
    policy = frappe.db.get_value("Travel Policy Row",
        {"parent": company, "designation": designation},
        ["max_budget_per_night", "max_star_rating"],
        as_dict=True
    )

    return policy or {"max_budget_per_night": 0, "max_star_rating": "Any"}


@frappe.whitelist()
def get_profile():
    """
    Get logged-in employee profile.
    Called after login to refresh employee data.

    API: POST /api/method/destiin.destiin.custom.sbt.employee.get_profile
    """
    employee = frappe.db.get_value("Employee",
        {"user_id": frappe.session.user, "status": "Active"},
        ["name", "employee_name", "designation", "department",
         "company", "reports_to", "cell_phone", "image"],
        as_dict=True
    )

    if not employee:
        frappe.throw(_("Employee not found"), frappe.PermissionError)

    travel_policy = get_travel_policy(employee.designation, employee.company)

    manager_name = None
    if employee.reports_to:
        manager_name = frappe.db.get_value("Employee",
            employee.reports_to, "employee_name")

    return {
        "employee": {
            "employee_id": employee.name,
            "employee_name": employee.employee_name,
            "designation": employee.designation,
            "department": employee.department,
            "company": employee.company,
            "reports_to": employee.reports_to,
            "manager_name": manager_name,
            "cell_phone": employee.cell_phone,
            "image": employee.image,
        },
        "travel_policy": travel_policy,
    }


@frappe.whitelist()
def logout():
    """
    Logout employee.

    API: POST /api/method/destiin.destiin.custom.sbt.employee.logout
    """
    frappe.local.login_manager.logout()
    return {"message": "Logged out successfully"}