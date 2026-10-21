from enum import Enum, auto


class TrustLevel(Enum):
    AUTHORITATIVE = auto()
    AUTHORITATIVE_FOR_RESULTS = auto()
    DERIVED = auto()
    INFORMATIONAL_ONLY = auto()
    CANONICAL_REPO_STATE = auto()


SOURCE_OF_TRUTH_CLASSIFICATION = {
    "git": TrustLevel.CANONICAL_REPO_STATE,
    "task_contract_authority": TrustLevel.AUTHORITATIVE,
    "task_contract_state": TrustLevel.AUTHORITATIVE,
    "evidence": TrustLevel.AUTHORITATIVE_FOR_RESULTS,
    "current_state_memory": TrustLevel.DERIVED,
    "conversation": TrustLevel.INFORMATIONAL_ONLY,
}
