import os
import frappe
import yaml


@frappe.whitelist(allow_guest=True)
def spec():
	api_dir = os.path.dirname(os.path.abspath(__file__))
	app_root = os.path.normpath(os.path.join(api_dir, "..", "..", "..", ".."))
	yaml_path = os.path.join(app_root, "docs", "swagger.yaml")
	if not os.path.exists(yaml_path):
		frappe.throw(f"swagger.yaml not found at: {yaml_path}", frappe.DoesNotExistError)
	with open(yaml_path, "r") as f:
		spec_dict = yaml.safe_load(f)
	return spec_dict
