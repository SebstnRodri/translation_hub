"""
Monkey patch for frappe.desk.doctype.desktop_icon.desktop_icon module.

Patches:
- get_desktop_icons(): Fix AttributeError and add translation for icon labels
"""

import frappe
import frappe.desk.doctype.desktop_icon.desktop_icon as desktop_icon_module
from frappe import _

# Store original function
_original_get_desktop_icons = None


def patched_get_desktop_icons(user=None, bootinfo=None):
	"""
	Patched version of get_desktop_icons that fixes AttributeError and translates labels.

	Fixes:
	1. Uses s.update({"doctype": "Desktop Icon"}) + frappe.get_doc(s) instead of
	   frappe.get_doc("Desktop Icon", s) to avoid AttributeError
	2. Translates icon labels with _()
	"""
	from frappe.desk.doctype.desktop_icon.desktop_icon import (
		get_standard_icons,
		get_user_copy,
	)

	if not user:
		user = frappe.session.user

	user_icons = frappe.cache.hget("desktop_icons", user)

	if not user_icons:
		active_domains = frappe.get_active_domains()

		standard_icons = get_standard_icons()

		# filter valid icons
		standard_icons = [
			icon
			for icon in standard_icons
			if (not icon.restrict_to_domain or icon.restrict_to_domain in active_domains)
		]

		user_icons = get_user_copy(standard_icons, user)

		# add missing standard icons (added via new install apps?)
		user_icon_names = [icon.module_name for icon in user_icons]
		for standard_icon in standard_icons:
			if standard_icon.module_name not in user_icon_names:
				# if blocked, hidden too!
				if standard_icon.blocked:
					standard_icon.hidden = 1
					standard_icon.hidden_in_standard = 1

				user_icons.append(standard_icon)

		user_blocked_modules = frappe.get_lazy_doc("User", user).get_blocked_modules()
		for icon in user_icons:
			if icon.module_name in user_blocked_modules:
				icon.hidden = 1

		# sort by idx
		user_icons.sort(key=lambda a: a.idx)

		# includes
		permitted_icons = []
		permitted_parent_labels = set()

		if bootinfo:
			for s in user_icons:
				# FIX: Add doctype to dict and use get_doc with dict instead of name
				s.update({"doctype": "Desktop Icon"})
				icon = frappe.get_doc(s)
				if icon.is_permitted(bootinfo):
					permitted_icons.append(s)

				if not s.parent_icon:
					permitted_parent_labels.add(s.label)

		user_icons = [
			s for s in permitted_icons if not s.parent_icon or s.parent_icon in permitted_parent_labels
		]

		# FIX: Translate labels
		for d in user_icons:
			if d.label:
				d.label = _(d.label)

		frappe.cache.hset("desktop_icons", user, user_icons)

	return user_icons


def apply():
	"""Apply the monkey patch."""
	global _original_get_desktop_icons

	_original_get_desktop_icons = desktop_icon_module.get_desktop_icons
	desktop_icon_module.get_desktop_icons = patched_get_desktop_icons
