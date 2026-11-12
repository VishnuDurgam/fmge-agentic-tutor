import os
import tempfile

os.environ["DB_PATH"] = tempfile.mktemp(suffix=".db")

from fastapi.testclient import TestClient  # noqa: E402

from app.agents.flashcards import sm2  # noqa: E402
from app.main import app  # noqa: E402

H = {"X-Learner-Id": "test-learner"}


def test_quiz_flow_and_stats():
    with TestClient(app) as c:
        q = c.get("/quiz/next", headers=H).json()
        assert "stem" in q and len(q["options"]) >= 2 and "answer" not in q
        r = c.post("/quiz/submit", json={"question_id": q["id"], "choice": 0}, headers=H).json()
        assert "correct" in r and r["explanation"]
        assert len(c.get("/quiz/stats", headers=H).json()) == 1


def test_requires_learner_header():
    with TestClient(app) as c:
        assert c.get("/quiz/next").status_code == 400


def test_planner():
    with TestClient(app) as c:
        assert c.get("/planner/plan", headers=H).status_code == 404
        c.put("/planner/profile", json={"exam_date": "2099-01-01", "hours_per_day": 5}, headers=H)
        p = c.get("/planner/plan", headers=H).json()
        assert len(p["plan"]) == 19 and p["revision_days"] == 14


def test_cards_and_sm2():
    with TestClient(app) as c:
        cid = c.post("/cards", json={"front": "PFK-1?", "back": "Rate-limiting glycolysis"}, headers=H).json()["id"]
        assert len(c.get("/cards/due", headers=H).json()) == 1
        assert c.post(f"/cards/{cid}/review", json={"quality": 5}, headers=H).json()["interval"] == 1
        assert c.get("/cards/due", headers=H).json() == []
    assert sm2(2.5, 6, 2, 1)[1:] == (1, 0)


def test_tutor_retrieval(tmp_path, monkeypatch):
    import app.retrieval as r
    import app.ingest as ing
    monkeypatch.setattr(r, "CONTENT_DIR", tmp_path)
    monkeypatch.setattr(ing, "CONTENT_DIR", tmp_path)
    (tmp_path / "raw").mkdir()
    (tmp_path / "raw" / "n.md").write_text("Magnesium sulphate antidote is calcium gluconate in eclampsia toxicity.")
    ing.main([])
    r.reload()
    with TestClient(app) as c:
        out = c.post("/tutor/ask", json={"question": "antidote for magnesium toxicity"}, headers=H).json()
        assert out["sources"] and "calcium gluconate" in out["sources"][0]["snippet"]
    r.reload()


def test_generate_questions_from_library(tmp_path, monkeypatch):
    import json

    import app.agents.generate as gen
    import app.ingest as ing
    import app.retrieval as r
    monkeypatch.setattr(r, "CONTENT_DIR", tmp_path)
    monkeypatch.setattr(ing, "CONTENT_DIR", tmp_path)
    (tmp_path / "raw").mkdir()
    (tmp_path / "raw" / "a.md").write_text(
        "source: Test Book (CC BY)\ntitle: Heart\n\nThe sinoatrial node is the pacemaker of the heart.")
    ing.main([])
    r.reload()
    fake = json.dumps([{"subject": "Physiology", "topic": "Heart", "stem": "Pacemaker of the heart?",
                        "options": ["SA node", "AV node", "Purkinje", "Bundle of His"], "answer": 0,
                        "explanation": "SA node sets the rate."}])
    monkeypatch.setattr(gen.llm, "available", lambda: True)
    monkeypatch.setattr(gen.llm, "complete", lambda *a, **k: fake)
    with TestClient(app) as c:
        made = gen.questions("sinoatrial pacemaker", 1)
        assert made and made[0]["source"] == "Test Book (CC BY) / Heart"
        stats = c.get("/library/stats").json()
        assert stats["chunks"] >= 1
    r.reload()


def test_header_parsing():
    from app.ingest import split_header
    meta, body = split_header("source: X\ntitle: Y\n\nhello", "f.md")
    assert meta == {"source": "X", "title": "Y"} and body.strip() == "hello"


def test_medmcqa_import(tmp_path, monkeypatch):
    import json

    import app.import_medmcqa as imp
    f = tmp_path / "train.json"
    rows = [
        {"id": "a1", "question": "Drug of choice for eclampsia?", "opa": "Diazepam", "opb": "MgSO4", "opc": "Phenytoin",
         "opd": "Labetalol", "cop": 1, "exp": "MgSO4 is used.", "subject_name": "Gynaecology & Obstetrics", "topic_name": "Eclampsia"},
        {"id": "a2", "question": "Dental q", "opa": "a", "opb": "b", "opc": "c", "opd": "d", "cop": 0, "exp": "x", "subject_name": "Dental", "topic_name": "t"},
    ]
    f.write_text("\n".join(json.dumps(r) for r in rows))
    monkeypatch.setattr(imp, "CONTENT_DIR", tmp_path)
    imp.main(str(f), 10)
    from app.db import conn
    with conn() as c:
        row = c.execute("SELECT subject, answer FROM questions WHERE id='mm-a1'").fetchone()
        assert row["subject"] == "Obstetrics and Gynaecology" and row["answer"] == 1
        assert c.execute("SELECT COUNT(*) n FROM questions WHERE id='mm-a2'").fetchone()["n"] == 0
    assert (tmp_path / "raw" / "medmcqa" / "Obstetrics_and_Gynaecology.md").exists()
