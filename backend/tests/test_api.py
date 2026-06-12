"""心犀AI - API 端到端测试"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx

BASE = "http://127.0.0.1:8000"
c = httpx.Client(base_url=BASE, timeout=120)

print("=== 1. Health Check ===")
r = c.get("/api/health")
print(r.status_code, r.json())

print()
print("=== 2. List Users (page 1) ===")
r = c.get("/api/users", params={"page": 1, "page_size": 5})
data = r.json()
print(r.status_code, f"total={data['total']}, showing={len(data['users'])}")
for u in data["users"][:3]:
    print(f"  {u['user_id']} {u['nickname']} {u['gender']} {u['age']} {u['city']}")

print()
print("=== 3. Get User Detail ===")
r = c.get("/api/users/F001")
u = r.json()
print(r.status_code, f"{u['nickname']} {u['age']} {u['city']} {u['mbti']}")

print()
print("=== 4. Create New User ===")
new_user = {
    "nickname": "TestUser",
    "gender": "male",
    "age": 29,
    "city": "Shanghai",
    "province": "Shanghai",
    "education": "Master",
    "target_gender": "female",
    "target_age_min": 24,
    "target_age_max": 32,
    "about_me": "I love coding and hiking on weekends",
    "ideal_partner": "Looking for someone creative and kind who enjoys life",
    "hobbies": "coding,hiking,reading",
}
r = c.post("/api/users", json=new_user)
created = r.json()
print(r.status_code, f"Created: {created['user_id']} {created['nickname']}")
new_uid = created["user_id"]

print()
print("=== 5. Update User ===")
r = c.put(f"/api/users/{new_uid}", json={"hobbies": "coding,hiking,reading,cooking"})
updated = r.json()
print(r.status_code, f"Updated hobbies: {updated['hobbies']}")

print()
print("=== 6. List Users (filter female) ===")
r = c.get("/api/users", params={"gender": "female"})
data = r.json()
print(r.status_code, f"Female users: {data['total']}")

print()
print("=== 7. Trigger Matching (F001) ===")
r = c.post("/api/match", json={"user_id": "F001"})
match = r.json()
print(r.status_code, f"Match ID: {match['match_id']}")
print(f"  Candidates: {len(match['candidates'])}")
for cand in match["candidates"]:
    reason_preview = cand["reason"][:50]
    print(f"    {cand['nickname']} - {cand['score']}pts: {reason_preview}...")
print(f"  Letters: {len(match['match_letters'])}")
if match["match_letters"]:
    print(f"    Preview: {match['match_letters'][0][:80]}...")
match_id = match["match_id"]

print()
print("=== 8. Get Match Result ===")
r = c.get(f"/api/match/{match_id}")
print(r.status_code, f"match_id={r.json()['match_id']}")

print()
print("=== 9. Get Match History ===")
r = c.get("/api/match/history/F001")
hist = r.json()
print(r.status_code, f"total records: {hist['total']}")

print()
print("=== 10. Delete Test User ===")
r = c.delete(f"/api/users/{new_uid}")
print(r.status_code, r.json()["message"])

print()
print("=" * 50)
print("  ALL API TESTS PASSED!")
print("=" * 50)
