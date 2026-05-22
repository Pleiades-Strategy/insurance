from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

tag_keywords = {
    "reinsurance": [
        "reinsurance", "cedent", "retrocession", "quota share", "excess of loss",
        "treaty reinsurance", "facultative", "catastrophe bond", "cat bond",
        "risk-linked securities", "insurance-linked securities", "ILS", "capital relief",
        "transfer of risk", "reinsurance capacity", "reinsurance treaty",
        "stop-loss", "aggregate cover", "proportional reinsurance", "non-proportional reinsurance"
    ],

    "insurer_of_last_resort": [
        "insurer of last resort", "state-backed insurance", "residual market",
        "assigned risk plan", "Citizens Property Insurance", "state-run insurer",
        "Fair Access to Insurance Requirements", "FAIR Plan", "Beach Plan",
        "state insurance pool", "coverage guarantee", "market failure",
        "availability crisis", "government insurer", "last resort coverage",
        "insurer of last resort programs", "state insurer",  "windstorm insurance","windstorm insurance association",
        'windstorm',"joint selfinsurance", "association fair plan", "association fair", "fair association", "state guaranty association","state guaranty",
        "guaranty association", "joint underwriting", "underwriting association", "joint underwriting association","TWIA","Texas Windstorm",
        "Texas Windstorm Insurance Association", "Texas Windstorm Association","fair access insurance","residual market","guaranty"
    ],

    "risk_mitigation": [
        "home hardening", "wind-resistant", "fire-resistant", "flood-proofing",
        "elevated structure", "impact windows", "storm shutters", "roof strapping",
        "community resilience", "risk reduction", "adaptation infrastructure",
        "natural buffers", "green infrastructure", "mitigation grants",
        "resilience zones", "infrastructure retrofit", "risk resilience",
        "building code upgrades", "hazard reduction", "hazard mitigation", "retrofitting","home retrofitting","building code",
        "strengthen home","strengthen rhody","strengthen rhody homes", "insurance guaranty association","weather resilience fund",
        "weather resilience","resilience fund","extreme weather resilience","mitigation","risk mitigation","damage mitigation",
        "strengthen home program","home resiliency","resilience","emergency management","resiliency"
    ],

    "climate_disclosure": [
        "climate disclosure", "climate risk reporting", "climate transparency",
        "climate risk disclosure", "climate-related financial risk",
        "Task Force on Climate-related Financial Disclosures", "TCFD",
        "GHG inventory", "transition risk", "physical risk",
        "scope 1 emissions", "scope 2 emissions", "scope 3 emissions",
        "reporting requirement", "climate data mandate", "emissions disclosure",
        "resilience plan submission", "climate survey", "climate-related risk",
        "climate risk", "ESG reporting", "carbon risk", "environmental risk disclosure",
        "climate scenario analysis", "climate stress testing","conduct surveillance","surveillance"
    ],

    "wildfire_risk": [
        "defensible space", "fuel reduction", "vegetation management", "firebreak",
        "fire-resistant building code", "home ignition zone", "structure hardening",
        "ember resistance", "wildland urban interface", "WUI", "fire zoning",
        "prescribed burns", "controlled burns", "risk mapping", "fire-prone area",
        "wildfire", "prescribed burn", "burn", "smoke exposure", "fire hazard",
        "fire mitigation", "urban fire interface", "fire suppression", "fire weather",
        'vegetative','vegetative fuel','forest health',"forestland"
    ],

    "flood_risk": [
        "floodplain", "100-year flood", "base flood elevation", "FEMA flood map",
        "special flood hazard area", "SFHA", "coastal high hazard zone",
        "elevation certificate", "storm surge", "flood barrier", "levee", "NFIP",
        "flood insurance program", "floodproofing", "wet floodproofing", "wetland",
        "national flood insurance", "national flood", "flood model", "flood resilience",
        "flood exposure", "flood control", "flood zone", "flash flood", "inundation", "floodproofing", 
        "flood proof", "flood proofing", "flood insurance","flood"
    ],

    "insurance_access": [
        "insurance availability", "premium hike", "insurance affordability",
        "policyholder", "rate filing", "coverage denial", "underwriting freeze",
        "market withdrawal", "redlining", "insurance deserts", "insurability",
        "coverage crisis", "uninsurable areas", "access to coverage",
        "disproportionate impact", "coverage gap", "insurance exclusion",
        "denial of coverage", "at-risk communities", "vulnerable communities",
        "insurance inequity", "rate hike", "premium surge","condominium","disadvantaged","disadvantaged community","condominium project",
        "condominium mutual insurance","coverage commercial risk","coverage commercial","disputed", "disputed loss", "policyholder", 
        "appraiser","taxpayer claim", "taxpayer deduction","expense qualified deductible","deduction","deductible"
    ],

    "polluter_pays": [
        "attributable", "attributable climate", "subrogation", "attributable climate change",
        "subrogation claim", "cost recovery", "polluter pays", "climate attribution",
        "climate accountability", "damage attribution", "liable for emissions",
        "responsible party", "climate litigation", "fossil fuel accountability",
        "climate liability", "recovery lawsuit", "environmental damages",
        "emitters responsibility"
    ],

    "study_bill":[
        "university","research","task force",
    ],

    "consumer_protection":[
        "consumer protection", "consumer protection", "policyholder rights", "bad faith claims",  "insurance fraud", "claim denial", "appeals process", 
        "regulatory complaint", "insurance transparency", "coverage clarity", "disclosure requirement", "consumer hotline", "ombudsman", "claims assistance", 
        "insurance grievance", "unfair practices", "rate justification", "rate renewal","policy renewal","cause believe","restitution",
        "commissioner order","request financial information","financial information","prior premium renewal","non-renewal", "nonrenewal","justification",
        "prior premium","prior premium renewal"
    ],

    "federal_intervention":[
        "united states","congress","federal catastrophe risk"
    ],

    "non_admitted":[
        "surplus line", "surplus line insurance", "surplus lines", "surplus insurance","surplus lines insurance",'risk retention group',
        "risk retention","captive","high-risk pool","risk pooling", "risk pool", "pool risk","self-insurance","self insurance","self insured",
        "selfinsurance", "joint self insurance", "selfinsurance", "self insurance"
    ]

}

