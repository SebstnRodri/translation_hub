# -*- coding: utf-8 -*-
# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import nowdate, add_days

@frappe.whitelist()
def get_dashboard_data():
    total_apps = frappe.db.sql("""
        SELECT COUNT(DISTINCT source_app)
        FROM `tabTranslation Job`
    """)[0][0]

    jobs_in_progress = frappe.db.count("Translation Job", {"status": "In Progress"})

    thirty_days_ago = add_days(nowdate(), -30)
    jobs_completed_last_30_days = frappe.db.sql("""
        SELECT COUNT(*)
        FROM `tabTranslation Job`
        WHERE status = 'Completed' AND end_time >= %s
    """, thirty_days_ago)[0][0]

    strings_translated = frappe.db.sql("""
        SELECT SUM(translated_strings)
        FROM `tabTranslation Job`
        WHERE status = 'Completed'
    """)[0][0] or 0

    recent_jobs = frappe.get_list(
        "Translation Job",
        fields=["name", "title", "source_app", "target_language", "status", "progress_percentage"],
        order_by="modified DESC",
        limit=5
    )

    return {
        "total_apps": total_apps,
        "jobs_in_progress": jobs_in_progress,
        "jobs_completed_last_30_days": jobs_completed_last_30_days,
        "strings_translated": strings_translated,
        "recent_jobs": recent_jobs
    }
