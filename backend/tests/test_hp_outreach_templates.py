"""
Tests for HP template-based outreach content generation.

Verifies that the outreach system uses exact HP PDF template text with only
bracket placeholders substituted — no free-form LLM generation.
"""
import pytest
from datetime import datetime


# ---------------------------------------------------------------------------
# HP template constants (must match production_main.py definitions exactly)
# ---------------------------------------------------------------------------

def _import_templates():
    """Import the HP template constants and fill helper from production_main."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from production_main import (
        HP_EMAIL_SUBJECT_A_TEMPLATE,
        HP_EMAIL_SUBJECT_B_TEMPLATE,
        HP_EMAIL_BODY_TEMPLATE,
        HP_LINKEDIN_SUBJECT_TEMPLATE,
        HP_LINKEDIN_BODY_TEMPLATE,
        HP_CALL_STEP1_TEMPLATE,
        HP_CALL_STEP2_TEMPLATE,
        HP_CALL_STEP3_TEMPLATE,
        HP_VOICEMAIL_TEMPLATE,
        HP_OBJECTION_NOT_INTERESTED_TEMPLATE,
        HP_OBJECTION_ANOTHER_VENDOR_TEMPLATE,
        HP_OBJECTION_NOT_GOOD_TIME_TEMPLATE,
        HP_OBJECTION_SEND_SOMETHING_TEMPLATE,
        fill_hp_outreach_templates,
    )
    return {
        'HP_EMAIL_SUBJECT_A_TEMPLATE': HP_EMAIL_SUBJECT_A_TEMPLATE,
        'HP_EMAIL_SUBJECT_B_TEMPLATE': HP_EMAIL_SUBJECT_B_TEMPLATE,
        'HP_EMAIL_BODY_TEMPLATE': HP_EMAIL_BODY_TEMPLATE,
        'HP_LINKEDIN_SUBJECT_TEMPLATE': HP_LINKEDIN_SUBJECT_TEMPLATE,
        'HP_LINKEDIN_BODY_TEMPLATE': HP_LINKEDIN_BODY_TEMPLATE,
        'HP_CALL_STEP1_TEMPLATE': HP_CALL_STEP1_TEMPLATE,
        'HP_CALL_STEP2_TEMPLATE': HP_CALL_STEP2_TEMPLATE,
        'HP_CALL_STEP3_TEMPLATE': HP_CALL_STEP3_TEMPLATE,
        'HP_VOICEMAIL_TEMPLATE': HP_VOICEMAIL_TEMPLATE,
        'HP_OBJECTION_NOT_INTERESTED_TEMPLATE': HP_OBJECTION_NOT_INTERESTED_TEMPLATE,
        'HP_OBJECTION_ANOTHER_VENDOR_TEMPLATE': HP_OBJECTION_ANOTHER_VENDOR_TEMPLATE,
        'HP_OBJECTION_NOT_GOOD_TIME_TEMPLATE': HP_OBJECTION_NOT_GOOD_TIME_TEMPLATE,
        'HP_OBJECTION_SEND_SOMETHING_TEMPLATE': HP_OBJECTION_SEND_SOMETHING_TEMPLATE,
        'fill_hp_outreach_templates': fill_hp_outreach_templates,
    }


# ---------------------------------------------------------------------------
# Sample data fixture
# ---------------------------------------------------------------------------

SAMPLE_FILLS = {
    "company_name": "Acme Corp",
    "first_name": "Jane",
    "industry": "financial services",
    "priority_area": "cybersecurity modernization",
    "outcome_or_kpi": "endpoint security compliance rates",
    "hp_capability_or_benefit": "modernizing device fleets with built-in security features",
    "relevant_goal_or_improvement": "zero-trust endpoint compliance",
    "salesperson_name": "John Smith",
    "address_challenge_or_improve_outcome": "strengthen their security posture and reduce compliance gaps",
    "example_a": "reducing endpoint vulnerabilities",
    "example_b": "streamlining compliance reporting",
    "short_summary_of_capability_or_solution": "modernizing device fleets to improve security and productivity",
    "similar_organization": "a major Canadian bank",
    "metric_outcome": "endpoint compliance rates by 40%",
    "hp_offering": "HP Wolf Security for Business",
    "result": "security incident reduction and faster audit cycles",
    "outcome": "stronger security posture",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestHPEmailTemplate:
    """Email template must match HP PDF exactly with bracket fills."""

    def test_subject_a_contains_company_name(self):
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        assert result['email']['subjectA'] == "Insights that matter to Acme Corp"

    def test_subject_b_contains_company_and_priority(self):
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        assert result['email']['subjectB'] == "Supporting Acme Corp on cybersecurity modernization"

    def test_body_starts_with_greeting(self):
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        assert result['email']['body'].startswith("Hi Jane,")

    def test_body_contains_company_name(self):
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        assert "Acme Corp" in result['email']['body']

    def test_body_contains_priority_area(self):
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        assert "cybersecurity modernization" in result['email']['body']

    def test_body_contains_salesperson_name(self):
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        assert "John Smith" in result['email']['body']

    def test_body_business_unit_is_hp(self):
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        assert "HP Canada | HP" in result['email']['body']

    def test_body_preserves_link_placeholder(self):
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        assert "[Insert link to supporting asset]" in result['email']['body']

    def test_body_structure_matches_pdf(self):
        """The template structure must follow the exact HP PDF flow."""
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        body = result['email']['body']
        # Key phrases from the PDF that must appear verbatim
        assert "I understand" in body
        assert "is focused on" in body
        assert "this year. I wanted to share something that might help advance that work." in body
        assert "We've seen similar organizations strengthen" in body
        assert "I thought you might find this useful:" in body
        assert "Would you be open to a brief conversation about how we could help you achieve" in body
        assert "Best regards," in body


class TestHPLinkedInTemplate:
    """LinkedIn InMail template must match HP PDF exactly."""

    def test_subject_contains_company_and_priority(self):
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        assert result['linkedin']['subject'] == "Supporting Acme Corp on cybersecurity modernization"

    def test_body_starts_with_greeting(self):
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        assert result['linkedin']['body'].startswith("Hi Jane,")

    def test_body_contains_industry(self):
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        assert "financial services" in result['linkedin']['body']

    def test_body_preserves_link_placeholder(self):
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        assert "[Insert link to supporting asset]" in result['linkedin']['body']

    def test_body_contains_salesperson_name(self):
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        assert "John Smith" in result['linkedin']['body']

    def test_body_structure_matches_pdf(self):
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        body = result['linkedin']['body']
        assert "seems to be a key focus across" in body
        assert "We've seen similar organizations strengthen" in body
        assert "Here's a short resource that outlines how:" in body
        assert "Would you be open to a quick chat about what might work best for" in body
        assert "HP Canada" in body


class TestHPCallScriptTemplate:
    """Call script must match HP PDF exactly: 3 steps + voicemail + objection handling."""

    def test_step1_context(self):
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        step1 = result['callScript']['step1Context']
        assert "Hi Jane, this is John Smith with HP Canada." in step1
        assert "cybersecurity modernization" in step1
        assert "financial services" in step1
        assert "Do you have 30 seconds to see if this is relevant?" in step1

    def test_step2_offering(self):
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        step2 = result['callScript']['step2Offering']
        assert "financial services" in step2
        assert "reducing endpoint vulnerabilities" in step2
        assert "streamlining compliance reporting" in step2
        assert "a major Canadian bank" in step2
        assert "HP Wolf Security for Business" in step2

    def test_step3_cta(self):
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        step3 = result['callScript']['step3CTA']
        assert "financial services" in step3
        assert "Would that be useful?" in step3


class TestHPVoicemailTemplate:
    def test_voicemail_contains_names(self):
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        vm = result['voicemail']['script']
        assert "Hi Jane, this is John Smith from HP Canada." in vm

    def test_voicemail_preserves_phone_placeholder(self):
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        vm = result['voicemail']['script']
        assert "[phone number]" in vm

    def test_voicemail_structure_matches_pdf(self):
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        vm = result['voicemail']['script']
        assert "I wanted to share a quick idea about" in vm
        assert "If it's something you're exploring" in vm
        assert "You can reach me at" in vm
        assert "Hope we can connect soon." in vm


class TestHPObjectionHandlingTemplate:
    def test_not_interested_contains_industry(self):
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        obj = result['objectionHandling']['notInterested']
        assert "financial services" in obj
        assert "Totally understand" in obj

    def test_another_vendor_is_fixed_text(self):
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        obj = result['objectionHandling']['anotherVendor']
        assert "That's great." in obj
        assert "Would it make sense to share a quick example?" in obj

    def test_not_good_time_is_fixed_text(self):
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        obj = result['objectionHandling']['notGoodTime']
        assert "Of course." in obj
        assert "10 minutes tops." in obj

    def test_send_something_contains_priority_area(self):
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        obj = result['objectionHandling']['sendSomething']
        assert "cybersecurity modernization" in obj
        assert "Absolutely." in obj


class TestLiteralPlaceholdersPreserved:
    """Only [phone number] and [Insert link to supporting asset] should remain as brackets."""

    def test_no_unfilled_brackets_except_allowed(self):
        """After fill, only [phone number] and [Insert link to supporting asset] should have brackets."""
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        import re
        allowed_brackets = {"[phone number]", "[Insert link to supporting asset]"}

        # Collect all text from all fields
        all_text = []
        all_text.append(result['email']['subjectA'])
        all_text.append(result['email']['subjectB'])
        all_text.append(result['email']['body'])
        all_text.append(result['linkedin']['subject'])
        all_text.append(result['linkedin']['body'])
        all_text.append(result['callScript']['step1Context'])
        all_text.append(result['callScript']['step2Offering'])
        all_text.append(result['callScript']['step3CTA'])
        all_text.append(result['voicemail']['script'])
        all_text.append(result['objectionHandling']['notInterested'])
        all_text.append(result['objectionHandling']['anotherVendor'])
        all_text.append(result['objectionHandling']['notGoodTime'])
        all_text.append(result['objectionHandling']['sendSomething'])

        combined = "\n".join(all_text)
        # Find all [brackets]
        found_brackets = set(re.findall(r'\[[^\]]+\]', combined))
        unexpected = found_brackets - allowed_brackets
        assert not unexpected, f"Unexpected unfilled brackets found: {unexpected}"


class TestOutputStructure:
    """Verify the output dict structure matches the expected contract."""

    def test_has_all_top_level_keys(self):
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        assert 'email' in result
        assert 'linkedin' in result
        assert 'callScript' in result
        assert 'voicemail' in result
        assert 'objectionHandling' in result

    def test_email_has_correct_keys(self):
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        assert 'subjectA' in result['email']
        assert 'subjectB' in result['email']
        assert 'body' in result['email']

    def test_linkedin_has_correct_keys(self):
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        assert 'subject' in result['linkedin']
        assert 'body' in result['linkedin']

    def test_call_script_has_correct_keys(self):
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        assert 'step1Context' in result['callScript']
        assert 'step2Offering' in result['callScript']
        assert 'step3CTA' in result['callScript']

    def test_voicemail_has_correct_keys(self):
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        assert 'script' in result['voicemail']

    def test_objection_handling_has_correct_keys(self):
        t = _import_templates()
        result = t['fill_hp_outreach_templates'](SAMPLE_FILLS)
        oh = result['objectionHandling']
        assert 'notInterested' in oh
        assert 'anotherVendor' in oh
        assert 'notGoodTime' in oh
        assert 'sendSomething' in oh
