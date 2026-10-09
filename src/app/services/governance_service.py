from src.app.config import settings
from src.app.models.governance import GovernanceRules, load_governance_rules


active_governance_rules: GovernanceRules = load_governance_rules(settings.governance_rules_path)
