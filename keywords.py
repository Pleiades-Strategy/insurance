from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

tag_keywords = {

    "state_insurance_residual_markets": [
        # FAIR Plans & residual market mechanisms
        "FAIR Plan", "fair access to insurance requirements", "residual market",
        "assigned risk plan", "beach plan", "windstorm insurance association",
        "TWIA", "Texas Windstorm Insurance Association", "Citizens Property Insurance",
        "state-backed insurance", "state-run insurer", "government insurer",
        "insurer of last resort", "last resort coverage", "market of last resort",
        "availability crisis", "market failure", "coverage guarantee",
        "state insurance pool", "joint underwriting association", "underwriting association",
        "guaranty association", "state guaranty association", "guaranty fund",
        "insurance guaranty", "insolvency fund", "liquidation",
        # Public options & models
        "public option", "public insurer", "state insurer", "state-owned insurer",
        "public reinsurance", "state reinsurance fund", "catastrophe fund",
        "hurricane catastrophe fund", "cat fund", "FHCF",
        "windstorm", "wind pool", "coastal insurance pool"
    ],

    "fortification_programs": [
        # Home hardening & property-level resilience
        "home hardening", "fortification", "fortification program",
        "home fortification", "roof strapping", "roof replacement",
        "impact windows", "storm shutters", "hurricane straps",
        "wind mitigation", "wind-resistant", "fire-resistant",
        "ember resistance", "home ignition zone", "structure hardening",
        "defensible space", "home retrofit", "retrofitting",
        "infrastructure retrofit", "elevated structure", "flood-proofing",
        "wet floodproofing", "flood proof", "elevation certificate",
        "mitigation grant", "fortification grant", "resilience grant",
        "ibhs", "strengthen home", "home resiliency program",
        "mystrong home", "build strong", "fortified home",
        "insurance discount", "mitigation credit", "premium discount",
        "premium reduction", "rate credit", "mitigation incentive"
    ],

    "non_admitted_market": [
        # Surplus lines & non-admitted carriers
        "surplus line", "surplus lines", "surplus lines insurance",
        "non-admitted", "nonadmitted", "non admitted",
        "surplus lines broker", "surplus lines tax",
        "risk retention group", "risk retention",
        "captive insurance", "captive insurer", "captive",
        "high-risk pool", "risk pooling", "risk pool",
        "self-insurance", "self insurance", "self-insured",
        "joint self insurance", "purchasing group",
        "alien insurer", "unauthorized insurer",
        "exempt commercial purchaser", "industrial insured"
    ],

    "consumer_protections_and_market_conduct": [
        # Policyholder rights & claims handling
        "consumer protection", "policyholder rights", "policyholder protection",
        "bad faith", "bad faith claims", "insurance bad faith",
        "claim denial", "denial of coverage", "coverage denial",
        "claims assistance", "claims handling", "claims process",
        "appeals process", "internal appeal", "external review",
        "insurance grievance", "regulatory complaint", "ombudsman",
        "consumer hotline", "insurance advocate",
        # Market conduct
        "unfair practices", "unfair trade practices", "market conduct",
        "insurance fraud", "anti-fraud", "fraud prevention",
        "insurance transparency", "coverage clarity", "disclosure requirement",
        "nonrenewal", "non-renewal", "cancellation notice",
        "policy renewal", "renewal notice", "prior premium",
        "restitution", "commissioner order", "cease and desist",
        "administrative action", "license revocation",
        "redlining", "insurance discrimination", "unfair discrimination"
    ],

    "catastrophe_modeling": [
        # Cat modeling & actuarial methods
        "catastrophe model", "cat model", "approved model",
        "probable maximum loss", "PML", "return period",
        "exceedance probability", "loss exceedance curve",
        "stochastic model", "deterministic model",
        "hurricane model", "flood model", "wildfire model",
        "seismic model", "modeled loss", "modeled output",
        "AIR model", "RMS model", "CoreLogic model",
        "model output", "model approval", "model certification",
        "commission on hurricane loss", "actuarial model",
        "catastrophe risk model", "event set",
        "vulnerability function", "hazard module",
        "model validation", "model review", "independent model",
        "Florida Commission on Hurricane Loss", "FCHLPM"
    ],

    "data_and_study": [
        # Studies, task forces & data collection
        "task force", "working group", "study commission",
        "legislative study", "interim study", "feasibility study",
        "insurance study", "climate study", "market study",
        "data collection", "data reporting", "data submission",
        "insurance data", "actuarial study", "actuarial report",
        "university study", "research institute", "commissioned research",
        "report to legislature", "report to commissioner",
        "annual report", "biennial report", "data call",
        "market analysis", "availability study", "affordability study",
        "insurance survey", "market survey"
    ],

    "fossil_fuel_accountability": [
        # Climate liability & polluter pays
        "fossil fuel accountability", "fossil fuel liability",
        "polluter pays", "climate attribution",
        "attributable climate change", "attributable climate",
        "climate accountability", "climate liability",
        "climate litigation", "climate lawsuit",
        "subrogation", "subrogation claim",
        "cost recovery", "damage attribution",
        "liable for emissions", "emitters responsibility",
        "responsible party", "environmental damages",
        "fossil fuel company", "oil company liability",
        "carbon major", "carbon liability",
        "loss and damage", "recovery lawsuit"
    ],

    "state_insurance_office_regulatory_powers": [
        # Commissioner & DOI authority
        "insurance commissioner", "commissioner of insurance",
        "department of insurance", "insurance department",
        "insurance regulator", "state regulator",
        "regulatory authority", "regulatory power",
        "commissioner authority", "commissioner approval",
        "market stabilization", "emergency order",
        "receivership", "rehabilitation", "conservation",
        "insurer examination", "financial examination",
        "market examination", "solvency", "risk-based capital",
        "RBC", "holding company", "insurance holding company",
        "prior approval", "file and use", "use and file",
        "rate review", "form approval", "policy form",
        "admitted insurer", "certificate of authority",
        "insurance regulation", "NAIC", "accreditation"
    ],

    "property_disclosure": [
        # Climate & hazard disclosure at property level
        "property disclosure", "natural hazard disclosure",
        "climate risk disclosure", "flood disclosure",
        "wildfire disclosure", "hazard disclosure",
        "seller disclosure", "transfer disclosure",
        "real estate disclosure", "property risk disclosure",
        "flood zone disclosure", "fire hazard disclosure",
        "insurance cost disclosure", "insurability disclosure",
        "climate risk notice", "hazard notice",
        "disclosure statement", "natural disaster disclosure",
        "risk notification", "buyer notification"
    ],

    "building_codes_land_use": [
        # Building codes & land use
        "building code", "building standard", "construction standard",
        "fire-resistant building code", "wind-resistant code",
        "flood-resistant construction", "coastal construction",
        "statewide building code", "local building code",
        "land use", "zoning", "land use regulation",
        "coastal zone", "floodplain management", "floodplain regulation",
        "setback requirement", "development restriction",
        "high-risk zone", "hazard zone", "fire hazard zone",
        "wildland urban interface", "WUI",
        "managed retreat", "coastal retreat", "buyout program",
        "repetitive loss", "severe repetitive loss",
        "building permit", "construction permit",
        "resilient construction", "green building"
    ],

    "climate_resilience_and_risk_mitigation": [
        # Community & landscape-scale resilience
        "community resilience", "climate resilience",
        "resilience fund", "resilience program",
        "extreme weather resilience", "weather resilience fund",
        "adaptation", "climate adaptation", "adaptation infrastructure",
        "natural buffers", "green infrastructure", "nature-based solution",
        "living shoreline", "wetland restoration", "coastal resilience",
        "prescribed burn", "prescribed fire", "controlled burn",
        "vegetation management", "fuel reduction", "firebreak",
        "forest health", "forestland", "vegetative fuel",
        "flood barrier", "levee", "storm surge barrier",
        "floodplain restoration", "stormwater management",
        "hazard mitigation", "hazard mitigation plan",
        "mitigation program", "risk reduction",
        "emergency management", "disaster preparedness",
        "FEMA", "BRIC", "hazard mitigation grant",
        "resilience zone", "community rating system", "CRS"
    ],

    "reinsurance": [
        # Reinsurance structures & instruments
        "reinsurance", "reinsurer", "cedent", "ceding company",
        "retrocession", "quota share", "excess of loss",
        "treaty reinsurance", "facultative reinsurance",
        "catastrophe bond", "cat bond",
        "insurance-linked securities", "ILS",
        "risk-linked securities", "capital relief",
        "transfer of risk", "reinsurance capacity",
        "reinsurance treaty", "reinsurance contract",
        "stop-loss", "aggregate cover",
        "proportional reinsurance", "non-proportional reinsurance",
        "reinsurance pool", "mandatory reinsurance",
        "reinsurance fund", "reinsurance program",
        "parametric insurance", "parametric trigger"
    ],

    "litigation_and_tort_reform": [
        # Tort reform & insurance litigation
        "tort reform", "litigation reform",
        "assignment of benefits", "AOB",
        "one-way attorney fees", "attorney fee",
        "fee shifting", "prevailing party",
        "bad faith litigation", "insurance litigation",
        "jury verdict", "damage cap", "damages cap",
        "punitive damages", "compensatory damages",
        "pre-suit notice", "pre-suit requirement",
        "mediation requirement", "appraisal",
        "compulsory mediation", "dispute resolution",
        "post-loss assignment", "claim assignment",
        "third-party assignment", "public adjuster",
        "statute of limitations", "claims deadline",
        "roof claim", "roof deductible",
        "frivolous lawsuit", "abusive claim"
    ],

    "rate_regulation": [
        # Rate filing & regulatory approval
        "rate filing", "rate approval", "rate review",
        "prior approval", "rate increase", "rate hike",
        "premium increase", "premium surge", "rate freeze",
        "rate rollback", "rate reduction",
        "insurance rate", "rate adequacy", "rate suppression",
        "actuarially sound", "actuarial justification",
        "rate hearing", "public hearing on rates",
        "rate moratorium", "underwriting freeze",
        "market withdrawal", "withdrawal of coverage",
        "insurance availability", "insurance affordability",
        "rate filing requirement", "supporting documentation",
        "file and use", "use and file", "flex rating",
        "competitive rating", "deregulation of rates",
        "commissioner disapproval", "rate order"
    ],

    "climate_risk_disclosure": [
        # Corporate & insurer climate disclosure
        "climate disclosure", "climate risk reporting",
        "climate risk disclosure", "climate transparency",
        "climate-related financial risk", "climate-related risk",
        "TCFD", "Task Force on Climate-related Financial Disclosures",
        "ISSB", "SEC climate disclosure",
        "GHG inventory", "greenhouse gas",
        "scope 1 emissions", "scope 2 emissions", "scope 3 emissions",
        "emissions disclosure", "carbon disclosure",
        "transition risk", "physical risk",
        "climate scenario analysis", "climate stress testing",
        "climate risk assessment", "ESG reporting",
        "carbon risk", "environmental risk disclosure",
        "climate data mandate", "climate survey",
        "ORSA", "own risk and solvency assessment",
        "insurer climate risk", "climate-related solvency"
    ],

    "anti_esg": [
        # Anti-ESG & restrictions on climate-based underwriting
        "anti-ESG", "ESG restriction", "ESG prohibition",
        "boycott energy", "energy boycott",
        "fossil fuel boycott", "coal divestment",
        "fiduciary duty", "pecuniary factor",
        "non-pecuniary factor", "social investing",
        "politically motivated", "ideological",
        "woke capitalism", "stakeholder capitalism",
        "environmental social governance",
        "climate-based underwriting", "ESG underwriting",
        "ESG scoring", "ESG rating",
        "restrict ESG", "prohibit ESG",
        "state pension ESG", "investment ESG",
        "net zero commitment", "carbon neutral commitment",
        "insurer ESG", "underwriting criteria",
        "unfair discrimination climate", "climate discrimination"
    ]

}

