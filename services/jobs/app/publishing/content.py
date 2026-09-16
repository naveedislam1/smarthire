"""Pure, deterministic content-processing helpers (no I/O, no GenAI)."""

import re

_SECTION_TRIGGERS: dict[str, tuple[str, ...]] = {
    "requirements": ("requirement", "qualification", "must have", "skills", "you have"),
    "responsibilities": ("responsibilit", "you will", "duties", "role", "what you"),
    "benefits": ("benefit", "we offer", "perks", "compensation"),
}

_KNOWN_SKILLS: tuple[str, ...] = (
    "python", "fastapi", "django", "flask", "sql", "postgresql", "mysql",
    "redis", "kafka", "rabbitmq", "celery", "temporal", "docker", "kubernetes",
    "aws", "gcp", "azure", "react", "typescript", "javascript", "go", "rust",
    "java", "graphql", "rest", "grpc", "terraform", "linux", "git",
)

_STOPWORDS: frozenset[str] = frozenset(
    """a an the and or of to in for with on at by from as is are be we you your
    our will who this that have has proven strong good excellent ability able
    experience years work working team teams role join looking candidate""".split()  # noqa: SIM905
)

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z+#.]{2,}")


def breakdown_description(description: str) -> dict[str, list[str]]:
    buckets: dict[str, list[str]] = {
        "requirements": [], "responsibilities": [], "benefits": [],
    }
    current = "requirements"
    for raw_line in description.splitlines():
        line = raw_line.strip(" \t-*•").strip()
        if not line:
            continue
        matched = _match_section(line)
        if matched is not None:
            current = matched
            after = line.split(":", 1)[1].strip() if ":" in line else ""
            if after:
                buckets[current].append(after)
            continue
        buckets[current].append(line)
    return buckets


def _match_section(line: str) -> str | None:
    lowered = line.lower()
    for section, triggers in _SECTION_TRIGGERS.items():
        if any(lowered.startswith(t) for t in triggers):
            return section
    return None


def extract_skills(text: str) -> list[str]:
    lowered = text.lower()
    return [
        skill
        for skill in _KNOWN_SKILLS
        if re.search(rf"(?<![a-z]){re.escape(skill)}(?![a-z])", lowered)
    ]


def extract_keywords(text: str, *, limit: int = 15) -> list[str]:
    counts: dict[str, int] = {}
    for match in _WORD_RE.findall(text.lower()):
        if match in _STOPWORDS:
            continue
        counts[match] = counts.get(match, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [word for word, _ in ranked[:limit]]
