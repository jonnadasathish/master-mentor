"""seed/learning validation (CONTENT_AUTHORING_GUIDE): the real content is valid, and every authoring
mistake that would make an item unshowable or unrecordable is reported before anything is loaded."""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

from app.domain.activity.vocabulary import ASSESSMENT_COMPONENTS
from app.domain.catalog import vocabulary as v
from app.domain.catalog.validate import validate_seed
from app.domain.learning.validate import validate_learning
from tests.catalog_helpers import real_raw

SKILLS = {"a.one": "dsa", "a.two": "dsa", "c.one": "cs", "b.one": "behavioral"}
CURRICULUM = {
    "seed_version": "seed-v9",
    "tracks": [
        {
            "key": "t",
            "title": "T",
            "summary": "S",
            "components": ["dsa"],
            "topics": [
                {
                    "key": "t.one",
                    "title": "One",
                    "summary": "S",
                    "skills": ["a.one", "a.two", "c.one", "b.one"],
                }
            ],
        }
    ],
}
LESSON = {
    "key": "t.lesson",
    "type": "lesson",
    "title": "Lesson",
    "skills": ["a.one"],
    "minutes": 10,
    "body": {
        "summary": "s",
        "what": "w",
        "why": "y",
        "when": "n",
        "how": "h",
        "mental_model": "m",
        "tradeoffs": "t",
        "mistakes": ["one"],
        "interview": "i",
        "explain_it": ["e"],
    },
}
CHECK = {
    "key": "t.check",
    "type": "concept_check",
    "title": "Check",
    "skills": ["a.one"],
    "minutes": 5,
    "body": {
        "questions": [
            {
                "id": f"q{i}",
                "kind": "single",
                "prompt": "p",
                "options": ["a", "b"],
                "answer": [0],
                "explanation": "e",
            }
            for i in range(3)
        ]
    },
}


def run(*items: dict[str, Any], curriculum: dict[str, Any] | None = None) -> set[str]:
    raw = {"learning:curriculum": curriculum or CURRICULUM, "learning:content": {"content": list(items)}}
    _, issues = validate_learning(
        raw, skills=SKILLS, problem_ids=frozenset({1}), stages=v.STAGES, kind_components=ASSESSMENT_COMPONENTS
    )
    return {i.code for i in issues}


def changed(base: dict[str, Any], mutate: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    mutate(out)
    return out


def test_real_seed_learning_content_is_valid() -> None:
    raw, lock = real_raw()
    result = validate_seed(raw, lock)
    assert not [i for i in result.errors if i.code.startswith("learning.")], [
        i.render() for i in result.errors
    ]
    assert result.catalog is not None and result.catalog.learning.content
    every_skill = {s.key for s in result.catalog.skills}
    placed = {k for t in result.catalog.learning.tracks for p in t.topics for k in p.skills}
    assert placed == every_skill  # every canonical skill is reachable from the curriculum


def test_a_minimal_valid_set() -> None:
    assert run(LESSON, CHECK) == set()


def test_skill_mapping_errors() -> None:
    assert "learning.unknown_skill" in run(changed(LESSON, lambda c: c.update(skills=["ghost.skill"])))
    assert "learning.no_skills" in run(changed(LESSON, lambda c: c.update(skills=[])))
    assert "learning.duplicate_key" in run(LESSON, LESSON)


def test_observation_kind_must_fit_the_type_and_the_skill_components() -> None:
    story_on_dsa = {
        "key": "t.story",
        "type": "behavioral_question",
        "title": "Q",
        "skills": ["a.one"],
        "minutes": 5,
        "body": {
            "prompt": "p",
            "competency": "c",
            "look_for": ["x"],
            "follow_ups": [{"prompt": "f", "look_for": "g"}],
        },
    }
    assert "learning.kind_component" in run(story_on_dsa)
    assert "learning.invalid_kind" in run(
        changed(LESSON, lambda c: c.update(observation={"kind": "RECALL_QUIZ"}))
    )
    assert "learning.time_limit_not_applicable" in run(
        changed(LESSON, lambda c: c.update(observation={"time_limit_seconds": 600}))
    )


def test_lesson_quality_fields_are_required() -> None:
    assert "learning.missing_field" in run(changed(LESSON, lambda c: c["body"].pop("mental_model")))
    assert "learning.unknown_field" in run(changed(LESSON, lambda c: c["body"].update(typo="x")))
    # "- Using X: a thing" without quotes is parsed by YAML as a mapping, not text
    assert "learning.invalid_list" in run(
        changed(LESSON, lambda c: c["body"].update(mistakes=[{"Using X": "a"}]))
    )


def test_questions_must_be_gradable() -> None:
    assert "learning.too_few_questions" in run(changed(CHECK, lambda c: c["body"]["questions"].pop()))
    assert "learning.invalid_answer" in run(
        changed(CHECK, lambda c: c["body"]["questions"][0].update(answer=[5]))
    )
    assert "learning.invalid_answer" in run(
        changed(CHECK, lambda c: c["body"]["questions"][0].update(answer=[0, 1]))
    )
    assert "learning.invalid_question" in run(
        changed(CHECK, lambda c: c["body"]["questions"][0].update(kind="short", options=None, answer=None))
    )  # a short answer needs a model answer
    assert "learning.duplicate_question" in run(
        changed(CHECK, lambda c: c["body"]["questions"][1].update(id="q0"))
    )


def test_problem_types_need_known_problems() -> None:
    guided = {
        "key": "t.guided",
        "type": "guided_problem",
        "title": "G",
        "skills": ["a.one"],
        "minutes": 15,
        "problems": [1],
        "body": {"guidance": ["g"]},
    }
    assert run(guided) == set()
    assert "learning.unknown_problem" in run(changed(guided, lambda c: c.update(problems=[99])))
    assert "learning.problems_not_applicable" in run(changed(LESSON, lambda c: c.update(problems=[1])))


def test_curriculum_must_place_every_skill() -> None:
    partial = changed(CURRICULUM, lambda c: c["tracks"][0]["topics"][0]["skills"].remove("b.one"))
    assert "learning.skill_without_topic" in run(LESSON, curriculum=partial)
    assert "learning.unknown_skill" in run(
        LESSON,
        curriculum=changed(CURRICULUM, lambda c: c["tracks"][0]["topics"][0]["skills"].append("ghost.x")),
    )


def test_no_required_skill_is_a_content_gap() -> None:
    """MASTER_SPEC_V3 §26: a critical skill must not be silently uncovered (dead-end rule, library side)."""
    from app.domain.learning.coverage import SkillFacts, coverage_report

    raw, lock = real_raw()
    catalog = validate_seed(raw, lock).catalog
    assert catalog is not None
    targets = {t.skill: t for t in catalog.profiles[0].targets}
    facts = [
        SkillFacts(
            s.key,
            s.name,
            s.component,
            targets[s.key].tier,
            targets[s.key].importance,
            targets[s.key].required,
        )
        for s in catalog.skills
    ]
    difficulties: dict[str, list[str]] = {}
    for p in catalog.problems:
        for m in p.skills:
            difficulties.setdefault(m.skill, []).append(p.difficulty)
    rows = coverage_report(facts, catalog.learning, difficulties, {})
    gaps = [
        (r.skill_key, r.coverage_state)
        for r in rows
        if r.required and r.coverage_state in ("CONTENT_GAP", "UNMEASURED")
    ]
    assert gaps == []
