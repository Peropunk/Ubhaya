"""Deterministic matching for the PC-14 synthetic case vocabulary."""
import re
from datetime import datetime, timedelta

from ..config import IST


def match(claim, events, config):
    action, quote = claim["action"], claim["quote"]
    date = datetime.fromisoformat(config["case_date"]).replace(tzinfo=IST)
    night = date + timedelta(hours=18), date + timedelta(days=1, hours=6)
    window = (datetime.fromisoformat(claim["t_min"]), datetime.fromisoformat(claim["t_max"])) if claim["t_min"] else night

    def overlaps(event, interval):
        return datetime.fromisoformat(event["t_min"]) <= interval[1] and datetime.fromisoformat(event["t_max"]) >= interval[0]

    actors = config["actors"]["Ravi Kumar"]
    night_events = [e for e in events if overlaps(e, night)]
    logons = [e for e in night_events if e["action"] == "logon" and e["actor"] in actors["accounts"]]
    exits = [e for e in night_events if e["action"] == "badge_out" and e["fields"].get("badge_id") in actors["badges"]]
    visitors = [e for e in night_events if e["action"] == "badge_in" and e["fields"].get("visitor_card")]
    arrivals = [e for e in night_events if e["action"] == "chat_message" and e["actor"] == actors["chat_name"]
                and "dhaba pahunch" in e["fields"]["message"].lower()]
    payments = [e for e in night_events if e["action"] == "upi_debit" and e["fields"].get("counterparty") in config["places"]["dhaba"]["merchants"]]
    matches = []
    rules = []
    verdict, strength = "no_evidence", None
    if action == "file_copy":
        copies = [e for e in night_events if e["action"] == action and overlaps(e, window) and e["place"] == "PC-14"]
        if copies:
            matches = [e for e in night_events if e["action"] == "usb_connected" and e["place"] == "PC-14" and overlaps(e, window)] + copies
    elif action == "logon":
        matches = [e for e in logons if overlaps(e, window)]
    elif action == "exclusive_access":
        matches = visitors[:1]
        if matches:
            verdict, rules = "contradicted", ["R3"]
    elif action in ("visitor_in", "visitor_badge", "badge_out"):
        matches = exits[-1:] if action == "badge_out" else visitors[:1]
        if action == "visitor_badge":
            matches = [e for e in visitors if e["fields"]["badge_id"] in quote][:1]
            strength = "indirect"
        if matches and not overlaps(matches[0], window):
            verdict, rules = "contradicted", ["R2"]
    elif action in ("personal_copy", "personal_logon"):
        if logons:
            matches = logons + payments + arrivals
            verdict, strength = "uncertain", "indirect"
            if action == "personal_logon":
                rules.append("R3")
            travel = next((r["seconds"] for r in config["min_travel_s"] if r["from"] == "office" and r["to"] == "dhaba"), 0)
            for remote in payments + arrivals:
                gaps = [abs((datetime.fromisoformat(logon[edge])-datetime.fromisoformat(remote[other])).total_seconds())
                        for logon in logons for edge,other in (("t_min","t_max"),("t_max","t_min"))]
                if max(gaps) < travel:
                    rules.append("R4")
                    break
    elif action == "arrival":
        matches = arrivals[:1]
        if matches and not overlaps(matches[0], window):
            verdict, rules, strength = "uncertain", ["R2"], "indirect"
        travel = next((r["seconds"] for r in config["min_travel_s"] if r["from"] == "office" and r["to"] == "dhaba"), None)
        for e in exits:
            earliest, latest = map(datetime.fromisoformat, (e["t_min"], e["t_max"]))
            if travel and max(window[1] - earliest, latest - window[0]) < timedelta(seconds=travel):
                matches.append(e)
                verdict, strength = "contradicted", "direct"
                rules.append("R4")
                break
    elif action in ("upi_debit", "repayment"):
        if action == "upi_debit":
            strength = "indirect"
        matches = [e for e in payments if overlaps(e, window)] if action == "upi_debit" else [
            e for e in events if e["action"] == "upi_credit" and e["actor"] == "Ravi Kumar"
            and e["fields"]["counterparty"].startswith("Aman ")]
        amount = re.search(r"(?:Rs\s+([\d,]+)|([\d,]+)\s+(?:rupaye|रुपये))", quote)
        if amount and matches:
            expected = int((amount[1] or amount[2]).replace(",", ""))
            if all(e["fields"]["amount"] != expected for e in matches):
                verdict, rules = "contradicted", ["R5"]
        if matches and ("night" in quote or "December" in quote) and not any(overlaps(e, window) for e in matches):
            verdict, rules = "contradicted", ["R2"]
    elif action == "employee_entry":
        door = [e for e in events if e["action"] in ("badge_in", "badge_out") and overlaps(e, window)]
        entries = [e for e in door if e["action"] == "badge_in" and not e["fields"]["visitor_card"]]
        matches = entries or door
        if entries:
            verdict, rules = "contradicted", ["R3"]
    if matches and verdict == "no_evidence":
        verdict = "supported"
    if matches and strength is None:
        strength = "direct"
    return dict(verdict=verdict, strength=strength, rule_ids=rules, event_ids=[e["id"] for e in matches],
                certainty="certain" if verdict == "contradicted" else None,
                explanation=f"{len(matches)} matching source records. " + (", ".join(rules) or "No contradiction rule fired."))


RULE_REASONS = {
    "R2": "The relevant event time falls outside the claim window.",
    "R3": "A recorded event conflicts with a claim of absence or exclusive access.",
    "R4": "The available time between the two locations is shorter than the configured minimum travel time.",
    "R5": "The amount in the statement differs from the amount in the matched transaction records.",
}


def explain_finding(claim, finding, events):
    """Describe the saved decision using only its cited evidence and rule IDs."""
    verdict = finding["verdict"]
    unresolved = None
    if verdict == "no_evidence":
        summary = "The matcher found no source record for this claim."
        unresolved = "The available evidence leaves the claim unverified."
    elif verdict == "uncertain" and claim["action"] in ("personal_copy", "personal_logon"):
        accounts = sorted({e["actor"] for e in events if e["action"] == "logon" and e["actor"]})
        summary = ("The PC log records a sign-in under " + ", ".join(accounts) + "."
                   if accounts else "The cited records provide only indirect evidence of the operator.")
        if any(e["action"] == "upi_debit" for e in events):
            summary += " The payment record traces the account holder’s transaction."
        unresolved = "Who was physically operating PC-14 at the time?"
    elif verdict == "uncertain":
        summary = "The cited records provide indirect or conflicting evidence about the claim."
        unresolved = "Independent confirmation of the claimed event is still needed."
    elif verdict == "contradicted":
        summary = "The matcher found a conflict between the statement and the cited records."
    elif claim["action"] == "file_copy":
        summary = "PC-14 records file-copy activity during the claimed interval."
    elif claim["action"] == "employee_entry":
        summary = "The matched door records contain no employee entry during the claimed interval."
    else:
        summary = "The cited records support the claimed activity under the PC-14 matching rules."
    return dict(summary=summary, unresolved=unresolved,
                rules=[dict(id=rule, reason=RULE_REASONS.get(rule, "See the recorded rule."))
                       for rule in finding["rule_ids"]])
