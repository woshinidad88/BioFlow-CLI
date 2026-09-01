from __future__ import annotations

import gzip
import json
import sys
from argparse import Namespace
from pathlib import Path

import pytest

import bioflow.cli as cli
import bioflow.longread as longread
import bioflow.project_batch as project_batch
import bioflow.report as report
from bioflow.config import ConfigError, load_project_config, load_workflow_config


FLAGSTAT = (
    "10 + 0 in total (QC-passed reads + QC-failed reads)\n"
    "1 + 0 secondary\n"
    "2 + 0 supplementary\n"
    "8 + 0 mapped (80.00% : N/A)\n"
)


def _write_inputs(tmp_path: Path) -> tuple[Path, Path]:
    reference = tmp_path / "ref.fa"
    reads = tmp_path / "reads.fastq"
    reference.write_text(">ref\nACGTACGTACGT\n", encoding="utf-8")
    reads.write_text(
        "@read-1\nACGT\n+\nIIII\n"
        "@read-2\nACGTAC\n+\n555555\n",
        encoding="utf-8",
    )
    return reference, reads


def _mock_pipeline_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_map(
        _ref: Path,
        _reads: Path,
        output_bam: Path,
        **_: object,
    ) -> bool:
        output_bam.write_bytes(b"bam")
        return True

    def fake_index(bam: Path, **_: object) -> bool:
        bam.with_suffix(bam.suffix + ".bai").write_bytes(b"bai")
        return True

    monkeypatch.setattr(longread, "_run_minimap2_pipe_sort", fake_map)
    monkeypatch.setattr(longread, "_run_samtools_index", fake_index)
    monkeypatch.setattr(longread, "_run_samtools_flagstat", lambda *args, **kwargs: FLAGSTAT)
    monkeypatch.setattr(longread, "display_longread_stats", lambda _stats: None)


def test_calculate_longread_fasta_stats(tmp_path: Path) -> None:
    reads = tmp_path / "reads.fa"
    reads.write_text(">a\nAAAA\n>b\nAAAAA\nAAAAA\n>c\nAAAAAA\n", encoding="utf-8")

    stats = longread.calculate_longread_stats(reads)

    assert stats["input_format"] == "fasta"
    assert stats["read_count"] == 3
    assert stats["total_bases"] == 20
    assert stats["mean_read_length"] == pytest.approx(20 / 3)
    assert stats["min_read_length"] == 4
    assert stats["max_read_length"] == 10
    assert stats["n50"] == 10
    assert stats["avg_quality"] is None


def test_calculate_longread_gzip_fastq_quality_stats(tmp_path: Path) -> None:
    reads = tmp_path / "reads.fastq.gz"
    with gzip.open(reads, "wt", encoding="utf-8") as handle:
        handle.write("@a\nACGT\n+\nIIII\n@b\nACGTAC\n+\n555555\n")

    stats = longread.calculate_longread_stats(reads)

    assert stats["input_format"] == "fastq"
    assert stats["read_count"] == 2
    assert stats["total_bases"] == 10
    assert stats["n50"] == 6
    assert stats["avg_quality"] == pytest.approx(28.0)
    assert stats["q20_ratio"] == pytest.approx(1.0)
    assert stats["q30_ratio"] == pytest.approx(0.4)


def test_calculate_longread_stats_rejects_invalid_input(tmp_path: Path) -> None:
    reads = tmp_path / "reads.txt"
    reads.write_text("not a sequence file\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported sequence format"):
        longread.calculate_longread_stats(reads)


