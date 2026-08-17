import json
from argparse import Namespace
from pathlib import Path

import bioflow.cli as cli
import bioflow.project_batch as project_batch
import bioflow.report as report
import bioflow.rnaseq as rnaseq
from bioflow.config import ConfigError, load_project_config, load_workflow_config
from bioflow.execution import build_execution_context


def _write_salmon_outputs(quant_dir: Path) -> None:
    (quant_dir / "aux_info").mkdir(parents=True, exist_ok=True)
    (quant_dir / "quant.sf").write_text(
        "\t".join(("Name", "Length", "EffectiveLength", "TPM", "NumReads"))
        + "\n"
        + "tx1\t1000\t900\t750000\t75\n"
        + "tx2\t500\t400\t250000\t25\n"
        + "tx3\t300\t200\t0\t0\n",
        encoding="utf-8",
    )
    (quant_dir / "aux_info" / "meta_info.json").write_text(
        json.dumps(
            {
                "num_processed": 125,
                "num_mapped": 100,
                "percent_mapped": 80.0,
                "library_types": ["IU"],
            }
        ),
        encoding="utf-8",
    )


def _fake_runner(command, **_kwargs):
    raw = list(command.raw_command)
    if raw[0] == "fastqc":
        input_path = Path(raw[1])
        output_dir = Path(raw[raw.index("-o") + 1])
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = input_path.name
        for suffix in (".fastq.gz", ".fq.gz", ".fastq", ".fq"):
            if stem.endswith(suffix):
                stem = stem[: -len(suffix)]
                break
        (output_dir / f"{stem}_fastqc.html").write_text("fastqc", encoding="utf-8")
    elif raw[:2] == ["salmon", "index"]:
        index_dir = Path(raw[raw.index("-i") + 1])
        index_dir.mkdir(parents=True, exist_ok=True)
        (index_dir / "versionInfo.json").write_text("{}", encoding="utf-8")
    elif raw[:2] == ["salmon", "quant"]:
        _write_salmon_outputs(Path(raw[raw.index("-o") + 1]))
    return True


def test_summarize_salmon_quant_reads_standard_outputs(tmp_path: Path) -> None:
    quant_dir = tmp_path / "quant"
    _write_salmon_outputs(quant_dir)

    summary = rnaseq.summarize_salmon_quant(
        quant_dir,
        sample_id="sample-a",
        group="control",
        condition="untreated",
        lane="L001",
        replicate=1,
        library_type="A",
        input_mode="paired-end",
    )

    assert summary["sample_id"] == "sample-a"
    assert summary["lane"] == "L001"
    assert summary["replicate"] == 1
    assert summary["mapping_rate"] == 0.8
    assert summary["transcript_count"] == 3
    assert summary["expressed_transcripts"] == 2
    assert summary["total_tpm"] == 1_000_000
    assert summary["estimated_num_reads"] == 100
    assert summary["inferred_library_type"] == ["IU"]


