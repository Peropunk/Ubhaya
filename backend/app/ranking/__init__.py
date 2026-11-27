"""Evidence-request catalogue for the synthetic PC-14 exercise."""

CATALOGUE = [
    ("visitor_register", "Visitor card V-03 issue register", (3, 3, 1, 0),
     {"visitor_badge", "exclusive_access", "register_signed"},
     "Ask the company custodian to preserve the V-03 issue and return register, including entries and amendments dated {date} from 21:45 to 22:45 IST."),
    ("dhaba_cctv", "Sharma Dhaba CCTV", (2, 2, 2, 2),
     {"arrival", "personal_copy", "personal_logon"},
     "Ask the proprietor to preserve original entrance CCTV for {date} from 22:00 to 22:40 IST and document the recording system clock."),
    ("telecom_location", "Telecom location records", (3, 1, 3, 0),
     {"personal_copy", "personal_logon"},
     "Draft for authorised review under BNSS section 94. Preserve relevant records for the verified subscriber identifier [insert after verification] for {date} from 21:45 to 22:45 IST."),
    ("pc_password", "PC-14 password-change history", (1, 2, 1, 0),
     {"password_shared"},
     "Ask IT to preserve password-change and account-access metadata for PC-14 for {date}. Omit credential values."),
    ("aman_bank", "Aman's bank statement", (1, 1, 3, 0),
     {"repayment"},
     "Request preservation of the transaction record for the specified counterparties for the day after {date}, pending confirmation of the transaction identifier."),
]


def rank_requests(case_id, case_date, claims):
    result = []
    for key, title, factors, actions, template in CATALOGUE:
        ids = [c["id"] for c in claims if c["action"] in actions and c["finding"]
               and c["finding"]["verdict"] != "supported"]
        if ids:
            dispute, feasibility, privacy, urgency = factors
            result.append(dict(catalogue_id=key, title=title,
                               score=2 * dispute + feasibility - privacy + urgency,
                               score_parts=dict(D=dispute, F=feasibility, P=privacy, U=urgency), claim_ids=ids,
                               draft_text=f"Synthetic draft for {case_id}. {template.format(date=case_date)} "
                                          f"Relevant claims: {', '.join(ids)}."))
    return sorted(result, key=lambda request: -request["score"])
