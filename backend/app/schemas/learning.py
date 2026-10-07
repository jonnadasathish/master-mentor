"""Learning API payloads (API_SPEC §11). Read models carry what the UI needs to explain: state, reason,
next step."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.activity import ProblemAttemptInput
from app.schemas.assessment import AssessmentOut

Rating = Literal[0, 1, 2]


class ProgressOut(BaseModel):
    completions: int
    last_points: int | None
    best_points: int | None
    last_on: date | None
    passed: bool | None
    milestones_done: list[str] = []
    defended: bool = False


class ContentSummary(BaseModel):
    key: str
    type: str
    title: str
    minutes: int
    difficulty: str | None
    skills: list[str]
    tab: str
    stages: list[str]
    observation_kind: str
    time_limit_seconds: int | None
    progress: ProgressOut | None
    spoken: bool = False  # a speaking practice: shown without a numeric score (D-087)


class ProblemBrief(BaseModel):
    id: int
    key: str
    title: str
    difficulty: str
    expected_minutes: int | None
    url: str | None
    practice_state: str


class ContentDetail(ContentSummary):
    body: dict[str, Any]  # check answers and explanations are removed until the check is submitted
    rubric: list[dict[str, Any]]  # criteria the learner rates (interview/behavioral: key points)
    pass_points: int | None
    problems: list[ProblemBrief]
    topic: dict[str, str] | None


class SpeechIn(BaseModel):
    """A speaking practice sent with the completion of an interview question (D-087). The client sends what
    the browser heard and how long it took; the server computes every metric and rating itself."""

    model_config = ConfigDict(extra="forbid")

    source: Literal["BROWSER", "MANUAL"]
    transcript: str | None = Field(default=None, max_length=8000)
    duration_seconds: int = Field(ge=0, le=3600)
    reflection: str | None = Field(default=None, max_length=2000)


class CompletionIn(BaseModel):
    """What the learner did. Ratings are 0 (missed), 1 (partly), 2 (fully)."""

    model_config = ConfigDict(extra="forbid")

    answers: dict[str, list[int]] = Field(default_factory=dict, max_length=50)
    self_grades: dict[str, Rating] = Field(default_factory=dict, max_length=50)
    ratings: dict[str, Rating] = Field(default_factory=dict, max_length=50)
    followups: dict[str, Rating] = Field(default_factory=dict, max_length=20)
    minutes: int | None = Field(default=None, ge=1, le=600)
    notes_used: bool = False
    reference_used: bool = False
    hints_used: int = Field(default=0, ge=0, le=20)
    timed: bool = False
    time_seconds: int | None = Field(default=None, ge=0, le=6 * 3600)
    milestone: str | None = Field(default=None, max_length=48)
    defense: bool = False
    notes: str | None = Field(default=None, max_length=4000)
    speech: SpeechIn | None = None
    client_request_id: str | None = Field(default=None, min_length=8, max_length=64)


class QuestionResultOut(BaseModel):
    id: str
    kind: str
    earned: int  # 0..2 halves
    chosen: list[int]
    answer: list[int]
    explanation: str
    model_answer: str | None


class SpeakingResultOut(BaseModel):
    """What the system measured, as signals. Never a grade of English, grammar or pronunciation."""

    source: Literal["BROWSER", "MANUAL"]
    metrics_version: str
    word_count: int
    sentence_count: int | None
    duration_seconds: int
    words_per_minute: int | None
    filler_count: int
    filler_per_100_words: int
    fillers: list[tuple[str, int]]
    structure_markers: list[str]
    vocabulary_used: list[str]
    vocabulary_missing: list[str]
    repeated_phrases: list[tuple[str, int]]
    criteria: dict[str, int]  # measured criteria, 0 missed / 1 partly / 2 fully
    evidence_note: str


class CompletionOut(BaseModel):
    content_key: str
    points: int | None
    passed: bool | None
    followup_points: int | None
    questions: list[QuestionResultOut]
    observation: AssessmentOut
    progress: ProgressOut | None
    speaking: SpeakingResultOut | None = None


# ------------------------------------------------------------------------------------------------ curriculum


class TopicSkillOut(BaseModel):
    key: str
    name: str
    tier: str | None
    required: bool | None
    score: int | None
    target_score: int | None
    label: str
    status: str | None  # gap status
    content_count: int
    done_count: int
    coverage_state: str


class TopicOut(BaseModel):
    key: str
    title: str
    summary: str
    skills: list[TopicSkillOut]


class TrackOut(BaseModel):
    key: str
    title: str
    summary: str
    components: list[str]
    topics: list[TopicOut]
    content_count: int
    done_count: int


class TrackDetail(TrackOut):
    content: dict[str, list[ContentSummary]]  # topic key -> content for that topic's skills, seed order


# -------------------------------------------------------------------------------------------- skill learning


class RelatedProblemOut(BaseModel):
    problem: ProblemBrief
    via_skill: str
    via_name: str
    relation: str  # USES_THIS | FOUNDATION | SAME_GROUP


class PracticeOut(BaseModel):
    case: str  # DIRECT | RELATED | CONCEPT | UNCOVERED
    direct: list[ProblemBrief]
    related: list[RelatedProblemOut]
    fallback_skill: str | None
    fallback_name: str | None
    fallback_relation: str | None


class StepPreview(BaseModel):
    position: int
    kind: str
    title: str
    minutes: int
    content_key: str | None
    content_type: str | None
    problem_id: int | None
    optional: bool = False  # D-087: a cross-track "explain it aloud" prompt; never blocks the session


class NextActionOut(BaseModel):
    kind: Literal["RESUME_SESSION", "START_SESSION", "FALLBACK", "NONE"]
    stage: str | None
    reason: str  # a code the UI words: GAP_FOCUS | UNASSESSED | MAINTAIN | ACTIVE_SESSION | NO_CONTENT
    session_id: int | None
    minutes: int | None
    steps: list[StepPreview]
    fallback_skill: str | None


class SkillLearningOut(BaseModel):
    skill: dict[str, Any]  # key, name, component, group, tier, importance, target_score, required
    why_it_matters: dict[str, Any]  # tier label, importance, rounds, unlocks, topic
    state: dict[
        str, Any
    ]  # score, effective_score, label, confidence, assessed, gap status/type/stage/reasons
    tabs: dict[str, list[ContentSummary]]
    practice: PracticeOut
    related_skills: list[dict[str, str]]  # key, name, relation (PREREQUISITE | DEPENDENT | SAME_TOPIC)
    next_action: NextActionOut
    coverage_state: str


# --------------------------------------------------------------------------------------------- sessions


class SessionStartIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill: str = Field(min_length=1, max_length=64)
    stage: str | None = Field(default=None, max_length=16)
    plan_item_id: int | None = None
    budget_minutes: int | None = Field(default=None, ge=5, le=240)


class StepCompleteIn(BaseModel):
    """CONTENT steps send ``completion``; PROBLEM steps send ``attempt``; REFLECTION steps send
    ``reflection``."""

    model_config = ConfigDict(extra="forbid")

    completion: CompletionIn | None = None
    attempt: ProblemAttemptInput | None = None
    reflection: str | None = Field(default=None, max_length=4000)


class StepOut(BaseModel):
    position: int
    kind: str
    title: str
    minutes: int
    status: str
    content_key: str | None
    content_type: str | None
    problem: ProblemBrief | None
    observation_type: str | None
    observation_id: int | None
    points: int | None
    passed: bool | None
    reflection: str | None
    optional: bool = False


class SessionOut(BaseModel):
    id: int
    skill: str
    skill_name: str
    stage: str
    status: str
    outcome: str | None
    plan_item_id: int | None
    budget_minutes: int | None
    minutes: int
    started_at: str
    completed_at: str | None
    next_position: int | None
    steps: list[StepOut]
    before: dict[str, int | None]  # score and level when the session started
    after: dict[str, int | None]  # current score and level


class StepResultOut(BaseModel):
    session: SessionOut
    completion: CompletionOut | None
    attempt_id: int | None


# --------------------------------------------------------------------------------------------- coverage


class MockKitOut(BaseModel):
    """One round of the interview loop with timed prompts from the library, weakest skills first (D-083)."""

    round: str
    round_type: str
    minutes: int
    components: list[str]
    focus_skills: list[dict[str, Any]]  # key, name, gap status: what this round should probe first
    items: list[ContentSummary]


class CoverageRowOut(BaseModel):
    skill_key: str
    skill_name: str
    component: str
    tracks: list[str]
    tier: str | None
    importance: int
    required: bool
    direct_learning_content: int
    concept_checks: int
    practice_count: int
    timed_practice: int
    revision_content: int
    mock_coverage: list[str]
    coverage_state: str


class CoverageOut(BaseModel):
    summary: dict[str, dict[str, int]]
    content_counts: dict[str, int]  # by content type
    rows: list[CoverageRowOut]