# Custom stopwords — noise words common in legislative text
# that would otherwise inflate TF-IDF scores unhelpfully
custom_stopwords = {
    # State names (appear in nearly every bill)
    "state", "alabama", "alaska", "arizona", "arkansas", "california",
    "colorado", "connecticut", "delaware", "florida", "georgia", "hawaii",
    "idaho", "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
    "maine", "maryland", "massachusetts", "michigan", "minnesota", "mississippi",
    "missouri", "montana", "nebraska", "nevada", "new hampshire", "new jersey",
    "new mexico", "new york", "north carolina", "north dakota", "ohio", "oklahoma",
    "oregon", "pennsylvania", "rhode island", "south carolina", "south dakota",
    "tennessee", "texas", "utah", "vermont", "virginia", "washington",
    "west virginia", "wisconsin", "wyoming",
    "carolina", "dakota", "hampshire", "island", "jersey", "mexico",
    "north", "rhode", "south", "west", "york",
    # Legislative formatting artifacts
    "stricken", "word stricken", "underlined", "word underlined",
    "word underline addition", "underline addition", "addition page",
    "stricken deletion", "code word stricken", "chapter", "shall",
    "section", "subsection", "paragraph", "subparagraph",
    "print version", "statutory", "appropriation",
    "inclusion terminate", "sec inclusion", "sec",
    "bab", "thereto know", "title", "amend thereto know",
    "ssb", "shb", "lrs", "rcw", "mca", "mca read",
    "engross", "engrossed", "final", "authorize print",
    "print", "version", "read follow",
    "amend", "amendment", "amended read",
    "legislature", "legislative", "violate", "violation", "violated",
    "inclusion terminate", "terminate pursuant",
    "commence article", "commence", "article commence article",
    "subchapter", "statutory",
    # Common but meaningless terms in this corpus
    "business", "business entity", "automobile", "motor",
    "passenger", "motor vehicle", "vehicle",
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
    "date", "addition", "code", "deletion", "page", "underline", "word",
    # Standard English stopwords handled separately via ENGLISH_STOP_WORDS
    "a", "about", "above", "after", "all", "also", "although", "an", "and",
    "any", "are", "as", "at", "be", "been", "before", "both", "but", "by",
    "can", "could", "did", "do", "does", "down", "during", "each", "either",
    "for", "from", "had", "has", "have", "he", "her", "here", "him", "his",
    "how", "if", "in", "into", "is", "it", "its", "made", "make", "many",
    "may", "me", "more", "most", "much", "must", "my", "no", "not", "now",
    "of", "on", "one", "only", "or", "other", "our", "out", "over", "own",
    "per", "re", "same", "she", "should", "since", "so", "some", "still",
    "such", "than", "that", "the", "their", "them", "then", "there", "these",
    "they", "this", "those", "through", "thus", "to", "too", "under", "up",
    "us", "used", "very", "was", "we", "well", "were", "what", "when",
    "where", "which", "while", "who", "will", "with", "would", "yes", "yet",
    "you", "your"
}

combined_stopwords = list(ENGLISH_STOP_WORDS.union(custom_stopwords))
