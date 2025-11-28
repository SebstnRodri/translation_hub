import os
import shutil

import frappe
from frappe import get_app_path
from frappe.tests.utils import FrappeTestCase

from translation_hub.tasks import ensure_pot_file


class TestPOTGeneration(FrappeTestCase):
	def test_ensure_pot_file(self):
		app_name = "translation_hub"
		app_path = get_app_path(app_name)
		locale_dir = os.path.join(app_path, "locale")
		pot_path = os.path.join(locale_dir, "main.pot")

		# 1. Backup existing POT if any
		backup_path = pot_path + ".bak"
		if os.path.exists(pot_path):
			shutil.move(pot_path, backup_path)

		try:
			# 2. Ensure POT file (should generate)
			ensure_pot_file(app_name)

			# 3. Verify existence
			self.assertTrue(os.path.exists(pot_path), "POT file was not generated")

			# 4. Verify content (basic check)
			with open(pot_path) as f:
				content = f.read()
				self.assertIn('msgid ""', content)
				self.assertIn("Project-Id-Version: translation_hub", content)

		finally:
			# 5. Restore backup
			if os.path.exists(backup_path):
				shutil.move(backup_path, pot_path)
