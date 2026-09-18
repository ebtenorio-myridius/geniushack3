from src.app.config import settings
from src.app.services.case_store import CaseStore


case_store = CaseStore(settings.database_path)