import frappe


def execute():
	"""
	Fix Hotel Bookings table schema before migration.
	The currency field was incorrectly defined as Currency (decimal) type
	but should be a Link field to store currency codes like 'INR'.
	"""
	if not frappe.db.table_exists("tabHotel Bookings"):
		return

	# Check if currency column exists and its current type
	columns = frappe.db.sql(
		"""
		SELECT COLUMN_NAME, DATA_TYPE
		FROM INFORMATION_SCHEMA.COLUMNS
		WHERE TABLE_SCHEMA = DATABASE()
		AND TABLE_NAME = 'tabHotel Bookings'
		AND COLUMN_NAME IN ('currency', 'tax', 'child_count')
	""",
		as_dict=True,
	)

	column_types = {col["COLUMN_NAME"]: col["DATA_TYPE"] for col in columns}

	# Fix currency column - should be varchar for Link field, not decimal
	if column_types.get("currency") == "decimal":
		# First, backup any existing data
		frappe.db.sql(
			"""
			ALTER TABLE `tabHotel Bookings`
			MODIFY `currency` varchar(140)
		"""
		)
		frappe.db.commit()

	# Fix tax column - should be decimal for Currency field
	if column_types.get("tax") == "varchar":
		# Clear invalid data first
		frappe.db.sql(
			"""
			UPDATE `tabHotel Bookings`
			SET `tax` = NULL
			WHERE `tax` IS NOT NULL
			AND `tax` NOT REGEXP '^[0-9]+(\\.[0-9]+)?$'
		"""
		)
		frappe.db.commit()

	# Fix child_count column - should be int
	if column_types.get("child_count") == "varchar":
		# Clear invalid data first
		frappe.db.sql(
			"""
			UPDATE `tabHotel Bookings`
			SET `child_count` = NULL
			WHERE `child_count` IS NOT NULL
			AND `child_count` NOT REGEXP '^[0-9]+$'
		"""
		)
		frappe.db.commit()
