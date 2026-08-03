import json

from agent.reporter import PipelineReporter


def test_summary_counts_and_totals():
    r = PipelineReporter("p")
    r.add_run({"status": "success", "rows_loaded": 4})
    r.add_run({"status": "failed", "rows_loaded": 0})
    r.add_run({"status": "success", "rows_loaded": 6})
    s = r.get_summary()
    assert s["total_runs"] == 3
    assert s["successful_runs"] == 2
    assert s["total_rows_loaded"] == 10
    assert s["last_run"]["status"] == "success"


def test_save_report_writes_valid_json(tmp_path):
    r = PipelineReporter("p")
    r.add_run({"status": "success", "rows_loaded": 4})
    out = r.save_report(tmp_path / "sub" / "report.json")
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["pipeline"] == "p"
    assert data["summary"]["total_rows_loaded"] == 4
    assert len(data["runs"]) == 1
