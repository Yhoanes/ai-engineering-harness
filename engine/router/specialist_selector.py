from pathlib import Path

import yaml


def get_available_specialists(repo_root: Path) -> dict[str, dict]:
    specialists_dir = repo_root / "core" / "specialists"
    auth_matrix_path = repo_root / "core" / "authority" / "authority-matrix.yaml"

    if not auth_matrix_path.is_file() or not specialists_dir.is_dir():
        return {}

    with open(auth_matrix_path, encoding="utf-8") as f:
        auth_data = yaml.safe_load(f)

    auth_specs = auth_data.get("specialists", {})
    available = {}

    for spec_dir in specialists_dir.iterdir():
        if spec_dir.is_dir() and spec_dir.name in auth_specs:
            spec_yaml = spec_dir / "specialist.yaml"
            if spec_yaml.is_file():
                with open(spec_yaml, encoding="utf-8") as f:
                    spec_data = yaml.safe_load(f)
                    available[spec_dir.name] = {
                        "auth": auth_specs[spec_dir.name],
                        "profile": spec_data
                    }
    return available

def determine_specialist(
    intent: str,
    task_contract: dict | None,
    repo_root: Path,
    workflow_id: str | None = None
) -> str | None:
    specialists = get_available_specialists(repo_root)
    if not specialists:
        return None

    # Filter out unauthorized specialists if workflow is provided
    if workflow_id:
        workflow_path = repo_root / "core" / "workflows" / workflow_id / "workflow.yaml"
        if workflow_path.is_file():
            with open(workflow_path, encoding="utf-8") as f:
                wf_data = yaml.safe_load(f)
            allowed = wf_data.get("allowed_specialists", [])
            if allowed:
                specialists = {k: v for k, v in specialists.items() if k in allowed}
                if not specialists:
                    return None

    # Base text to analyze
    text_to_analyze = intent.lower()
    if task_contract and task_contract.get("description"):
        text_to_analyze += " " + task_contract["description"].lower()
    if task_contract and task_contract.get("title"):
        text_to_analyze += " " + task_contract["title"].lower()

    def extract_words(text: str) -> set[str]:
        words = set()
        if not text:
            return words
        text_clean = text.replace("-", " ").replace("_", " ").replace(",", " ").replace(".", " ")
        for w in text_clean.split():
            w = w.lower()
            if len(w) > 2:
                words.add(w)
        return words

    stopwords = {"engineer", "specialist", "advisor", "lead", "director", "analyst", "architect"}
    intent_words = extract_words(text_to_analyze)

    scores = {spec_id: 0 for spec_id in specialists}

    # Dynamically score based on vocabulary overlap with the canonical profiles
    for spec_id, data in specialists.items():
        profile = data.get("profile", {})

        # 1. Keywords from ID
        for w in extract_words(spec_id):
            if w not in stopwords and w in intent_words:
                scores[spec_id] += 1

        # 2. Keywords from Display Name
        for w in extract_words(profile.get("display_name", "")):
            if w not in stopwords and w in intent_words:
                scores[spec_id] += 1

        # 3. Exact capability words (stronger signal)
        for cap in profile.get("capabilities", []):
            for w in extract_words(cap):
                if w not in stopwords and w in intent_words:
                    scores[spec_id] += 2  # Weight capabilities more

        # 4. Keyword extraction from purpose/description (naive check)
        for w in extract_words(profile.get("purpose", "")):
            if w not in stopwords and w in intent_words:
                scores[spec_id] += 1

        for w in extract_words(profile.get("description", "")):
            if w not in stopwords and w in intent_words:
                scores[spec_id] += 1

    # Find highest score
    max_score = 0
    best_specs = []
    for spec_id, score in scores.items():
        if score > max_score:
            max_score = score
            best_specs = [spec_id]
        elif score == max_score and score > 0:
            best_specs.append(spec_id)

    if max_score == 0:
        return None # Low confidence

    if len(best_specs) > 1:
        return None # Tie

    return best_specs[0]
