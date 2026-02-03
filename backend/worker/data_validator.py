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
        # Known C-suite executives (verified)
        "known_executives": [
            {"name": "Satya Nadella", "role": "CEO", "title": "Chairman and CEO"},
            {"name": "Amy Hood", "role": "CFO", "title": "Executive Vice President and CFO"},
            {"name": "Brad Smith", "role": "President", "title": "Vice Chair and President"},
            {"name": "Judson Althoff", "role": "CCO", "title": "Executive Vice President and Chief Commercial Officer"},
            {"name": "Scott Guthrie", "role": "EVP", "title": "Executive Vice President, Cloud + AI"},
            {"name": "Kathleen Hogan", "role": "CPO", "title": "Executive Vice President and Chief People Officer"},
            {"name": "Charlie Bell", "role": "EVP", "title": "Executive Vice President, Security"},
        ],
    },
    "apple.com": {
        "ceo": ["Tim Cook"],
        "company_name": ["Apple", "Apple Inc."],
        "headquarters": ["Cupertino", "Cupertino, California", "Cupertino, CA"],
        "industry": ["Technology", "Consumer Electronics"],
        "founded_year": [1976],
        "known_executives": [
            {"name": "Tim Cook", "role": "CEO", "title": "Chief Executive Officer"},
            {"name": "Luca Maestri", "role": "CFO", "title": "Senior Vice President and CFO"},
            {"name": "Jeff Williams", "role": "COO", "title": "Chief Operating Officer"},
            {"name": "Craig Federighi", "role": "SVP", "title": "Senior Vice President of Software Engineering"},
            {"name": "Katherine Adams", "role": "SVP", "title": "Senior Vice President and General Counsel"},
        ],
    },
    "google.com": {
        "ceo": ["Sundar Pichai"],
        "company_name": ["Google", "Google LLC", "Alphabet"],
        "headquarters": ["Mountain View", "Mountain View, California", "Mountain View, CA"],
        "industry": ["Technology", "Internet", "Software"],
        "founded_year": [1998],
        "known_executives": [
            {"name": "Sundar Pichai", "role": "CEO", "title": "CEO of Google and Alphabet"},
            {"name": "Ruth Porat", "role": "CFO", "title": "President and Chief Investment Officer"},
            {"name": "Philipp Schindler", "role": "CBO", "title": "Senior Vice President and Chief Business Officer"},
            {"name": "Prabhakar Raghavan", "role": "SVP", "title": "Senior Vice President, Knowledge & Information"},
        ],
    },
    "amazon.com": {
        "ceo": ["Andy Jassy"],
        "company_name": ["Amazon", "Amazon.com", "Amazon.com Inc."],
        "headquarters": ["Seattle", "Seattle, Washington", "Seattle, WA"],
        "industry": ["E-commerce", "Technology", "Retail"],
        "founded_year": [1994],
        "known_executives": [
            {"name": "Andy Jassy", "role": "CEO", "title": "President and Chief Executive Officer"},
            {"name": "Brian Olsavsky", "role": "CFO", "title": "Senior Vice President and Chief Financial Officer"},
            {"name": "Adam Selipsky", "role": "CEO AWS", "title": "CEO of Amazon Web Services"},
            {"name": "Doug Herrington", "role": "CEO Stores", "title": "CEO of Worldwide Amazon Stores"},
        ],
    },
    "meta.com": {
        "ceo": ["Mark Zuckerberg"],
        "company_name": ["Meta", "Meta Platforms", "Facebook"],
        "headquarters": ["Menlo Park", "Menlo Park, California", "Menlo Park, CA"],
        "industry": ["Technology", "Social Media"],
        "founded_year": [2004],
        "known_executives": [
            {"name": "Mark Zuckerberg", "role": "CEO", "title": "Chairman and CEO"},
            {"name": "Susan Li", "role": "CFO", "title": "Chief Financial Officer"},
            {"name": "Javier Olivan", "role": "COO", "title": "Chief Operating Officer"},
            {"name": "Chris Cox", "role": "CPO", "title": "Chief Product Officer"},
        ],
    },
    "facebook.com": {
        "ceo": ["Mark Zuckerberg"],
        "company_name": ["Meta", "Meta Platforms", "Facebook"],
        "headquarters": ["Menlo Park", "Menlo Park, California", "Menlo Park, CA"],
        "industry": ["Technology", "Social Media"],
        "founded_year": [2004],
        "known_executives": [
            {"name": "Mark Zuckerberg", "role": "CEO", "title": "Chairman and CEO"},
            {"name": "Susan Li", "role": "CFO", "title": "Chief Financial Officer"},
            {"name": "Javier Olivan", "role": "COO", "title": "Chief Operating Officer"},
            {"name": "Chris Cox", "role": "CPO", "title": "Chief Product Officer"},
        ],
    },
    "tesla.com": {
        "ceo": ["Elon Musk"],
        "company_name": ["Tesla", "Tesla Inc."],
        "headquarters": ["Austin", "Austin, Texas", "Palo Alto"],
        "industry": ["Automotive", "Electric Vehicles", "Energy"],
        "founded_year": [2003],
        "known_executives": [
            {"name": "Elon Musk", "role": "CEO", "title": "Chief Executive Officer"},
            {"name": "Vaibhav Taneja", "role": "CFO", "title": "Chief Financial Officer"},
            {"name": "Tom Zhu", "role": "SVP", "title": "Senior Vice President of Automotive"},
        ],
    },
    "nvidia.com": {
        "ceo": ["Jensen Huang"],
        "company_name": ["NVIDIA", "NVIDIA Corporation"],
        "headquarters": ["Santa Clara", "Santa Clara, California"],
        "industry": ["Technology", "Semiconductors"],
        "founded_year": [1993],
        "known_executives": [
            {"name": "Jensen Huang", "role": "CEO", "title": "President and Chief Executive Officer"},
            {"name": "Colette Kress", "role": "CFO", "title": "Executive Vice President and CFO"},
        ],
    },
    "salesforce.com": {
        "ceo": ["Marc Benioff"],
        "company_name": ["Salesforce", "Salesforce.com"],
        "headquarters": ["San Francisco", "San Francisco, California"],
        "industry": ["Technology", "Software", "CRM"],
        "founded_year": [1999],
        "known_executives": [
            {"name": "Marc Benioff", "role": "CEO", "title": "Chair and Chief Executive Officer"},
            {"name": "Amy Weaver", "role": "CFO", "title": "President and Chief Financial Officer"},
            {"name": "Brian Millham", "role": "COO", "title": "President and Chief Operating Officer"},
        ],
    },
    "oracle.com": {
        "ceo": ["Safra Catz"],
        "company_name": ["Oracle", "Oracle Corporation"],
        "headquarters": ["Austin", "Austin, Texas", "Redwood City"],
        "industry": ["Technology", "Software", "Database"],
        "founded_year": [1977],
        "known_executives": [
            {"name": "Safra Catz", "role": "CEO", "title": "Chief Executive Officer"},
            {"name": "Larry Ellison", "role": "CTO", "title": "Chairman and Chief Technology Officer"},
        ],
    },
    "ibm.com": {
        "ceo": ["Arvind Krishna"],
        "company_name": ["IBM", "International Business Machines"],
        "headquarters": ["Armonk", "Armonk, New York"],
        "industry": ["Technology", "Software", "IT Services"],
        "founded_year": [1911],
        "known_executives": [
            {"name": "Arvind Krishna", "role": "CEO", "title": "Chairman and Chief Executive Officer"},
            {"name": "James Kavanaugh", "role": "CFO", "title": "Senior Vice President and CFO"},
        ],
    },
    "intel.com": {
        "ceo": ["Pat Gelsinger"],
        "company_name": ["Intel", "Intel Corporation"],
        "headquarters": ["Santa Clara", "Santa Clara, California"],
        "industry": ["Technology", "Semiconductors"],
        "founded_year": [1968],
        "known_executives": [
            {"name": "Pat Gelsinger", "role": "CEO", "title": "Chief Executive Officer"},
            {"name": "David Zinsner", "role": "CFO", "title": "Executive Vice President and CFO"},
        ],
    },
    "cisco.com": {
        "ceo": ["Chuck Robbins"],
        "company_name": ["Cisco", "Cisco Systems"],
        "headquarters": ["San Jose", "San Jose, California"],
        "industry": ["Technology", "Networking"],
        "founded_year": [1984],
        "known_executives": [
            {"name": "Chuck Robbins", "role": "CEO", "title": "Chair and Chief Executive Officer"},
            {"name": "Scott Herren", "role": "CFO", "title": "Executive Vice President and CFO"},
        ],
    },
    "adobe.com": {
        "ceo": ["Shantanu Narayen"],
        "company_name": ["Adobe", "Adobe Inc."],
        "headquarters": ["San Jose", "San Jose, California"],
        "industry": ["Technology", "Software"],
        "founded_year": [1982],
        "known_executives": [
            {"name": "Shantanu Narayen", "role": "CEO", "title": "Chairman and Chief Executive Officer"},
            {"name": "Dan Durn", "role": "CFO", "title": "Executive Vice President and CFO"},
            {"name": "David Wadhwani", "role": "President", "title": "President, Digital Media Business"},
        ],
    },
}

