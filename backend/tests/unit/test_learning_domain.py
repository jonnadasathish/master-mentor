"""LEARNING_ENGINE rules: grading, completion -> observation, session composition, practice resolution,
progress, coverage and problem practice state. Pure domain, no database."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from app.domain.learning import grading
from app.domain.learning.coverage import SkillFacts, coverage_report, coverage_state
from app.domain.learning.evidence import CompletionError, Submission, grade_completion, source_key
from app.domain.learning.model import ContentItem, LearningCatalog, Topic, Track
from app.domain.learning.practice import AttemptFact, ProblemRef, problem_state, resolve_practice
from app.domain.learning.progress import ContentObservation, content_progress, parse_source_key
from app.domain.learning.session import ProblemOption, StepState, compose_session, summarize

COMPONENTS = {
    "a.skill": "dsa",
    "b.skill": "dsa",
    "c.skill": "cs",
    "p.skill": "project",
    "beh.skill": "behavioral",
}
QUESTIONS = [
    {"id": "q1", "kind": "single", "prompt": "?", "options": ["x", "y"], "answer": [1], "explanation": "e"},
    {
        "id": "q2",
        "kind": "multi",
        "prompt": "?",
        "options": ["x", "y", "z"],
        "answer": [0, 2],
        "explanation": "e",
    },
    {"id": "q3", "kind": "short", "prompt": "?", "model_answer": "m", "explanation": "e"},
]
RUBRIC = [{"key": "correct", "label": "c", "points": 3}, {"key": "clean", "label": "k", "points": 1}]


def item(
    key: str, ctype: str, *, skills: tuple[str, ...] = ("a.skill",), minutes: int = 10, **extra: Any
) -> ContentItem:
    body = extra.pop("body", {})
    kind = extra.pop("kind", "STUDY_SESSION")
    return ContentItem(
        key=key,
        type=ctype,
        title=extra.pop("title", key),
        skills=skills,
        minutes=minutes,
        difficulty=extra.pop("difficulty", None),
        stages=tuple(extra.pop("stages", ("LEARN",))),
        observation_kind=kind,
        time_limit_seconds=extra.pop("limit", None),
        problem_ids=tuple(extra.pop("problems", ())),
        body=body,
        position=extra.pop("position", 1),
    )


# ------------------------------------------------------------------------------------------------ grading


def test_share_points_is_integer_round_half_up() -> None:
    assert grading.share_points([(2, 1), (1, 1)]) == 75
    assert grading.share_points([(1, 1), (0, 1), (0, 1)]) == 17  # 16.67 -> 17
    assert grading.share_points([(1, 1), (0, 1), (0, 1), (0, 1), (0, 1), (0, 1), (0, 1), (0, 1)]) == 6  # 6.25
    assert grading.share_points([(1, 1), (0, 1), (0, 1), (0, 1)]) == 13  # 12.5 rounds up
    assert grading.share_points([]) == 0


def test_choice_questions_are_graded_by_the_answer_key_short_ones_by_self_grade() -> None:
    result = grading.grade_questions(QUESTIONS, {"q1": [1], "q2": [2, 0]}, {"q3": 1})
    assert [q.earned for q in result.questions] == [2, 2, 1]
    assert result.points == 83  # 5 of 6 halves
    wrong = grading.grade_questions(QUESTIONS, {"q1": [0], "q2": [0]}, {})
    assert [q.earned for q in wrong.questions] == [0, 0, 0] and wrong.points == 0  # partial multi is wrong
    assert wrong.questions[0].answer == (1,) and wrong.questions[2].model_answer == "m"


def test_rubric_points_are_weighted_and_invalid_ratings_count_as_missed() -> None:
    assert grading.rubric_points(RUBRIC, {"correct": 2, "clean": 0}) == 75
    assert grading.rubric_points(RUBRIC, {"correct": 1, "clean": 2}) == 63  # 5/8 = 62.5 -> 63
    assert grading.rubric_points(RUBRIC, {"correct": 7}) == 0
    assert grading.followup_points([{"prompt": "a", "look_for": "b"}] * 2, {"0": 2, "1": 1}) == 75
    assert grading.grade_cards([{}, {}, {}, {}], {"0": 2, "1": 2, "2": 2, "3": 0}) == 75


# ------------------------------------------------------------------------------- completion -> observation


def test_reading_records_a_study_session_with_no_points() -> None:
    graded = grade_completion(item("l", "lesson", minutes=20), Submission(), COMPONENTS)
    assert graded.payload["kind"] == "STUDY_SESSION" and graded.payload["study_minutes"] == 20
    assert graded.points is None and graded.passed is None
    assert graded.payload["skills"] == [
        {"skill": "a.skill", "outcome_points": None, "mapping_weight_bp": 10000}
    ]
    assert graded.payload["source_key"] == "content:l"


def test_check_records_a_recall_quiz_and_notes_make_it_open_book() -> None:
    check = item("c", "concept_check", skills=("a.skill", "b.skill"), body={"questions": QUESTIONS})
    graded = grade_completion(
        check, Submission(answers={"q1": [1], "q2": [0, 2]}, self_grades={"q3": 2}), COMPONENTS
    )
    assert graded.payload["kind"] == "RECALL_QUIZ" and graded.points == 100 and graded.passed is True
    assert [s["mapping_weight_bp"] for s in graded.payload["skills"]] == [
        10000,
        5000,
    ]  # supporting skill counts half
    assert {s["outcome_points"] for s in graded.payload["skills"]} == {100}
    with_notes = grade_completion(check, Submission(notes_used=True), COMPONENTS)
    assert with_notes.payload["notes_used"] is True and with_notes.passed is False  # 0 points, L0 open-book


def test_rubric_practice_is_timed_only_within_the_content_limit() -> None:
    ex = item(
        "x",
        "coding_exercise",
        kind="CODE_EXERCISE",
        limit=900,
        body={"rubric": RUBRIC, "follow_ups": [{"prompt": "f", "look_for": "g"}]},
    )
    timed = grade_completion(
        ex,
        Submission(ratings={"correct": 2, "clean": 2}, timed=True, time_seconds=600, followups={"0": 2}),
        COMPONENTS,
    )
    assert timed.payload["kind"] == "CODE_EXERCISE" and timed.points == 100
    assert (timed.payload["timed"], timed.payload["time_limit_seconds"], timed.payload["time_seconds"]) == (
        True,
        900,
        600,
    )
    assert timed.followup_points == 100 and timed.payload["followup_points"] == 100
    untimed = grade_completion(ex, Submission(ratings={"correct": 2}, timed=True), COMPONENTS)
    assert untimed.payload["timed"] is False and untimed.payload["time_limit_seconds"] is None
    assert untimed.payload["followup_points"] is None  # follow-ups not rated -> no L5 claim


def test_interview_and_behavioral_questions_score_their_key_points() -> None:
    q = item(
        "i",
        "interview_question",
        kind="CONCEPT_EXPLAIN",
        body={"key_points": ["a", "b", "c", "d"], "follow_ups": []},
    )
    assert grade_completion(q, Submission(ratings={"p0": 2, "p1": 2, "p2": 1}), COMPONENTS).points == 63
    b = item(
        "b",
        "behavioral_question",
        skills=("beh.skill",),
        kind="STORY_REHEARSAL",
        body={"look_for": ["x", "y"]},
    )
    assert (
        grade_completion(b, Submission(ratings={"p0": 2, "p1": 2}), COMPONENTS).payload["kind"]
        == "STORY_REHEARSAL"
    )


def test_project_milestones_are_applied_tasks_and_the_defense_a_walkthrough() -> None:
    body = {
        "milestones": [{"key": "m1", "skills": ["c.skill"], "rubric": RUBRIC}],
        "defense_questions": ["why", "how", "what if"],
    }
    project = item("proj", "project", skills=("c.skill", "p.skill"), kind="APPLIED_TASK", body=body)
    m = grade_completion(project, Submission(milestone="m1", ratings={"correct": 2, "clean": 2}), COMPONENTS)
    assert m.payload["kind"] == "APPLIED_TASK" and m.payload["source_key"] == "content:proj#m1"
    assert [s["skill"] for s in m.payload["skills"]] == ["c.skill"]
    d = grade_completion(project, Submission(defense=True, ratings={"q0": 2, "q1": 2, "q2": 1}), COMPONENTS)
    assert d.payload["kind"] == "PROJECT_WALKTHROUGH" and [s["skill"] for s in d.payload["skills"]] == [
        "p.skill"
    ]
    assert d.points == 83 and source_key(project, defense=True) == "content:proj#defense"
    with pytest.raises(CompletionError):
        grade_completion(project, Submission(milestone="nope"), COMPONENTS)
    with pytest.raises(CompletionError):
        grade_completion(item("g", "guided_problem", problems=(1,)), Submission(), COMPONENTS)


# ----------------------------------------------------------------------------------------- sessions


def learn_content() -> list[ContentItem]:
    return [
        item("check", "concept_check", minutes=8, stages=("LEARN", "RECALL"), position=3),
        item("lesson", "lesson", minutes=20, position=1),
        item("example", "worked_example", minutes=10, stages=("LEARN", "GUIDED"), position=2),
        item(
            "ex",
            "coding_exercise",
            minutes=15,
            stages=("GUIDED", "INDEPENDENT"),
            kind="CODE_EXERCISE",
            position=4,
        ),
        item("cards", "revision_card", minutes=5, stages=("RECALL",), position=5),
    ]


def test_learn_session_follows_the_slot_order_and_ends_with_reflection() -> None:
    steps = compose_session(
        stage="LEARN", content=learn_content(), problems=[], done=(), attempted=(), budget_minutes=None
    )
    assert [(s.kind, s.content_key) for s in steps] == [
        ("CONTENT", "lesson"),
        ("CONTENT", "example"),
        ("CONTENT", "check"),
        ("CONTENT", "ex"),
        ("REFLECTION", None),
    ]
    again = compose_session(
        stage="LEARN", content=learn_content(), problems=[], done=(), attempted=(), budget_minutes=None
    )
    assert again == steps  # deterministic


def test_session_respects_the_budget_and_prefers_undone_items() -> None:
    steps = compose_session(
        stage="LEARN", content=learn_content(), problems=[], done=(), attempted=(), budget_minutes=40
    )
    assert [s.content_key for s in steps] == ["lesson", "example", "check"]  # 38 min; reflection does not fit
    content = [*learn_content(), item("lesson2", "lesson", minutes=12, position=6)]
    redo = compose_session(
        stage="LEARN", content=content, problems=[], done={"lesson"}, attempted=(), budget_minutes=None
    )
    assert redo[0].content_key == "lesson2"  # repeat session: what is not done yet comes first


def test_recall_session_and_problem_fallback() -> None:
    recall = compose_session(
        stage="RECALL", content=learn_content(), problems=[], done=(), attempted=(), budget_minutes=None
    )
    assert [s.content_key for s in recall] == ["cards", "check"]
    problems = [ProblemOption(7, "Medium one", "MEDIUM", 30), ProblemOption(3, "Easy one", "EASY", 15)]
    independent = compose_session(
        stage="INDEPENDENT", content=[], problems=problems, done=(), attempted={3}, budget_minutes=None
    )
    assert [(s.kind, s.problem_id) for s in independent] == [("PROBLEM", 7), ("REFLECTION", None)]
    guided = compose_session(
        stage="GUIDED", content=[], problems=problems, done=(), attempted=(), budget_minutes=None
    )
    assert guided[0].problem_id == 3  # GUIDED prefers an EASY problem
    assert (
        compose_session(stage="TIMED", content=[], problems=[], done=(), attempted=(), budget_minutes=30)
        == ()
    )


def test_timed_stage_only_uses_timed_content() -> None:
    content = [
        item("ex", "coding_exercise", kind="CODE_EXERCISE", stages=("TIMED",)),
        item("ex_t", "coding_exercise", kind="CODE_EXERCISE", stages=("TIMED",), limit=600, position=2),
    ]
    steps = compose_session(
        stage="TIMED", content=content, problems=[], done=(), attempted=(), budget_minutes=None
    )
    assert steps[0].content_key == "ex_t"


def test_session_summary_outcomes() -> None:
    assert summarize([StepState(1, "DONE", 80, True), StepState(2, "PENDING", None, None)]).next_position == 2
    passed = summarize([StepState(1, "DONE", 80, True), StepState(2, "DONE", None, None)])
    assert (passed.status, passed.outcome) == ("COMPLETED", "PASSED")
    failed = summarize([StepState(1, "DONE", 40, False), StepState(2, "SKIPPED", None, None)])
    assert (failed.outcome, failed.skipped) == ("NEEDS_REPEAT", 1)
    assert summarize([StepState(1, "SKIPPED", None, None)]).outcome == "NOT_SCORED"


# ------------------------------------------------------------------------------------- practice resolution


def ref(pid: int, difficulty: str = "MEDIUM", weight: int = 10000, canonical: bool = True) -> ProblemRef:
    return ProblemRef(pid, f"p{pid}", difficulty, canonical, weight)


def resolve(**kw: Any) -> Any:
    args: dict[str, Any] = {
        "skill": "s",
        "component": "dsa",
        "prerequisites": [],
        "dependents": [],
        "group_skills": [],
        "problems_by_skill": {},
        "content_by_skill": {},
    }
    return resolve_practice(**(args | kw))


def test_case_a_direct_problems_are_ordered_primary_canonical_easy_first() -> None:
    r = resolve(
        problems_by_skill={
            "s": [ref(9, "HARD"), ref(4, "EASY", 5000), ref(2, "EASY", canonical=False), ref(5, "EASY")]
        }
    )
    assert r.case == "DIRECT" and [p.id for p in r.direct] == [5, 2, 9, 4]


def test_case_b_related_problems_explain_the_relation() -> None:
    r = resolve(
        dependents=["dep"],
        prerequisites=["pre"],
        group_skills=["s", "sib"],
        problems_by_skill={"dep": [ref(1)], "pre": [ref(2), ref(1)], "sib": [ref(3)]},
    )
    assert r.case == "RELATED"
    assert [(x.problem.id, x.via_skill, x.relation) for x in r.related] == [
        (1, "dep", "USES_THIS"),
        (2, "pre", "FOUNDATION"),
        (3, "sib", "SAME_GROUP"),
    ]  # no duplicates


def test_case_c_concept_skill_uses_its_checks_and_exercises() -> None:
    content = {"s": [item("l", "lesson"), item("c", "concept_check"), item("i", "interview_question")]}
    r = resolve(component="cs", content_by_skill=content)
    assert r.case == "CONCEPT" and r.content == ("c", "i")
    dsa = resolve(content_by_skill=content, problems_by_skill={"pre": [ref(1)]}, prerequisites=["pre"])
    assert (
        dsa.case == "CONCEPT" and dsa.related[0].relation == "FOUNDATION"
    )  # related application still shown


def test_case_d_uncovered_points_to_the_nearest_practised_skill() -> None:
    r = resolve(
        component="cs",
        prerequisites=["empty", "pre"],
        group_skills=["sib"],
        content_by_skill={"pre": [item("c", "concept_check")], "sib": [item("x", "quiz")]},
    )
    assert (r.case, r.fallback_skill, r.fallback_relation) == ("UNCOVERED", "pre", "FOUNDATION")
    alone = resolve(component="cs", group_skills=["sib"], content_by_skill={"sib": [item("x", "quiz")]})
    assert (alone.fallback_skill, alone.fallback_relation) == ("sib", "SAME_GROUP")
    assert resolve(component="cs").fallback_skill is None


def test_problem_practice_state_never_equates_completion_with_mastery() -> None:
    def a(
        outcome: str,
        hints: int = 0,
        solution: bool = False,
        timed: bool = False,
        within: bool = False,
        explanation: int | None = None,
        complexity: bool | None = None,
    ) -> AttemptFact:
        return AttemptFact(outcome, hints, solution, timed, within, explanation, complexity)

    assert problem_state([]) == "not_started"
    assert problem_state([a("PARTIAL")]) == "attempted"
    assert problem_state([a("FAIL")]) == "failed"
    assert problem_state([a("PASS", solution=True)]) == "solved_after_solution"
    assert problem_state([a("PASS", hints=1)]) == "solved_with_hint"
    assert problem_state([a("PASS")]) == "independent_solve"
    assert problem_state([a("PASS", timed=True, within=False)]) == "independent_solve"
    assert problem_state([a("PASS", timed=True, within=True)]) == "timed_solve"
    assert (
        problem_state([a("PASS", timed=True, within=True, explanation=7, complexity=True)])
        == "interview_grade"
    )
    assert problem_state([a("FAIL"), a("PASS", hints=2)]) == "solved_with_hint"  # strongest attempt counts


# ------------------------------------------------------------------------------------------ progress


def test_progress_is_derived_from_observations() -> None:
    catalog = {
        "chk": item("chk", "concept_check", body={"questions": QUESTIONS}),
        "les": item("les", "lesson"),
        "proj": item(
            "proj", "project", body={"milestones": [{"key": "m1"}, {"key": "m2"}], "defense_questions": []}
        ),
    }
    obs = [
        ContentObservation("content:chk", 40, date(2026, 10, 1), 1),
        ContentObservation("content:chk", 80, date(2026, 10, 2), 2),
        ContentObservation("content:les", None, date(2026, 10, 1), 3),
        ContentObservation("content:proj#m1", 75, date(2026, 10, 3), 4),
        ContentObservation("content:proj#m2", 60, date(2026, 10, 3), 5),
        ContentObservation("prompt:other", 90, date(2026, 10, 3), 6),
        ContentObservation("content:gone", 90, date(2026, 10, 3), 7),
    ]
    p = content_progress(obs, catalog)
    assert set(p) == {"chk", "les", "proj"}
    assert (p["chk"].completions, p["chk"].best_points, p["chk"].last_points, p["chk"].passed) == (
        2,
        80,
        80,
        True,
    )
    assert (p["les"].completions, p["les"].passed) == (1, None)
    assert p["proj"].milestones_done == ("m1",) and p["proj"].passed is False
    assert parse_source_key("content:proj#m1") == ("proj", "m1") and parse_source_key("story:3") is None


# ------------------------------------------------------------------------------------------ coverage


def test_coverage_states() -> None:
    assert coverage_state(0, 0, 0, 0, 0) == "CONTENT_GAP"
    assert coverage_state(2, 0, 0, 0, 0) == "UNMEASURED"
    assert coverage_state(1, 1, 1, 1, 1) == "FULL"
    assert coverage_state(1, 1, 2, 0, 1) == "PARTIAL"
    assert coverage_state(0, 0, 3, 3, 0) == "PARTIAL"  # problems only: practised but nothing taught


def test_coverage_report_counts_content_and_problems_per_skill() -> None:
    catalog = LearningCatalog(
        tracks=(Track("dsa", 1, "DSA", "s", ("dsa",), (Topic("dsa.t", "dsa", 1, "T", "s", ("a.skill",)),)),),
        content=(
            item("l", "lesson"),
            item("c", "concept_check"),
            item("x", "coding_exercise", kind="CODE_EXERCISE", limit=600),
            item("r", "revision_card"),
        ),
    )
    facts = [
        SkillFacts("a.skill", "A", "dsa", "T1", 100, True),
        SkillFacts("b.skill", "B", "dsa", "T4", 20, False),
    ]
    rows = coverage_report(
        facts, catalog, {"a.skill": ["EASY", "MEDIUM"], "b.skill": ["EASY"]}, {"dsa": ["DSA"]}
    )
    a, b = rows
    assert (
        a.direct_learning_content,
        a.concept_checks,
        a.practice_count,
        a.timed_practice,
        a.revision_content,
    ) == (1, 1, 3, 2, 1)
    assert a.coverage_state == "FULL" and a.tracks == ("dsa",) and a.mock_coverage == ("DSA",)
    assert b.coverage_state == "PARTIAL" and b.timed_practice == 0


def test_a_skills_own_lesson_beats_a_lesson_that_only_supports_it() -> None:
    own = item("own.lesson", "lesson", skills=("a.skill",), position=9)
    other = item("other.lesson", "lesson", skills=("b.skill", "a.skill"), position=1)  # earlier in the seed
    steps = compose_session(
        stage="LEARN", content=[own, other], problems=[], done=(), attempted=(), budget_minutes=None
    )
    assert steps[0].content_key == "own.lesson"  # for_skill order (primary first) breaks the tie
