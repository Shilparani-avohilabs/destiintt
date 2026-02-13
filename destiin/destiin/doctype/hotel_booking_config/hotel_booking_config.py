# Copyright (c) 2026, Destiin and contributors
# For license information, please see license.txt

import json
import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class HotelBookingConfig(Document):
	pass


@frappe.whitelist(allow_guest=True)
def get_service_config(company=None):
	"""
	Fetch service configuration for hotel, flight, and transit services.
	Returns configuration in a structured JSON format.
	"""
	filters = {}
	if company:
		filters["company"] = company

	config = frappe.get_doc("Hotel Booking Config", filters) if filters else frappe.get_last_doc("Hotel Booking Config")

	if not config:
		return {
			"status": "error",
			"message": "No configuration found"
		}

	employee_level = json.loads(config.employee_level) if config.employee_level else []
	budget_options = json.loads(config.budget_options) if config.budget_options else []

	return {
		"status": "success",
		"timestamp": now_datetime().isoformat() + "Z",
		"employee_level": employee_level,
		"budget_options": budget_options,
		"services": {
			"hotel": {
				"active": bool(config.hotel_active),
				"features": {
					"search": bool(config.hotel_search),
					"book": bool(config.hotel_book),
					"valuation": bool(config.hotel_valuation),
					"add_to_cart": bool(config.hotel_add_to_cart),
					"email_automation": bool(config.hotel_email_automation)
				}
			},
			"flight": {
				"active": bool(config.flight_active),
				"features": {
					"search": bool(config.flight_search),
					"book": bool(config.flight_book),
					"valuation": bool(config.flight_valuation),
					"add_to_cart": bool(config.flight_add_to_cart),
					"email_automation": bool(config.flight_email_automation)
				}
			},
			"transit": {
				"active": bool(config.transit_active),
				"features": {
					"search": bool(config.transit_search),
					"book": bool(config.transit_book),
					"valuation": bool(config.transit_valuation),
					"add_to_cart": bool(config.transit_add_to_cart),
					"email_automation": bool(config.transit_email_automation)
				}
			}
		}
	}
