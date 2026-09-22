import os
import json
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase: Client = create_client(url, key)

session_prefix = "1a09e0ad"

# Get session
res = supabase.table("agent_sessions").select("*").execute()
session = None
for s in res.data:
    if str(s['id']).startswith(session_prefix):
        session = s
        break

if not session:
    print("Session not found")
    exit(1)

session_id = session['id']

with open("session_output_utf8.txt", "w", encoding="utf-8") as f:
    f.write(f"Session ID: {session_id}\n")
    f.write(f"Status: {session['status']}, Outcome: {session['outcome']}, Reason: {session['outcome_reason']}\n")
    f.write(f"Pages Visited: {session['pages_visited']}, Steps: {session['step_count']}\n\n")

    # Get interaction events
    events = supabase.table("interaction_events").select("*").eq("session_id", session_id).order("sequence_no").execute()

    f.write("--- Interaction Events ---\n")
    for ev in events.data:
        f.write(f"[{ev['sequence_no']}] {ev['event_type']} on '{ev['target_element']}' -> URL: {ev['page_url']}\n")
        if ev.get('details'):
            f.write(f"    Details: {json.dumps(ev['details'])}\n")
        if ev.get('reasoning'):
            f.write(f"    Reasoning: {ev['reasoning']}\n")
        f.write("\n")

    # Get findings
    findings = supabase.table("findings").select("*").eq("session_id", session_id).execute()
    f.write(f"--- Findings ({len(findings.data)}) ---\n")
    for fin in findings.data:
        f.write(f"[{fin['type']}] {fin.get('feeling_label', '')}: {fin['description']}\n")
    f.write("\n")

    # Get decision explanations
    decisions = supabase.table("decision_explanations").select("*").eq("session_id", session_id).execute()
    f.write(f"--- Decision Explanations ({len(decisions.data)}) ---\n")
    for d in decisions.data:
        f.write(f"[{d['decision_type']}] {d['rationale_text']}\n")
