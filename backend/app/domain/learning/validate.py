"""Validation of seed/learning/*.yaml (curriculum + content).

Pure: parsed YAML in, typed catalog + issues out.

Every rule here exists so that a content item can always be shown and its completion always recorded:
known skills, allowed observation kinds for those skills' components, gradable questions, scorable rubrics.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any, TypeGuard

from app.domain.catalog.issues import Issue
from app.domain.communication.cross_track import is_communication_skill
from app.domain.learning import vocabulary as lv
from app.domain.learning.model import ContentItem, LearningCatalog, Topic, Track

CURRICULUM_ROLE = "learning:curriculum"

DEFAULT_STAGES: dict[str, tuple[str, ...]] = {
    "lesson": ("LEARN",),
    "concept": ("LEARN",),
    "worked_example": ("LEARN", "GUIDED"),
    "visual_explanation": ("LEARN",),
    "concept_check": ("LEARN", "RECALL", "DIAGNOSE"),
    "quiz": ("RECALL", "DIAGNOSE", "REINFORCE"),
    "revision_card": ("RECALL", "REINFORCE", "REVISION"),
    "coding_exercise": ("GUIDED", "INDEPENDENT", "TIMED"),
    "debugging_exercise": ("INDEPENDENT", "TIMED", "TRANSFER"),
    "sql_exercise": ("GUIDED", "INDEPENDENT", "TIMED"),
    "design_exercise": ("GUIDED", "INDEPENDENT", "TIMED", "EXPLAIN"),
    "architecture_case": ("GUIDED", "INDEPENDENT", "TIMED", "EXPLAIN"),
    "interview_question": ("EXPLAIN", "THINK_ALOUD", "TIMED", "INDEPENDENT"),
    "behavioral_question": ("LEARN", "GUIDED", "INDEPENDENT", "TIMED", "EXPLAIN"),
    "guided_problem": ("GUIDED",),
    "timed_problem": ("INDEPENDENT", "TIMED"),
    "project": ("TRANSFER", "SIMULATE"),
}

# Body fields per type: name -> (shape, required). Shapes are checked by ``_shape``.
TEXT, TEXTS, CODE, ANY_TEXT = "text", "texts", "code", "text_or_code"
BODY: dict[str, dict[str, tuple[str, bool]]] = {
    "lesson": {
        "summary": (TEXT, True),
        "what": (TEXT, True),
        "why": (TEXT, True),
        "when": (TEXT, True),
        "how": (TEXT, True),
        "mental_model": (TEXT, True),
        "tradeoffs": (TEXT, True),
        "mistakes": (TEXTS, True),
        "interview": (TEXT, True),
        "explain_it": (TEXTS, True),
        "example": (CODE, False),
        "complexity": (TEXT, False),
        "internals": (TEXT, False),
        "edge_cases": (TEXTS, False),
        "misconceptions": (TEXTS, False),
    },
    "concept": {
        "summary": (TEXT, True),
        "explanation": (TEXT, True),
        "points": (TEXTS, True),
        "example": (CODE, False),
        "misconceptions": (TEXTS, False),
    },
    "worked_example": {
        "problem": (TEXT, True),
        "steps": ("steps", True),
        "takeaways": (TEXTS, True),
        "complexity": (TEXT, False),
        "code": (CODE, False),
    },
    "visual_explanation": {"summary": (TEXT, True), "frames": ("frames", True)},
    "concept_check": {"intro": (TEXT, False), "questions": ("questions", True)},
    "quiz": {"intro": (TEXT, False), "questions": ("questions", True)},
    "revision_card": {"cards": ("cards", True)},
    "coding_exercise": {
        "prompt": (TEXT, True),
        "examples": (TEXTS, False),
        "constraints": (TEXTS, False),
        "starter": (CODE, False),
        "hints": (TEXTS, True),
        "solution": (CODE, True),
        "rubric": ("rubric", True),
        "follow_ups": ("follow_ups", False),
    },
    "debugging_exercise": {
        "scenario": (TEXT, True),
        "symptoms": (TEXTS, True),
        "artifacts": (ANY_TEXT, False),
        "tasks": (TEXTS, True),
        "hints": (TEXTS, False),
        "reference": (TEXT, True),
        "solution": (CODE, False),
        "rubric": ("rubric", True),
        "follow_ups": ("follow_ups", False),
    },
    "sql_exercise": {
        "prompt": (TEXT, True),
        "schema": (CODE, True),
        "hints": (TEXTS, True),
        "solution": (CODE, True),
        "rubric": ("rubric", True),
        "follow_ups": ("follow_ups", False),
    },
    "design_exercise": {
        "prompt": (TEXT, True),
        "requirements": ("requirements", True),
        "approach": (TEXTS, True),
        "hints": (TEXTS, False),
        "reference": (TEXT, False),
        "code": (CODE, False),
        "rubric": ("rubric", True),
        "follow_ups": ("follow_ups", True),
    },
    "architecture_case": {
        "prompt": (TEXT, True),
        "requirements": ("requirements", True),
        "approach": (TEXTS, True),
        "estimates": (TEXT, False),
        "hints": (TEXTS, False),
        "reference": (TEXT, False),
        "rubric": ("rubric", True),
        "follow_ups": ("follow_ups", True),
    },
    "interview_question": {
        "prompt": (TEXT, True),
        "key_points": (TEXTS, True),
        "model_answer": (TEXT, False),
        "pitfalls": (TEXTS, False),
        "follow_ups": ("follow_ups", True),
        "speaking": ("speaking", False),  # D-087: targets for the measurable criteria of a spoken answer
        "explains": ("explains", False),  # D-087: technical skills/components this prompt can follow
    },
    "behavioral_question": {
        "prompt": (TEXT, True),
        "competency": (TEXT, True),
        "look_for": (TEXTS, True),
        "pitfalls": (TEXTS, False),
        "follow_ups": ("follow_ups", True),
    },
    "guided_problem": {"guidance": (TEXTS, True), "hints": (TEXTS, False)},
    "timed_problem": {"guidance": (TEXTS, True)},
    "project": {
        "summary": (TEXT, True),
        "stack": (TEXTS, False),
        "requirements": ("requirements", True),
        "architecture": (TEXT, True),
        "schema": (ANY_TEXT, True),
        "apis": (TEXTS, True),
        "milestones": ("milestones", True),
        "testing": (TEXTS, True),
        "deployment": (TEXTS, True),
        "observability": (TEXTS, True),
        "failure_scenarios": (TEXTS, True),
        "defense_questions": (TEXTS, True),
    },
}


class _Issues:
    def __init__(self) -> None:
        self.items: list[Issue] = []

    def error(self, code: str, where: str, message: str) -> None:
        self.items.append(Issue(code, where, message))


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _texts(value: Any) -> TypeGuard[list[str]]:
    return isinstance(value, list) and bool(value) and all(_text(v) for v in value)


def _code(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and _text(value.get("language"))
        and _text(value.get("code"))
        and (value.get("explanation") is None or _text(value.get("explanation")))
        and set(value) <= {"language", "code", "explanation"}
    )


def validate_learning(
    raw: Mapping[str, Any],
    *,
    skills: Mapping[str, str],
    problem_ids: frozenset[int],
    stages: Sequence[str],
    kind_components: Mapping[str, Sequence[str]],
) -> tuple[LearningCatalog, tuple[Issue, ...]]:
    """``raw``: role -> parsed YAML for ``learning:curriculum`` and every ``learning:<file>`` content file.
    ``skills``: skill key -> component. Returns an empty catalog when no learning files exist."""
    issues = _Issues()
    if not raw:
        return LearningCatalog(), ()
    tracks = _curriculum(issues, raw.get(CURRICULUM_ROLE), skills)
    content: list[ContentItem] = []
    position = 0
    for role in sorted(r for r in raw if r != CURRICULUM_ROLE):
        f = f"learning/{role.split(':', 1)[1]}.yaml"
        data = raw[role]
        items = data.get("content") if isinstance(data, Mapping) else None
        if not isinstance(items, list):
            issues.error("learning.missing_content", f, "a content file needs a 'content' list")
            continue
        for i, record in enumerate(items):
            position += 1
            item = _item(issues, f, i, record, position, skills, problem_ids, stages, kind_components)
            if item is not None:
                content.append(item)
    for key, count in Counter(c.key for c in content).items():
        if count > 1:
            issues.error("learning.duplicate_key", "learning/", f"content key {key!r} appears {count} times")
    by_key = {c.key: c for c in content}
    return LearningCatalog(tuple(tracks), tuple(content), by_key), tuple(issues.items)


# ------------------------------------------------------------------------------------------- curriculum


def _curriculum(issues: _Issues, data: Any, skills: Mapping[str, str]) -> list[Track]:
    f = "learning/curriculum.yaml"
    if not isinstance(data, Mapping) or not isinstance(data.get("tracks"), list):
        issues.error("learning.missing_curriculum", f, "curriculum.yaml with a 'tracks' list is required")
        return []
    tracks: list[Track] = []
    topic_keys: list[str] = []
    placed: set[str] = set()
    for t_index, t in enumerate(data["tracks"], start=1):
        where = f"{f}: tracks[{t_index - 1}]"
        if not isinstance(t, Mapping):
            issues.error("seed.wrong_type", where, "each track must be a mapping")
            continue
        key, title, summary = t.get("key"), t.get("title"), t.get("summary")
        if not (isinstance(key, str) and lv.TRACK_KEY_PATTERN.match(key)):
            issues.error("learning.invalid_key", where, f"track key must be lower_snake_case, got {key!r}")
            continue
        if not (_text(title) and _text(summary)):
            issues.error("seed.missing_field", where, "track needs a title and a summary")
        components = t.get("components") or []
        if not isinstance(components, list) or not all(isinstance(c, str) for c in components):
            issues.error("seed.wrong_type", where, "components must be a list of component names")
            components = []
        topics: list[Topic] = []
        for p_index, p in enumerate(t.get("topics") or [], start=1):
            pwhere = f"{where}.topics[{p_index - 1}]"
            if not isinstance(p, Mapping):
                issues.error("seed.wrong_type", pwhere, "each topic must be a mapping")
                continue
            pkey = p.get("key")
            if not (isinstance(pkey, str) and lv.CONTENT_KEY_PATTERN.match(pkey)):
                issues.error(
                    "learning.invalid_key", pwhere, f"topic key must look like 'dsa.arrays', got {pkey!r}"
                )
                continue
            topic_skills = p.get("skills") or []
            if not _texts(topic_skills):
                issues.error("learning.topic_without_skills", pwhere, "a topic must list at least one skill")
                topic_skills = []
            for s in topic_skills:
                if s not in skills:
                    issues.error("learning.unknown_skill", pwhere, f"unknown skill {s!r}")
            if len(set(topic_skills)) != len(topic_skills):
                issues.error("learning.duplicate_skill", pwhere, "a topic lists a skill twice")
            if not (_text(p.get("title")) and _text(p.get("summary"))):
                issues.error("seed.missing_field", pwhere, "topic needs a title and a summary")
            placed.update(topic_skills)
            topic_keys.append(pkey)
            topics.append(
                Topic(
                    pkey,
                    key,
                    p_index,
                    str(p.get("title") or ""),
                    str(p.get("summary") or ""),
                    tuple(s for s in topic_skills if s in skills),
                )
            )
        if not topics:
            issues.error("learning.track_without_topics", where, "a track needs at least one topic")
        tracks.append(
            Track(key, t_index, str(title or ""), str(summary or ""), tuple(components), tuple(topics))
        )
    for key, count in Counter(t.key for t in tracks).items():
        if count > 1:
            issues.error("learning.duplicate_key", f, f"track key {key!r} appears {count} times")
    for key, count in Counter(topic_keys).items():
        if count > 1:
            issues.error("learning.duplicate_key", f, f"topic key {key!r} appears {count} times")
    for skill in sorted(set(skills) - placed):
        issues.error("learning.skill_without_topic", f, f"skill {skill!r} is in no curriculum topic")
    return tracks


# ---------------------------------------------------------------------------------------------- content


def _item(
    issues: _Issues,
    f: str,
    index: int,
    record: Any,
    position: int,
    skills: Mapping[str, str],
    problem_ids: frozenset[int],
    stages: Sequence[str],
    kind_components: Mapping[str, Sequence[str]],
) -> ContentItem | None:
    where = f"{f}: content[{index}]"
    if not isinstance(record, Mapping):
        issues.error("seed.wrong_type", where, "each content item must be a mapping")
        return None
    key = record.get("key")
    if not (isinstance(key, str) and lv.CONTENT_KEY_PATTERN.match(key)):
        issues.error(
            "learning.invalid_key",
            where,
            f"content key must look like 'dsa.binary_search.lesson', got {key!r}",
        )
        return None
    where = f"{f}: content[key={key}]"
    if len(key) > lv.MAX_CONTENT_KEY_LENGTH:
        issues.error(
            "learning.key_too_long", where, f"content keys are at most {lv.MAX_CONTENT_KEY_LENGTH} characters"
        )
    known = {
        "key",
        "type",
        "title",
        "skills",
        "minutes",
        "difficulty",
        "stages",
        "observation",
        "problems",
        "body",
    }
    for extra in sorted(set(record) - known):
        issues.error("learning.unknown_field", where, f"unknown field {extra!r}")
    ctype = record.get("type")
    if ctype not in lv.CONTENT_TYPES:
        issues.error("learning.invalid_type", where, f"type must be one of {lv.CONTENT_TYPES}, got {ctype!r}")
        return None
    title = record.get("title")
    if not _text(title):
        issues.error("seed.missing_field", where, "missing title")
    item_skills: list[str] | Any = record.get("skills")
    if not _texts(item_skills):
        issues.error("learning.no_skills", where, "content must map to at least one skill")
        item_skills = []
    unknown = [s for s in item_skills if s not in skills]
    for s in unknown:
        issues.error("learning.unknown_skill", where, f"unknown skill {s!r}")
    if len(set(item_skills)) != len(item_skills):
        issues.error("learning.duplicate_skill", where, "a skill is listed twice")
    minutes = record.get("minutes")
    if not (
        isinstance(minutes, int) and not isinstance(minutes, bool) and 1 <= minutes <= lv.MAX_CONTENT_MINUTES
    ):
        issues.error(
            "learning.invalid_minutes", where, f"minutes must be an integer 1-{lv.MAX_CONTENT_MINUTES}"
        )
        minutes = 0
    difficulty = record.get("difficulty")
    if difficulty is not None and difficulty not in lv.DIFFICULTIES:
        issues.error("learning.invalid_difficulty", where, f"difficulty must be one of {lv.DIFFICULTIES}")
    item_stages = record.get("stages") or list(DEFAULT_STAGES[ctype])
    if not isinstance(item_stages, list) or any(s not in stages for s in item_stages):
        issues.error("learning.invalid_stage", where, f"stages must be a subset of {tuple(stages)}")
        item_stages = list(DEFAULT_STAGES[ctype])

    observation = record.get("observation") or {}
    allowed_kinds = lv.TYPE_KINDS[ctype]
    kind = observation.get("kind", allowed_kinds[0]) if isinstance(observation, Mapping) else allowed_kinds[0]
    if kind not in allowed_kinds:
        issues.error("learning.invalid_kind", where, f"{ctype} records one of {allowed_kinds}, got {kind!r}")
        kind = allowed_kinds[0]
    limit = observation.get("time_limit_seconds") if isinstance(observation, Mapping) else None
    if limit is not None and not (
        isinstance(limit, int) and not isinstance(limit, bool) and 60 <= limit <= lv.MAX_TIME_LIMIT_SECONDS
    ):
        issues.error(
            "learning.invalid_time_limit", where, f"time_limit_seconds must be 60-{lv.MAX_TIME_LIMIT_SECONDS}"
        )
        limit = None
    if limit is not None and ctype not in lv.RUBRIC_TYPES:
        issues.error("learning.time_limit_not_applicable", where, f"{ctype} cannot be timed")
    if isinstance(observation, Mapping):
        for extra in sorted(set(observation) - {"kind", "time_limit_seconds"}):
            issues.error("learning.unknown_field", where, f"unknown observation field {extra!r}")
    if not unknown:
        _check_components(issues, where, ctype, kind, item_skills, skills, kind_components)

    problems: list[int] = []
    if ctype in lv.PROBLEM_TYPES:
        raw_problems = record.get("problems")
        if not (
            isinstance(raw_problems, list) and raw_problems and all(isinstance(p, int) for p in raw_problems)
        ):
            issues.error(
                "learning.missing_problems", where, f"{ctype} needs a 'problems' list of problem ids"
            )
        else:
            problems = list(raw_problems)
            for p in problems:
                if p not in problem_ids:
                    issues.error("learning.unknown_problem", where, f"unknown problem id {p}")
    elif record.get("problems") is not None:
        issues.error("learning.problems_not_applicable", where, f"{ctype} does not reference problems")

    body = record.get("body")
    if not isinstance(body, Mapping):
        issues.error("learning.missing_body", where, "missing body mapping")
        return None
    _body(issues, where, ctype, body, skills)
    if body.get("explains") and not is_communication_skill(item_skills[0] if item_skills else ""):
        issues.error(
            "learning.explains_not_communication",
            where,
            "only a communication skill's prompt can pair with others",
        )
    return ContentItem(
        key=key,
        type=ctype,
        title=str(title or ""),
        skills=tuple(item_skills),
        minutes=minutes,
        difficulty=difficulty,
        stages=tuple(item_stages),
        observation_kind=kind,
        time_limit_seconds=limit,
        problem_ids=tuple(problems),
        body=body,
        position=position,
        source_file=f,
    )


def _check_components(
    issues: _Issues,
    where: str,
    ctype: str,
    kind: str,
    item_skills: Sequence[str],
    skills: Mapping[str, str],
    kind_components: Mapping[str, Sequence[str]],
) -> None:
    if kind == "ATTEMPT":
        return  # problem mapping decides the skills of an attempt
    kinds = [kind] + ([lv.PROJECT_DEFENSE_KIND] if ctype == "project" else [])
    for k in kinds:
        allowed = kind_components.get(k, ())
        relevant = (
            item_skills if k != lv.PROJECT_DEFENSE_KIND else [s for s in item_skills if skills[s] in allowed]
        )
        if k == lv.PROJECT_DEFENSE_KIND and not relevant:
            issues.error(
                "learning.project_without_defense_skill",
                where,
                "a project needs a project or behavioral skill",
            )
        for s in relevant:
            if skills[s] not in allowed:
                issues.error(
                    "learning.kind_component",
                    where,
                    f"{k} cannot observe {skills[s]} skill {s!r} (allowed: {', '.join(allowed)})",
                )


def _body(
    issues: _Issues, where: str, ctype: str, body: Mapping[str, Any], skills: Mapping[str, str]
) -> None:
    spec = BODY[ctype]
    for extra in sorted(set(body) - set(spec)):
        issues.error("learning.unknown_field", f"{where}.body", f"unknown body field {extra!r}")
    for name, (shape, required) in spec.items():
        value = body.get(name)
        if value is None:
            if required:
                issues.error("learning.missing_field", f"{where}.body", f"missing {name!r}")
            continue
        _shape(issues, f"{where}.body.{name}", ctype, shape, value, skills)


def _shape(
    issues: _Issues, where: str, ctype: str, shape: str, value: Any, skills: Mapping[str, str]
) -> None:
    if shape == TEXT and not _text(value):
        issues.error("learning.invalid_text", where, "must be non-empty text")
    elif shape == TEXTS and not _texts(value):
        issues.error(
            "learning.invalid_list",
            where,
            "must be a non-empty list of non-empty text "
            "(quote an item that contains ': ', or YAML reads a mapping)",
        )
    elif shape == CODE and not _code(value):
        issues.error("learning.invalid_code", where, "must be {language, code, explanation?}")
    elif shape == ANY_TEXT and not (_text(value) or _code(value)):
        issues.error("learning.invalid_text", where, "must be text or {language, code}")
    elif shape == "questions":
        _questions(issues, where, ctype, value)
    elif shape == "rubric":
        _rubric(issues, where, value)
    elif shape == "follow_ups":
        _list_of(issues, where, value, ("prompt", "look_for"), "follow-up")
    elif shape == "steps":
        _list_of(issues, where, value, ("title", "text"), "step", minimum=2, optional_code=True)
    elif shape == "frames":
        _list_of(issues, where, value, ("caption", "diagram"), "frame", minimum=2)
    elif shape == "cards":
        _list_of(issues, where, value, ("front", "back"), "card", minimum=lv.MIN_CARDS)
    elif shape == "requirements":
        if not (
            isinstance(value, Mapping)
            and _texts(value.get("functional"))
            and _texts(value.get("non_functional"))
        ):
            issues.error(
                "learning.invalid_requirements", where, "needs 'functional' and 'non_functional' lists"
            )
    elif shape == "milestones":
        _milestones(issues, where, value, skills)
    elif shape == "speaking":
        _speaking(issues, where, value)
    elif shape == "explains":
        _explains(issues, where, value, skills)


SPEAKING_FIELDS = {
    "target_seconds": (0, 600),
    "min_words": (0, 1000),
    "max_words": (0, 1000),
    "max_filler_per_100": (0, 50),
    "structure_markers_min": (0, 10),
}
MAX_SPEAKING_VOCABULARY = 12


def _speaking(issues: _Issues, where: str, value: Any) -> None:
    if not isinstance(value, Mapping) or set(value) - {*SPEAKING_FIELDS, "vocabulary"}:
        issues.error(
            "learning.invalid_speaking",
            where,
            f"speaking fields are {sorted([*SPEAKING_FIELDS, 'vocabulary'])}",
        )
        return
    for name, (low, high) in SPEAKING_FIELDS.items():
        v = value.get(name, 0)
        if isinstance(v, bool) or not isinstance(v, int) or not low <= v <= high:
            issues.error("learning.invalid_speaking", f"{where}.{name}", f"must be an integer {low}..{high}")
    if value.get("max_words", 0) and value.get("min_words", 0) > value["max_words"]:
        issues.error("learning.invalid_speaking", where, "min_words must not exceed max_words")
    vocabulary = value.get("vocabulary", [])
    if (
        not isinstance(vocabulary, list)
        or len(vocabulary) > MAX_SPEAKING_VOCABULARY
        or not all(_text(v) for v in vocabulary)
    ):
        issues.error(
            "learning.invalid_speaking",
            f"{where}.vocabulary",
            f"must be at most {MAX_SPEAKING_VOCABULARY} non-empty phrases",
        )


def _explains(issues: _Issues, where: str, value: Any, skills: Mapping[str, str]) -> None:
    from app.domain.catalog.vocabulary import COMPONENTS

    if not _texts(value):
        issues.error("learning.invalid_explains", where, "must be a non-empty list of skills or components")
        return
    for entry in value:
        if entry not in skills and entry not in COMPONENTS:
            issues.error("learning.invalid_explains", where, f"{entry!r} is neither a skill nor a component")


def _list_of(
    issues: _Issues,
    where: str,
    value: Any,
    fields: tuple[str, str],
    noun: str,
    *,
    minimum: int = 1,
    optional_code: bool = False,
) -> None:
    if not isinstance(value, list) or len(value) < minimum:
        issues.error("learning.invalid_list", where, f"needs at least {minimum} {noun}(s)")
        return
    allowed = set(fields) | ({"code"} if optional_code else set())
    for i, entry in enumerate(value):
        ok = isinstance(entry, Mapping) and all(_text(entry.get(k)) for k in fields) and set(entry) <= allowed
        if ok and optional_code and entry.get("code") is not None and not _code(entry["code"]):
            ok = False
        if not ok:
            issues.error(
                "learning.invalid_entry", f"{where}[{i}]", f"each {noun} needs {' and '.join(fields)}"
            )


def _questions(issues: _Issues, where: str, ctype: str, value: Any) -> None:
    minimum = lv.MIN_QUESTIONS.get(ctype, 1)
    if not isinstance(value, list) or len(value) < minimum:
        issues.error("learning.too_few_questions", where, f"{ctype} needs at least {minimum} questions")
        return
    ids: list[str] = []
    for i, q in enumerate(value):
        qwhere = f"{where}[{i}]"
        if not isinstance(q, Mapping):
            issues.error("learning.invalid_question", qwhere, "each question must be a mapping")
            continue
        allowed = {"id", "kind", "prompt", "code", "options", "answer", "explanation", "model_answer"}
        for extra in sorted(set(q) - allowed):
            issues.error("learning.unknown_field", qwhere, f"unknown question field {extra!r}")
        qid, kind = q.get("id"), q.get("kind")
        if not (isinstance(qid, str) and lv.TRACK_KEY_PATTERN.match(qid)):
            issues.error("learning.invalid_question", qwhere, "id must be lower_snake_case (e.g. q1)")
        else:
            ids.append(qid)
        if kind not in lv.QUESTION_KINDS:
            issues.error("learning.invalid_question", qwhere, f"kind must be one of {lv.QUESTION_KINDS}")
            continue
        if not _text(q.get("prompt")) or not _text(q.get("explanation")):
            issues.error("learning.invalid_question", qwhere, "needs a prompt and an explanation")
        if q.get("code") is not None and not _code(q["code"]):
            issues.error("learning.invalid_code", qwhere, "code must be {language, code}")
        if kind == "short":
            if not _text(q.get("model_answer")):
                issues.error("learning.invalid_question", qwhere, "a short question needs a model_answer")
            if q.get("options") is not None or q.get("answer") is not None:
                issues.error("learning.invalid_question", qwhere, "a short question has no options or answer")
            continue
        options, answer = q.get("options"), q.get("answer")
        if not _texts(options) or len(options) < 2:
            issues.error("learning.invalid_question", qwhere, "needs at least two options")
            continue
        if len(set(options)) != len(options):
            issues.error("learning.invalid_question", qwhere, "options must be distinct")
        valid = (
            isinstance(answer, list)
            and bool(answer)
            and all(isinstance(a, int) and not isinstance(a, bool) and 0 <= a < len(options) for a in answer)
            and len(set(answer)) == len(answer)
        )
        if not valid:
            issues.error("learning.invalid_answer", qwhere, "answer must list valid option indexes (0-based)")
        elif kind == "single" and len(answer or []) != 1:
            issues.error("learning.invalid_answer", qwhere, "a single-choice question has exactly one answer")
    for qid, count in Counter(ids).items():
        if count > 1:
            issues.error("learning.duplicate_question", where, f"question id {qid!r} appears {count} times")


def _rubric(issues: _Issues, where: str, value: Any) -> None:
    if not isinstance(value, list) or len(value) < 2:
        issues.error("learning.invalid_rubric", where, "a rubric needs at least two criteria")
        return
    keys: list[str] = []
    for i, r in enumerate(value):
        ok = (
            isinstance(r, Mapping)
            and isinstance(r.get("key"), str)
            and bool(lv.TRACK_KEY_PATTERN.match(r["key"]))
            and _text(r.get("label"))
            and isinstance(r.get("points"), int)
            and not isinstance(r.get("points"), bool)
            and 1 <= r["points"] <= lv.MAX_RUBRIC_POINTS
            and set(r) <= {"key", "label", "points"}
        )
        if not ok:
            issues.error(
                "learning.invalid_rubric",
                f"{where}[{i}]",
                f"needs key, label and points 1-{lv.MAX_RUBRIC_POINTS}",
            )
        else:
            keys.append(r["key"])
    for k, count in Counter(keys).items():
        if count > 1:
            issues.error("learning.invalid_rubric", where, f"criterion {k!r} appears {count} times")


def _milestones(issues: _Issues, where: str, value: Any, skills: Mapping[str, str]) -> None:
    if not isinstance(value, list) or len(value) < 2:
        issues.error("learning.invalid_milestones", where, "a project needs at least two milestones")
        return
    keys: list[str] = []
    for i, m in enumerate(value):
        mwhere = f"{where}[{i}]"
        allowed = {"key", "title", "goal", "deliverables", "skills", "minutes", "rubric"}
        if not isinstance(m, Mapping) or set(m) - allowed:
            issues.error("learning.invalid_milestone", mwhere, f"milestone fields are {sorted(allowed)}")
            continue
        key = m.get("key")
        if not (isinstance(key, str) and lv.TRACK_KEY_PATTERN.match(key)):
            issues.error("learning.invalid_milestone", mwhere, "key must be lower_snake_case")
        else:
            keys.append(key)
        if not (_text(m.get("title")) and _text(m.get("goal")) and _texts(m.get("deliverables"))):
            issues.error("learning.invalid_milestone", mwhere, "needs title, goal and deliverables")
        ms = m.get("skills")
        if not _texts(ms) or any(s not in skills for s in ms):
            issues.error("learning.invalid_milestone", mwhere, "skills must list known skills")
        minutes = m.get("minutes")
        if not (
            isinstance(minutes, int)
            and not isinstance(minutes, bool)
            and 1 <= minutes <= lv.MAX_CONTENT_MINUTES
        ):
            issues.error("learning.invalid_milestone", mwhere, f"minutes must be 1-{lv.MAX_CONTENT_MINUTES}")
        _rubric(issues, f"{mwhere}.rubric", m.get("rubric"))
    for k, count in Counter(keys).items():
        if count > 1:
            issues.error("learning.invalid_milestone", where, f"milestone {k!r} appears {count} times")
