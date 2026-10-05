from __future__ import annotations

from pathlib import Path

from app.infrastructure.seed_files import read_seed
from app.services.seed_service import lock_seed_dir, validate_seed_dir
from tests.catalog_helpers import bump_version, copy_seed


def test_formatting_does_not_change_fingerprints(tmp_path: Path) -> None:
    """Rewriting every file with a different YAML layout (and no comments) keeps the content fingerprint."""
    original = validate_seed_dir(copy_seed(tmp_path / "a"))
    reformatted = validate_seed_dir(copy_seed(tmp_path / "b", mutate=lambda raw: None))
    assert reformatted.ok
    assert reformatted.catalog_fingerprint == original.catalog_fingerprint


def test_lock_workflow_for_a_new_version(tmp_path: Path) -> None:
    def change(raw: dict[str, object]) -> None:
        bump_version(raw, "seed-v2")  # type: ignore[arg-type]
        raw["problem_catalog"]["problems"][0]["title"] = "Two Sum (v2)"  # type: ignore[index]

    seed = copy_seed(tmp_path, mutate=change)
    assert {i.code for i in validate_seed_dir(seed).errors} == {"lock.unlocked_version"}
    version, lock_path = lock_seed_dir(seed)
    assert version == "seed-v2"
    _, lock = read_seed(seed)
    assert lock is not None and set(lock) == {"seed-v1", "seed-v2"}  # append-only
    assert validate_seed_dir(seed).ok
    assert lock_path.name == "seed.lock.yaml"
