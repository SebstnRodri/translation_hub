import frappe
from frappe import _

@frappe.whitelist()
def get_reviews(source_app=None, language=None, status="Pending"):
	filters = {"status": status}
	if source_app:
		filters["source_app"] = source_app
	if language:
		filters["language"] = language
		
	reviews = frappe.get_all("Translation Review", 
		fields=["*"], 
		filters=filters,
		order_by="creation asc"
	)
	return reviews

@frappe.whitelist()
def process_review(name, action, adjusted_text=None, reason=None, problematic_term=None, correct_term=None):
	"""
	Process a translation review: Approve or Reject.
	
	Args:
		name: Translation Review name
		action: "Approve" or "Reject"
		adjusted_text: Human-corrected translation (for approval)
		reason: Rejection reason
		problematic_term: Specific term that was mistranslated (e.g. "against")
		correct_term: How it should be translated (e.g. "para")
	"""
	review = frappe.get_doc("Translation Review", name)
	
	if action == "Approve":
		review.status = "Approved"
		if adjusted_text and adjusted_text != review.suggested_text:
			review.suggested_text = adjusted_text
			review.was_edited = 1
			# Trigger Feedback Loop - Full Correction
			create_translation_learning(review, adjusted_text)
			
		review.save()
		review.submit()
		
	elif action == "Reject":
		review.status = "Rejected"
		if reason:
			review.rejection_reason = reason
		review.save()
		
		# If problematic term was identified, create a Term Correction learning
		if problematic_term and correct_term:
			create_term_learning(review, problematic_term, correct_term, reason)

def create_translation_learning(review, correction):
    """
    Creates a Translation Learning record for Few-Shot Learning.
    Type: Full Correction - learns from complete translation corrections.
    """
    if not frappe.db.exists("Translation Learning", {"review_ref": review.name, "learning_type": "Full Correction"}):
        doc = frappe.get_doc({
            "doctype": "Translation Learning",
            "learning_type": "Full Correction",
            "source_text": review.source_text,
            "domain": review.source_app,
            "language": review.language,
            "review_ref": review.name,
            "ai_output": review.ai_suggestion_snapshot or review.suggested_text,
            "human_correction": correction
        })
        doc.insert(ignore_permissions=True)

def create_term_learning(review, problematic_term, correct_term, context=None):
    """
    Creates a Translation Learning record for term-specific corrections.
    Type: Term Correction - learns that specific terms should be translated differently.
    
    Example: "against" should be "para" not "contra" in certain contexts.
    """
    # Check if this term correction already exists
    existing = frappe.db.exists("Translation Learning", {
        "learning_type": "Term Correction",
        "problematic_term": problematic_term,
        "correct_term": correct_term,
        "language": review.language
    })
    
    if not existing:
        doc = frappe.get_doc({
            "doctype": "Translation Learning",
            "learning_type": "Term Correction",
            "source_text": review.source_text,
            "domain": review.source_app,
            "language": review.language,
            "review_ref": review.name,
            "problematic_term": problematic_term,
            "correct_term": correct_term,
            "ai_output": review.ai_suggestion_snapshot or review.suggested_text,
            "human_correction": context or f"Term '{problematic_term}' should be translated as '{correct_term}'"
        })
        doc.insert(ignore_permissions=True)
        frappe.msgprint(
            _("Term learning created: '{0}' → '{1}'").format(problematic_term, correct_term),
            indicator="green"
        )
