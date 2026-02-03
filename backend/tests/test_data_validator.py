"""
Tests for the pre-LLM data validation module.
"""
import pytest
from backend.worker.data_validator import (
    DataValidator,
    get_validator,
    ValidationIssue,
    DataValidationResult
)


class TestDataValidator:
    """Test cases for DataValidator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = DataValidator()

    def test_validate_correct_microsoft_ceo(self):
        """Test that correct Microsoft CEO passes validation."""
        result = self.validator.validate_company_data(
            domain="microsoft.com",
            data={
                "ceo": "Satya Nadella",
                "company_name": "Microsoft Corporation",
                "headquarters": "Redmond, Washington"
            },
            source="apollo"
        )

        assert result.is_valid
        assert result.confidence_score >= 0.9
        assert len([i for i in result.issues if i.severity == "critical"]) == 0

    def test_validate_incorrect_microsoft_ceo(self):
        """Test that incorrect Microsoft CEO is flagged and corrected."""
        result = self.validator.validate_company_data(
            domain="microsoft.com",
            data={
                "ceo": "Julie Strau",  # Wrong CEO name
                "company_name": "Microsoft",
                "headquarters": "Redmond"
            },
            source="apollo"
        )

        # Should have a critical issue for wrong CEO
        critical_issues = [i for i in result.issues if i.severity == "critical"]
        assert len(critical_issues) >= 1

        # CEO field should be in critical issues
        ceo_issues = [i for i in critical_issues if i.field_name == "ceo"]
        assert len(ceo_issues) == 1
        assert ceo_issues[0].provided_value == "Julie Strau"

        # Should have corrected value
        assert "ceo" in result.corrected_values
        assert result.corrected_values["ceo"] == "Satya Nadella"

        # Confidence should be reduced
        assert result.confidence_score < 0.8

    def test_validate_correct_apple_ceo(self):
        """Test that correct Apple CEO passes validation."""
        result = self.validator.validate_company_data(
            domain="apple.com",
            data={
                "ceo": "Tim Cook",
                "company_name": "Apple Inc.",
                "headquarters": "Cupertino, California"
            },
            source="pdl"
        )

        assert result.is_valid
        assert len([i for i in result.issues if i.severity == "critical"]) == 0

    def test_validate_incorrect_apple_ceo(self):
        """Test that incorrect Apple CEO is caught."""
        result = self.validator.validate_company_data(
            domain="apple.com",
            data={
                "ceo": "Steve Jobs",  # Deceased, no longer CEO
                "company_name": "Apple"
            },
            source="pdl"
        )

        # Should flag incorrect CEO
        ceo_issues = [i for i in result.issues if i.field_name == "ceo"]
        assert len(ceo_issues) >= 1

    def test_validate_unknown_company(self):
        """Test validation for company not in known facts database."""
        result = self.validator.validate_company_data(
            domain="unknowncompany.com",
            data={
                "ceo": "John Doe",
                "company_name": "Unknown Company Inc."
            },
            source="hunter"
        )

        # Should pass with high confidence (no facts to contradict)
        assert result.is_valid
        assert result.confidence_score >= 0.9

    def test_validate_stakeholder_with_wrong_ceo(self):
        """Test that stakeholders with wrong CEO name are flagged."""
        result = self.validator.validate_company_data(
            domain="microsoft.com",
            data={
                "stakeholders": [
                    {"name": "Julie Strau", "title": "CEO", "roleType": "CEO"},
                    {"name": "Amy Hood", "title": "CFO", "roleType": "CFO"}
                ]
            },
            source="apollo"
        )

        # Should flag the incorrect CEO in stakeholders
        stakeholder_issues = [i for i in result.issues if "stakeholder" in i.field_name]
        assert len(stakeholder_issues) >= 1

    def test_validate_placeholder_name(self):
        """Test that placeholder names are flagged."""
        result = self.validator.validate_company_data(
            domain="example.com",
            data={
                "stakeholders": [
                    {"name": "Test User", "title": "CTO", "roleType": "CTO"},
                    {"name": "John Doe", "title": "CIO", "roleType": "CIO"}
                ]
            },
            source="apollo"
        )

        # Should flag "Test User" as suspicious
        suspicious_issues = [
            i for i in result.issues
            if "placeholder" in i.message.lower() or "test" in i.message.lower()
        ]
        assert len(suspicious_issues) >= 1

    def test_validate_unrealistic_employee_count(self):
        """Test that unrealistic employee counts are flagged."""
        result = self.validator.validate_company_data(
            domain="example.com",
            data={
                "employee_count": "999999999"
            },
            source="pdl"
        )

        employee_issues = [i for i in result.issues if i.field_name == "employee_count"]
        assert len(employee_issues) >= 1

    def test_validate_negative_employee_count(self):
        """Test that negative employee counts are flagged."""
        result = self.validator.validate_company_data(
            domain="example.com",
            data={
                "employee_count": -100
            },
            source="pdl"
        )

        employee_issues = [i for i in result.issues if i.field_name == "employee_count"]
        assert len(employee_issues) >= 1

    def test_validate_invalid_founded_year(self):
        """Test that invalid founded years are flagged."""
        result = self.validator.validate_company_data(
            domain="example.com",
            data={
                "founded_year": 1500  # Too old
            },
            source="apollo"
        )

        year_issues = [i for i in result.issues if i.field_name == "founded_year"]
        assert len(year_issues) >= 1

    def test_cross_validate_sources(self):
        """Test cross-validation of data from multiple sources."""
        source_data = {
            "apollo": {
                "ceo": "Julie Strau",  # Wrong
                "company_name": "Microsoft",
                "headquarters": "Redmond"
            },
            "pdl": {
                "ceo": "Satya Nadella",  # Correct
                "company_name": "Microsoft Corporation",
                "headquarters": "Redmond, WA"
            }
        }

        merged_data, confidence = self.validator.cross_validate_sources(
            domain="microsoft.com",
            source_data=source_data
        )

        # Should use the correct CEO
        assert merged_data.get("ceo") == "Satya Nadella"

    def test_get_validator_singleton(self):
        """Test that get_validator returns a singleton."""
        v1 = get_validator()
        v2 = get_validator()
        assert v1 is v2

    def test_domain_normalization(self):
        """Test that domain is normalized correctly."""
        # With www prefix
        result1 = self.validator.validate_company_data(
            domain="www.microsoft.com",
            data={"ceo": "Satya Nadella"},
            source="test"
        )

        # Without www prefix
        result2 = self.validator.validate_company_data(
            domain="microsoft.com",
            data={"ceo": "Satya Nadella"},
            source="test"
        )

        # Both should validate the same way
        assert result1.is_valid == result2.is_valid
        assert len(result1.issues) == len(result2.issues)


class TestValidationIntegration:
    """Integration tests for data validation in the full pipeline."""

    def test_pre_validation_catches_wrong_ceo_before_llm(self):
        """Test that wrong CEO is caught before LLM council processing."""
        validator = DataValidator()

        # Simulate data that would be sent to LLM council
        apollo_data = {
            "ceo": "Julie Strau",
            "company_name": "Microsoft",
            "executives": [
                {"name": "Julie Strau", "title": "CEO", "roleType": "CEO"}
            ]
        }

        result = validator.validate_company_data(
            domain="microsoft.com",
            data=apollo_data,
            source="apollo"
        )

        # Pre-validation should catch this
        assert not result.is_valid or len(result.corrected_values) > 0

        # Corrected value should be available
        if "ceo" in result.corrected_values:
            assert result.corrected_values["ceo"] == "Satya Nadella"
