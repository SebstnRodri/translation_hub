# Copyright (c) 2025, Sebastian Rodrigues and contributors
# For license information, please see license.txt

"""
File patches for Frappe core files.

This module provides utilities to patch Frappe core files with fixes that
haven't been merged yet (or for older versions). Patches are applied during
installation and migration, and are designed to be idempotent and safe.
"""

import os
import re
import shutil
from pathlib import Path

import frappe

# Marker to identify patched files
PATCH_MARKER = "<!-- translation_hub_patched -->"


def get_frappe_app_path() -> Path:
    """Get the path to the Frappe app directory."""
    return Path(frappe.get_app_path("frappe"))


def apply_all_file_patches():
    """Apply all file patches. Called from after_install and after_migrate."""
    try:
        print("\n[translation_hub] Applying Frappe core patches...")
        
        results = []
        results.append(patch_sidebar_item_html())
        
        applied = sum(1 for r in results if r == "applied")
        skipped = sum(1 for r in results if r == "skipped")
        
        if applied > 0:
            print(f"[translation_hub] ✅ Applied {applied} patch(es), skipped {skipped}")
            # Trigger asset rebuild
            _trigger_asset_rebuild()
        else:
            print(f"[translation_hub] ✓ All patches already applied ({skipped} files)")
            
    except Exception as e:
        frappe.log_error(f"Error applying file patches: {e}", "Translation Hub Patches")
        print(f"[translation_hub] ⚠ Error applying patches: {e}")


def revert_all_file_patches():
    """Revert all file patches. Called from before_uninstall."""
    try:
        print("\n[translation_hub] Reverting Frappe core patches...")
        
        results = []
        results.append(revert_sidebar_item_html())
        
        reverted = sum(1 for r in results if r == "reverted")
        print(f"[translation_hub] ✅ Reverted {reverted} patch(es)")
        
        if reverted > 0:
            _trigger_asset_rebuild()
            
    except Exception as e:
        frappe.log_error(f"Error reverting file patches: {e}", "Translation Hub Patches")
        print(f"[translation_hub] ⚠ Error reverting patches: {e}")


def patch_sidebar_item_html() -> str:
    """
    Patch sidebar_item.html to use __() for translation.
    
    The original file uses {{ item.label }} directly without translation.
    This patch wraps labels with {{ __(item.label) }}.
    
    Returns: "applied", "skipped", or "error"
    """
    frappe_path = get_frappe_app_path()
    target_file = frappe_path / "public" / "js" / "frappe" / "ui" / "sidebar" / "sidebar_item.html"
    
    if not target_file.exists():
        print(f"  [sidebar_item.html] File not found, skipping")
        return "skipped"
    
    content = target_file.read_text()
    
    # Check if already patched
    if PATCH_MARKER in content:
        print(f"  [sidebar_item.html] Already patched, skipping")
        return "skipped"
    
    # Create backup
    backup_file = target_file.with_suffix(".html.backup")
    if not backup_file.exists():
        shutil.copy(target_file, backup_file)
    
    # Apply patches
    original_content = content
    
    # Patch 1: title="{{ item.label }}" → title="{{ __(item.label) }}"
    content = re.sub(
        r'title="\{\{\s*item\.label\s*\}\}"',
        'title="{{ __(item.label) }}"',
        content
    )
    
    # Patch 2: <span class="sidebar-item-label">{{ item.label }}</span>
    # Only replace when inside the span tag (not data attributes)
    content = re.sub(
        r'(<span class="sidebar-item-label">)\{\{\s*item\.label\s*\}\}(</span>)',
        r'\1{{ __(item.label) }}\2',
        content
    )
    
    # Add patch marker at the beginning (as HTML comment)
    content = PATCH_MARKER + "\n" + content
    
    # Write patched content
    if content != original_content:
        target_file.write_text(content)
        print(f"  [sidebar_item.html] ✓ Patched (added __() for translation)")
        return "applied"
    else:
        print(f"  [sidebar_item.html] No changes needed")
        return "skipped"


def revert_sidebar_item_html() -> str:
    """
    Revert sidebar_item.html patch by restoring from backup.
    
    Returns: "reverted", "skipped", or "error"
    """
    frappe_path = get_frappe_app_path()
    target_file = frappe_path / "public" / "js" / "frappe" / "ui" / "sidebar" / "sidebar_item.html"
    backup_file = target_file.with_suffix(".html.backup")
    
    if backup_file.exists():
        shutil.copy(backup_file, target_file)
        backup_file.unlink()
        print(f"  [sidebar_item.html] ✓ Reverted from backup")
        return "reverted"
    else:
        # Try to remove patch marker and revert changes manually
        if target_file.exists():
            content = target_file.read_text()
            if PATCH_MARKER in content:
                # Remove patch marker
                content = content.replace(PATCH_MARKER + "\n", "")
                # Revert translations back to original
                content = content.replace('title="{{ __(item.label) }}"', 'title="{{ item.label }}"')
                content = re.sub(
                    r'(<span class="sidebar-item-label">)\{\{\s*__\(item\.label\)\s*\}\}(</span>)',
                    r'\1{{ item.label }}\2',
                    content
                )
                target_file.write_text(content)
                print(f"  [sidebar_item.html] ✓ Reverted (removed __() wrappers)")
                return "reverted"
        
        print(f"  [sidebar_item.html] No backup found, skipping")
        return "skipped"


def _trigger_asset_rebuild():
    """Trigger asset rebuild to apply HTML template changes."""
    try:
        import subprocess
        bench_path = Path(frappe.get_app_path("frappe")).parent.parent
        
        print("[translation_hub] Rebuilding Frappe assets...")
        result = subprocess.run(
            ["bench", "build", "--app", "frappe"],
            cwd=bench_path,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            print("[translation_hub] ✓ Assets rebuilt successfully")
        else:
            # Log full error but only show summary to user
            if result.stderr:
                frappe.log_error(
                    f"Asset rebuild warning:\n{result.stderr}",
                    "Translation Hub - Asset Rebuild"
                )
            print("[translation_hub] ⚠ Asset rebuild had warnings (logged)")
            print("[translation_hub] Note: Run 'bench build --app frappe' manually if needed")
            
    except subprocess.TimeoutExpired:
        print("[translation_hub] ⚠ Asset rebuild timed out")
        print("[translation_hub] Note: Changes will be applied on next 'bench build'")
    except FileNotFoundError:
        # bench command not found (production environment without bench CLI)
        print("[translation_hub] ⚠ 'bench' command not available")
        print("[translation_hub] Note: Run 'bench build --app frappe' manually or restart web workers")
    except Exception as e:
        frappe.log_error(f"Could not rebuild assets: {e}", "Translation Hub - Asset Rebuild")
        print("[translation_hub] ⚠ Could not rebuild assets (logged)")
        print("[translation_hub] Note: Run 'bench build --app frappe' manually")
