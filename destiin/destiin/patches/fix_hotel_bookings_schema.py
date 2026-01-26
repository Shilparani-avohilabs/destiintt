import frappe


def execute():
	"""
	Fix Hotel Bookings DocType and table schema before migration.
	The currency field was incorrectly defined as Currency (decimal) type
	but should be a Link field to store currency codes like 'INR'.
	"""
	# First, fix the DocType definition in the database
	# This prevents the migration from trying to alter varchar to decimal
	doctype_exists = frappe.db.exists("DocType", "Hotel Bookings")
	if doctype_exists:
		# Get the DocField for currency
		currency_field = frappe.db.get_value(
			"DocField",
			{"parent": "Hotel Bookings", "fieldname": "currency"},
			["name", "fieldtype", "options"],
			as_dict=True,
		)

		if currency_field and currency_field.fieldtype == "Currency":
			# Update the field to be a Data field (to store currency codes like 'INR', 'USD')
			frappe.db.set_value(
				"DocField",
				currency_field.name,
				{"fieldtype": "Data", "options": ""},
			)
			frappe.db.commit()

		# Fix tax field - should be Currency type
		tax_field = frappe.db.get_value(
			"DocField",
			{"parent": "Hotel Bookings", "fieldname": "tax"},
			["name", "fieldtype"],
			as_dict=True,
		)

		if tax_field and tax_field.fieldtype != "Currency":
			frappe.db.set_value("DocField", tax_field.name, "fieldtype", "Currency")
			frappe.db.commit()

		# Fix child_count field - should be Int type
		child_count_field = frappe.db.get_value(
			"DocField",
			{"parent": "Hotel Bookings", "fieldname": "child_count"},
			["name", "fieldtype"],
			as_dict=True,
		)

		if child_count_field and child_count_field.fieldtype != "Int":
			frappe.db.set_value("DocField", child_count_field.name, "fieldtype", "Int")
			frappe.db.commit()

	# Now fix the actual table data
	if not frappe.db.table_exists("tabHotel Bookings"):
		return

	# Fix tax column data - clear non-numeric values before conversion
	try:
		frappe.db.sql(
			"""
			UPDATE `tabHotel Bookings`
			SET `tax` = NULL
			WHERE `tax` IS NOT NULL
			AND `tax` NOT REGEXP '^-?[0-9]+(\\.[0-9]+)?$'
		"""
		)
		frappe.db.commit()
	except Exception:
		pass

	# Fix child_count column data - clear non-numeric values
	try:
		frappe.db.sql(
			"""
			UPDATE `tabHotel Bookings`
			SET `child_count` = NULL
			WHERE `child_count` IS NOT NULL
			AND `child_count` NOT REGEXP '^[0-9]+$'
		"""
		)
		frappe.db.commit()
	except Exception:
		pass