# Common fake/generic names that should be flagged
SUSPICIOUS_NAMES = [
    # Test/placeholder patterns
    "test", "sample", "example", "placeholder", "unknown", "n/a", "tbd", "tba", "xxx",
    "fake", "dummy", "temp", "demo",
    # Generic common names often used as placeholders
    "john doe", "jane doe", "john smith", "jane smith", "tom smith", "bob smith",
    "julie strau", "mike johnson", "test user", "admin user", "default user",
    # Single word names (likely fake)
    "admin", "user", "manager", "director", "executive", "officer",
]

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

        STRICT VALIDATION: For known major companies, only allow executives
        that match the verified known_executives list.

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
        known_executives = known_facts.get("known_executives", [])

        # Combine stakeholders and executives
        all_people = stakeholders + executives

        for person in all_people:
            name = person.get("name", "")
            title = person.get("title", "")
            role_type = person.get("roleType", person.get("role_type", ""))

            if not name:
                continue

            name_lower = name.lower().strip()

            # STRICT CHECK 1: Check against suspicious/fake names
            is_suspicious = False
            for suspicious in SUSPICIOUS_NAMES:
                if suspicious in name_lower or name_lower == suspicious:
                    is_suspicious = True
                    issues.append(ValidationIssue(
                        field_name=f"stakeholder.{role_type}.name",
                        provided_value=name,
                        expected_values=[],
                        severity="critical",
                        message=f"Name '{name}' is a known fake/placeholder name - REJECTED",
                        source=source
                    ))
                    break

            if is_suspicious:
                continue

            # STRICT CHECK 2: For major companies, verify against known executives
            if known_executives:
                known_names = [exec["name"].lower().strip() for exec in known_executives]

                # Check if the name matches any known executive
                is_known_executive = any(
                    name_lower == known_name or
                    name_lower in known_name or
                    known_name in name_lower
                    for known_name in known_names
                )

                if not is_known_executive:
                    # This person is NOT in our known executives list for this major company
                    issues.append(ValidationIssue(
                        field_name=f"stakeholder.{role_type}.name",
                        provided_value=name,
                        expected_values=[exec["name"] for exec in known_executives],
                        severity="critical",
                        message=f"'{name}' is NOT a verified executive at {domain}. Known executives: {[e['name'] for e in known_executives[:5]]}",
                        source=source
                    ))
                    continue

            # STRICT CHECK 3: CEO validation
            if role_type == "CEO" or "CEO" in title.upper():
                if known_ceo:
                    known_ceo_lower = [c.lower().strip() for c in known_ceo]

                    is_valid_ceo = any(
                        name_lower == ceo or name_lower in ceo or ceo in name_lower
                        for ceo in known_ceo_lower
                    )

                    if not is_valid_ceo:
                        issues.append(ValidationIssue(
                            field_name=f"stakeholder.{role_type}.name",
                            provided_value=name,
                            expected_values=known_ceo,
                            severity="critical",
                            message=f"'{name}' listed as CEO but verified CEO is {known_ceo[0]}",
                            source=source
                        ))

        return issues

    def filter_invalid_stakeholders(
        self,
        domain: str,
        stakeholders: List[Dict[str, Any]],
        source: str = "unknown"
    ) -> List[Dict[str, Any]]:
        """
        Filter out stakeholders that fail validation.
        Returns only verified/valid stakeholders.

        Args:
            domain: Company domain
            stakeholders: List of stakeholder records
            source: Data source name

        Returns:
            List of valid stakeholders only
        """
        domain_normalized = domain.lower().strip()
        if domain_normalized.startswith("www."):
            domain_normalized = domain_normalized[4:]

        known_facts = self.known_facts.get(domain_normalized, {})
        known_executives = known_facts.get("known_executives", [])

        valid_stakeholders = []

        for person in stakeholders:
            name = person.get("name", "")
            if not name:
                continue

            name_lower = name.lower().strip()

            # Check 1: Reject suspicious names
            is_suspicious = any(
                suspicious in name_lower or name_lower == suspicious
                for suspicious in SUSPICIOUS_NAMES
            )
            if is_suspicious:
                logger.warning(f"Filtering out suspicious stakeholder: {name}")
                continue

            # Check 2: For known companies, only allow verified executives
            if known_executives:
                known_names = [exec["name"].lower().strip() for exec in known_executives]
                is_known = any(
                    name_lower == known_name or
                    name_lower in known_name or
                    known_name in name_lower
                    for known_name in known_names
                )
                if not is_known:
                    logger.warning(f"Filtering out unverified stakeholder for {domain}: {name}")
                    continue

            valid_stakeholders.append(person)

        logger.info(f"Stakeholder validation for {domain}: {len(valid_stakeholders)}/{len(stakeholders)} passed")
        return valid_stakeholders

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
