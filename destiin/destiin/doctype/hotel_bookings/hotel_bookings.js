// Copyright (c) 2026, Destiin and contributors
// For license information, please see license.txt

frappe.ui.form.on("Hotel Bookings", {
	refresh(frm) {
		frm.add_custom_button(__("Send Bill-to-Company Report"), function () {
			frappe.confirm(
				"This will generate a report for all <b>Bill to Company</b> bookings with <b>Payment Pending</b> status, create payment links, and send the report to respective company emails.<br><br>Do you want to proceed?",
				function () {
					frappe.call({
						method: "destiin.destiin.doctype.hotel_bookings.hotel_bookings.send_bill_to_company_report",
						freeze: true,
						freeze_message: __("Generating report and sending emails..."),
						callback: function (r) {
							if (r.message && r.message.success) {
								let msg = r.message.message || "Report sent successfully";
								let details = r.message.data || {};
								let summary = msg;
								if (details.companies_processed) {
									summary += `<br><br><b>Companies processed:</b> ${details.companies_processed}`;
								}
								if (details.total_bookings) {
									summary += `<br><b>Total bookings:</b> ${details.total_bookings}`;
								}
								if (details.emails_sent) {
									summary += `<br><b>Emails sent:</b> ${details.emails_sent}`;
								}
								frappe.msgprint({
									title: __("Report Sent"),
									indicator: "green",
									message: summary,
								});
							} else {
								frappe.msgprint({
									title: __("Error"),
									indicator: "red",
									message: r.message ? r.message.error : "An error occurred",
								});
							}
						},
					});
				}
			);
		}, __("Actions"));
	},
});
