# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt

"""
Uninstallation cleanup script for Translation Hub.
"""

import frappe


def before_uninstall():
    """Cleanup before app uninstallation."""
    try:
        print("=" * 60)
        print("TRANSLATION HUB - UNINSTALL CLEANUP")
        print("=" * 60)
        
        revert_frappe_patches()
        
        print("\n" + "=" * 60)
        print("CLEANUP COMPLETE!")
        print("=" * 60)
        
    except Exception as e:
        print(f"Warning: Uninstall cleanup failed: {e}")
        # Don't raise - allow uninstallation to complete


def revert_frappe_patches():
    """Revert file patches applied to Frappe core."""
    from translation_hub.overrides.file_patches import revert_all_file_patches
    revert_all_file_patches()
