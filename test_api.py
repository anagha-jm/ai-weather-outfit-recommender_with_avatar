"""
Stage 1 smoke test — calls the live Flask API at 127.0.0.1:5000
Run AFTER starting backend with: py backend/app.py
"""
import requests
import json

BASE = "http://127.0.0.1:5000"

def check(label, response, expected_status):
    ok = response.status_code == expected_status
    status_str = "PASS" if ok else "FAIL"
    print(f"[{status_str}] {label} -> HTTP {response.status_code}")
    try:
        data = response.json()
        print(f"       {json.dumps(data, indent=2)[:400]}")
    except Exception:
        print(f"       (no JSON body)")
    print()
    return ok

results = []

# Test 1: valid city
r = requests.post(BASE + "/predict", json={"city": "Kottayam"}, timeout=15)
results.append(check("Valid city (Kottayam)", r, 200))
if r.status_code == 200:
    d = r.json()
    assert "recommended_outfit" in d, "FAIL: recommended_outfit missing"
    assert "current" in d, "FAIL: current missing"
    assert "forecast" in d, "FAIL: forecast missing"
    assert "ranked_outfits" in d, "FAIL: ranked_outfits missing"
    assert "weather_description" in d["current"], "FAIL: weather_description missing in current"
    print("       Field assertions: PASS")
    print()

# Test 2: style/occasion/comfort_level params (backward compatible)
r = requests.post(BASE + "/predict", json={
    "city": "Kottayam",
    "style": "Formal",
    "occasion": "Party",
    "comfort_level": 70
}, timeout=15)
results.append(check("With style/occasion/comfort_level params", r, 200))

# Test 3: invalid city
r = requests.post(BASE + "/predict", json={"city": "zzzzfakecity99"}, timeout=15)
results.append(check("Invalid city -> expect 404", r, 404))

# Test 4: missing city field
r = requests.post(BASE + "/predict", json={}, timeout=15)
results.append(check("Missing city field -> expect 400", r, 400))


# Test 5: no body
r = requests.post(BASE + "/predict", timeout=15)

ok = r.status_code in (400, 415)
print(f"[{'PASS' if ok else 'FAIL'}] No body -> HTTP {r.status_code}")
results.append(ok)
print()


# Summary
passed = sum(results)
total = len(results)
print(f"Results: {passed}/{total} passed")
if passed == total:
    print("[PASS] All Flask API smoke tests passed.")
else:
    print("[FAIL] Some tests failed — see above.")
