"""
Monkey patch for frappe.boot module.

Patches:
- load_desktop_data(): Wrap app_title and modules with _() for translation
- get_sidebar_items(): Wrap sidebar item labels with _() for translation
"""

import frappe
import frappe.boot
from frappe import _

# Store original functions
_original_load_desktop_data = None
_original_get_sidebar_items = None


def patched_load_desktop_data(bootinfo):
	"""
	Patched version of load_desktop_data that translates app titles and module names.
	"""
	from frappe.desk.desktop import get_workspace_sidebar_items
	from frappe.model.base_document import get_controller

	bootinfo.workspaces = get_workspace_sidebar_items()
	bootinfo.show_app_icons_as_folder = frappe.db.get_single_value(
		"Desktop Settings", "show_app_icons_as_folder"
	)
	# Use patched version if available
	bootinfo.workspace_sidebar_item = patched_get_sidebar_items()
	allowed_pages = [d.name for d in bootinfo.workspaces.get("pages")]
	bootinfo.module_wise_workspaces = get_controller("Workspace").get_module_wise_workspaces()
	bootinfo.dashboards = frappe.get_all("Dashboard")
	bootinfo.app_data = []

	Workspace = frappe.qb.DocType("Workspace")
	Module = frappe.qb.DocType("Module Def")

	for app_name in frappe.get_installed_apps():
		# get app details from app_info (/apps)
		apps = frappe.get_hooks("add_to_apps_screen", app_name=app_name)
		app_info = {}
		if apps:
			app_info = apps[0]
			has_permission = app_info.get("has_permission")
			if has_permission and not frappe.get_attr(has_permission)():
				continue

		workspaces = [
			r[0]
			for r in (
				frappe.qb.from_(Workspace)
				.inner_join(Module)
				.on(Workspace.module == Module.name)
				.select(Workspace.name)
				.where(Module.app_name == app_name)
				.run()
			)
			if r[0] in allowed_pages
		]

		# Get app title with translation
		app_title = (
			app_info.get("title")
			or (
				(
					frappe.get_hooks("app_title", app_name=app_name)
					and frappe.get_hooks("app_title", app_name=app_name)[0]
				)
				or ""
			)
			or app_name
		)

		bootinfo.app_data.append(
			dict(
				app_name=app_info.get("name") or app_name,
				app_title=_(app_title),  # Translate app title
				app_route=(
					frappe.get_hooks("app_home", app_name=app_name)
					and frappe.get_hooks("app_home", app_name=app_name)[0]
				)
				or (workspaces and "/desk/" + frappe.utils.slug(workspaces[0]))
				or "",
				app_logo_url=app_info.get("logo")
				or frappe.get_hooks("app_logo_url", app_name=app_name)
				or frappe.get_hooks("app_logo_url", app_name="frappe"),
				modules=[
					_(m.name) for m in frappe.get_all("Module Def", dict(app_name=app_name))
				],  # Translate modules
				workspaces=workspaces,
			)
		)


def patched_get_sidebar_items():
	"""
	Patched version of get_sidebar_items that translates sidebar item labels.
	"""
	sidebars = frappe.get_all(
		"Workspace Sidebar", fields=["name", "header_icon"], filters={"name": ["not like", "%My Workspaces%"]}
	)
	frappe.boot.add_user_specific_sidebar(sidebars)
	sidebar_items = {}

	for s in sidebars:
		w = frappe.get_doc("Workspace Sidebar", s["name"])
		sidebar_items[s["name"].lower()] = {
			"label": s["name"],
			"items": [],
			"header_icon": s["header_icon"],
			"module": w.module,
		}
		for si in w.items:
			workspace_sidebar = {
				"label": _(si.label),  # Translate label
				"link_to": si.link_to,
				"link_type": si.link_type,
				"type": si.type,
				"icon": si.icon,
				"child": si.child,
				"collapsible": si.collapsible,
				"indent": si.indent,
				"keep_closed": si.keep_closed,
				"display_depends_on": si.display_depends_on,
				"url": si.url,
				"show_arrow": si.show_arrow,
				"filters": si.filters,
				"route_options": si.route_options,
			}
			if si.link_type == "Report" and si.link_to:
				report_type, ref_doctype = frappe.db.get_value(
					"Report", si.link_to, ["report_type", "ref_doctype"]
				)
				workspace_sidebar["report"] = {
					"report_type": report_type,
					"ref_doctype": ref_doctype,
				}

			if (
				"My Workspaces" in s["name"]
				or si.type == "Section Break"
				or w.is_item_allowed(si.link_to, si.link_type)
			):
				sidebar_items[s["name"].lower()]["items"].append(workspace_sidebar)

	old_name = f"my workspaces-{frappe.session.user.lower()}"
	if old_name in sidebar_items.keys():
		sidebar_items["my workspaces"] = sidebar_items.pop(old_name)
	return sidebar_items


def apply():
	"""Apply the monkey patches."""
	global _original_load_desktop_data, _original_get_sidebar_items

	_original_load_desktop_data = frappe.boot.load_desktop_data
	frappe.boot.load_desktop_data = patched_load_desktop_data

	_original_get_sidebar_items = frappe.boot.get_sidebar_items
	frappe.boot.get_sidebar_items = patched_get_sidebar_items
