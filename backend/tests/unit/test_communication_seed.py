"""D-087: the communication track in the seed: optional, outside calibration, coherent with the graph."""

from __future__ import annotations

import pytest

from app.domain.catalog.model import Catalog
from app.domain.catalog.vocabulary import COMPONENTS
from app.domain.learning import vocabulary as lv
from app.services.seed_service import validate_seed_dir
from tests.catalog_helpers import SEED_DIR


@pytest.fixture(scope="module")
def catalog() -> Catalog:
    result = validate_seed_dir(SEED_DIR)
    assert result.catalog is not None
    return result.catalog


GROUPS = {
    "comm.spoken_foundation",
    "comm.fluency",
    "comm.workplace",
    "comm.technical_explanation",
    "comm.writing",
}


def comm_skills(catalog: Catalog) -> list:
    return [s for s in catalog.skills if s.key.startswith("comm.")]


def test_there_are_28_communication_skills_in_five_groups_and_none_duplicates_an_existing_one(
    catalog: Catalog,
) -> None:
    skills = comm_skills(catalog)
    assert len(skills) == 28 and {s.parent for s in skills} == GROUPS
    assert {g.key for g in catalog.groups if g.key.startswith("comm.")} == GROUPS
    assert len({s.key for s in catalog.skills}) == len(catalog.skills)
    assert {s.component for s in skills} == {"coding"} and "communication" not in COMPONENTS


def test_every_communication_skill_is_optional_and_nothing_required_depends_on_it(catalog: Catalog) -> None:
    targets = {t.skill: t for t in catalog.profiles[0].targets}
    assert all(targets[s.key].tier == "T4" and not targets[s.key].required for s in comm_skills(catalog))
    assert sum(1 for t in targets.values() if t.required) == 123  # the calibration denominator
    for s in catalog.skills:
        if targets[s.key].required:
            assert not any(p.skill.startswith("comm.") for p in s.prerequisites)


def test_the_baseline_battery_never_covers_communication(catalog: Catalog) -> None:
    assert len(catalog.baseline) == 12
    covered = {c for b in catalog.baseline for c in b.covers}
    assert not any(c.startswith("comm.") for c in covered)  # M0-B01 is "all required", and none are required


def test_prerequisites_stay_inside_the_family_and_are_acyclic(catalog: Catalog) -> None:
    keys = {s.key for s in comm_skills(catalog)}
    for s in comm_skills(catalog):
        assert all(p.skill in keys for p in s.prerequisites)  # technical weakness never blocks communication
    assert catalog.max_depth <= 6


def test_the_interview_area_reuses_existing_skills_instead_of_duplicating_them(catalog: Catalog) -> None:
    track = next(t for t in catalog.learning.tracks if t.key == "communication")
    interview = next(t for t in track.topics if t.key == "comm.interview")
    assert set(interview.skills) == {
        "communication.structured_answers",
        "communication.followup_handling",
        "execution.clarification",
        "execution.think_aloud",
    }
    assert [t.key for t in track.topics] == [
        "comm.spoken_foundation",
        "comm.fluency",
        "comm.workplace",
        "comm.technical_explanation",
        "comm.writing",
        "comm.interview",
    ]


def test_every_cross_track_prompt_pairs_with_real_technical_targets(catalog: Catalog) -> None:
    skills = {s.key for s in catalog.skills}
    pairing = [c for c in catalog.learning.content if c.body.get("explains")]
    assert len(pairing) >= 8
    for item in pairing:
        assert item.type == "interview_question" and item.skills[0].startswith(("comm.", "communication."))
        assert all(e in skills or e in COMPONENTS for e in item.body["explains"])
        assert item.minutes <= 5 and item.body.get("speaking")  # short and spoken


def test_content_keys_are_unique_and_spoken_prompts_have_measurable_targets(catalog: Catalog) -> None:
    keys = [c.key for c in catalog.learning.content]
    assert len(keys) == len(set(keys))
    spoken = [c for c in catalog.learning.content if c.body.get("speaking")]
    assert len(spoken) >= 40
    for item in spoken:
        s = item.body["speaking"]
        assert 0 < s["target_seconds"] <= 600 and s["min_words"] <= s["max_words"]
        if item.time_limit_seconds:
            assert item.time_limit_seconds >= s["target_seconds"]  # the limit never undercuts the target


def test_core_communication_skills_have_the_full_learning_path(catalog: Catalog) -> None:
    core = [
        "comm.speak_1m",
        "comm.filler_reduction",
        "comm.status_update",
        "comm.clarification_request",
        "comm.help_and_blockers",
        "comm.explain_code",
        "comm.explain_bug_root_cause",
        "comm.explain_decisions_tradeoffs",
        "comm.explain_query_optimization",
        "comm.explain_simply",
    ]
    for skill in core:
        types = {c.type for c in catalog.learning.for_skill(skill)}
        assert {"lesson", "concept_check", "interview_question", "revision_card"} <= types, skill
        assert any(c.time_limit_seconds for c in catalog.learning.for_skill(skill)), skill  # timed practice
    for skill in (s.key for s in comm_skills(catalog)):
        items = catalog.learning.for_skill(skill)
        assert {"learn", "revision"} <= {lv.TAB_OF_TYPE[c.type] for c in items}, skill
        assert any(c.type == "interview_question" for c in items), skill  # a practice prompt
        assert any(c.time_limit_seconds for c in catalog.learning.for_skill(skill)), (
            skill
        )  # no TIMED dead end
