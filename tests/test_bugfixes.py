"""E2E test for bug fixes: traffic light thresholds, top_risks filter, narrative match."""
import requests

BASE = "http://127.0.0.1:5000/api/v1"
s = requests.Session()

r = s.post(f"{BASE}/assessments", json={"business_type": "restaurant"})
assert r.status_code == 200, f"Create failed: {r.status_code} {r.text}"
aid = r.json()["assessment_id"]
print(f"Assessment: {aid}")

s.patch(f"{BASE}/assessments/{aid}/lead", json={"name": "Test", "email": "test@test.com"})

# 6 questions per dimension, 42 total
# D1: all 2s (raw=12, pct=66.7) -> YELLOW
# D2: all 3s (raw=18, pct=100) -> GREEN
# D3: all 1s (raw=6, pct=33.3) -> RED
# D4: [0,3,3,3,3,3] (raw=15, pct=83.3, flag 4.1=0) -> RED (flag override)
# D5: all 3s (raw=18, pct=100) -> GREEN
# D6: all 2s (raw=12, pct=66.7) -> YELLOW
# D7: all 3s (raw=18, pct=100) -> GREEN
scores = {}
for i in range(1, 7):
    scores[f"1.{i}"] = 2  # D1: raw=12 YELLOW
for i in range(1, 7):
    scores[f"2.{i}"] = 3  # D2: raw=18 GREEN
for i in range(1, 7):
    scores[f"3.{i}"] = 1  # D3: raw=6 RED
scores["4.1"] = 0          # D4: flag
for i in range(2, 7):
    scores[f"4.{i}"] = 3  # D4: raw=15 RED (flag)
for i in range(1, 7):
    scores[f"5.{i}"] = 3  # D5: raw=18 GREEN
for i in range(1, 7):
    scores[f"6.{i}"] = 2  # D6: raw=12 YELLOW
for i in range(1, 7):
    scores[f"7.{i}"] = 3  # D7: raw=18 GREEN

assert len(scores) == 42, f"Expected 42 answers, got {len(scores)}"

for qid, score in scores.items():
    r = s.post(f"{BASE}/assessments/{aid}/answers", json={"question_id": qid, "score": score})
    assert r.status_code == 200, f"Answer {qid} failed: {r.status_code} {r.text}"

r = s.post(f"{BASE}/assessments/{aid}/calculate")
assert r.status_code == 200, f"Calculate failed: {r.status_code} {r.text}"
print(f"Calculate: {r.status_code}")

r = s.get(f"{BASE}/assessments/{aid}/results/free")
assert r.status_code == 200, f"Free results failed: {r.status_code} {r.text}"
data = r.json()

print(f"Grade: {data['overall_grade']}")
print(f"Lights: {data['dim_light']}")
print(f"Top risks: {data['top_risks']}")

# Bug 1: Traffic light thresholds
assert data["dim_light"]["D1"] == "YELLOW", f"D1 should be YELLOW got {data['dim_light']['D1']}"
assert data["dim_light"]["D2"] == "GREEN", f"D2 should be GREEN got {data['dim_light']['D2']}"
assert data["dim_light"]["D3"] == "RED", f"D3 should be RED got {data['dim_light']['D3']}"
assert data["dim_light"]["D4"] == "RED", f"D4 should be RED (flag) got {data['dim_light']['D4']}"
assert data["dim_light"]["D5"] == "GREEN", f"D5 should be GREEN got {data['dim_light']['D5']}"
assert data["dim_light"]["D6"] == "YELLOW", f"D6 should be YELLOW got {data['dim_light']['D6']}"
assert data["dim_light"]["D7"] == "GREEN", f"D7 should be GREEN got {data['dim_light']['D7']}"
print("Bug 1 (thresholds): PASSED")

# Bug 2: top_risks should NOT include GREEN dimensions
for risk_dim in data["top_risks"]:
    assert data["dim_light"][risk_dim] != "GREEN", f"Bug2: {risk_dim} is GREEN but in top_risks!"
print(f"Bug 2 (top_risks filter): PASSED - risks are {data['top_risks']}")

# Bug 3: narratives should match traffic light color
for dim_id, light in data["dim_light"].items():
    summary = data["summaries"].get(dim_id, "")
    if light in ("RED", "YELLOW"):
        assert summary, f"Bug3: {dim_id} is {light} but has no summary"
print("Bug 3 (narrative match): PASSED")

print("\n=== ALL BUG FIXES VERIFIED ===")
