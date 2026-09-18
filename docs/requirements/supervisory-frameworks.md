# Supervisory Framework Mapping

The scoring categories are a prototype and must not be treated as a production control. The following official sources are the research baseline; the FCRM owner must approve the final interpretation before production.

## Sources

| Source | Publisher | Use in this workbench |
|---|---|---|
| [BSA/AML Examination Manual](https://bsaaml.ffiec.gov/manual) | FFIEC | Risk assessment, customer risk, products/services, geography, and controls. |
| [Risk-Based Approach for the Banking Sector](https://www.fatf-gafi.org/en/publications/Fatfrecommendations/Risk-based-approach-banking-sector.html) | FATF | Proportionate risk-based assessment and control expectations. |
| [Sanctions Programs and Country Information](https://ofac.treasury.gov/sanctions-programs-and-country-information) | U.S. Treasury OFAC | Sanctions and country-risk research; not a substitute for legal advice. |

Retrieval date for this mapping: 2026-09-18.

## Prototype category mapping

| Workbench category | Framework principle | Prototype rule | Production decision |
|---|---|---|---|
| Customer & Geography | Customer, geographic, and cross-border exposure should inform risk assessment. | Geography and customer-segment signals increase the category score. | Replace keywords with governed country/customer risk data and approved taxonomy. |
| Product & Channel | Products, services, and delivery channels can change exposure. | New products, new segments, multiple products, and explicit high-impact factors affect the score. | Add approved product/channel typology and evidence references. |
| Third Party / Vendor | Outsourcing and third parties require risk management and accountability. | Vendor involvement produces a higher category score and synthetic vendor evidence. | Add due diligence, control effectiveness, and vendor inventory references. |
| Change Complexity | Complexity and uncertainty affect the ability to identify and control risk. | Stated risk factors and low extraction confidence increase the score. | Separate inherent risk, control effectiveness, and residual risk. |

Controls mitigate risk; they do not reduce it to zero. The current prototype does not yet calculate residual risk, so that is a required production increment rather than a demo claim.

The mapping must record:

- source title, publisher, URL, and retrieval date;
- requirement or principle being used;
- category and rule it supports;
- why the rule applies to the change type; and
- analyst approval of the mapping.

The current implementation exposes `scoring_method` so a versioned, governed rule set can replace the prototype weights. Every production assessment must record the approved rule version, source evidence, control assumptions, and analyst approval.
