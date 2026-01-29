# Copyright (c) 2026, shilpa@avohilabs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class RequestBookingDetails(Document):
	def before_insert(self):
		# Only generate request_booking_id if not already set by API
		if not self.request_booking_id and self.employee and self.check_in and self.check_out:
			check_in_str = str(self.check_in).replace("-", "")
			check_out_str = str(self.check_out).replace("-", "")
			self.request_booking_id = f"{self.employee}_{check_in_str}_{check_out_str}"
