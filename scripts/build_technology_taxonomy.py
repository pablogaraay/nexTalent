"""Build nexTalent's canonical technology taxonomy from O*NET Software Skills.

The O*NET input is an occupation/software relation table, not a ready-to-use
taxonomy. This builder aggregates its rows, normalizes the most relevant labels,
assigns nexTalent categories and keeps the O*NET evidence used for selection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import unicodedata
from collections import defaultdict
from pathlib import Path


TAXONOMY_VERSION = "1.0.0"
DEFAULT_LIMIT = 350

CATEGORIES = {
  "ai_ml": "Inteligencia artificial y machine learning",
  "business_intelligence": "Business intelligence y analítica",
  "cloud": "Cloud computing",
  "creative_media": "Diseño y contenidos digitales",
  "cybersecurity": "Ciberseguridad",
  "data_engineering": "Ingeniería e integración de datos",
  "databases": "Bases de datos y almacenamiento",
  "devops": "DevOps, automatización y observabilidad",
  "engineering_design": "Ingeniería, CAD y simulación",
  "enterprise_apps": "Aplicaciones empresariales",
  "geospatial": "Tecnologías geoespaciales",
  "infrastructure": "Sistemas, redes e infraestructura",
  "productivity": "Productividad y colaboración",
  "programming": "Programación y desarrollo de software",
  "scientific": "Software científico y estadístico",
  "web_mobile": "Desarrollo web y móvil",
  "industry_specific": "Tecnología sectorial especializada",
}


# O*NET uses product-oriented workplace examples. Only labels that are known to
# be equivalent are merged. Uncertain product families deliberately stay apart.
CANONICAL_OVERRIDES = {
  "Advanced business application programming ABAP": "ABAP",
  "Alteryx software": "Alteryx",
  "Amazon DynamoDB": "AWS DynamoDB",
  "Amazon Elastic Compute Cloud EC2": "AWS EC2",
  "Amazon Simple Storage Service S3": "AWS S3",
  "Amazon Web Services AWS CloudFormation": "AWS CloudFormation",
  "Amazon Web Services AWS SageMaker": "Amazon SageMaker",
  "Amazon Web Services AWS software": "Amazon Web Services (AWS)",
  "Ansible software": "Ansible",
  "Atlassian Bitbucket": "Bitbucket",
  "Atlassian Confluence": "Confluence",
  "Atlassian JIRA": "Jira",
  "Cascading style sheets CSS": "CSS",
  "ESRI ArcGIS software": "ArcGIS",
  "Extensible markup language XML": "XML",
  "Formula translation/translator FORTRAN": "Fortran",
  "Google Angular": "Angular",
  "Google Cloud software": "Google Cloud Platform (GCP)",
  "Google Looker Analytics": "Looker",
  "Grafana Labs Grafana Cloud": "Grafana",
  "Hypertext markup language HTML": "HTML",
  "IBM SPSS Statistics": "SPSS",
  "IBM Terraform": "Terraform",
  "IBM Rational DOORS": "IBM DOORS",
  "JavaScript Object Notation JSON": "JSON",
  "Microsoft .NET Framework": ".NET Framework",
  "Microsoft Azure Data Factory": "Azure Data Factory",
  "Microsoft Azure DevOps Services": "Azure DevOps",
  "Microsoft Azure Sentinel": "Microsoft Sentinel",
  "Microsoft Azure software": "Microsoft Azure",
  "Microsoft Excel": "Excel",
  "Microsoft Office software": "Microsoft Office",
  "Microsoft Outlook": "Outlook",
  "Microsoft Power BI": "Power BI",
  "Microsoft PowerPoint": "PowerPoint",
  "Microsoft Power Platform software": "Microsoft Power Platform",
  "Microsoft PowerShell": "PowerShell",
  "Microsoft Visual Basic for Applications VBA": "VBA",
  "Microsoft Word": "Word",
  "Mlflow": "MLflow",
  "Oracle Java": "Java",
  "Qlik Tech QlikView": "QlikView",
  "Palo Alto Networks Next-Generation Security Platform": "Palo Alto Networks",
  "Red Hat OpenShift": "OpenShift",
  "Rust programming language": "Rust",
  "Salesforce software": "Salesforce",
  "SAP software": "SAP",
  "Scikit-learn": "scikit-learn",
  "Structured query language SQL": "SQL",
  "Talend Big Data Integration": "Talend",
  "Talend Data Fabric": "Talend",
  "Talend Open Studio": "Talend",
  "TalendForge": "Talend",
  "The MathWorks MATLAB": "MATLAB",
  "Unity Technologies Unity": "Unity",
  "Unreal Technology Unreal Engine": "Unreal Engine",
  "Workday software": "Workday",
  "Dynamic object-oriented requirements system DOORS": "IBM DOORS",
}


EXTRA_ALIASES = {
  ".NET Framework": [".NET", "dotnet", "Microsoft .NET"],
  "Amazon SageMaker": ["AWS SageMaker", "SageMaker"],
  "Amazon Web Services (AWS)": ["AWS", "Amazon Web Services"],
  "Apache Airflow": ["Airflow"],
  "Apache Cassandra": ["Cassandra"],
  "Apache Hadoop": ["Hadoop"],
  "Apache Kafka": ["Kafka"],
  "Apache Spark": ["Spark"],
  "ArcGIS": ["ESRI ArcGIS"],
  "Amazon Redshift": ["Redshift"],
  "AWS CloudFormation": ["CloudFormation", "cloud formation"],
  "AWS DynamoDB": ["DynamoDB"],
  "AWS EC2": ["Amazon EC2", "EC2"],
  "AWS S3": ["Amazon S3", "S3"],
  "Azure Data Factory": ["ADF", "Microsoft Azure Data Factory"],
  "Azure DevOps": ["Azure Dev Ops"],
  "C#": ["C Sharp", "csharp"],
  "C++": ["CPP"],
  "CSS": ["Cascading Style Sheets"],
  "Docker": ["Docker Compose", "Docker-Compose"],
  "Elasticsearch": ["ElasticSearch", "Elastic Search"],
  "Google Cloud Platform (GCP)": ["GCP", "Google Cloud", "Google Cloud Platform"],
  "HTML": ["HyperText Markup Language"],
  "Java": ["Oracle Java"],
  "Jira": ["JIRA", "Atlassian Jira"],
  "Jenkins CI": ["Jenkins"],
  "IBM DOORS": ["DOORS", "Rational DOORS"],
  "JSON": ["JavaScript Object Notation"],
  "Kubernetes": ["K8s"],
  "Microsoft Azure": ["Azure"],
  "Microsoft Dynamics": [
    "Dynamics 365", "Microsoft Dynamics 365", "Microsoft Dynamics 365 Business Central",
    "Microsoft Dynamics 365 CRM", "Microsoft Dynamics 365 Customer Engagement",
  ],
  "Microsoft Sentinel": ["Azure Sentinel", "Microsoft Azure Sentinel"],
  "Microsoft Office": ["MS Office", "Office", "Office 365", "Microsoft 365"],
  "Microsoft Project": ["MS Project"],
  "Microsoft Exchange": ["Exchange Online"],
  "Microsoft Power Platform": ["Power Platform"],
  "Microsoft SharePoint": ["SharePoint Online", "Sharepoint"],
  "MLflow": ["Mlflow"],
  "MongoDB": ["Mongo DB"],
  "Node.js": ["NodeJS", "Node JS"],
  "OpenShift": ["Red Hat OpenShift"],
  "PostgreSQL": ["Postgres"],
  "Power BI": ["Microsoft Power BI", "PowerBI", "power bi"],
  "BigQuery": ["Big Query", "Google BigQuery"],
  "PowerPoint": ["Microsoft PowerPoint", "Power Point", "MS PowerPoint"],
  "PyTorch": ["Torch"],
  "Palo Alto Networks": ["Palo Alto"],
  "RESTful API": ["REST API", "REST APIs", "REST", "APIs REST"],
  "SAP": ["SAP software"],
  "scikit-learn": ["sklearn", "Scikit-learn"],
  "SQL": ["Structured Query Language"],
  "Splunk Enterprise": ["Splunk"],
  "Talend": ["Talend Data Fabric", "Talend Open Studio"],
  "TensorFlow": ["Tensor Flow"],
  "Terraform": ["HashiCorp Terraform"],
  "TypeScript": ["TS"],
  "VBA": ["Visual Basic for Applications", "Excel Macros", "VBA/Macros"],
  "Vue.js": ["Vue", "VueJS"],
  "XML": ["Extensible Markup Language"],
}


# These technologies are strategically relevant to the offer corpus even when
# O*NET associates them with only a few occupations.
CORE_LABELS = {
  ".NET Framework", "ABAP", "Alteryx", "Amazon SageMaker", "Amazon Web Services (AWS)",
  "Angular", "Ansible", "Apache Airflow", "Apache Hadoop", "Apache Kafka", "Apache Spark",
  "AWS CloudFormation", "AWS DynamoDB", "AWS EC2", "AWS S3", "Azure Data Factory", "Azure DevOps", "Bash", "BigQuery",
  "Bitbucket", "C", "C#", "C++", "CSS", "Confluence", "Django",
  "Docker", "Dynatrace", "Eclipse IDE", "Elasticsearch", "Excel", "Git", "GitHub", "GitLab",
  "Google Cloud Platform (GCP)", "Grafana", "GraphQL", "HTML", "Hugging Face", "IBM DOORS", "Java",
  "JavaScript", "Jenkins CI", "Jira", "JUnit", "Kotlin", "Kubernetes", "LangChain",
  "Linux", "Looker", "MATLAB", "Microsoft Azure", "Microsoft Power Platform", "Microsoft Sentinel", "MLflow",
  "MongoDB", "MySQL", "Nagios", "Neo4j", "Node.js", "NoSQL", "OpenShift", "Oracle Database",
  "pandas", "PHP", "PostgreSQL", "Power BI", "PowerShell", "Prometheus", "PySpark", "Python",
  "Palo Alto Networks", "PyTorch", "QlikView", "R", "React", "Redis", "RESTful API", "Rust", "Salesforce", "SAP",
  "SAS", "Scala", "scikit-learn", "Selenium", "ServiceNow", "Snowflake", "SonarQube",
  "Spring Boot", "Spring Framework", "SQL", "Tableau", "Talend", "TensorFlow", "Terraform", "TypeScript",
  "Trello", "VBA", "VMware", "Vue.js", "Word", "Workday", "XML", "Zabbix",
}


GENERIC_EXCLUSIONS = {
  "business software applications", "collaborative editing software", "data entry software",
  "database software", "email software", "graphics software", "productivity software",
  "reporting software", "scheduling software", "software development tools", "statistical software",
  "web application software", "web browser software", "work scheduling software", "google",
  "facebook", "linkedin", "social media sites", "tiktok", "twitter", "youtube", "pci express pcie",
}

EXCLUDED_SOURCE_CATEGORIES = {
  "Library software",
  "Medical software",
  "Tax preparation software",
}


PROGRAMMING_LABELS = {
  "ABAP", "Bash", "C", "C#", "C++", "Fortran", "Go", "Java", "JavaScript", "Kotlin",
  "Perl", "PHP", "PowerShell", "Python", "R", "Ruby", "Rust", "Scala", "Shell script",
  "Swift", "TypeScript", "VBA",
}
AI_LABELS = {
  "Amazon SageMaker", "Hugging Face", "LangChain", "MLflow", "pandas", "PySpark", "PyTorch",
  "scikit-learn", "TensorFlow",
}
CLOUD_LABELS = {
  "Amazon Web Services (AWS)", "AWS CloudFormation", "AWS EC2", "AWS S3", "Google Cloud Platform (GCP)",
  "Microsoft Azure", "Oracle Cloud software",
}
DATABASE_LABELS = {
  "Amazon Redshift", "Apache Cassandra", "AWS DynamoDB", "Elasticsearch", "IBM DB2", "MongoDB",
  "MySQL", "Neo4j", "NoSQL", "Oracle Database", "PostgreSQL", "Redis", "Snowflake", "SQL",
  "Microsoft SQL Server", "Teradata Database",
}
BI_LABELS = {"Alteryx", "Looker", "Power BI", "QlikView", "Tableau"}
DEVOPS_LABELS = {
  "Ansible", "Apache Maven", "Bitbucket", "Chef", "Docker", "Dynatrace", "Git", "GitHub",
  "GitLab", "Grafana", "Jenkins CI", "Kubernetes", "Nagios", "OpenShift", "Prometheus", "Puppet",
  "Selenium", "SonarQube", "Terraform", "Zabbix",
}

CATEGORY_OVERRIDES = {
  "Adobe Analytics": "business_intelligence",
  "Apache JMeter": "devops",
  "ArcGIS": "geospatial",
  "Asana": "productivity",
  "AWS S3": "cloud",
  "Azure Data Factory": "data_engineering",
  "Azure DevOps": "devops",
  "BigQuery": "databases",
  "Border Gateway Protocol BGP": "infrastructure",
  "Citrix cloud computing software": "infrastructure",
  "Confluence": "productivity",
  "ESRI ArcGIS ArcPy": "geospatial",
  "ESRI ArcGIS Survey 123": "geospatial",
  "Figma": "creative_media",
  "Google Analytics": "business_intelligence",
  "Google Drive": "productivity",
  "GraphQL": "web_mobile",
  "Guidance Software EnCase Enterprise": "cybersecurity",
  "Kali Linux": "cybersecurity",
  "Microsoft Active Directory": "infrastructure",
  "Microsoft Sentinel": "cybersecurity",
  "Microsoft Internet Information Services (IIS)": "infrastructure",
  "Microsoft Team Foundation Server": "devops",
  "Microsoft Visio": "productivity",
  "Microsoft Windows Server": "infrastructure",
  "MITRE ATT&CK software": "cybersecurity",
  "Palo Alto Networks": "cybersecurity",
  "Procore software": "enterprise_apps",
  "ServiceNow": "enterprise_apps",
  "Slack": "productivity",
  "Splunk Enterprise": "devops",
  "Talend": "data_engineering",
  "VMware": "infrastructure",
  "Yardi software": "enterprise_apps",
}


def normalize_key(value: str) -> str:
  value = unicodedata.normalize("NFKD", str(value or ""))
  value = "".join(char for char in value if not unicodedata.combining(char))
  return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def canonical_label(source_label: str) -> str:
  return CANONICAL_OVERRIDES.get(source_label, source_label.strip())


def technology_id(label: str) -> str:
  replacements = {
    ".NET": " DOTNET ",
    "C++": " C PLUS PLUS ",
    "C#": " C SHARP ",
  }
  value = label
  for source, target in replacements.items():
    value = value.replace(source, target)
  value = unicodedata.normalize("NFKD", value)
  value = "".join(char for char in value if not unicodedata.combining(char))
  slug = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper()
  if not slug:
    slug = hashlib.sha1(label.encode("utf-8")).hexdigest()[:12].upper()
  return f"TECH_{slug}"


def infer_category(label: str, source_categories: set[str]) -> str:
  if label in CATEGORY_OVERRIDES:
    return CATEGORY_OVERRIDES[label]
  if label in AI_LABELS or any(token in label.casefold() for token in ("machine learning", "neural", "chatbot")):
    return "ai_ml"
  if label in PROGRAMMING_LABELS:
    return "programming"
  if label in BI_LABELS:
    return "business_intelligence"
  if label in DATABASE_LABELS:
    return "databases"
  if label in CLOUD_LABELS:
    return "cloud"
  if label in DEVOPS_LABELS:
    return "devops"

  category_text = " ".join(source_categories).casefold()
  label_text = label.casefold()
  if any(token in label_text for token in ("firewall", "security", "sentinel", "nessus", "nmap", "wireshark", "burp", "metasploit", "qualys")):
    return "cybersecurity"
  if any(token in label_text for token in ("hadoop", "spark", "kafka", "airflow", "datastage", "informatica", "talend", "hive", "pig")):
    return "data_engineering"
  if any(token in label_text for token in ("react", "angular", "vue", "node.js", "django", "spring", "jquery", "bootstrap", "wordpress", "drupal", "android", "ios")):
    return "web_mobile"
  if any(token in category_text for token in ("business intelligence", "reporting software", "financial analysis")):
    return "business_intelligence"
  if any(token in category_text for token in ("data base", "database", "metadata management", "data mining")):
    return "databases"
  if any(token in category_text for token in ("security", "virus protection", "authentication")):
    return "cybersecurity"
  if any(token in category_text for token in ("configuration management", "file versioning", "program testing", "application server")):
    return "devops"
  if any(token in category_text for token in ("web platform", "web page", "graphical user interface")):
    return "web_mobile"
  if any(token in category_text for token in ("development environment", "object or component oriented", "compiler")):
    return "programming"
  if any(token in category_text for token in ("operating system", "network", "communications server", "clustering", "backup")):
    return "infrastructure"
  if any(token in category_text for token in ("office suite", "spreadsheet", "word processing", "presentation", "electronic mail", "calendar", "video conferencing", "document management")):
    return "productivity"
  if any(token in category_text for token in ("enterprise resource planning", "customer relationship", "human resources", "accounting", "project management", "procurement", "inventory", "sales and marketing", "content workflow")):
    return "enterprise_apps"
  if any(token in category_text for token in ("geographic information", "map creation", "mobile location")):
    return "geospatial"
  if any(token in category_text for token in ("computer aided design", "computer aided manufacturing", "industrial control")):
    return "engineering_design"
  if any(token in category_text for token in ("graphics", "video", "music or sound", "desktop publishing")):
    return "creative_media"
  if "analytical or scientific" in category_text:
    return "scientific"
  if any(token in category_text for token in ("medical", "legal", "tax preparation", "library software")):
    return "industry_specific"
  if any(token in category_text for token in ("enterprise application integration", "cloud-based data")):
    return "data_engineering"
  return "industry_specific"


def infer_type(label: str, category_id: str, source_categories: set[str]) -> str:
  if label in PROGRAMMING_LABELS:
    return "programming_language"
  if label in DATABASE_LABELS:
    return "database"
  if label in {"Linux", "UNIX", "Microsoft Windows", "Apple macOS", "Google Android", "Apple iOS"}:
    return "operating_system"
  if label in {"HTML", "CSS", "JSON", "XML", "RESTful API", "GraphQL", "NoSQL"}:
    return "standard_or_concept"
  if any(token in label.casefold() for token in ("framework", "react", "angular", "vue.js", "django", "spring", "bootstrap", "jquery")):
    return "framework"
  if label in {"pandas", "PyTorch", "scikit-learn", "TensorFlow"}:
    return "library"
  if category_id in {"cloud", "devops", "data_engineering"}:
    return "platform_or_tool"
  if any("software" in category.casefold() for category in source_categories):
    return "software_application"
  return "technology"


def relevance_score(occupation_count: int, hot_count: int, demand_count: int) -> float:
  return (
    math.log1p(occupation_count)
    + 2.0 * math.log1p(hot_count)
    + 4.0 * math.log1p(demand_count)
  )


def _source_version(payload: dict) -> str:
  match = re.search(r"/(\d+\.\d+)/", str(payload.get("data_dictionary", "")))
  return match.group(1) if match else "unknown"


def build_taxonomy_evidence(payload: dict, limit: int = DEFAULT_LIMIT) -> list[dict]:
  grouped: dict[str, dict] = {}
  for row in payload.get("row", []):
    source_label = str(row.get("workplace_example", "") or "").strip()
    if not source_label:
      continue
    label = canonical_label(source_label)
    item = grouped.setdefault(label, {
      "source_labels": set(),
      "source_categories": set(),
      "source_elements": set(),
      "occupations": {},
    })
    item["source_labels"].add(source_label)
    item["source_categories"].add(str(row.get("element_name", "") or "").strip())
    item["source_elements"].add(str(row.get("element_id", "") or "").strip())
    occupation_code = str(row.get("onetsoc_code", "") or "").strip()
    occupation = item["occupations"].setdefault(occupation_code, {
      "code": occupation_code,
      "title": str(row.get("title", "") or "").strip(),
      "hot_technology": False,
      "in_demand": False,
    })
    occupation["hot_technology"] |= row.get("hot_technology") == "Y"
    occupation["in_demand"] |= row.get("in_demand") == "Y"

  candidates = []
  for label, item in grouped.items():
    if normalize_key(label) in GENERIC_EXCLUSIONS:
      continue
    source_categories = {value for value in item["source_categories"] if value}
    if label not in CORE_LABELS and source_categories and source_categories <= EXCLUDED_SOURCE_CATEGORIES:
      continue
    occupations = list(item["occupations"].values())
    occupation_count = len(occupations)
    hot_count = sum(occupation["hot_technology"] for occupation in occupations)
    demand_count = sum(occupation["in_demand"] for occupation in occupations)
    score = relevance_score(occupation_count, hot_count, demand_count)
    is_core = label in CORE_LABELS
    if not (is_core or demand_count >= 1 or hot_count >= 3 or occupation_count >= 20):
      continue
    candidates.append((score, label, item, occupation_count, hot_count, demand_count, is_core))

  candidates.sort(key=lambda entry: (-entry[0], normalize_key(entry[1])))
  selected = candidates[:max(0, limit)]
  selected_labels = {entry[1] for entry in selected}
  selected.extend(entry for entry in candidates if entry[6] and entry[1] not in selected_labels)
  selected.sort(key=lambda entry: (-entry[0], normalize_key(entry[1])))

  max_score = max((entry[0] for entry in selected), default=1.0)
  source_version = _source_version(payload)
  documents = []
  seen_ids = set()
  for score, label, item, occupation_count, hot_count, demand_count, is_core in selected:
    tech_id = technology_id(label)
    if tech_id in seen_ids:
      digest = hashlib.sha1(label.encode("utf-8")).hexdigest()[:8].upper()
      tech_id = f"{tech_id}_{digest}"
    seen_ids.add(tech_id)

    source_categories = {value for value in item["source_categories"] if value}
    category_id = infer_category(label, source_categories)
    aliases = {*item["source_labels"], *EXTRA_ALIASES.get(label, [])}
    aliases = sorted(
      {alias.strip() for alias in aliases if alias.strip() and normalize_key(alias) != normalize_key(label)},
      key=normalize_key,
    )
    occupations = sorted(
      item["occupations"].values(),
      key=lambda occupation: (
        -int(occupation["in_demand"]),
        -int(occupation["hot_technology"]),
        occupation["code"],
      ),
    )
    selection_reasons = []
    if is_core:
      selection_reasons.append("nexTalent_core")
    if demand_count:
      selection_reasons.append("onet_in_demand")
    if hot_count:
      selection_reasons.append("onet_hot_technology")
    if occupation_count >= 20:
      selection_reasons.append("broad_occupation_coverage")

    documents.append({
      "technology_id": tech_id,
      "preferred_label": label,
      "aliases": aliases,
      "skill_type": "technology",
      "technology_type": infer_type(label, category_id, source_categories),
      "category_id": category_id,
      "category_name": CATEGORIES[category_id],
      "description": (
        f"Tecnología de {CATEGORIES[category_id].casefold()} relacionada por O*NET "
        f"con {occupation_count} ocupaciones."
      ),
      "relevance": {
        "score": round(100 * score / max_score, 2),
        "tier": "core" if is_core or demand_count >= 5 else "relevant",
        "occupation_count": occupation_count,
        "hot_occupation_count": hot_count,
        "in_demand_occupation_count": demand_count,
        "selection_reasons": selection_reasons,
      },
      "source": {
        "framework": "O*NET Software Skills",
        "version": source_version,
        "source_labels": sorted(item["source_labels"], key=normalize_key),
        "element_ids": sorted(value for value in item["source_elements"] if value),
        "element_names": sorted(source_categories),
        "data_dictionary": payload.get("data_dictionary", ""),
      },
      "top_occupations": occupations[:20],
      "taxonomy_version": TAXONOMY_VERSION,
      "active": True,
      "review_status": "curated" if label in CANONICAL_OVERRIDES.values() or is_core else "source_normalized",
    })
  return documents


def compact_taxonomy(evidence_documents: list[dict]) -> list[dict]:
  """Keep only fields required by runtime mapping and administration."""
  return [
    {
      "technology_id": document["technology_id"],
      "preferred_label": document["preferred_label"],
      "aliases": document["aliases"],
      "category_id": document["category_id"],
    }
    for document in evidence_documents
  ]


def build_taxonomy(payload: dict, limit: int = DEFAULT_LIMIT) -> list[dict]:
  return compact_taxonomy(build_taxonomy_evidence(payload, limit=limit))


def validate_taxonomy(documents: list[dict]) -> None:
  if not documents:
    raise ValueError("La taxonomía generada está vacía.")
  ids = [document.get("technology_id") for document in documents]
  # Punctuation is semantically significant for labels such as C, C# and C++.
  labels = [str(document.get("preferred_label", "") or "").strip().casefold() for document in documents]
  if len(ids) != len(set(ids)):
    raise ValueError("La taxonomía contiene technology_id duplicados.")
  if len(labels) != len(set(labels)):
    raise ValueError("La taxonomía contiene preferred_label duplicados.")
  for document in documents:
    if not document.get("technology_id") or not document.get("preferred_label"):
      raise ValueError("Hay tecnologías sin identificador o etiqueta preferida.")
    if document.get("category_id") not in CATEGORIES:
      raise ValueError(f"Categoría inválida en {document.get('technology_id')}.")
    expected_fields = {
      "technology_id", "preferred_label", "aliases", "category_id",
    }
    if set(document) != expected_fields:
      raise ValueError(
        f"Esquema operativo inválido en {document.get('technology_id')}: "
        f"{sorted(set(document) - expected_fields)}"
      )


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    description="Genera onet_technologies_taxonomy desde O*NET Software Skills."
  )
  parser.add_argument("input", type=Path, help="Ruta al software_skills.json de O*NET.")
  parser.add_argument(
    "--output",
    type=Path,
    default=Path("nexTalent.technology_skills.json"),
    help="JSON de salida compatible con mongoimport --jsonArray.",
  )
  parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="Máximo base de tecnologías por relevancia.")
  parser.add_argument(
    "--evidence-output",
    type=Path,
    help="Salida opcional con métricas y ocupaciones O*NET; no se importa en producción.",
  )
  return parser.parse_args()


def main() -> None:
  args = parse_args()
  with args.input.open("r", encoding="utf-8") as source_file:
    payload = json.load(source_file)
  evidence_documents = build_taxonomy_evidence(payload, limit=args.limit)
  documents = compact_taxonomy(evidence_documents)
  validate_taxonomy(documents)
  args.output.parent.mkdir(parents=True, exist_ok=True)
  with args.output.open("w", encoding="utf-8") as output_file:
    json.dump(documents, output_file, ensure_ascii=False, indent=2)
    output_file.write("\n")

  if args.evidence_output:
    args.evidence_output.parent.mkdir(parents=True, exist_ok=True)
    with args.evidence_output.open("w", encoding="utf-8") as evidence_file:
      json.dump(evidence_documents, evidence_file, ensure_ascii=False, indent=2)
      evidence_file.write("\n")

  by_category = defaultdict(int)
  for document in documents:
    by_category[document["category_id"]] += 1
  print(f"O*NET source rows: {len(payload.get('row', []))}")
  print(f"Technology skills generated: {len(documents)}")
  print(f"Output: {args.output.resolve()}")
  if args.evidence_output:
    print(f"Evidence output: {args.evidence_output.resolve()}")
  for category_id, count in sorted(by_category.items(), key=lambda item: (-item[1], item[0])):
    print(f"  {category_id}: {count}")


if __name__ == "__main__":
  main()
