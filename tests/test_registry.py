from pathlib import Path

from bioflow.config import load_project_config, load_workflow_config
from bioflow.registry import get_workflow_manifest, list_workflow_manifests


def test_builtin_workflow_manifests_cover_existing_workflows() -> None:
    manifests = list_workflow_manifests()
    workflow_ids = [manifest.workflow_id for manifest in manifests]

    assert workflow_ids == ["align", "qc", "rnaseq", "search"]
    assert get_workflow_manifest("qc").display_name == "Quality Control"
    assert "paired-end" in get_workflow_manifest("align").supported_inputs
    assert "hpc-slurm" in get_workflow_manifest("search").supported_profiles
    assert "summary" in get_workflow_manifest("search").key_outputs
    assert "quant_sf" in get_workflow_manifest("rnaseq").key_outputs


def test_manifest_exposes_config_schema_fields() -> None:
    align = get_workflow_manifest("align")
    search = get_workflow_manifest("search")
    rnaseq = get_workflow_manifest("rnaseq")

    assert "input_r1" in align.allowed_keys
    assert align.project_fields["ref"].required_for_project is True
    assert search.fields["evalue"].kind == "number"
    assert search.fields["max_target_seqs"].positive is True
    assert rnaseq.fields["library_type"].kind == "str"
    assert "condition" in rnaseq.project_allowed_keys


def test_checked_in_examples_match_manifest_schemas() -> None:
    examples_dir = Path(__file__).parents[1] / "examples"
    for workflow in ("qc", "align", "search", "rnaseq"):
        config = load_workflow_config(examples_dir / f"{workflow}.yml", workflow)
        assert config

    project = load_project_config(examples_dir / "project.yml")
    assert [sample["workflow"] for sample in project["samples"]] == [
        "qc",
        "align",
        "search",
        "rnaseq",
    ]
