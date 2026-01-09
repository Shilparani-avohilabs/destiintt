app_name = "destiin"
app_title = "Destiin"
app_publisher = "shilpa@avohilabs.com"
app_description = "Destiin App for Travelling"
app_email = "shilpa@avohilabs.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "destiin",
# 		"logo": "/assets/destiin/logo.png",
# 		"title": "Destiin",
# 		"route": "/destiin",
# 		"has_permission": "destiin.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/destiin/css/destiin.css"
# app_include_js = "/assets/destiin/js/destiin.js"

# include js, css files in header of web template
# web_include_css = "/assets/destiin/css/destiin.css"
# web_include_js = "/assets/destiin/js/destiin.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "destiin/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "destiin/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "destiin.utils.jinja_methods",
# 	"filters": "destiin.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "destiin.install.before_install"
# after_install = "destiin.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "destiin.uninstall.before_uninstall"
# after_uninstall = "destiin.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "destiin.utils.before_app_install"
# after_app_install = "destiin.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "destiin.utils.before_app_uninstall"
# after_app_uninstall = "destiin.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "destiin.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

doc_events = {
    "Travel Policy Data": {
        "after_insert": "destiin.destiin.custom.api.policy.upload_policy_to_external_api",
        "on_update": "destiin.destiin.custom.api.policy.upload_policy_to_external_api"
    },
    "Employee": {
        "after_insert": [
            "destiin.destiin.custom.auto_creations.user_creation.create_user_for_manager",
            "destiin.destiin.custom.auto_creations.auto_user_permission.create_user_permission_for_hr_manager"
        ],
        "on_update": [
            "destiin.destiin.custom.auto_creations.user_creation.create_user_for_manager",
            "destiin.destiin.custom.auto_creations.auto_user_permission.create_user_permission_for_hr_manager"
        ]
    },
    "Travel Request": {
        "after_insert": "destiin.destiin.custom.auto_creations.auto_submit_travel_request.auto_submit_travel_request"
    }
}


# Scheduled Tasks
# ---------------

scheduler_events = {
    # Weekly booking report - runs every Friday at 9 AM
    "cron": {
        "0 9 * * 5": [
            "destiin.destiin.tasks.send_weekly_booking_report"
        ]
    }
}

# Testing
# -------

# before_tests = "destiin.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "destiin.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "destiin.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "destiin.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["destiin.utils.before_request"]
# after_request = ["destiin.utils.after_request"]

# Job Events
# ----------
# before_job = ["destiin.utils.before_job"]
# after_job = ["destiin.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"destiin.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