# custom stopwords
custom_stopwords = {
    "state","alabama","alaska","arizona","arkansas","california", "colorado","connecticut","delaware","florida","georgia","hawaii",
    "idaho","illinois","indiana","iowa","kansas","kentucky","louisiana","maine",
    "maryland","massachusetts","michigan","minnesota","mississippi","missouri","montana","nebraska","nevada",
    "new hampshire","new jersey","new mexico","new york","north carolina","north dakota","ohio","oklahoma","oregon","pennsylvania",
    "rhode island","south carolina","south dakota","tennessee","texas","utah","vermont","virginia","washington","west virginia",
    "wisconsin","wyoming","section","carolina", "dakota", "hampshire", "island", "jersey", "mexico", "new", "north", "rhode", 
    "south", "west", "york","stricken","word stricken","underlined","word underlined","word underline addition","underline addition","addition page",
    "stricken deletion","code word stricken","chapter","shall", "a", "about", "above", "according", "across", "actually", "adj", 
    "after", "afterwards", "again", "all", "almost", "alone", "along", "already", "also", "although", "always", "among", "amongst", 
    "an", "and", "another", "any", "anyhow", "anyone", "anything", "anywhere", "are", "aren", "around", 
    "as", "at", "be", "become", "because", "become", "becomes", "becoming", "been", "before", 
    "beforehand", "begin", "beginning", "behind", "below", "beside", "besides", "between", "beyond", "billion", "both", 
    "but", "by", "can", "cannot", "caption", "co", "could", "couldn", "did", "didn", "do", "does", "doesn", "don", "down", 
    "during", "each", "eg", "eight", "eighty", "either", "else", "elsewhere", "end", "ending", "enough", "etc", "even", "ever", 
    "every", "everyone", "everything", "everywhere", "except", "few", "fifty", "first", "five", "for", "former", "formerly", 
    "forty", "found", "four", "form", "further", "had", "has", "hasn", "have", "haven", "he", "hence", "her", "here", "hereafter", 
    "hereby", "herein", "hereupon", "hers", "herself", "him", "himself", "his", "how", "however", "hundred", "ie", "if", "in", "inc", 
    "Indeed", "instead", "into", "is", "isn", "it", "its", "itself", "last", "later", "latter", "latterly", "least", "less", "let", "like", 
    "likely", "ll", "ltd", "made", "make", "makes", "many", "maybe", "me", "meantime", "meanwhile", "might", "might", "million", 
    "miss", "more", "moreover", "most", "mostly", "mr", "mrs", "much", "must", "my", "myself", "namely", "neither", "never", 
    "nevertheless", "next", "nine", "ninety", "no", "nobody", "none", "nonetheless", "noon", "nor", "not", "nothing", "now", 
    "nowhere", "of", "off", "often", "on", "once", "one", "only", "onto", "or", "other", "others", "otherwise", "our", "ours", 
    "ourselves", "out", "over", "overall", "own", "per", "perhaps", "rather", "re", "recent", "recently", "same", "seem", "seemed", 
    "seeming", "seems", "seven", "seventy", "several", "she", "should", "shouldn", "since", "six", "sixty", "so", "some", "somehow", 
    "someone", "sometime", "sometimes", "somewhere", "still", "stop", "such", "talking", "ten", "than", "that", "the", "their", 
    "them", "themselves", "thence", "there", "thereafter", "thereby", "therefore", "therein", "therein", "thereupon", "these", 
    "they", "thirty", "this", "those", "though", "thousand", "three", "through", "throughout", "thru", "thus", "to", "together", 
    "too", "toward", "towards", "trillion", "twenty", "two", "under", "unless", "unlike", "unlikely", "until;", "up", "upon", "us", 
    "used", "using", "ve", "very", "via", "very", "was", "wasn", "we", "well", "were", "weren", "what", "whatever", "when", "whence", 
    "whenever", "where", "whereafter", "whereas", "whereby", "wherein", "whereupon", "wherever", "whether", "which", "while", "whither", 
    "which", "while", "whither", "who", "whoever", "whole", "whom", "whomever", "whose", "why", "will", "with", "within", "without", "won", 
    "would", "wouldn", "yes", "yet", "you", "your", "yours", "yourself", "yourselves", 'addition', 'code', 'deletion', 'page', 'underline', 'word',
    "subchapter", 'shb', 'business','business entity','commence article','commence',"article commence article",
    "passeng motor vehicle", "motor","passenger","motor vehicle","vehicle","rcw","amend","amendment","amended read","legislature","legislative","violate","violation","violated","amend"
    'print version', 'statutory', 'appropriation', 'inclusion terminate', 'sec inclusion', 'sec',"bab", 'thereto know', 'title', 
    'amend thereto know','date','ssb',"january","february","march","april","may","june","july","august","september","october","november","december",
    "print","print version","version","authorize print","lrs","final","engross","engrossed",'inclusion terminate', 'terminate pursuant',"mca","mca read",
    "read follow","automobile"
}
combined_stopwords = list(ENGLISH_STOP_WORDS.union(custom_stopwords))