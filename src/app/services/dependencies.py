from src.app.config import settings
from src.app.services.case_store import CaseStore
from src.app.services.governance_service import active_governance_rules


case_store = CaseStore(
    settings.database_path,
    source_document_dir=settings.source_document_dir,
    governance_rules=active_governance_rules,
)