def test_run_rnaseq_pipeline_writes_metadata_and_supports_resume(
    tmp_path: Path,
    monkeypatch,
) -> None:
    transcriptome = tmp_path / "transcripts.fa"
    reads = tmp_path / "reads.fastq"
    transcriptome.write_text(">tx1\nACGT\n", encoding="utf-8")
    reads.write_text("@r1\nACGT\n+\nIIII\n", encoding="utf-8")
    outdir = tmp_path / "rnaseq-run"
    calls: list[tuple[str, ...]] = []

    def fake_runner(command, **kwargs):
        calls.append(command.raw_command)
        return _fake_runner(command, **kwargs)

    monkeypatch.setattr(rnaseq, "_run_command", fake_runner)
    execution = build_execution_context(
        {
            "profile": "workstation",
            "backend": "conda",
            "conda_env": "rnaseq-env",
            "threads": 4,
        },
        source="test",
    )
    result = rnaseq.run_rnaseq_pipeline(
        transcriptome,
        reads,
        outdir=outdir,
        threads=4,
        sample_id="sample-a",
        group="control",
        condition="untreated",
        lane="L001",
        replicate=1,
        execution=execution,
        skip_preflight=True,
        cli_mode=True,
    )

    assert result is not None
    assert len(calls) == 3
    metadata = json.loads((outdir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["workflow"] == "rnaseq"
    assert metadata["status"] == "success"
    assert metadata["parameters"]["sample_id"] == "sample-a"
    assert metadata["parameters"]["lane"] == "L001"
    assert metadata["summary"]["replicate"] == 1
    assert metadata["stats"]["mapping_rate"] == 0.8
    assert metadata["summary"]["condition"] == "untreated"
    assert metadata["steps"]["fastqc"]["status"] == "success"
    assert metadata["steps"]["salmon_index"]["status"] == "success"
    assert metadata["steps"]["salmon_quant"]["status"] == "success"
    assert metadata["steps"]["salmon_quant"]["backend"] == "conda"
    assert metadata["steps"]["salmon_quant"]["resolved_command"].startswith(
        "conda run --no-capture-output -n rnaseq-env salmon quant"
    )

    calls.clear()
    resumed = rnaseq.run_rnaseq_pipeline(
        transcriptome,
        reads,
        outdir=outdir,
        threads=4,
        sample_id="sample-a",
        group="control",
        condition="untreated",
        lane="L001",
        replicate=1,
        resume=True,
        execution=execution,
        skip_preflight=True,
        cli_mode=True,
    )
    assert resumed is not None
    assert calls == []
    metadata = json.loads((outdir / "metadata.json").read_text(encoding="utf-8"))
    assert all(step["status"] == "skipped" for step in metadata["steps"].values())

    changed_design = rnaseq.run_rnaseq_pipeline(
        transcriptome,
        reads,
        outdir=outdir,
        threads=4,
        sample_id="sample-a",
        group="control",
        condition="untreated",
        lane="L002",
        replicate=1,
        resume=True,
        execution=execution,
        skip_preflight=True,
        cli_mode=True,
    )
    assert changed_design is not None
    assert calls == []
    metadata = json.loads((outdir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["summary"]["lane"] == "L002"
    assert metadata["steps"]["summary"]["status"] == "success"


def test_run_rnaseq_pipeline_uses_prebuilt_index_and_paired_reads(
    tmp_path: Path,
    monkeypatch,
) -> None:
    index = tmp_path / "salmon-index"
    index.mkdir()
    (index / "versionInfo.json").write_text("{}", encoding="utf-8")
    r1 = tmp_path / "reads_1.fastq"
    r2 = tmp_path / "reads_2.fastq"
    r1.write_text("@r1\nACGT\n+\nIIII\n", encoding="utf-8")
    r2.write_text("@r1\nTGCA\n+\nIIII\n", encoding="utf-8")
    commands: list[tuple[str, ...]] = []

    def fake_runner(command, **kwargs):
        commands.append(command.raw_command)
        return _fake_runner(command, **kwargs)

    monkeypatch.setattr(rnaseq, "_run_command", fake_runner)
    result = rnaseq.run_rnaseq_pipeline(
        None,
        None,
        index=index,
        input_r1=r1,
        input_r2=r2,
        outdir=tmp_path / "run",
        library_type="A",
        skip_preflight=True,
        cli_mode=True,
    )

    assert result is not None
    assert not any(command[:2] == ("salmon", "index") for command in commands)
    quant_command = next(command for command in commands if command[:2] == ("salmon", "quant"))
    assert "-1" in quant_command
    assert "-2" in quant_command
    metadata = json.loads((tmp_path / "run" / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["summary"]["input_mode"] == "paired-end"
    assert metadata["steps"]["salmon_index"]["note"] == "using prebuilt index"


def test_run_rnaseq_pipeline_records_summary_parse_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    transcriptome = tmp_path / "transcripts.fa"
    reads = tmp_path / "reads.fastq"
    transcriptome.write_text(">tx1\nACGT\n", encoding="utf-8")
    reads.write_text("@r1\nACGT\n+\nIIII\n", encoding="utf-8")
    outdir = tmp_path / "run"

    def fake_runner(command, **kwargs):
        raw = list(command.raw_command)
        if raw[:2] != ["salmon", "quant"]:
            return _fake_runner(command, **kwargs)
        quant_dir = Path(raw[raw.index("-o") + 1])
        (quant_dir / "aux_info").mkdir(parents=True)
        (quant_dir / "quant.sf").write_text("bad\theader\n1\t2\n", encoding="utf-8")
        (quant_dir / "aux_info" / "meta_info.json").write_text("{}", encoding="utf-8")
        return True

    monkeypatch.setattr(rnaseq, "_run_command", fake_runner)
    result = rnaseq.run_rnaseq_pipeline(
        transcriptome,
        reads,
        outdir=outdir,
        skip_preflight=True,
        cli_mode=True,
    )

    assert result is None
    metadata = json.loads((outdir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["status"] == "failed"
    assert metadata["steps"]["summary"]["status"] == "failed"
    assert "invalid Salmon quant.sf header" in metadata["failure_summary"]


def test_rnaseq_workflow_and_project_schema_validation(tmp_path: Path) -> None:
    workflow_path = tmp_path / "rnaseq.yml"
    workflow_path.write_text(
        "\n".join(
            [
                "rnaseq:",
                "  transcriptome: transcripts.fa",
                "  input_r1: reads_1.fastq",
                "  input_r2: reads_2.fastq",
                "  library_type: A",
                "  threads: 4",
                "  group: control",
                "  condition: untreated",
                "  lane: L001",
                "  replicate: 1",
            ]
        ),
        encoding="utf-8",
    )
    config = load_workflow_config(workflow_path, "rnaseq")
    assert config["threads"] == 4
    assert config["group"] == "control"

    project_path = tmp_path / "project.yml"
    project_path.write_text(
        "\n".join(
            [
                "project:",
                "  samples:",
                "    - sample_id: sample-a",
                "      workflow: rnaseq",
                "      index: salmon-index",
                "      input: reads.fastq",
                "      group: control",
                "      condition: untreated",
                "      lane: L001",
                "      replicate: 1",
            ]
        ),
        encoding="utf-8",
    )
    project = load_project_config(project_path)
    assert project["samples"][0]["workflow"] == "rnaseq"
    assert project["samples"][0]["lane"] == "L001"
    assert project["samples"][0]["replicate"] == 1


def test_rnaseq_schema_rejects_incomplete_design_and_invalid_replicate(tmp_path: Path) -> None:
    incomplete_path = tmp_path / "incomplete.yml"
    incomplete_path.write_text(
        "\n".join(
            [
                "rnaseq:",
                "  index: salmon-index",
                "  input: reads.fastq",
                "  group: control",
            ]
        ),
        encoding="utf-8",
    )
    try:
        load_workflow_config(incomplete_path, "rnaseq")
    except ConfigError as exc:
        assert "requires 'group' and 'condition' together" in str(exc)
    else:
        raise AssertionError("expected ConfigError")

    inconsistent_project_path = tmp_path / "inconsistent-project.yml"
    inconsistent_project_path.write_text(
        "\n".join(
            [
                "samples:",
                "  - sample_id: sample-a",
                "    workflow: rnaseq",
                "    index: salmon-index",
                "    input: reads-a.fastq",
                "    group: control",
                "    condition: untreated",
                "  - sample_id: sample-b",
                "    workflow: rnaseq",
                "    index: salmon-index",
                "    input: reads-b.fastq",
            ]
        ),
        encoding="utf-8",
    )
    try:
        load_project_config(inconsistent_project_path)
    except ConfigError as exc:
        assert "for every RNA-seq sample" in str(exc)
    else:
        raise AssertionError("expected ConfigError")

    invalid_replicate_path = tmp_path / "invalid-replicate.yml"
    invalid_replicate_path.write_text(
        "\n".join(
            [
                "rnaseq:",
                "  index: salmon-index",
                "  input: reads.fastq",
                "  replicate: 0",
            ]
        ),
        encoding="utf-8",
    )
    try:
        load_workflow_config(invalid_replicate_path, "rnaseq")
    except ConfigError as exc:
        assert "'replicate' must be positive" in str(exc)
    else:
        raise AssertionError("expected ConfigError")


def test_rnaseq_project_schema_requires_reference(tmp_path: Path) -> None:
    project_path = tmp_path / "project.yml"
    project_path.write_text(
        "\n".join(
            [
                "samples:",
                "  - sample_id: sample-a",
                "    workflow: rnaseq",
                "    input: reads.fastq",
            ]
        ),
        encoding="utf-8",
    )
    try:
        load_project_config(project_path)
    except ConfigError as exc:
        assert "requires 'transcriptome' or 'index'" in str(exc)
    else:
        raise AssertionError("expected ConfigError")


def test_cmd_rnaseq_json_outputs_result(tmp_path: Path, monkeypatch, capsys) -> None:
    transcriptome = tmp_path / "transcripts.fa"
    reads = tmp_path / "reads.fastq"
    transcriptome.write_text(">tx1\nACGT\n", encoding="utf-8")
    reads.write_text("@r1\nACGT\n+\nIIII\n", encoding="utf-8")

    monkeypatch.setattr(
        cli,
        "run_rnaseq_pipeline",
        lambda *_args, **_kwargs: {
            "outdir": str(tmp_path / "run"),
            "quant_sf": str(tmp_path / "run" / "results" / "salmon_quant" / "quant.sf"),
            "summary": {"mapping_rate": 0.8},
        },
    )
    args = Namespace(
        config=None,
        transcriptome=str(transcriptome),
        index=None,
        input=str(reads),
        input_r1=None,
        input_r2=None,
        outdir=str(tmp_path / "run"),
        threads=2,
        library_type="A",
        sample_id="sample-a",
        group="control",
        condition="untreated",
        lane="L001",
        replicate=1,
        resume=False,
        profile="local",
        memory=None,
        queue=None,
        time_limit=None,
        backend="system",
        conda_env=None,
        container_image=None,
        quiet=True,
        json=True,
    )

    assert cli.cmd_rnaseq(args) == cli.EXIT_SUCCESS
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "success"
    assert payload["summary"]["mapping_rate"] == 0.8
    assert payload["execution"]["resources"]["threads"] == 2


def test_project_job_dispatches_rnaseq(tmp_path: Path, monkeypatch) -> None:
    run_dir = tmp_path / "project" / "001-sample-a-rnaseq"
    captured: dict[str, object] = {}

    def fake_rnaseq(*_args, **kwargs):
        captured.update(kwargs)
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "metadata.json").write_text(
            json.dumps(
                {
                    "workflow": "rnaseq",
                    "status": "success",
                    "started_at": "2026-07-28T00:00:00Z",
                    "outputs": {"quant_sf": str(run_dir / "results" / "salmon_quant" / "quant.sf")},
                }
            ),
            encoding="utf-8",
        )
        return {"status": "success"}

    monkeypatch.setattr(project_batch, "run_rnaseq_pipeline", fake_rnaseq)
    result = project_batch._run_project_job(
        run_dir,
        {
            "sample_id": "sample-a",
            "workflow": "rnaseq",
            "index": str(tmp_path / "index"),
            "input": str(tmp_path / "reads.fastq"),
            "condition": "treated",
            "group": "treatment",
            "lane": "L002",
            "replicate": 2,
            "threads": 8,
        },
    )

    assert result.status == "success"
    assert captured["sample_id"] == "sample-a"
    assert captured["condition"] == "treated"
    assert captured["group"] == "treatment"
    assert captured["lane"] == "L002"
    assert captured["replicate"] == 2
    assert captured["threads"] == 8


def test_report_exposes_rnaseq_outputs_and_metrics(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs" / "rnaseq-001"
    run_dir.mkdir(parents=True)
    (run_dir / "metadata.json").write_text(
        json.dumps(
            {
                "workflow": "rnaseq",
                "version": "1.0.0",
                "status": "success",
                "started_at": "2026-07-28T00:00:00Z",
                "completed_at": "2026-07-28T00:05:00Z",
                "command": "rnaseq",
                "parameters": {"sample_id": "sample-a", "condition": "treated"},
                "inputs": {"input": "reads.fastq", "index": "salmon-index"},
                "outputs": {
                    "quant_sf": "/tmp/quant.sf",
                    "meta_info": "/tmp/meta_info.json",
                    "summary": "/tmp/rnaseq_summary.json",
                },
                "stats": {
                    "mapped_fragments": 100,
                    "mapping_rate": 0.8,
                    "expressed_transcripts": 2,
                },
                "summary": {
                    "mapped_fragments": 100,
                    "mapping_rate": 0.8,
                    "expressed_transcripts": 2,
                },
                "steps": {},
            }
        ),
        encoding="utf-8",
    )

    data = report.collect_summary_data(run_dir.parent)
    assert data["workflow_counts"] == {"rnaseq": 1}
    assert data["runs"][0]["key_metric"] == "mapping_rate"
    assert data["runs"][0]["outputs"]["quant_sf"] == "/tmp/quant.sf"

    html_path = tmp_path / "rnaseq-report.html"
    report.generate_report(run_dir.parent, html_path)
    html = html_path.read_text(encoding="utf-8")
    assert "RNASEQ" in html
    assert "Avg RNA-seq Mapping Rate" in html
    assert "80.00%" in html
    assert "Expressed Transcripts" in html


def test_project_rnaseq_exports_matrices_design_and_missing_samples(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    planned_samples = [
        {
            "sample_id": "sample-a",
            "workflow": "rnaseq",
            "group": "control",
            "condition": "untreated",
            "lane": "L001",
            "replicate": 1,
        },
        {
            "sample_id": "sample-b",
            "workflow": "rnaseq",
            "group": "treatment",
            "condition": "treated",
            "lane": "L002",
            "replicate": 1,
        },
        {"sample_id": "sample-failed", "workflow": "rnaseq"},
        {"sample_id": "sample-missing", "workflow": "rnaseq"},
        {"sample_id": "sample-not-run", "workflow": "rnaseq"},
    ]

    def successful_result(sample_id: str, rows: str) -> project_batch.ProjectJobResult:
        run_dir = project_root / f"{sample_id}-rnaseq"
        quant_path = run_dir / "results" / "salmon_quant" / "quant.sf"
        quant_path.parent.mkdir(parents=True)
        quant_path.write_text(
            "Name\tLength\tEffectiveLength\tTPM\tNumReads\n" + rows,
            encoding="utf-8",
        )
        (run_dir / "metadata.json").write_text(
            json.dumps(
                {
                    "workflow": "rnaseq",
                    "version": "1.0.1",
                    "status": "success",
                    "started_at": "2026-08-17T00:00:00Z",
                    "parameters": {"sample_id": sample_id},
                    "outputs": {"quant_sf": str(quant_path)},
                }
            ),
            encoding="utf-8",
        )
        return project_batch.ProjectJobResult(
            sample_id=sample_id,
            workflow="rnaseq",
            run_dir=run_dir,
            metadata_path=run_dir / "metadata.json",
            status="success",
            outputs={"quant_sf": str(quant_path)},
        )

    results = [
        successful_result("sample-a", "tx2\t500\t400\t250000\t25\ntx1\t1000\t900\t750000\t75\n"),
        successful_result("sample-b", "tx1\t1000\t900\t600000\t60\ntx3\t300\t200\t400000\t40\n"),
        project_batch.ProjectJobResult(
            sample_id="sample-failed",
            workflow="rnaseq",
            run_dir=project_root / "sample-failed-rnaseq",
            metadata_path=project_root / "sample-failed-rnaseq" / "metadata.json",
            status="failed",
            outputs={},
            error="salmon failed",
        ),
        project_batch.ProjectJobResult(
            sample_id="sample-missing",
            workflow="rnaseq",
            run_dir=project_root / "sample-missing-rnaseq",
            metadata_path=project_root / "sample-missing-rnaseq" / "metadata.json",
            status="success",
            outputs={},
        ),
    ]

    exported = project_batch._write_rnaseq_project_exports(
        project_root,
        planned_samples=planned_samples,
        results=results,
    )

    counts = Path(exported["counts_matrix"]).read_text(encoding="utf-8")
    tpm = Path(exported["tpm_matrix"]).read_text(encoding="utf-8")
    metadata = Path(exported["sample_metadata"]).read_text(encoding="utf-8")
    assert counts.splitlines() == [
        "transcript_id\tsample-a\tsample-b",
        "tx1\t75\t60",
        "tx2\t25\t0",
        "tx3\t0\t40",
    ]
    assert "tx1\t750000\t600000" in tpm
    assert "sample-a\tcontrol\tuntreated\tL001\t1\tsuccess" in metadata
    assert "sample-failed" in exported["failed_samples"]
    assert "sample-missing" in exported["missing_quant_samples"]
    assert "sample-not-run" in exported["not_run_samples"]
    assert exported["group_counts"] == {"control": 1, "treatment": 1}

    (project_root / "project_summary.json").write_text(
        json.dumps({"rnaseq": exported}),
        encoding="utf-8",
    )
    report_path = project_root / "project_report.html"
    report.generate_report(project_root, report_path)
    html = report_path.read_text(encoding="utf-8")
    assert "RNA-seq Project Summary" in html
    assert "counts_matrix.tsv" in html
    assert "sample_metadata.tsv" in html
    assert "sample-failed" in html
    assert "sample-not-run" in html
