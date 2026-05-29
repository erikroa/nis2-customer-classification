# NIS2 / NIS2UmsuCG / DORA — Quick Reference

A short reference for the regulations this pipeline classifies against. Not legal advice.

## NIS2 Directive (EU 2022/2555)

The EU's network and information security directive. Replaces the original NIS Directive (2016). EU member states had until 17 October 2024 to transpose it into national law (Germany's national implementation is the **NIS2UmsuCG**, which lags the deadline but covers the same scope).

NIS2 distinguishes two tiers of regulated entity:

### Essential Entity ("particularly important")
- Operates in an **Annex 1** sector
- AND is a **large enterprise** (≥250 employees, OR turnover >€50M and balance sheet >€43M)

**Annex 1 sectors:**
- Energy (electricity, gas, district heating/cooling, oil, hydrogen)
- Transport (air, rail, water, road — subset)
- Banking
- Financial market infrastructures
- Health (providers, EU reference labs, pharmaceuticals, critical medical devices)
- Drinking water
- Waste water
- Digital infrastructure (IXPs, DNS, TLD registries, cloud, data centers, CDNs, trust services, public electronic comms)
- ICT service management (managed service providers, managed security service providers)
- Public administration (central/regional)
- Space (ground infrastructure for space-based services)

### Important Entity
- Operates in an **Annex 2** sector (or Annex 1 at medium size)
- Medium enterprise (50-249 employees, OR turnover €10M–€50M)

**Annex 2 sectors:**
- Postal and courier services
- Waste management
- Manufacture, production and distribution of chemicals
- Production, processing and distribution of food
- Manufacturing (medical devices, computer/electronics, electrical equipment, machinery, motor vehicles, other transport equipment)
- Digital providers (online marketplaces, search engines, social networks)
- Research

### Out of scope

Entities that are either:
- In a sector not listed in Annex 1 or 2, OR
- Small or micro enterprises (<50 employees AND turnover <€10M), with named exceptions (e.g. TLD registries, DNS providers are in regardless of size)

## DORA — Digital Operational Resilience Act (EU 2022/2554)

The EU's financial-sector resilience regulation. Applies from 17 January 2025. Targets specifically financial entities, with parallel scope to (but narrower than) NIS2 Annex 1 Finance.

### DORA-applicable entities
- Credit institutions (banks)
- Payment institutions
- Electronic money institutions
- Account information service providers
- Investment firms
- Trading venues
- Central counterparties (CCPs)
- Central securities depositories (CSDs)
- Trade repositories
- Managers of alternative investment funds
- Management companies (UCITS)
- Insurance and reinsurance undertakings
- Insurance, reinsurance, and ancillary intermediaries
- Crypto-asset service providers (CASPs)
- Issuers of asset-referenced tokens
- Crowdfunding service providers
- Institutions for occupational retirement provisions (IORPs)
- Credit rating agencies
- Auditors and audit firms (when auditing financial entities)
- Administrators of critical benchmarks

### Relationship to NIS2

DORA and NIS2 overlap on financial entities. Most DORA-applicable entities also fall under NIS2 Annex 1 (Banking, Financial market infrastructures). The two regulations are parallel regimes with distinct technical requirements — a bank complies with both.

This pipeline models that as: `classification = 'Essential Entity'` + `dora_applicability = TRUE` for entities in scope of both.

## Practical implications for a B2B SaaS doing customer scoping

If you sell to regulated entities, your **customers' regulatory obligations affect you** in three main ways:

1. **Contractual security requirements.** NIS2 requires Essential and Important entities to manage supply-chain risk — they will push contractual security obligations onto their software vendors. Expect questionnaires, SOC2 requirements, breach-notification clauses.

2. **DORA's Third-Party ICT Provider regime.** DORA explicitly regulates the relationship between financial entities and their ICT providers, including standardized contractual terms and the EU's ability to designate providers as "critical." If you have substantial revenue from DORA-applicable customers, you may eventually fall under direct DORA oversight as a critical third-party.

3. **Incident reporting cascade.** Regulated customers are required to report security incidents to their regulators within tight windows (24h initial, 72h full). They expect their vendors to support that — meaning you need incident detection and reporting capabilities that match.

Knowing which customers fall under which regime is the foundation for prioritizing all three of these.

## Sources

- [NIS2 Directive (EU 2022/2555)](https://eur-lex.europa.eu/eli/dir/2022/2555/oj)
- [DORA (EU 2022/2554)](https://eur-lex.europa.eu/eli/reg/2022/2554/oj)
- German NIS2UmsuCG (NIS2 Umsetzungs- und Cybersicherheitsstärkungsgesetz) — Bundesministerium des Innern und für Heimat

This pipeline's classification logic is a starter mapping. The actual regulatory classification of any individual entity is a legal determination, not a SQL output.