def test_minimap2_sort_pipeline_streams_between_resolved_commands(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reference, reads = _write_inputs(tmp_path)
    output_bam = tmp_path / "results" / "reads.bam"
    output_bam.parent.mkdir()
    first = (
        sys.executable,
        "-c",
        "import sys; sys.stdout.buffer.write(b'fake-bam')",
    )
    second = (
        sys.executable,
        "-c",
        f"import pathlib,sys; pathlib.Path({str(output_bam)!r}).write_bytes(sys.stdin.buffer.read())",
    )
    monkeypatch.setattr(
        longread,
        "resolve_pipeline_commands",
        lambda *args, **kwargs: [
            longread.ResolvedCommand(first, first, "system", "fingerprint"),
            longread.ResolvedCommand(second, second, "system", "fingerprint"),
        ],
    )

    assert longread._run_minimap2_pipe_sort(
        reference,
        reads,
        output_bam,
        preset="map-ont",
        threads=1,
        execution=None,
        stdout_log=tmp_path / "stdout.log",
        stderr_log=tmp_path / "stderr.log",
    )
    assert output_bam.read_bytes() == b"fake-bam"


def test_longread_pipeline_writes_outputs_metadata_and_summaries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reference, reads = _write_inputs(tmp_path)
    run_dir = tmp_path / "runs" / "longread-001"
    _mock_pipeline_tools(monkeypatch)

    result = longread.run_longread_pipeline(
        reference,
        reads,
        outdir=run_dir,
        preset="map-hifi",
        threads=4,
        sample_id="sample-long",
        skip_preflight=True,
    )

    assert result is not None
    assert Path(result["bam"]).is_file()
    assert Path(result["bai"]).is_file()
    assert Path(result["flagstat"]).is_file()
    assert Path(result["qc_summary"]).is_file()
    assert Path(result["summary"]).is_file()
    assert result["stats"]["read_count"] == 2
    assert result["stats"]["n50"] == 6
    assert result["stats"]["mapped_reads"] == 8
    assert result["stats"]["mapping_rate"] == pytest.approx(0.8)

    metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["workflow"] == "longread"
    assert metadata["status"] == "success"
    assert metadata["parameters"]["preset"] == "map-hifi"
    assert metadata["parameters"]["sample_id"] == "sample-long"
    assert metadata["tool_versions"].keys() == {"minimap2", "samtools"}
    assert metadata["steps"]["map_sort"]["status"] == "success"
    assert "minimap2 -a -x map-hifi" in metadata["steps"]["map_sort"]["raw_command"]
    assert metadata["summary"]["n50"] == 6

    summary = json.loads(Path(result["summary"]).read_text(encoding="utf-8"))
    assert summary["workflow"] == "longread"
    assert summary["stats"]["supplementary_alignments"] == 2


def test_longread_resume_reuses_valid_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    reference, reads = _write_inputs(tmp_path)
    run_dir = tmp_path / "runs" / "longread-resume"
    _mock_pipeline_tools(monkeypatch)
    assert longread.run_longread_pipeline(reference, reads, outdir=run_dir, skip_preflight=True)

    monkeypatch.setattr(
        longread,
        "_run_minimap2_pipe_sort",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("mapping should be reused")),
    )
    monkeypatch.setattr(
        longread,
        "_run_samtools_index",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("index should be reused")),
    )
    monkeypatch.setattr(
        longread,
        "_run_samtools_flagstat",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("flagstat should be reused")),
    )

    result = longread.run_longread_pipeline(
        reference,
        reads,
        outdir=run_dir,
        resume=True,
        skip_preflight=True,
    )

    assert result is not None
    metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
    assert all(step["status"] == "skipped" for step in metadata["steps"].values())


def test_longread_resume_does_not_reuse_changed_preset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reference, reads = _write_inputs(tmp_path)
    run_dir = tmp_path / "runs" / "longread-preset"
    _mock_pipeline_tools(monkeypatch)
    assert longread.run_longread_pipeline(reference, reads, outdir=run_dir, skip_preflight=True)

    calls: list[str] = []

    def fake_map(_ref: Path, _reads: Path, output_bam: Path, **kwargs: object) -> bool:
        calls.append(str(kwargs["preset"]))
        output_bam.write_bytes(b"new-bam")
        return True

    monkeypatch.setattr(longread, "_run_minimap2_pipe_sort", fake_map)
    result = longread.run_longread_pipeline(
        reference,
        reads,
        outdir=run_dir,
        preset="map-pb",
        resume=True,
        skip_preflight=True,
    )

    assert result is not None
    assert calls == ["map-pb"]


def test_longread_resume_recomputes_downstream_outputs_after_bam_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reference, reads = _write_inputs(tmp_path)
    run_dir = tmp_path / "runs" / "longread-bam-refresh"
    _mock_pipeline_tools(monkeypatch)
    initial = longread.run_longread_pipeline(reference, reads, outdir=run_dir, skip_preflight=True)
    assert initial is not None
    Path(initial["bam"]).write_bytes(b"")
    calls: list[str] = []

    def fake_map(_ref: Path, _reads: Path, output_bam: Path, **_: object) -> bool:
        calls.append("map")
        output_bam.write_bytes(b"replacement-bam")
        return True

    def fake_index(bam: Path, **_: object) -> bool:
        calls.append("index")
        bam.with_suffix(bam.suffix + ".bai").write_bytes(b"replacement-index")
        return True

    def fake_flagstat(*args: object, **kwargs: object) -> str:
        calls.append("flagstat")
        return FLAGSTAT

    monkeypatch.setattr(longread, "_run_minimap2_pipe_sort", fake_map)
    monkeypatch.setattr(longread, "_run_samtools_index", fake_index)
    monkeypatch.setattr(longread, "_run_samtools_flagstat", fake_flagstat)

    result = longread.run_longread_pipeline(
        reference,
        reads,
        outdir=run_dir,
        resume=True,
        skip_preflight=True,
    )

    assert result is not None
    assert calls == ["map", "index", "flagstat"]
    metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["steps"]["sequence_stats"]["status"] == "skipped"
    assert metadata["steps"]["map_sort"]["status"] == "success"
    assert metadata["steps"]["bam_index"]["status"] == "success"
    assert metadata["steps"]["flagstat"]["status"] == "success"
    assert metadata["steps"]["summary"]["status"] == "success"


