import frappe
import base64
import requests
from frappe.utils import nowdate

def get_context(context):
    context.title = "Expense Claim Page"
    context.custom_message = "Upload your bill — it will create an Expense Claim automatically!"
    return context


@frappe.whitelist(allow_guest=True)
def upload_image(image_data=None, filename=None):
    if not image_data or not filename:
        frappe.throw("Missing image data or filename.")

    try:
        # --- 1️⃣ Decode base64 image ---
        if "," in image_data:
            image_data = image_data.split(",")[1]
        image_bytes = base64.b64decode(image_data)

        # --- 2️⃣ Create File doc (store uploaded bill) ---
        file_doc = frappe.get_doc({
            "doctype": "File",
            "file_name": filename,
            "is_private": 0,
            "content": image_bytes,
        })
        file_doc.insert(ignore_permissions=True)

        # --- 3️⃣ Call your external API ---
        api_url = "https://07d585809f49.ngrok-free.app/parse-receipt"
        files = {"file": (filename, image_bytes, "image/jpeg")}
        data = {"page_range": "1"}

        response = requests.post(api_url, files=files, data=data, timeout=90)

        if response.status_code != 200:
            frappe.throw(f"Failed to parse receipt: {response.text}")

        parsed_data = response.json()
        frappe.logger().info(f"Parsed Receipt Data: {parsed_data}")

        vendor_name = parsed_data.get("vendor_name") or "Unknown Vendor"

        # --- 4️⃣ Create Employee if not exists ---
        employee = frappe.db.exists("Employee", {"first_name": vendor_name})
        if not employee:
            emp_doc = frappe.get_doc({
                "doctype": "Employee",
                "naming_series": "HR-EMP-.YYYY.-",
                "first_name": vendor_name,
                "gender": "Other",
                "date_of_birth": "1990-01-01",
                "date_of_joining": nowdate(),
                "status": "Active",
                "company": "Destiin",
                "expense_approver": "shilpa@avohilabs.com"
            })
            emp_doc.insert(ignore_permissions=True)
            employee = emp_doc.name
            frappe.logger().info(f"✅ Created new Employee: {employee}")
        else:
            frappe.logger().info(f"ℹ️ Using existing Employee: {employee}")

        # --- 5️⃣ Calculate grand total from items ---
        items = parsed_data.get("items", [])
        if not items:
            frappe.throw("No items found in parsed data.")

        grand_total = sum(item.get("amount") or 0 for item in items)

        # --- 6️⃣ Create Expense Claim ---
        expense_claim = frappe.get_doc({
            "doctype": "Expense Claim",
            "naming_series": "HR-EXP-.YYYY.-",
            "employee": employee,
            "expense_approver": "shilpa@avohilabs.com",
            "total_claimed_amount": grand_total,  # ✅ computed total
            "grand_total": grand_total,           # ✅ optional if field exists
            "remarks": f"Auto-created from vendor {vendor_name} (Bill {parsed_data.get('bill_number')})"
        })

        # --- 7️⃣ Add child table entries (expenses) ---
        for item in items:
            expense_claim.append("expenses", {
                "expense_type": "Food",  # ✅ valid Expense Claim Type
                "description": f"{item.get('description')} ({item.get('quantity')} x {item.get('rate')} {item.get('currency', 'INR')})",
                "amount": item.get("amount") or 0,
            })

        expense_claim.insert(ignore_permissions=True)

        # --- 8️⃣ Attach file to the Expense Claim ---
        file_doc.attached_to_doctype = "Expense Claim"
        file_doc.attached_to_name = expense_claim.name
        file_doc.save(ignore_permissions=True)

        frappe.db.commit()

        # --- ✅ Done ---
        return {
            "success": True,
            "message": f"✅ Expense Claim {expense_claim.name} created successfully for {vendor_name}!",
            "employee": employee,
            "grand_total": grand_total,
            "file_url": file_doc.file_url,
            "parsed_data": parsed_data,
            "expense_claim": expense_claim.name
        }

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Expense Claim Auto Creation Failed")
        return {"success": False, "message": f"❌ Upload failed: {str(e)}"}
