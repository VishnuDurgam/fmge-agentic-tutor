import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONTENT_DIR = Path(os.getenv("CONTENT_DIR", ROOT / "content"))
DB_PATH = os.getenv("DB_PATH", str(ROOT / "apps" / "api" / "fmge.db"))
CORS_ORIGINS = [o for o in os.getenv("CORS_ORIGINS", "*").split(",") if o]

SUBJECTS = [
    "Anatomy", "Physiology", "Biochemistry", "Pathology", "Microbiology",
    "Pharmacology", "Forensic Medicine", "Community Medicine", "Medicine",
    "Surgery", "Obstetrics and Gynaecology", "Paediatrics", "Ophthalmology",
    "ENT", "Orthopaedics", "Dermatology", "Psychiatry", "Anaesthesia",
    "Radiology",
]