def test_longread_config_and_project_validation(tmp_path: Path) -> None:
    workflow_config = tmp_path / "longread.yml"
    workflow_config.write_text(
        "longread:\n  ref: ref.fa\n  input: reads.fastq\n  preset: map-ont\n  threads: 4\n",
        encoding="utf-8",
    )
    assert load_workflow_config(workflow_config, "longread")["preset"] == "map-ont"

    bad_config = tmp_path / "bad-longread.yml"
    bad_config.write_text("ref: ref.fa\ninput: reads.fastq\npreset: invalid\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="preset"):
        load_workflow_config(bad_config, "longread")

    project_config = tmp_path / "project.yml"
    project_config.write_text(
        "samples:\n  - sample_id: lr1\n    workflow: longread\n    ref: ref.fa\n    input: reads.fastq\n",
        encoding="utf-8",
    )
    project = load_project_config(project_config)
    assert project["samples"][0]["workflow"] == "longread"


def test_cmd_longread_json_dispatches_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    reference, reads = _write_inputs(tmp_path)
    outdir = tmp_path / "run"
    seen: dict[str, object] = {}

    def fake_run(ref: Path, input_path: Path, **kwargs: object) -> dict[str, object]:
        seen.update({"ref": ref, "input": input_path, **kwargs})
        return {"run_dir": str(outdir), "bam": str(outdir / "results" / "reads.bam"), "stats": {"n50": 6}}

    monkeypatch.setattr(cli, "run_longread_pipeline", fake_run)
    args = Namespace(
        config=None,
        ref=str(reference),
        input=str(reads),
        output=None,
        outdir=str(outdir),
        preset="map-hifi",
        threads=2,
        sample_id="lr1",
        resume=False,
        profile=None,
        memory=None,
        queue=None,
        time_limit=None,
        backend=None,
        conda_env=None,
        container_image=None,
        quiet=True,
        json=True,
    )

    assert cli.cmd_longread(args) == cli.EXIT_SUCCESS
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "success"
    assert payload["stats"]["n50"] == 6
    assert seen["preset"] == "map-hifi"
    assert seen["sample_id"] == "lr1"


def test_project_job_dispatches_longread(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    reference, reads = _write_inputs(tmp_path)
    run_dir = tmp_path / "project" / "001-lr-longread"
    seen: dict[str, object] = {}

    def fake_run(ref: Path, input_path: Path, **kwargs: object) -> dict[str, object]:
        seen.update({"ref": ref, "input": input_path, **kwargs})
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "metadata.json").write_text(
            json.dumps(
                {
                    "workflow": "longread",
                    "status": "success",
                    "started_at": "2026-09-01T00:00:00Z",
                    "outputs": {"bam": str(run_dir / "results" / "lr.bam")},
                }
            ),
            encoding="utf-8",
        )
        return {"run_dir": str(run_dir)}

    monkeypatch.setattr(project_batch, "run_longread_pipeline", fake_run)
    result = project_batch._run_project_job(
        run_dir,
        {
            "sample_id": "lr",
            "workflow": "longread",
            "ref": str(reference),
            "input": str(reads),
            "preset": "map-hifi",
            "threads": 3,
        },
    )

    assert result.status == "success"
    assert result.workflow == "longread"
    assert seen["preset"] == "map-hifi"
    assert seen["sample_id"] == "lr"


def test_report_exports_longread_metrics(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs" / "longread-001"
    run_dir.mkdir(parents=True)
    (run_dir / "metadata.json").write_text(
        json.dumps(
            {
                "workflow": "longread",
                "version": "1.0.2",
                "status": "success",
                "started_at": "2026-09-01T00:00:00Z",
                "completed_at": "2026-09-01T00:01:00Z",
                "command": "longread",
                "parameters": {"sample_id": "lr1", "preset": "map-ont"},
                "outputs": {
                    "bam": "/tmp/lr.bam",
                    "bai": "/tmp/lr.bam.bai",
                    "flagstat": "/tmp/lr.flagstat.txt",
                    "qc_summary": "/tmp/longread_qc.json",
                    "summary": "/tmp/longread_summary.json",
                },
                "stats": {
                    "read_count": 12,
                    "total_bases": 24000,
                    "mean_read_length": 2000.0,
                    "n50": 3000,
                    "mapped_reads": 10,
                    "mapping_rate": 0.8333,
                },
                "steps": {},
            }
        ),
        encoding="utf-8",
    )

    data = report.collect_summary_data(run_dir)
    assert data["runs"][0]["key_metric"] == "n50"
    assert data["runs"][0]["metrics"]["read_count"] == 12

    html_path = tmp_path / "report.html"
    report.generate_report(run_dir, html_path)
    html = html_path.read_text(encoding="utf-8")
    assert "LONGREAD" in html
    assert "Read N50" in html
    assert "3000" in html
    assert "Avg Long-read Mapping Rate" in html
