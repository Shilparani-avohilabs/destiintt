import frappe
import requests
import os
from PyPDF2 import PdfReader

def upload_policy_to_external_api(doc, method):
    """
    Upload Travel Policy PDF to external API and store its content in Employee Policy Data Doctype.
    Works for both new and updated Travel Policy Data records.
    """
    try:
        logger = frappe.logger("travel_policy")
        logger.info(f"Triggered upload_policy_to_external_api for {doc.name} | Method: {method}")

        if not doc.policy_file:
            frappe.throw("Please attach a PDF file before saving the Travel Policy Data.")

        # Avoid duplicate trigger immediately after insert
        if method == "on_update" and getattr(frappe.flags, "skip_next_update_upload", False):
            logger.info("Skipping on_update trigger immediately after insert.")
            frappe.flags.skip_next_update_upload = False
            return

        # --- 1️⃣ Resolve file path safely ---
        file_doc = frappe.get_doc("File", {"file_url": doc.policy_file})

        if file_doc.file_url.startswith("/private/files/"):
            file_path = frappe.get_site_path("private", "files", os.path.basename(file_doc.file_url))
        else:
            file_path = frappe.get_site_path("public", "files", os.path.basename(file_doc.file_url))

        logger.info(f"Resolved File Path: {file_path}")

        if not os.path.exists(file_path):
            frappe.throw(f"File not found at path: {file_path}")

        # --- 2️⃣ Upload PDF to external API ---
        policy_upload_url = "https://1677945acfd9.ngrok-free.app/api/policy/upload"
        frappe.log_error(
            f"[Policy Upload API] REQUEST - URL: {policy_upload_url}\nFile: {file_path}",
            "Travel Policy Upload Request"
        )
        with open(file_path, "rb") as pdf_file:
            response = requests.post(
                policy_upload_url,
                files={"pdf": pdf_file},
                timeout=30
            )

        frappe.log_error(
            f"[Policy Upload API] RESPONSE - Status: {response.status_code}\nBody: {response.text}",
            "Travel Policy Upload Response"
        )
        logger.info(f"External API Response: {response.status_code} - {response.text}")

        api_response_msg = (
            "✅ Successfully uploaded to external API." 
            if response.status_code == 200 
            else f"❌ Upload failed ({response.status_code}): {response.text}"
        )

        # --- 3️⃣ Extract PDF text ---
        pdf_reader = PdfReader(file_path)
        pdf_text = "".join(page.extract_text() or "" for page in pdf_reader.pages)
        pdf_text = pdf_text[:5000]  # truncate long text to avoid storing too much

        # --- 4️⃣ Create or Update Employee Policy Data ---
        existing_policy_data = frappe.db.exists("Employee Policy Data", {
            "policy_name": doc.name1,  # Use human-readable policy name
            "company": doc.company
        })

        if existing_policy_data:
            # Update existing record
            policy_data_doc = frappe.get_doc("Employee Policy Data", existing_policy_data)
            policy_data_doc.file_content = pdf_text
            policy_data_doc.save(ignore_permissions=True)
            action_message = "✅ Policy updated successfully in Employee Policy Data."
        else:
            # Create new record
            frappe.get_doc({
                "doctype": "Employee Policy Data",
                "policy_name": doc.name1,  # Use human-readable policy name
                "company": doc.company,
                "file_content": pdf_text
            }).insert(ignore_permissions=True)
            action_message = "✅ New policy created and stored in Employee Policy Data."

            # Prevent immediate on_update trigger
            frappe.flags.skip_next_update_upload = True

        # --- 5️⃣ Update API response in Travel Policy Data ---
        frappe.db.set_value("Travel Policy Data", doc.name, "api_response", api_response_msg)
        frappe.db.commit()

        frappe.msgprint(action_message)
        logger.info(action_message)

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Travel Policy Upload Error")
        frappe.throw(f"Error while uploading policy: {str(e)}")
