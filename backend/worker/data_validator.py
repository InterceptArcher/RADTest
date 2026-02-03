"""
Pre-LLM Data Validation Module.

This module validates data from API sources BEFORE sending to the LLM council.
It catches egregiously wrong data (like incorrect CEO names for well-known companies)
using a combination of:
1. Known facts database (for major companies)
2. Cross-source agreement checking
3. Confidence scoring based on source reliability
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


# Known facts for major companies - CEO names, HQ locations, etc.
# This serves as a sanity check to catch egregiously wrong data
KNOWN_COMPANY_FACTS = {
    "microsoft.com": {
        "ceo": ["Satya Nadella"],
        "company_name": ["Microsoft", "Microsoft Corporation"],
        "headquarters": ["Redmond", "Redmond, Washington", "Redmond, WA"],
        "industry": ["Technology", "Software", "Computer Software"],
        "founded_year": [1975],
    },
    "apple.com": {
        "ceo": ["Tim Cook"],
        "company_name": ["Apple", "Apple Inc."],
        "headquarters": ["Cupertino", "Cupertino, California", "Cupertino, CA"],
        "industry": ["Technology", "Consumer Electronics"],
        "founded_year": [1976],
    },
    "google.com": {
        "ceo": ["Sundar Pichai"],
        "company_name": ["Google", "Google LLC", "Alphabet"],
        "headquarters": ["Mountain View", "Mountain View, California", "Mountain View, CA"],
        "industry": ["Technology", "Internet", "Software"],
        "founded_year": [1998],
    },
    "amazon.com": {
        "ceo": ["Andy Jassy"],
        "company_name": ["Amazon", "Amazon.com", "Amazon.com Inc."],
        "headquarters": ["Seattle", "Seattle, Washington", "Seattle, WA"],
        "industry": ["E-commerce", "Technology", "Retail"],
        "founded_year": [1994],
    },
    "meta.com": {
        "ceo": ["Mark Zuckerberg"],
        "company_name": ["Meta", "Meta Platforms", "Facebook"],
        "headquarters": ["Menlo Park", "Menlo Park, California", "Menlo Park, CA"],
        "industry": ["Technology", "Social Media"],
        "founded_year": [2004],
    },
    "facebook.com": {
        "ceo": ["Mark Zuckerberg"],
        "company_name": ["Meta", "Meta Platforms", "Facebook"],
        "headquarters": ["Menlo Park", "Menlo Park, California", "Menlo Park, CA"],
        "industry": ["Technology", "Social Media"],
        "founded_year": [2004],
    },
    "tesla.com": {
        "ceo": ["Elon Musk"],
        "company_name": ["Tesla", "Tesla Inc."],
        "headquarters": ["Austin", "Austin, Texas", "Palo Alto"],
        "industry": ["Automotive", "Electric Vehicles", "Energy"],
        "founded_year": [2003],
    },
    "nvidia.com": {
        "ceo": ["Jensen Huang"],
        "company_name": ["NVIDIA", "NVIDIA Corporation"],
        "headquarters": ["Santa Clara", "Santa Clara, California"],
        "industry": ["Technology", "Semiconductors"],
        "founded_year": [1993],
    },
    "salesforce.com": {
        "ceo": ["Marc Benioff"],
        "company_name": ["Salesforce", "Salesforce.com"],
        "headquarters": ["San Francisco", "San Francisco, California"],
        "industry": ["Technology", "Software", "CRM"],
        "founded_year": [1999],
    },
    "oracle.com": {
        "ceo": ["Safra Catz"],
        "company_name": ["Oracle", "Oracle Corporation"],
        "headquarters": ["Austin", "Austin, Texas", "Redwood City"],
        "industry": ["Technology", "Software", "Database"],
        "founded_year": [1977],
    },
    "ibm.com": {
        "ceo": ["Arvind Krishna"],
        "company_name": ["IBM", "International Business Machines"],
        "headquarters": ["Armonk", "Armonk, New York"],
        "industry": ["Technology", "Software", "IT Services"],
        "founded_year": [1911],
    },
    "intel.com": {
        "ceo": ["Pat Gelsinger"],
        "company_name": ["Intel", "Intel Corporation"],
        "headquarters": ["Santa Clara", "Santa Clara, California"],
        "industry": ["Technology", "Semiconductors"],
        "founded_year": [1968],
    },
    "cisco.com": {
        "ceo": ["Chuck Robbins"],
        "company_name": ["Cisco", "Cisco Systems"],
        "headquarters": ["San Jose", "San Jose, California"],
        "industry": ["Technology", "Networking"],
        "founded_year": [1984],
    },
    "adobe.com": {
        "ceo": ["Shantanu Narayen"],
        "company_name": ["Adobe", "Adobe Inc."],
        "headquarters": ["San Jose", "San Jose, California"],
        "industry": ["Technology", "Software"],
        "founded_year": [1982],
    },
}

# C-suite titles to validate
CSUITE_TITLES = {
    "CEO": ["Chief Executive Officer", "CEO", "Co-CEO"],
    "CTO": ["Chief Technology Officer", "CTO"],
    "CIO": ["Chief Information Officer", "CIO"],
    "CFO": ["Chief Financial Officer", "CFO"],
    "COO": ["Chief Operating Officer", "COO"],
    "CISO": ["Chief Information Security Officer", "CISO"],
    "CMO": ["Chief Marketing Officer", "CMO"],
    "CPO": ["Chief Product Officer", "CPO"],
}


@dataclass
class ValidationIssue:
    """Represents a data validation issue found."""
    field_name: str
    provided_value: Any
    expected_values: List[Any]
    severity: str  # "critical", "warning", "info"
    message: str
    source: str


@dataclass
class DataValidationResult:
    """Result of pre-LLM data validation."""
    is_valid: bool
    confidence_score: float  # 0-1, how confident we are in the data
    issues: List[ValidationIssue] = field(default_factory=list)
    corrected_values: Dict[str, Any] = field(default_factory=dict)
    validated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class DataValidator:
    """
    Pre-LLM Data Validator.

    Validates incoming data from API sources before it goes to the LLM council.
    Catches egregiously wrong data early to prevent garbage-in-garbage-out.
    """

    def __init__(self):
        self.known_facts = KNOWN_COMPANY_FACTS
        logger.info("DataValidator initialized with known facts for %d companies",
                   len(self.known_facts))

    def validate_company_data(
        self,
        domain: str,
        data: Dict[str, Any],
        source: str = "unknown"
    ) -> DataValidationResult:
        """
        Validate company data against known facts and cross-source checks.

        Args:
            domain: Company domain (e.g., "microsoft.com")
            data: Dictionary of company data from an API source
            source: Name of the data source (e.g., "apollo", "pdl")

        Returns:
            DataValidationResult with validation status and any issues found
        """
        issues: List[ValidationIssue] = []
        corrected_values: Dict[str, Any] = {}
        confidence_score = 1.0

        # Normalize domain
        domain_normalized = domain.lower().strip()
        if domain_normalized.startswith("www."):
            domain_normalized = domain_normalized[4:]

        # Check against known facts if we have them
        known_facts = self.known_facts.get(domain_normalized)

        if known_facts:
            # Validate CEO
            ceo_issue = self._validate_field(
                field_name="ceo",
                provided_value=data.get("ceo"),
                expected_values=known_facts.get("ceo", []),
                source=source,
                severity="critical"
            )
            if ceo_issue:
                issues.append(ceo_issue)
                # Correct the value
                corrected_values["ceo"] = known_facts["ceo"][0]
                confidence_score -= 0.3

            # Validate company name
            name_issue = self._validate_field(
                field_name="company_name",
                provided_value=data.get("company_name"),
                expected_values=known_facts.get("company_name", []),
                source=source,
                severity="warning"
            )
            if name_issue:
                issues.append(name_issue)
                confidence_score -= 0.1

            # Validate headquarters
            hq_issue = self._validate_field(
                field_name="headquarters",
                provided_value=data.get("headquarters"),
                expected_values=known_facts.get("headquarters", []),
                source=source,
                severity="warning"
            )
            if hq_issue:
                issues.append(hq_issue)
                confidence_score -= 0.1

            # Validate industry
            industry_issue = self._validate_field(
                field_name="industry",
                provided_value=data.get("industry"),
                expected_values=known_facts.get("industry", []),
                source=source,
                severity="info"
            )
            if industry_issue:
                issues.append(industry_issue)
                confidence_score -= 0.05

            # Validate founded year
            year_issue = self._validate_field(
                field_name="founded_year",
                provided_value=data.get("founded_year"),
                expected_values=known_facts.get("founded_year", []),
                source=source,
                severity="warning"
            )
            if year_issue:
                issues.append(year_issue)
                confidence_score -= 0.1

        # Validate stakeholder data
        stakeholder_issues = self._validate_stakeholders(
            domain_normalized,
            data.get("stakeholders", []),
            data.get("executives", []),
            source
        )
        issues.extend(stakeholder_issues)
        if stakeholder_issues:
            confidence_score -= 0.1 * len([i for i in stakeholder_issues if i.severity == "critical"])

        # General sanity checks
        sanity_issues = self._sanity_checks(data, source)
        issues.extend(sanity_issues)
        if sanity_issues:
            confidence_score -= 0.05 * len(sanity_issues)

        # Clamp confidence score
        confidence_score = max(0.0, min(1.0, confidence_score))

        # Log validation results
        if issues:
            critical_count = len([i for i in issues if i.severity == "critical"])
            warning_count = len([i for i in issues if i.severity == "warning"])
            logger.warning(
                f"Data validation for {domain}: {critical_count} critical, "
                f"{warning_count} warning issues found from source {source}"
            )
            for issue in issues:
                logger.warning(f"  - [{issue.severity}] {issue.field_name}: {issue.message}")

        return DataValidationResult(
            is_valid=len([i for i in issues if i.severity == "critical"]) == 0,
            confidence_score=confidence_score,
            issues=issues,
            corrected_values=corrected_values
        )

    def _validate_field(
        self,
        field_name: str,
        provided_value: Any,
        expected_values: List[Any],
        source: str,
        severity: str = "warning"
    ) -> Optional[ValidationIssue]:
        """
        Validate a single field against expected values.

        Args:
            field_name: Name of the field being validated
            provided_value: Value provided by the data source
            expected_values: List of acceptable values
            source: Data source name
            severity: Issue severity if validation fails

        Returns:
            ValidationIssue if validation fails, None otherwise
        """
        if not provided_value or not expected_values:
            return None

        # Normalize for comparison
        provided_normalized = str(provided_value).lower().strip()
        expected_normalized = [str(v).lower().strip() for v in expected_values]

        # Check for exact or partial match
        if provided_normalized in expected_normalized:
            return None

        # Check for partial matches (e.g., "Satya" in "Satya Nadella")
        for expected in expected_normalized:
            if provided_normalized in expected or expected in provided_normalized:
                return None

        return ValidationIssue(
            field_name=field_name,
            provided_value=provided_value,
            expected_values=expected_values,
            severity=severity,
            message=f"Value '{provided_value}' does not match known values: {expected_values}",
            source=source
        )

    def _validate_stakeholders(
        self,
        domain: str,
        stakeholders: List[Dict[str, Any]],
        executives: List[Dict[str, Any]],
        source: str
    ) -> List[ValidationIssue]:
        """
        Validate stakeholder data for consistency and accuracy.

        Args:
            domain: Company domain
            stakeholders: List of stakeholder records
            executives: List of executive records
            source: Data source name

        Returns:
            List of validation issues found
        """
        issues = []
        known_facts = self.known_facts.get(domain, {})
        known_ceo = known_facts.get("ceo", [])

        # Combine stakeholders and executives
        all_people = stakeholders + executives

        for person in all_people:
            name = person.get("name", "")
            title = person.get("title", "")
            role_type = person.get("roleType", person.get("role_type", ""))

            # Check if someone is incorrectly listed as CEO
            if role_type == "CEO" or "CEO" in title.upper():
                if known_ceo and name:
                    name_lower = name.lower().strip()
                    known_ceo_lower = [c.lower().strip() for c in known_ceo]

                    # Check if the name matches any known CEO
                    is_valid_ceo = any(
                        name_lower in ceo or ceo in name_lower
                        for ceo in known_ceo_lower
                    )

                    if not is_valid_ceo:
                        issues.append(ValidationIssue(
                            field_name=f"stakeholder.{role_type}.name",
                            provided_value=name,
                            expected_values=known_ceo,
                            severity="critical",
                            message=f"Person '{name}' listed as CEO but known CEO is {known_ceo}",
                            source=source
                        ))

            # Check for duplicate stakeholders with different names in same role
            # (this might indicate bad data)

            # Check for obviously fake or placeholder names
            suspicious_patterns = [
                "test", "sample", "example", "placeholder", "unknown",
                "n/a", "tbd", "tba", "xxx"
            ]
            if name and any(pattern in name.lower() for pattern in suspicious_patterns):
                issues.append(ValidationIssue(
                    field_name=f"stakeholder.{role_type}.name",
                    provided_value=name,
                    expected_values=[],
                    severity="warning",
                    message=f"Name '{name}' appears to be a placeholder or test value",
                    source=source
                ))

        return issues

    def _sanity_checks(
        self,
        data: Dict[str, Any],
        source: str
    ) -> List[ValidationIssue]:
        """
        Perform general sanity checks on the data.

        Args:
            data: Company data dictionary
            source: Data source name

        Returns:
            List of validation issues found
        """
        issues = []

        # Check employee count is reasonable
        employee_count = data.get("employee_count")
        if employee_count:
            try:
                count = int(str(employee_count).replace(",", "").replace("+", ""))
                if count < 0:
                    issues.append(ValidationIssue(
                        field_name="employee_count",
                        provided_value=employee_count,
                        expected_values=["positive number"],
                        severity="warning",
                        message="Employee count cannot be negative",
                        source=source
                    ))
                elif count > 10_000_000:
                    issues.append(ValidationIssue(
                        field_name="employee_count",
                        provided_value=employee_count,
                        expected_values=["< 10,000,000"],
                        severity="warning",
                        message="Employee count seems unrealistically high",
                        source=source
                    ))
            except (ValueError, TypeError):
                pass

        # Check founded year is reasonable
        founded_year = data.get("founded_year")
        if founded_year:
            try:
                year = int(founded_year)
                current_year = datetime.now().year
                if year < 1800 or year > current_year:
                    issues.append(ValidationIssue(
                        field_name="founded_year",
                        provided_value=founded_year,
                        expected_values=[f"1800-{current_year}"],
                        severity="warning",
                        message=f"Founded year {year} is outside reasonable range",
                        source=source
                    ))
            except (ValueError, TypeError):
                pass

        # Check for empty required fields
        required_fields = ["company_name", "domain"]
        for field in required_fields:
            value = data.get(field)
            if not value or (isinstance(value, str) and not value.strip()):
                issues.append(ValidationIssue(
                    field_name=field,
                    provided_value=value,
                    expected_values=["non-empty value"],
                    severity="warning",
                    message=f"Required field '{field}' is empty",
                    source=source
                ))

        return issues

    def cross_validate_sources(
        self,
        domain: str,
        source_data: Dict[str, Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], float]:
        """
        Cross-validate data from multiple sources and return best values.

        Args:
            domain: Company domain
            source_data: Dict mapping source name to data from that source

        Returns:
            Tuple of (merged best data, confidence score)
        """
        if not source_data:
            return {}, 0.0

        # Validate each source
        validation_results = {}
        for source, data in source_data.items():
            validation_results[source] = self.validate_company_data(
                domain=domain,
                data=data,
                source=source
            )

        # Merge data, preferring sources with higher confidence
        sorted_sources = sorted(
            validation_results.items(),
            key=lambda x: x[1].confidence_score,
            reverse=True
        )

        merged_data = {}
        for source, result in sorted_sources:
            data = source_data[source]
            for key, value in data.items():
                if key not in merged_data and value:
                    # Use corrected value if available
                    if key in result.corrected_values:
                        merged_data[key] = result.corrected_values[key]
                    else:
                        merged_data[key] = value

        # Calculate overall confidence
        if sorted_sources:
            overall_confidence = sorted_sources[0][1].confidence_score
        else:
            overall_confidence = 0.0

        return merged_data, overall_confidence


# Singleton instance for reuse
_validator_instance: Optional[DataValidator] = None


def get_validator() -> DataValidator:
    """Get or create the singleton DataValidator instance."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = DataValidator()
    return _validator_instance
