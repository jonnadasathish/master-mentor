"""ORM models. Importing this package registers every table on ``Base.metadata`` (used by Alembic)."""

from app.models.activity import (
    Assessment,
    AssessmentSkill,
    AttemptMistake,
    Mock,
    MockRoundRow,
    MockRoundSkill,
    ProblemAttempt,
    RevisionItemAction,
)
from app.models.base import Base
from app.models.catalog import (
    BaselineItem,
    CatalogLoad,
    MissionTemplate,
    Problem,
    ProblemSkill,
    RoadmapMilestone,
    RoadmapMilestoneSkill,
    RoleProfile,
    RoleSkillTarget,
    Skill,
    SkillGroup,
    SkillPrerequisite,
)
from app.models.content import AssessmentPrompt, BehavioralStory, Project, StoryCompetency
from app.models.derived import (
    Evidence,
    GapState,
    ReadinessSnapshot,
    RevisionItemRow,
    SkillDailySnapshot,
    SkillState,
)
from app.models.plan import DailyPlanRow, PlanItemRow, WeeklyReviewRow
from app.models.profile import Goal, StartingProfile
from app.models.system import AppSettings, AuditLog, MentorRun

__all__ = [
    "AssessmentPrompt",
    "BehavioralStory",
    "Mock",
    "MockRoundRow",
    "MockRoundSkill",
    "Project",
    "StoryCompetency",
    "WeeklyReviewRow",
    "AppSettings",
    "Assessment",
    "AssessmentSkill",
    "AttemptMistake",
    "AuditLog",
    "Base",
    "BaselineItem",
    "CatalogLoad",
    "DailyPlanRow",
    "Evidence",
    "GapState",
    "Goal",
    "StartingProfile",
    "MentorRun",
    "MissionTemplate",
    "PlanItemRow",
    "Problem",
    "ProblemAttempt",
    "ProblemSkill",
    "ReadinessSnapshot",
    "RevisionItemAction",
    "RevisionItemRow",
    "RoadmapMilestone",
    "RoadmapMilestoneSkill",
    "RoleProfile",
    "RoleSkillTarget",
    "Skill",
    "SkillDailySnapshot",
    "SkillGroup",
    "SkillPrerequisite",
    "SkillState",
]
