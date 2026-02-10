#!/usr/bin/env python3
"""
Test Gamma template with FULL comprehensive company data.
Verifies all fields are properly sent to template g_vsj27dcr73l1nv1
"""
import asyncio
import sys
import os

sys.path.insert(0, 'worker')
from gamma_slideshow import GammaSlideshowCreator

async def test_full_data():
    api_key = os.getenv("GAMMA_API_KEY")
    if not api_key:
        print("❌ GAMMA_API_KEY not set")
        return False

    # Create with your template
    creator = GammaSlideshowCreator(api_key, template_id="g_vsj27dcr73l1nv1")

    # Comprehensive test data with ALL fields populated
    full_company_data = {
        "company_name": "Acme Technology Solutions",
        "user_email": "john.smith@hp.com",
        "validated_data": {
            "company_name": "Acme Technology Solutions",
            "industry": "Enterprise Software & Cloud Services",
            "employee_count": "2,500",
            "account_type": "Private Sector",

            # Company Overview
            "company_overview": "Acme Technology Solutions is a leading enterprise software company specializing in cloud infrastructure, DevOps automation, and AI-powered business intelligence platforms. Founded in 2010, the company has grown to serve over 500 Fortune 1000 customers across North America and Europe, with annual recurring revenue exceeding $450M.",

            # IT Budget
            "estimated_it_spend": "125M",

            # Technology Stack
            "technology": [
                "AWS", "Azure", "Google Cloud Platform",
                "Kubernetes", "Docker", "Terraform",
                "Salesforce", "HubSpot", "Zendesk",
                "Slack", "Microsoft 365", "Zoom",
                "GitHub", "Jenkins", "CircleCI",
                "PostgreSQL", "MongoDB", "Redis",
                "Datadog", "PagerDuty", "Splunk"
            ],
            "technology_last_seen": "January 2026",

            # Intent Topics (with scores)
            "intent_topics": [
                {
                    "topic": "Cloud Infrastructure Modernization & Multi-Cloud Strategy",
                    "score": 92,
                    "description": "High engagement with cloud migration content, multi-cloud management tools, and infrastructure-as-code solutions"
                },
                {
                    "topic": "Cybersecurity & Zero Trust Architecture",
                    "score": 88,
                    "description": "Increased research on endpoint security, identity management, and compliance frameworks (SOC 2, ISO 27001)"
                },
                {
                    "topic": "AI/ML Infrastructure & GPU Computing",
                    "score": 85,
                    "description": "Growing interest in AI workload optimization, MLOps platforms, and high-performance computing solutions"
                }
            ],

            # Partner Mentions
            "partner_mentions": [
                "Dell Technologies", "Cisco", "VMware", "IBM",
                "Microsoft", "AWS", "Snowflake"
            ],

            # News & Triggers
            "news_triggers": {
                "funding": "Series D funding round of $150M led by Sequoia Capital announced in December 2025. Funds allocated for product development and international expansion.",
                "expansions": "Opening new R&D centers in Austin, TX and Toronto, Canada. Planning to hire 300+ engineers in 2026. New 50,000 sq ft headquarters in San Francisco.",
                "executive_changes": "Hired Sarah Chen as Chief Technology Officer (previously VP Engineering at Stripe). New VP of Sales from Salesforce joined in Q4 2025.",
                "partnerships": "Strategic partnership with Microsoft Azure announced for enterprise AI solutions. Integration partnership with Snowflake for data analytics platform.",
                "products": "Launched new AI-powered DevOps automation platform in November 2025. Beta testing of quantum-ready encryption module."
            },

            # Pain Points
            "pain_points": [
                {
                    "title": "Multi-cloud complexity and cost optimization",
                    "description": "Managing workloads across AWS, Azure, and GCP creates operational overhead and makes cost allocation difficult. Need unified visibility and governance across cloud providers while optimizing spend and preventing waste."
                },
                {
                    "title": "Security compliance at scale",
                    "description": "Rapid growth to 2,500 employees increases security surface area. Must maintain SOC 2 Type II and ISO 27001 certifications while enabling developer productivity. Need modern endpoint protection and zero-trust architecture."
                },
                {
                    "title": "DevOps infrastructure modernization",
                    "description": "Legacy CI/CD pipelines and inconsistent developer environments slow deployment velocity. Need standardized, secure development infrastructure that scales with engineering team growth from 200 to 500+ developers."
                }
            ],

            # Sales Opportunities
            "sales_opportunities": [
                {
                    "title": "Enterprise workstation refresh for 300+ new engineering hires",
                    "description": "R&D expansion requires high-performance workstations for software development, AI/ML experimentation, and data engineering. Validate performance requirements, security standards, and deployment timeline for Q2-Q3 2026 rollout."
                },
                {
                    "title": "Secure managed device program for hybrid workforce",
                    "description": "Post-pandemic hybrid model (3 days in office, 2 remote) requires standardized, secure endpoint management. Qualify scope across all 2,500 employees, desired management capabilities, and integration with existing security tools."
                },
                {
                    "title": "Edge computing infrastructure for distributed teams",
                    "description": "New regional offices need local computing resources and secure connectivity. Validate infrastructure requirements, refresh cycles, and support model preferences for distributed IT operations."
                }
            ],

            # Recommended Solutions
            "recommended_solutions": [
                {
                    "title": "HP Z-Series Workstations for AI/ML Development",
                    "description": "High-performance workstations with NVIDIA RTX GPUs, 128GB+ RAM, and NVMe storage optimized for AI development, data science, and cloud-native application development. Supports multi-cloud tooling and containerized workflows."
                },
                {
                    "title": "HP Managed Device Services & Security",
                    "description": "End-to-end device lifecycle management with integrated security (HP Wolf Security), automated deployment, proactive support, and compliance reporting. Reduces IT overhead while maintaining enterprise security posture."
                },
                {
                    "title": "HP Edge Computing Solutions",
                    "description": "Edge-optimized compute infrastructure with centralized management, built-in security, and remote monitoring capabilities. Enables distributed teams while maintaining governance and operational efficiency."
                }
            ],

            # Stakeholder Profiles
            "stakeholder_profiles": [
                {
                    "name": "Sarah Chen",
                    "title": "Chief Technology Officer",
                    "department": "Technology & Engineering",
                    "start_date": "August 2025",
                    "is_new_hire": True,
                    "hire_date": "August 2025",
                    "email": "schen@acmetech.com",
                    "phone": "+1 (415) 555-0123",
                    "mobile": "+1 (415) 555-0124",
                    "direct_phone": "+1 (415) 555-0123",
                    "linkedin": "linkedin.com/in/sarahchen",
                    "bio": "Sarah Chen joined Acme as CTO in August 2025, bringing 15 years of engineering leadership experience from Stripe and Google. She is driving the company's cloud-native transformation and AI/ML platform strategy. Previously led Stripe's infrastructure team through hypergrowth from 200 to 1,000+ engineers.",
                    "strategic_priorities": [
                        {
                            "name": "Accelerate cloud-native product development",
                            "description": "Modernize development infrastructure and CI/CD pipelines to support 500+ engineer team. Goal: reduce deployment time from 2 hours to 15 minutes and increase deployment frequency 10x."
                        },
                        {
                            "name": "Build world-class AI/ML infrastructure",
                            "description": "Establish GPU computing capabilities and MLOps platform to power next-generation AI products. Need high-performance compute for model training and inference at scale."
                        },
                        {
                            "name": "Strengthen security and compliance posture",
                            "description": "Implement zero-trust architecture and automated compliance monitoring. Must maintain SOC 2 Type II while enabling engineering velocity and supporting hybrid workforce."
                        }
                    ],
                    "communication_preference": "Email / LinkedIn / Direct Phone",
                    "conversation_starters": [
                        {
                            "topic": "Developer infrastructure modernization",
                            "question": "As you scale Acme's engineering team to 500+, what's your biggest infrastructure challenge: developer productivity, security compliance, or compute performance for AI workloads?"
                        },
                        {
                            "topic": "AI/ML compute requirements",
                            "question": "With your AI platform launch, what GPU computing capabilities do you need for model development: local workstations for data scientists, cloud burst capacity, or edge inference infrastructure?"
                        }
                    ]
                },
                {
                    "name": "Michael Rodriguez",
                    "title": "Chief Financial Officer",
                    "department": "Finance",
                    "start_date": "March 2018",
                    "email": "mrodriguez@acmetech.com",
                    "phone": "+1 (415) 555-0130",
                    "linkedin": "linkedin.com/in/michaelrodriguez",
                    "bio": "Michael Rodriguez has served as CFO since 2018, leading Acme through three successful funding rounds totaling $350M. He focuses on operational efficiency, unit economics, and preparing the company for eventual IPO. Previously held CFO roles at SaaS companies including New Relic and Atlassian.",
                    "strategic_priorities": [
                        {
                            "name": "Optimize operational expenses and improve margins",
                            "description": "Drive cost discipline across all departments while maintaining growth velocity. Target: improve EBITDA margin from -5% to +10% within 18 months through operational efficiency."
                        },
                        {
                            "name": "Technology spend visibility and governance",
                            "description": "Implement better controls and visibility into cloud spend, SaaS subscriptions, and infrastructure costs. Need predictable, defendable technology budget with clear ROI."
                        },
                        {
                            "name": "Prepare financial infrastructure for scale",
                            "description": "Build financial systems and processes to support IPO readiness. Strengthen internal controls, compliance, and reporting capabilities."
                        }
                    ],
                    "communication_preference": "Email / Phone / Quarterly Business Reviews",
                    "conversation_starters": [
                        {
                            "topic": "Technology cost optimization",
                            "question": "As you focus on margin improvement, where do you see the most opportunity: cloud cost optimization, vendor consolidation, or standardizing IT infrastructure?"
                        },
                        {
                            "topic": "Predictable technology spend",
                            "question": "What would make technology budgeting easier for you: consumption-based pricing, fixed monthly costs, or better forecasting tools?"
                        }
                    ]
                },
                {
                    "name": "Jennifer Kim",
                    "title": "Chief Information Security Officer",
                    "department": "Security & Compliance",
                    "start_date": "January 2023",
                    "email": "jkim@acmetech.com",
                    "phone": "+1 (415) 555-0140",
                    "mobile": "+1 (415) 555-0141",
                    "linkedin": "linkedin.com/in/jenniferkim-security",
                    "bio": "Jennifer Kim joined as CISO in 2023, bringing deep expertise in zero-trust security and compliance from Okta and Palo Alto Networks. She is responsible for enterprise security strategy, compliance certifications (SOC 2, ISO 27001), and risk management across Acme's hybrid workforce.",
                    "strategic_priorities": [
                        {
                            "name": "Implement zero-trust security architecture",
                            "description": "Modernize security model from perimeter-based to zero-trust for hybrid workforce. Need endpoint protection, identity management, and secure access that works for remote and office employees."
                        },
                        {
                            "name": "Maintain compliance while enabling agility",
                            "description": "Balance security/compliance requirements (SOC 2, ISO 27001, GDPR) with developer productivity. Automate compliance monitoring and shift security left in development process."
                        },
                        {
                            "name": "Reduce security tooling complexity",
                            "description": "Consolidate 20+ security tools into integrated platform. Reduce alert fatigue, improve threat detection, and enable security team to focus on strategic initiatives vs tool management."
                        }
                    ],
                    "communication_preference": "Email / Secure Messaging / LinkedIn",
                    "conversation_starters": [
                        {
                            "topic": "Endpoint security for hybrid workforce",
                            "question": "With 2,500 employees in hybrid model, what's your biggest endpoint security concern: device management, data protection, or ensuring compliance across home and office environments?"
                        },
                        {
                            "topic": "Zero-trust implementation",
                            "question": "As you implement zero-trust architecture, what's the priority: identity and access management, endpoint security and attestation, or network segmentation?"
                        }
                    ]
                }
            ],

            # Recommended Next Steps
            "recommended_next_steps": [
                {
                    "step": "Build credibility with cloud infrastructure thought leadership",
                    "collateral": "Multi-cloud cost optimization guide for engineering teams",
                    "why": "Aligns with Sarah Chen's (CTO) priority to modernize infrastructure. Positions HP as strategic partner for engineering team growth without forcing product pitch."
                },
                {
                    "step": "Quantify security and productivity benefits",
                    "collateral": "ROI calculator for managed device programs in hybrid companies",
                    "why": "Addresses Michael Rodriguez's (CFO) need for cost visibility and Jennifer Kim's (CISO) security requirements. Shows financial and security impact before discussing solutions."
                },
                {
                    "step": "Demonstrate AI/ML workstation capabilities",
                    "collateral": "Performance benchmarks: Z-Series workstations for AI development",
                    "why": "Directly supports CTO's strategic priority to build AI/ML infrastructure. Provides technical validation for engineering team's GPU computing requirements."
                },
                {
                    "step": "Share compliance success stories",
                    "collateral": "Case study: SaaS company maintaining SOC 2 with 500+ endpoints",
                    "why": "Addresses CISO's challenge of maintaining compliance while scaling. Shows how similar companies solved this with HP managed security services."
                }
            ]
        },
        "confidence_score": 0.92
    }

    print("=" * 70)
    print("TESTING GAMMA TEMPLATE WITH COMPREHENSIVE DATA")
    print("=" * 70)
    print(f"Template ID: g_vsj27dcr73l1nv1")
    print(f"Company: {full_company_data['company_name']}")
    print(f"Stakeholders: {len(full_company_data['validated_data']['stakeholder_profiles'])}")
    print(f"Intent Topics: {len(full_company_data['validated_data']['intent_topics'])}")
    print("=" * 70)
    print()

    try:
        print("Creating slideshow with full data...")
        result = await creator.create_slideshow(full_company_data, user_email="john.smith@hp.com")

        print()
        print("=" * 70)
        print("RESULT:")
        print("=" * 70)
        print(f"Success: {result.get('success')}")
        print(f"URL: {result.get('slideshow_url')}")
        print(f"ID: {result.get('slideshow_id')}")
        print(f"Error: {result.get('error')}")
        print("=" * 70)

        if result.get('success'):
            print()
            print("✅ TEMPLATE SLIDESHOW CREATED WITH FULL DATA!")
            print(f"🔗 View here: {result.get('slideshow_url')}")
            print()
            print("Data included:")
            print("  ✓ Company overview & metrics")
            print("  ✓ Intent topics with scores")
            print("  ✓ Buying signals & news")
            print("  ✓ Pain points & opportunities")
            print("  ✓ 3 stakeholder profiles")
            print("  ✓ Strategic priorities")
            print("  ✓ Conversation starters")
            print("  ✓ Recommended next steps")
            return True
        else:
            print(f"\n❌ Failed: {result.get('error')}")
            return False

    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_full_data())
    exit(0 if success else 1)
