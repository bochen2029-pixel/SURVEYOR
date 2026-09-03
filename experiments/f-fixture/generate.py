#!/usr/bin/env python3
"""experiments/f-fixture/generate.py - the synthetic OPO world for F-FIXTURE (arm A).

Seeded, stdlib-only. Emits records in the floor/FIELDS.md vocabulary:
  - donor cases: organ, tissue, or both; brain-dead or DCD; completed or an in-progress
    snapshot (late events absent, as_of inside every open window);
  - referrals that never became donors;
  - the registers the revision/release/CAPA families read (contracts, standards, risks,
    QAPI plan, CAPA rows, reports, controlled documents, check definitions).
A CLEAN record is authored to satisfy every check that applies to it. A PLANT is a fresh
clean record with exactly one authored nonconformity; the check that must catch it, and
the verdict it must return, are the ground truth the generator owns and the floor never
sees. Every plant is built by a named function in PLANTS - one per catalog check.

Timeline law of this world: for a brain-dead donor, death is declared long before the
circulation stops; the tissue refrigeration clocks run from ASYSTOLE (cross-clamp), so
every donor record carries both death.declared_ts and death.asystole_ts.

CLI: python experiments/f-fixture/generate.py [--seed S] [--cases N] [--plants K] [--out corpus.jsonl]
Corpus line: {"corpus_id", "kind", "variant", "clean": bool, "plants": [{"check","expect","how"}], "record": {...}}
"""
from __future__ import annotations

import argparse
import copy
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "floor"))

ORGAN_CODES = ["KI-L", "KI-R", "LU-L", "LU-R", "LI", "HR", "PA", "IN"]
TISSUE_TOKENS = ["bone", "skin", "tendon", "heart_valve", "vein", "fascia"]
TISSUE_TERM = {"bone": "Musculoskeletal tissue for transplant", "tendon": "Musculoskeletal tissue for transplant",
               "fascia": "Musculoskeletal tissue for transplant", "skin": "Skin for transplant",
               "heart_valve": "Cardiovascular tissue for transplant", "vein": "Cardiovascular tissue for transplant"}
CONTROLLED_VOCAB = ["Musculoskeletal tissue for transplant", "Musculoskeletal tissue for research",
                    "Skin for transplant", "Skin for research", "Cardiovascular tissue for transplant"]
PARAPHRASES = ["bone for research", "MSK for transplant", "skin grafts", "heart valves"]
SITES = ["L-forearm-abrasion", "R-knee-scar", "chest-incision", "L-antecubital-puncture", "back-tattoo",
         "R-forearm-bruise", "abdomen-surgical-scar", "L-shin-laceration"]
CENTERS = [f"TXC-{i:02d}" for i in range(1, 21)]
PROCESSORS = ["PRC-A", "PRC-B", "PRC-C", "PRC-D"]
DECLINE_CODES = ["DR-810", "DR-830", "DR-841", "DR-921", "DR-930"]
DISQUALIFYING = {"DR-921", "DR-930"}
FORMS = {"FRM-DRE-02": "REV-05", "FRM-AUTH-01": "REV-11", "FRM-RECOV-07": "REV-03", "FRM-FLOW-01": "REV-08"}
ROLES_NEEDING_COMPETENCY = ["tissue_recovery_technician", "organ_recovery_coordinator", "family_services_coordinator"]


def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def month_end(dt: datetime) -> datetime:
    y, m = (dt.year + 1, 1) if dt.month == 12 else (dt.year, dt.month + 1)
    return datetime(y, m, 1, tzinfo=timezone.utc) - timedelta(seconds=1)


class World:
    """Vocabulary pools and id counters; every random choice goes through self.r."""

    def __init__(self, seed: int):
        self.r = random.Random(seed)
        self.seed = seed
        self.n = {"OD": 0, "TD": 0, "RF": 0, "REG": 0, "P": 0, "C": 0}
        self.opo_staff = [f"STF-{i:03d}" for i in range(1, 81)]
        self.surgeons = [f"STF-{i:03d}" for i in range(301, 321)]
        self.lab_staff = [f"STF-{i:03d}" for i in range(201, 216)]
        self.hospital_clinicians = [f"HCL-{i:03d}" for i in range(1, 41)]

    def next(self, prefix: str) -> str:
        self.n[prefix] += 1
        return f"{prefix}-2026-{self.n[prefix]:04d}"

    def minutes(self, lo: int, hi: int) -> timedelta:
        return timedelta(minutes=self.r.randint(lo, hi))

    def hours(self, lo: float, hi: float) -> timedelta:
        return timedelta(minutes=self.r.randint(int(lo * 60), int(hi * 60)))

    def days(self, lo: int, hi: int) -> timedelta:
        return timedelta(minutes=self.r.randint(lo * 1440, hi * 1440))

    def pick(self, xs, k=1):
        return self.r.sample(xs, k)

    def business_days_after(self, dt: datetime, n: int) -> datetime:
        """A time on the n-th weekday after dt's date, during the working day."""
        d = dt.date()
        k = 0
        while k < n:
            d += timedelta(days=1)
            if d.weekday() < 5:
                k += 1
        return datetime(d.year, d.month, d.day, self.r.randint(8, 16), self.r.randint(0, 59), tzinfo=timezone.utc)

    def base_time(self) -> datetime:
        start = datetime(2026, 1, 5, tzinfo=timezone.utc)
        return start + timedelta(minutes=self.r.randint(0, 227 * 1440))


# ---------------------------------------------------------------- donor cases
def make_donor_case(w: World, variant: str = "both", donor_type: str | None = None, snapshot: bool = False) -> dict:
    """variant: organ | tissue | both. donor_type: brain_dead | dcd (tissue-only donors are 'tissue')."""
    r = w.r
    if variant == "tissue":
        donor_type = "tissue"
    elif donor_type is None:
        donor_type = "brain_dead" if r.random() < 0.7 else "dcd"
    T = w.base_time()                                   # the referral
    case_id = w.next("OD" if variant != "tissue" else "TD")
    donor_id = f"DN-{case_id[3:]}"
    name = f"SYNTH-NAME-{case_id[-4:]}"
    dob = f"19{r.randint(40, 99):02d}-{r.randint(1, 12):02d}-{r.randint(1, 28):02d}"
    age_months = (2026 - int(dob[:4])) * 12
    rec: dict = {"case_id": case_id, "donor_type": donor_type,
                 "chart": {"donor_id": donor_id, "donor_name": name, "donor_dob": dob},
                 "donor": {"age_months": age_months, "breastfed_within_12_months": "no"}}

    # -- referral, onsite, authorization
    rec["referral"] = {"received_ts": iso(T), "dispatched_ts": iso(T + w.minutes(3, 15)), "hospital_ref": f"HOSP-{r.randint(1, 30):02d}"}
    rec["onsite"] = {"arrived_ts": iso(T + w.minutes(20, 85))}
    signed = T + w.hours(3, 10)
    method = "phone" if r.random() < 0.3 else "in_person"
    organs_authorized = sorted(w.pick(ORGAN_CODES, r.randint(2, 6)))
    tissue_tokens = sorted(w.pick(TISSUE_TOKENS, r.randint(2, 4)))
    categories = sorted({TISSUE_TERM[t] for t in tissue_tokens})
    auth = {"required_fields": ["authorizing_party_relationship", "method", "witness_affiliation", "organs_authorized", "signed_ts"],
            "authorizing_party_relationship": r.choice(["spouse", "adult_child", "parent", "sibling", "registry"]),
            "method": method, "witness_affiliation": "hospital_care_team",
            "witness_role": r.choice(["bedside_nurse", "charge_nurse", "chaplain"]),
            "organs_authorized": organs_authorized, "signed_ts": iso(signed),
            "donor_name": name, "donor_dob": dob, "categories": categories, "tissues_authorized": tissue_tokens}
    if method == "phone":
        auth["recording_ref"] = f"REC-{case_id[-4:]}-{r.randint(100, 999)}"
    rec["authorization"] = auth
    rec["controlled_vocabulary"] = {"authorized_categories": list(CONTROLLED_VOCAB)}
    rec["document_of_gift"] = {"donor_name": name, "donor_dob": dob}
    branches = []
    for q in range(r.randint(2, 5)):
        ans = "yes" if r.random() < 0.4 else "no"
        kids = [{"id": f"Q{10 + q}{c}", "answer": (r.choice(["2024-11", "outpatient", "none", "unknown"]) if ans == "yes" else "")}
                for c in "ab"[: r.randint(1, 2)]]
        branches.append({"parent_id": f"Q{10 + q}", "parent_answer": ans, "children": kids})
    rec["dre"] = {"donor_name": name, "donor_dob": dob, "subjects": ["donor"], "branches": branches}

    # -- identity and verification
    band = f"DB-{r.randint(400000, 499999)}"
    rec["donor_band"] = {"number": band}
    rec["recovery_paperwork"] = {"donor_band_number": band, "page_count": r.randint(4, 9)}
    roster = w.pick(w.opo_staff, 4)
    rec["team_worksheet"] = {"roster": roster}
    rec["donor_verification"] = {"identifiers": ["name", "dob"] + (["mrn"] if r.random() < 0.5 else []),
                                 "sources": ["bedside_nurse", "hospital_wristband", "donor_band"],
                                 "verified_by": roster[:2], "verified_ts": iso(T + w.minutes(90, 240))}
    sites = w.pick(SITES, r.randint(0, 3))
    rec["body_diagram"] = {"sites": sorted(sites)}
    rec["narrative"] = {"sites": sorted(sites, reverse=True), "text_ref": f"NOTE-{r.randint(4000, 4999)}"}
    inj = [{"site": s, "classification": r.choice(["medical", "non_medical"])} for s in w.pick(SITES, r.randint(0, 2))]
    rec["physical_assessment"] = {"injection_sites": inj, "injection_sites_assessed": "yes"}

    # -- blood: two ABO determinations, serology, hemodilution
    det1 = signed + w.minutes(30, 120)
    det2 = det1 + w.minutes(20, 240)
    abo_type = r.choice(["O", "O", "A", "A", "B", "AB"])
    abo = {"type": abo_type, "draw_ts": iso(det1),
           "determination_1": {"draw_ts": iso(det1), "result": abo_type},
           "determination_2": {"draw_ts": iso(det2), "result": abo_type}}
    if abo_type in ("A", "AB"):
        if r.random() < 0.8:
            abo["subtype"] = r.choice(["A1", "A2", "A1B", "A2B"])
        else:
            abo["subtype_reason_code"] = "SUBTYPE-NOT-USED-FOR-ALLOCATION"
    rec["abo"] = abo
    draw = det1 + w.minutes(0, 30)
    lab_ref = f"LAB-{r.randint(70000, 79999)}"
    rec["serology"] = {"draw_ts": iso(draw), "result_ref": lab_ref,
                       "source": "reused_from_organ_case" if variant == "both" else ("tissue_case_draw" if variant == "tissue" else "organ_case_draw"),
                       "resulted_ts": iso(draw + w.hours(6, 30))}
    rec["serology_report"] = {"donor_id": donor_id, "donor_dob": dob, "draw_ts": iso(draw), "lab_ref": lab_ref}
    if r.random() < 0.08:
        reactive = draw + w.hours(6, 24)
        rec["serology"]["reactive_marker"] = r.choice(["HIV-1/2 Ab", "HCV Ab", "HBsAg", "HCV RNA"])
        rec["serology"]["reactive_result_ts"] = iso(reactive)
        rec["serology"]["confirmatory_result_ts"] = iso(reactive + w.hours(8, 30))
        rec["county_epidemiology"] = {"notified_ts": iso(reactive + w.hours(1, 23)), "channel": "fax"}
    logged_bp, logged_cr = [], []
    for i in range(r.randint(0, 3)):
        logged_bp.append({"ref": f"BP-{i + 1}", "ts": iso(draw - w.hours(0.1, 72)), "volume_ml": r.choice([250, 300, 350])})
    for i in range(r.randint(0, 3)):
        logged_cr.append({"ref": f"CR-{i + 1}", "ts": iso(draw - w.minutes(2, 180)), "volume_ml": r.choice([250, 500, 1000])})
    calc_bp = [e for e in logged_bp if 0 <= (draw - parse(e["ts"])).total_seconds() / 60 <= 48 * 60]
    calc_cr = [e for e in logged_cr if 0 <= (draw - parse(e["ts"])).total_seconds() / 60 <= 60]
    rec["hemodilution"] = {"sample_draw_ts": iso(draw),
                           "logged": {"blood_products": logged_bp, "blood_product_refs": [e["ref"] for e in logged_bp],
                                      "crystalloids": logged_cr, "crystalloid_refs": [e["ref"] for e in logged_cr]},
                           "calc": {"blood_products": copy.deepcopy(calc_bp), "blood_product_refs": [e["ref"] for e in calc_bp],
                                    "blood_products_ml": sum(e["volume_ml"] for e in calc_bp),
                                    "crystalloids": copy.deepcopy(calc_cr), "crystalloid_refs": [e["ref"] for e in calc_cr],
                                    "crystalloids_ml": sum(e["volume_ml"] for e in calc_cr)}}

    # -- the record system: edits, entries, forms, competencies, corrections
    coord = r.choice(w.opo_staff)
    rec["edit"] = ({"class": "routine", "field": "vitals.hr", "ts": iso(T + w.hours(4, 30))} if r.random() < 0.8 else
                   {"class": r.choice(["post_completion", "late_signature", "second_signature"]), "field": "medications.list",
                    "ts": iso(T + w.days(3, 6)), "case_note_ref": f"NOTE-{r.randint(5000, 5999)}"})
    rec["edits"] = [{"field": f, "editor_id": s, "session_actor_id": s, "ts": iso(T + w.hours(2, 40))}
                    for f, s in zip(["vitals.hr", "vitals.map", "medications.list"][: r.randint(1, 3)], w.pick(w.opo_staff, 3))]
    signoff = T + w.hours(30, 60)
    documented = T + w.hours(2, 20)
    rec["entry"] = {"field": "vitals.hr", "documented_ts": iso(documented), "entered_ts": iso(documented + w.minutes(1, 90))}
    rec["signoff"] = {"ts": iso(signoff), "signed_by": coord}
    form_id = r.choice(list(FORMS))
    rec["form"] = {"document_id": form_id, "revision_used": FORMS[form_id], "used_ts": iso(T + w.hours(1, 20))}
    rec["document_control"] = {"current_revision_at_use": dict(FORMS)}
    actor = r.choice(w.opo_staff)
    role = r.choice(ROLES_NEEDING_COMPETENCY)
    act_ts = T + w.hours(2, 40)
    rec["action"] = {"kind": role.replace("_coordinator", "").replace("_technician", ""), "role": role, "performed_by": actor, "ts": iso(act_ts)}
    rec["competencies"] = {actor: {role: {"granted_ts": iso(act_ts - w.days(30, 300)), "expires_ts": iso(act_ts + w.days(10, 300))}}}
    rec["corrections"] = [{"field": r.choice(["vitals.temp", "recovery.start_ts", "medications.dose"]), "method": "single_line_through",
                           "initialed_by": r.choice(w.opo_staff), "dated": iso(T + w.hours(3, 30))[:10]} for _ in range(r.randint(0, 2))]

    # -- the death, the OR, the organs (organ donors)
    if variant in ("organ", "both"):
        alloc_start = signed + w.hours(1, 6)
        organs_recovered = sorted(w.pick(organs_authorized, r.randint(1, len(organs_authorized))))
        n_off = r.randint(2, 8)
        t = alloc_start
        offers = []
        for i in range(n_off):
            t = t + w.minutes(5, 29) if i else t
            offers.append({"offer_ref": f"OF-{case_id[-4:]}{i + 1:02d}", "center_id": r.choice(CENTERS), "sent_ts": iso(t),
                           "center_bypassed": "no", "primary_list_exhausted_at_send": "no"})
        latest = t
        closed = latest + w.minutes(1, 29)
        declines = []
        for o in offers[:-1]:
            if r.random() < 0.5:
                code = r.choice(DECLINE_CODES)
                declines.append({"center_id": o["center_id"], "reason_code": code,
                                 "classification": "disqualifying" if code in DISQUALIFYING else "non_disqualifying",
                                 "list_status": "removed" if code in DISQUALIFYING else "active"})
        rec["allocation"] = {"organs": organs_recovered, "start_ts": iso(alloc_start), "offers": offers,
                             "latest_offer_ts": iso(latest), "closed_ts": iso(closed), "declines": declines}
        if r.random() < 0.05:
            rec["allocation"]["unstable_donor_exception_ref"] = f"NOTE-{r.randint(6000, 6999)}"
        rec["organ_id"] = organs_recovered[0]
        rec["offer_ref"] = offers[-1]["offer_ref"]
        rec["active_primary_offers"] = {o: [f"OF-{case_id[-4:]}P{i + 1}"] for i, o in enumerate(organs_recovered)}
        screen = w.pick(CENTERS, 2)
        rec["perfusion_screening"] = {"centers": screen}
        rec["match_run"] = {"id": f"MR-{r.randint(80000, 89999)}", "centers": sorted(set(screen + w.pick(CENTERS, 4)))}
        prep = closed + w.hours(4, 12)
        incision = prep + w.minutes(10, 70)
        clamp = incision + w.minutes(60, 180)
        organ_recovery = clamp + w.minutes(20, 90)
        rec["or_timeline"] = {"prep_complete_ts": iso(prep), "draping_ts": iso(prep + w.minutes(5, 9)), "incision_ts": iso(incision)}
        rec["recovery"] = {"cross_clamp_ts": iso(clamp), "organ_recovery_ts": iso(organ_recovery),
                           "end_ts": iso(organ_recovery + w.minutes(30, 120)), "organs": organs_recovered}
        if donor_type == "brain_dead":
            declared, asystole = T + w.hours(1, 12), clamp
        else:
            declared = prep - w.minutes(30, 90)
            asystole = declared
        rec["death"] = {"declared_ts": iso(declared), "asystole_ts": iso(asystole)}
        surgeons = w.pick(w.surgeons, r.randint(1, 2))
        roles = ["circulator", "coordinator"] + ["recovery_surgeon"] * len(surgeons)
        if donor_type == "brain_dead" or r.random() < 0.5:
            roles.insert(0, "anesthesiologist")
        rec["or_roster"] = {"roles": roles, "recovering_physicians": surgeons, "physician_signatures": list(surgeons)}
        rec["declaration"] = {"pronouncing_clinician": r.choice(w.hospital_clinicians)}
        rec["hla_abo"] = {"coordinator_signatures": w.pick(w.opo_staff, 2), "lab_signature": r.choice(w.lab_staff), "status": "complete"}
        covid_collected = clamp - w.hours(2, 70)
        rec["covid"] = {"collected_ts": iso(covid_collected), "resulted_ts": iso(covid_collected + w.hours(4, 12)), "result": "negative"}
        if "LU-L" in organs_recovered or "LU-R" in organs_recovered:
            rec["covid"]["lower_respiratory_specimen_ref"] = f"SPEC-BAL-{r.randint(2000, 2999)}"
        if "LI" in organs_recovered:
            inr_c = alloc_start - w.hours(1, 11)
            rec["labs"] = {"inr": {"collected_ts": iso(inr_c), "resulted_ts": iso(inr_c + w.minutes(60, 180)), "value": round(r.uniform(0.9, 1.8), 1)}}
        else:
            rec["labs"] = {}
        specs = [f"SPL-{i:02d}" for i in range(1, r.randint(1, 4))]
        rec["research_tab"] = {"specimens": specs}
        rec["or_summary"] = {"research_specimens": list(reversed(specs))}
        rec["organs"] = [{"organ_id": o, "organ_page_disposition": d, "summary_page_disposition": d}
                         for o in organs_recovered for d in [r.choice(["transplanted", "transplanted", "recovered_not_transplanted"])]]
        segs = []
        t0 = alloc_start.replace(minute=0, second=0)
        for i in range(r.randint(2, 4)):
            s = t0 + timedelta(hours=i)
            segs.append({"start_ts": iso(s), "end_ts": iso(s + timedelta(minutes=59)),
                         "vitals": [{"name": "hr", "value": r.randint(60, 110)}, {"name": "map", "value": r.randint(60, 95)},
                                    {"name": "urine_ml", "value": r.choice([0, 20, 40, 80])}]})
        rec["flow_sheet"] = {"vitals_per_segment": 3, "segments": segs}
        results = [f"SER-{i}" for i in range(1, r.randint(2, 4))]
        rec["shared_case"] = {"id": case_id, "results": results,
                              "processors": [{"processor_id": p, "results_received": list(results)} for p in w.pick(PROCESSORS, 2)]}
        feedback = w.business_days_after(organ_recovery, r.randint(1, 5))
        rec["feedback"] = {"submitted_ts": iso(feedback)}
        rec["ddr"] = {"submitted_ts": iso(feedback + w.days(5, 29))}
        if r.random() < 0.10:
            info = organ_recovery + w.days(1, 10)
            rec["disease_transmission"] = {"info_received_ts": iso(info), "confirmed_ts": iso(info + w.hours(2, 30)),
                                           "notified_ts": iso(info + w.hours(1, 23)), "notified_to": ["optn_patient_safety", "accepting_programs"]}
        recovery_end_for_tissue = organ_recovery + w.hours(1, 3)
    else:
        declared = T - w.minutes(30, 180)
        asystole = declared
        rec["death"] = {"declared_ts": iso(declared), "asystole_ts": iso(asystole)}
        rec["recovery"] = {}
        recovery_end_for_tissue = None

    # -- the tissue recovery (tissue donors)
    if variant in ("tissue", "both"):
        branch = r.random()
        if branch < 0.90:                                   # cooled within 12h -> 24h rule
            cooling = asystole + w.minutes(60, 600)
            start = asystole + w.minutes(int((cooling - asystole).total_seconds() // 60) + 60, 23 * 60)
            rec["cooling"] = {"initial_ts": iso(cooling)}
            outs = [{"out_ts": iso(asystole), "in_ts": iso(cooling)}, {"out_ts": iso(start - w.minutes(30, 80)), "in_ts": iso(start)}]
        elif branch < 0.97:                                 # cooled after 12h -> 15h rule
            cooling = asystole + w.minutes(721, 780)
            start = asystole + w.minutes(int((cooling - asystole).total_seconds() // 60) + 30, 15 * 60 - 10)
            rec["cooling"] = {"initial_ts": iso(cooling)}
            outs = [{"out_ts": iso(asystole), "in_ts": iso(cooling)}, {"out_ts": iso(start - w.minutes(10, 40)), "in_ts": iso(start)}]
        else:                                               # never cooled -> 15h rule
            start = asystole + w.minutes(120, 14 * 60)
            rec["cooling"] = {}
            outs = [{"out_ts": iso(asystole), "in_ts": iso(start)}]
        if variant == "both" and recovery_end_for_tissue is not None and start < recovery_end_for_tissue:
            start = recovery_end_for_tissue + w.minutes(10, 60)   # tissue after the organs leave; still within the rule by construction of the 24h branch
        rec["refrigeration"] = {"out_intervals": outs}
        end = start + w.hours(3, 6)
        rec["recovery"].update({"start_ts": iso(start), "end_ts": iso(end),
                                "tissues_recovered": sorted(w.pick(tissue_tokens, r.randint(1, len(tissue_tokens))))})
        items, seq = [], 0
        for tk in rec["recovery"]["tissues_recovered"]:
            seq += 1
            items.append({"seq": seq, "tissue": f"{tk}_left"})
        pairs = []
        if r.random() < 0.3:
            seq += 1
            items += [{"seq": seq, "tissue": "tibia_left"}, {"seq": seq, "tissue": "fibula_left"}]
            pairs.append(seq)
        rec["recovery"]["items"] = items
        rec["recovery"]["paired_sequence_numbers"] = pairs
        pstart = start + w.minutes(10, 40)
        rec["prep"] = {"start_ts": iso(pstart)}
        rec["inspection"] = {"pre_inspection_ts": iso(pstart - w.minutes(5, 60))}
        rec["tissue"] = {"category": "fresh" if r.random() < 0.15 else "standard"}
        rec["release"] = {"contamination_pct": 0, "required_document_count": 4,
                          "required_documents": [{"name": n, "status": "complete"} for n in ("dre", "serology_panel", "recovery_record", "physical_assessment")]}
        chart_sent = end + (w.days(3, 9) if rec["tissue"]["category"] == "fresh" else w.days(5, 28))
        rec["chart"]["sent_to_processor_ts"] = iso(chart_sent)
    else:
        end = parse(rec["recovery"]["end_ts"])
    rec["audit"] = {"started_ts": iso(end + w.days(1, 6))}
    rec["dnr"] = {"submitted_ts": iso(month_end(T) + w.days(1, 29))}

    # -- the evaluation instant
    latest_ts = max(parse(v) for v in _all_ts(rec))
    rec["as_of"] = iso(latest_ts + w.days(1, 30))
    if snapshot:
        _snapshot(rec, end + timedelta(days=2))
    return rec


def _all_ts(obj) -> list[str]:
    out = []
    if isinstance(obj, dict):
        for v in obj.values():
            out += _all_ts(v)
    elif isinstance(obj, list):
        for v in obj:
            out += _all_ts(v)
    elif isinstance(obj, str) and len(obj) == 20 and obj.endswith("Z") and obj[4] == "-" and obj[10] == "T":
        out.append(obj)
    return out


def _snapshot(rec: dict, as_of: datetime) -> None:
    """An in-progress case: the late events have not happened; as_of sits inside every open window."""
    rec["as_of"] = iso(as_of)
    rec["audit"] = {}
    rec["chart"].pop("sent_to_processor_ts", None)
    rec.pop("feedback", None)
    rec.pop("ddr", None)
    rec["dnr"] = {}
    rec.pop("disease_transmission", None)


# ---------------------------------------------------------------- referrals and registers
def make_referral(w: World) -> dict:
    T = w.base_time()
    rec = {"case_id": w.next("RF"), "referral": {"received_ts": iso(T), "dispatched_ts": iso(T + w.minutes(3, 15)), "hospital_ref": f"HOSP-{w.r.randint(1, 30):02d}"},
           "onsite": {"arrived_ts": iso(T + w.minutes(20, 85))}, "dnr": {"submitted_ts": iso(month_end(T) + w.days(1, 29))}}
    rec["as_of"] = iso(month_end(T) + timedelta(days=35))
    return rec


def make_contracts(w: World) -> dict:
    as_of = w.base_time()
    cs = []
    for i in range(w.r.randint(2, 5)):
        c = {"id": f"CT-{w.r.randint(10, 99)}", "vendor_class": w.r.choice(["records-system", "courier", "lab", "document-control"])}
        if w.r.random() < 0.6:
            c["notice_deadline_ts"] = iso(as_of + w.days(121, 400))
        else:
            c["notice_deadline_ts"] = iso(as_of + w.days(1, 119))
            c["decision_ref"] = f"DEC-2026-{w.r.randint(1, 40):02d}"
        cs.append(c)
    return {"register_id": "CONTRACTS-2026", "contracts": cs, "as_of": iso(as_of)}


def make_standards(w: World) -> dict:
    as_of = w.base_time()
    ss = []
    for i in range(w.r.randint(1, 3)):
        s = {"id": f"STD-{'ABC'[i]}", "adopted_edition": f"ed-{w.r.randint(3, 16)}"}
        roll = w.r.random()
        if roll < 0.4:
            s["next_edition"] = s["adopted_edition"] + "-next"
            s["next_edition_effective_ts"] = iso(as_of + w.days(91, 400))
        elif roll < 0.6:
            s["next_edition"] = s["adopted_edition"]
            s["next_edition_effective_ts"] = iso(as_of + w.days(1, 89))
        ss.append(s)
    return {"register_id": "STANDARDS-2026", "standards": ss, "as_of": iso(as_of)}


def make_risk(w: World) -> dict:
    pr = w.r.randint(1, 20)
    rk = {"id": f"RSK-{w.r.randint(1, 140):03d}", "priority": pr}
    if pr >= 12:
        rk["owner_role"] = w.r.choice(["director_of_operations", "quality_manager", "it_director"])
        rk["review_ts"] = iso(w.base_time() + w.days(30, 200))
    return {"risk_register": {"id": "RR-2026", "owner_required_at_priority": 12}, "risk": rk}


def make_qapi(w: World) -> dict:
    as_of = w.base_time()
    last = as_of - w.days(30, 360)
    rec = {"qapi": {"plan_revision": "2026-A", "last_board_presentation_ts": iso(last), "plan_revised_ts": iso(last + w.days(1, 20))}, "as_of": iso(as_of)}
    if w.r.random() < 0.5:
        rec["qapi"]["next_board_presentation_ts"] = iso(last + w.days(200, 366))
    return rec


def make_capa(w: World) -> dict:
    as_of = w.base_time()
    horizon = as_of + w.days(-120, 200)
    capa = {"id": f"CAPA-2026-{w.r.randint(1, 60):03d}", "variance_class": w.r.choice(["documentation", "process", "equipment"]),
            "owner_role": "quality_manager",
            "expectation": {"metric": "late_feedback_forms_per_100_cases", "baseline": 6, "target": 2, "horizon_ts": iso(horizon)},
            "expires": iso(horizon + timedelta(days=365)), "inverse": "retire_training_module_and_restore_prior_form", "status": "open"}
    if horizon <= as_of:
        if w.r.random() < 0.7:
            capa["status"] = "sustained"
            capa["effectiveness"] = {"result": "met", "observed": 1, "data_ref": "FOLD-2026-07-LINE-OF-SIGHT"}
        else:
            capa["status"] = "returned_to_committee"
            capa["effectiveness"] = {"result": "unmet", "observed": 5, "data_ref": "FOLD-2026-07-LINE-OF-SIGHT"}
    return {"capa": capa, "as_of": iso(as_of)}


def make_report(w: World) -> dict:
    metrics = [{"family": "tissue_donors", "variant": "tissue_donor", "value": w.r.randint(40, 90), "section": 3}]
    if w.r.random() < 0.6:
        metrics += [{"family": "organ_donors", "variant": "organ_donor", "value": 41, "denominator": "donors from whom at least one organ was recovered", "section": 2},
                    {"family": "organ_donors", "variant": "cms_organ_donor", "value": 38, "denominator": "CMS-defined organ donors (external death-record denominator, imported)", "section": 9}]
    else:
        metrics += [{"family": "organ_donors", "variant": "organ_donor", "value": 41, "section": 2}]
    return {"report": {"id": f"RPT-2026-{w.r.randint(1, 12):02d}-{w.r.choice(['LINE-OF-SIGHT', 'BOARD', 'TOWNHALL'])}", "metrics": metrics}}


def make_document(w: World) -> dict:
    req = ["quality_director", "medical_director"]
    if w.r.random() < 0.6:
        return {"document": {"id": f"SOP-QA-{w.r.randint(1, 60):03d}", "status": "effective", "required_approval_roles": req, "approved_roles": req + ["ceo"]}}
    return {"document": {"id": f"SOP-QA-{w.r.randint(1, 60):03d}", "status": "draft", "required_approval_roles": req, "approved_roles": req[: w.r.randint(0, 2)]}}


def make_check_definition(w: World) -> dict:
    return {"check": {"id": f"SITE-CHECK-{w.r.randint(1, 40):02d}", "corrects_field": "contact.phone",
                      "verification_fields": ["contact.email_verified", "identity.document_ref"]}}


REGISTERS = {"contracts": make_contracts, "standards": make_standards, "risk": make_risk, "qapi": make_qapi,
             "capa": make_capa, "report": make_report, "document": make_document, "check_definition": make_check_definition}


# ---------------------------------------------------------------- the plants
def _shift(rec: dict, path: str, delta: timedelta) -> None:
    obj, parts = rec, path.split(".")
    for p in parts[:-1]:
        obj = obj[p]
    obj[parts[-1]] = iso(parse(obj[parts[-1]]) + delta)


def _set(rec: dict, path: str, value) -> None:
    obj, parts = rec, path.split(".")
    for p in parts[:-1]:
        obj = obj.setdefault(p, {})
    obj[parts[-1]] = value


def _get(rec: dict, path: str):
    obj = rec
    for p in path.split("."):
        obj = obj[p]
    return obj


def _ensure_liver(w, rec):
    if "LI" not in rec["allocation"]["organs"]:
        rec["allocation"]["organs"].append("LI")
    inr_c = parse(rec["allocation"]["start_ts"]) - w.hours(1, 11)
    rec["labs"] = {"inr": {"collected_ts": iso(inr_c), "resulted_ts": iso(inr_c + w.minutes(60, 180)), "value": 1.3}}


def _ensure_event(w, rec):
    if "disease_transmission" not in rec:
        info = parse(rec["recovery"]["organ_recovery_ts"]) + w.days(1, 10)
        rec["disease_transmission"] = {"info_received_ts": iso(info), "confirmed_ts": iso(info + w.hours(2, 30)),
                                       "notified_ts": iso(info + w.hours(1, 23)), "notified_to": ["optn_patient_safety"]}
        rec["as_of"] = iso(max(parse(rec["as_of"]), info + timedelta(days=40)))


def _ensure_reactive(w, rec):
    if "reactive_result_ts" not in rec["serology"]:
        reactive = parse(rec["serology"]["draw_ts"]) + w.hours(6, 24)
        rec["serology"]["reactive_marker"] = "HCV Ab"
        rec["serology"]["reactive_result_ts"] = iso(reactive)
        rec["county_epidemiology"] = {"notified_ts": iso(reactive + w.hours(1, 23)), "channel": "fax"}


def _yes_branch(w, rec):
    for b in rec["dre"]["branches"]:
        if b["parent_answer"] == "yes":
            return b
    b = rec["dre"]["branches"][0]
    b["parent_answer"] = "yes"
    for c in b["children"]:
        c["answer"] = "2024-11"
    return b


# each entry: check id -> (record kind, function(w, rec) -> how). The function mutates rec in
# place into a record the named check must catch with its declared action.
PLANTS = {
    "SV-001": ("donor", lambda w, r: (_set(r, "dre.donor_dob", r["chart"]["donor_dob"][:-2] + ("21" if r["chart"]["donor_dob"].endswith("12") else "12")), "DOB transposed on the DRE")[1]),
    "SV-002": ("donor", lambda w, r: (_set(r, "serology_report.donor_id", "DN-2026-0391"), "serology report filed to another donor")[1]),
    "SV-003": ("donor", lambda w, r: (_set(r, "recovery_paperwork.donor_band_number", r["donor_band"]["number"][:-1] + ("1" if r["donor_band"]["number"].endswith("0") else "0")), "band number off by one digit on the paperwork")[1]),
    "SV-004": ("donor", lambda w, r: (_set(r, "donor_verification.identifiers", ["name", "name"]), "the same identifier twice")[1]),
    "SV-005": ("donor", lambda w, r: (r["body_diagram"]["sites"].append("L-shin-laceration-extra"), "a diagram site the narrative never mentions")[1]),
    "SV-010": ("donor", lambda w, r: (_set(r, "hla_abo.coordinator_signatures", [r["hla_abo"]["coordinator_signatures"][0]] * 2), "one coordinator signed twice")[1]),
    "SV-011": ("donor", lambda w, r: (_set(r, "donor_verification.verified_by", [r["team_worksheet"]["roster"][0], "STF-999"]), "a verifier not on the roster")[1]),
    "SV-012": ("donor", lambda w, r: (_set(r, "declaration.pronouncing_clinician", r["or_roster"]["recovering_physicians"][0]), "the declaring clinician is on the recovery team")[1]),
    "SV-013": ("donor", lambda w, r: (_set(r, "edit", {"class": "late_signature", "field": "consent.signature_2", "ts": r["edit"]["ts"]}), "a late signature without a case note")[1]),
    "SV-014": ("donor", lambda w, r: (_set(r, "edits", [{**r["edits"][0], "editor_id": "STF-001", "session_actor_id": "STF-002"}]), "attribution frozen to another editor")[1]),
    "SV-015": ("donor", lambda w, r: (_set(r, "authorization.witness_affiliation", "recovering_organization"), "witnessed by the recovering organization")[1]),
    "SV-020": ("donor", lambda w, r: (_set(r, "audit.started_ts", iso(parse(r["recovery"]["end_ts"]) + w.days(8, 20))), "audit started after day 7")[1]),
    "SV-021": ("donor", lambda w, r: (_set(r, "chart.sent_to_processor_ts", iso(parse(r["recovery"]["end_ts"]) + (w.days(11, 20) if r["tissue"]["category"] == "fresh" else w.days(31, 60)))), "chart sent past the processor window")[1]),
    "SV-022": ("donor", lambda w, r: (_ensure_event(w, r), _set(r, "disease_transmission.notified_ts", iso(parse(r["disease_transmission"]["info_received_ts"]) + w.hours(25, 72))), "reported after 24h")[2]),
    "SV-023": ("donor", lambda w, r: (_ensure_reactive(w, r), _set(r, "county_epidemiology.notified_ts", iso(parse(r["serology"]["reactive_result_ts"]) + w.hours(25, 72))), "county notified after 24h")[2]),
    "SV-024": ("donor", lambda w, r: (_set(r, "covid.collected_ts", iso(parse(r["recovery"]["cross_clamp_ts"]) - w.hours(73, 120))), "specimen older than 72h at clamp")[1]),
    "SV-025": ("donor", lambda w, r: (_ensure_liver(w, r), _set(r, "labs.inr.collected_ts", iso(parse(r["allocation"]["start_ts"]) - w.hours(13, 30))), "liver offered on an INR older than 12h")[2]),
    "SV-026": ("donor", lambda w, r: (r["hemodilution"]["calc"]["blood_products"].append({"ref": "BP-99", "ts": iso(parse(r["hemodilution"]["sample_draw_ts"]) - timedelta(hours=5)), "volume_ml": 300}),
                                       r["hemodilution"]["calc"]["blood_product_refs"].append("BP-99"),
                                       _set(r, "hemodilution.calc.blood_products_ml", r["hemodilution"]["calc"]["blood_products_ml"] + 300), "a phantom unit in the calculation")[3]),
    "SV-027": ("donor", lambda w, r: (_set(r, "or_timeline.incision_ts", iso(parse(r["or_timeline"]["prep_complete_ts"]) + w.minutes(76, 150))), "incision more than 75 minutes after prep")[1]),
    "SV-028": ("donor", lambda w, r: (_set(r, "recovery.start_ts", iso(parse(r["death"]["asystole_ts"]) + w.hours(25, 30))), "tissue recovery began after 24h from asystole")[1]),
    "SV-029": ("donor", lambda w, r: (_set(r, "serology.source", "reused_from_organ_case"), _set(r, "serology.draw_ts", iso(parse(r["recovery"]["start_ts"]) - w.days(8, 12))), _set(r, "serology_report.draw_ts", r["serology"]["draw_ts"]), "reused sample drawn more than 7 days before recovery")[3]),
    "SV-030": ("donor", lambda w, r: (_set(r, "feedback.submitted_ts", iso(w.business_days_after(parse(r["recovery"]["organ_recovery_ts"]), w.r.randint(6, 10)))), "feedback after 5 business days")[1]),
    "SV-031": ("donor", lambda w, r: (_set(r, "ddr.submitted_ts", iso(parse(r["feedback"]["submitted_ts"]) + w.days(31, 50))), "DDR past the 30-day site buffer")[1]),
    "SV-032": ("donor", lambda w, r: (_set(r, "dnr.submitted_ts", iso(month_end(parse(r["referral"]["received_ts"])) + w.days(31, 45))), "DNR past 30 days after month end")[1]),
    "SV-033": ("donor", lambda w, r: (_set(r, "onsite.arrived_ts", iso(parse(r["referral"]["received_ts"]) + w.minutes(91, 180))), "onsite after 90 minutes")[1]),
    "SV-034": ("donor", lambda w, r: (r["allocation"].pop("unstable_donor_exception_ref", None), _set(r, "allocation.offers", r["allocation"]["offers"][:1] + [{**r["allocation"]["offers"][-1], "sent_ts": iso(parse(r["allocation"]["offers"][0]["sent_ts"]) + w.minutes(31, 60))}]),
                                       _set(r, "allocation.latest_offer_ts", r["allocation"]["offers"][-1]["sent_ts"]), _set(r, "allocation.closed_ts", iso(parse(r["allocation"]["offers"][-1]["sent_ts"]) + timedelta(minutes=5))), "a gap over 30 minutes between offers")[4]),
    "SV-035": ("contracts", lambda w, r: (r["contracts"].append({"id": "CT-99", "notice_deadline_ts": iso(parse(r["as_of"]) + w.days(30, 119)), "vendor_class": "courier"}), "a notice deadline inside 120 days with no decision")[1]),
    "SV-040": ("donor", lambda w, r: (_set(r, "form.revision_used", "REV-01"), "a stale form revision")[1]),
    "SV-041": ("document", lambda w, r: (_set(r, "document.status", "effective"), _set(r, "document.approved_roles", ["quality_director"]), "effective without the medical director")[2]),
    "SV-042": ("standards", lambda w, r: (r["standards"].append({"id": "STD-Z", "adopted_edition": "ed-15", "next_edition": "ed-16", "next_edition_effective_ts": iso(parse(r["as_of"]) + w.days(10, 89))}), "an unadopted edition inside the lead time")[1]),
    "SV-043": ("donor", lambda w, r: (_set(r, f"competencies.{r['action']['performed_by']}.{r['action']['role']}.expires_ts", iso(parse(r["action"]["ts"]) - w.days(1, 30))), "competency expired before the action")[1]),
    "SV-050": ("donor", lambda w, r: (_yes_branch(w, r)["children"][0].__setitem__("answer", ""), "a blank child under a yes parent")[1]),
    "SV-051": ("donor", lambda w, r: (_set(r, "corrections", r["corrections"] + [{"field": "vitals.temp", "method": "white_out", "initialed_by": "STF-014", "dated": "2026-08-18"}]), "a white-out correction")[1]),
    "SV-052": ("donor", lambda w, r: (r["authorization"]["categories"].append(w.r.choice(PARAPHRASES)), "a paraphrased category")[1]),
    "SV-053": ("donor", lambda w, r: (_set(r, "recovery.items", [{"seq": 1, "tissue": "femur_left"}, {"seq": 1, "tissue": "femur_right"}] + r["recovery"]["items"][2:]), _set(r, "recovery.paired_sequence_numbers", []), "two femurs share a sequence number")[2]),
    "SV-054": ("donor", lambda w, r: (r["recovery"]["tissues_recovered"].append(next(t for t in TISSUE_TOKENS if t not in r["authorization"]["tissues_authorized"])), "a tissue recovered that was not authorized")[1]),
    "SV-055": ("donor", lambda w, r: (_set(r, "inspection.pre_inspection_ts", iso(parse(r["prep"]["start_ts"]) + w.minutes(0, 30))), "inspection documented at or after prep")[1]),
    "SV-056": ("donor", lambda w, r: (_set(r, "entry.entered_ts", iso(parse(r["signoff"]["ts"]) + timedelta(hours=1))), _set(r, "entry.documented_ts", iso(parse(r["signoff"]["ts"]) - timedelta(hours=2))), "an entry backdated past the signoff")[2]),
    "SV-057": ("donor", lambda w, r: (_set(r, "flow_sheet.segments", [r["flow_sheet"]["segments"][0], {**r["flow_sheet"]["segments"][1], "start_ts": iso(parse(r["flow_sheet"]["segments"][1]["start_ts"]) + timedelta(minutes=3))}]), "a three-minute gap in the flow sheet")[1]),
    "SV-058": ("donor", lambda w, r: (_set(r, "donor.age_months", w.r.randint(1, 18)), _set(r, "dre.subjects", ["donor"]), "an infant with the donor interview only")[2]),
    "SV-059": ("donor", lambda w, r: (_set(r, "abo.type", "A"), r["abo"].pop("subtype", None), r["abo"].pop("subtype_reason_code", None), "type A with no subtype and no reason")[3]),
    "SV-060": ("donor", lambda w, r: (_set(r, "abo.determination_2.draw_ts", r["abo"]["determination_1"]["draw_ts"]), "both ABO determinations from one draw")[1]),
    "SV-061": ("donor", lambda w, r: (_set(r, "physical_assessment.injection_sites", [{"site": "L-antecubital", "classification": "unknown"}]), "an injection site classified unknown")[1]),
    "SV-062": ("check_definition", lambda w, r: (_set(r, "check.verification_fields", ["contact.phone"]), "verified through the field under correction")[1]),
    "SV-070": ("donor", lambda w, r: (r["active_primary_offers"][r["organ_id"]].append("OF-DUP"), "a second active primary on the organ")[1]),
    "SV-071": ("donor", lambda w, r: (_set(r, "authorization.witness_affiliation", ""), "a required authorization field left blank")[1]),
    "SV-072": ("donor", lambda w, r: (_set(r, "authorization.method", "phone"), _set(r, "authorization.recording_ref", ""), "phone authorization without its recording")[2]),
    "SV-073": ("donor", lambda w, r: (r["research_tab"]["specimens"].append("SPL-99"), "a research specimen missing from the OR summary")[1]),
    "SV-074": ("donor", lambda w, r: (r["perfusion_screening"]["centers"].append("TXC-99"), "a screening center absent from the match run")[1]),
    "SV-075": ("donor", lambda w, r: (_set(r, "allocation.declines", r["allocation"]["declines"] + [{"center_id": "TXC-03", "reason_code": "", "classification": "non_disqualifying", "list_status": "active", "free_text": "surgeon unavailable"}]), "a free-text decline with no code")[1]),
    "SV-076": ("donor", lambda w, r: (r["allocation"]["offers"].append({**r["allocation"]["offers"][-1], "offer_ref": "OF-BYP", "center_bypassed": "yes", "primary_list_exhausted_at_send": "no"}), "an offer to a bypassed center before exhaustion")[1]),
    "SV-077": ("donor", lambda w, r: (r["organs"][0].__setitem__("summary_page_disposition", "recovered_not_transplanted" if r["organs"][0]["organ_page_disposition"] == "transplanted" else "transplanted"), "dispositions disagree for one organ")[1]),
    "SV-078": ("donor", lambda w, r: (r["shared_case"]["processors"][1].__setitem__("results_received", r["shared_case"]["results"][:-1]), "a processor missing the last result")[1]),
    "SV-080": ("donor", lambda w, r: (_set(r, "release.contamination_pct", w.r.choice([2, 4, 7])), "a positive culture on released tissue")[1]),
    "SV-081": ("capa", lambda w, r: (_set(r, "capa.owner_role", ""), "a CAPA nobody owns")[1]),
    "SV-082": ("capa", lambda w, r: (_set(r, "capa.expectation.horizon_ts", iso(parse(r["as_of"]) - w.days(1, 60))), r["capa"].pop("effectiveness", None), _set(r, "capa.status", "open"), "horizon passed with no effectiveness result")[3]),
    "SV-083": ("risk", lambda w, r: (_set(r, "risk.priority", 15), _set(r, "risk.owner_role", "quality_manager"), _set(r, "risk.review_ts", ""), "a high-priority risk with no review date")[3]),
    "SV-084": ("qapi", lambda w, r: (_set(r, "qapi.last_board_presentation_ts", iso(parse(r["as_of"]) - w.days(367, 500))), r["qapi"].pop("next_board_presentation_ts", None), "more than a year since the board saw the plan")[2]),
    "SV-085": ("report", lambda w, r: (_set(r, "report.metrics", [{"family": "organ_donors", "variant": "organ_donor", "value": 41, "section": 3}, {"family": "organ_donors", "variant": "cms_organ_donor", "value": 38, "section": 9}]), "two variants, no denominators")[1]),
}


def base_for(w: World, kind: str) -> dict:
    if kind == "donor":
        return make_donor_case(w, "both")
    return REGISTERS[kind](w)


# ---------------------------------------------------------------- the corpus
def corpus(seed: int, n_cases: int, k_plants: int) -> list[dict]:
    """Deterministic in (seed, n_cases, k_plants)."""
    w = World(seed)
    out = []
    kinds = ["both"] * 50 + ["organ"] * 25 + ["tissue"] * 25
    for i in range(n_cases):
        variant = kinds[i % len(kinds)]
        snapshot = w.r.random() < 0.15
        rec = make_donor_case(w, variant, snapshot=snapshot)
        out.append({"corpus_id": w.next("C"), "kind": "donor", "variant": f"{variant}/{rec['donor_type']}/{'snapshot' if snapshot else 'complete'}",
                    "clean": True, "plants": [], "record": rec})
    for _ in range(max(1, n_cases // 5)):
        out.append({"corpus_id": w.next("C"), "kind": "referral", "variant": "referral", "clean": True, "plants": [], "record": make_referral(w)})
    for name, fn in REGISTERS.items():
        for _ in range(max(2, n_cases // 10)):
            out.append({"corpus_id": w.next("C"), "kind": name, "variant": name, "clean": True, "plants": [], "record": fn(w)})
    for cid, (kind, fn) in PLANTS.items():
        for _ in range(k_plants):
            base = base_for(w, kind)
            rec = copy.deepcopy(base)
            how = fn(w, rec)
            # THE PLANT INVARIANT: a plant that does not change the record is not a plant.
            # Without this, a no-op mutation reads as a MISSED defect and kills the run for
            # the wrong reason - which is exactly what the first S3 run did (the SV-003
            # plant flipped a band number's last digit to zero, a no-op when it was
            # already zero). An instrument defect must never be reported as a subject defect.
            if rec == base:
                raise AssertionError(f"{cid}: plant changed nothing ({how}) - the instrument is broken, not the floor")
            out.append({"corpus_id": w.next("P"), "kind": kind, "variant": f"plant/{cid}", "clean": False,
                        "plants": [{"check": cid, "how": how}], "record": rec, "base_record": base})
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260903)
    ap.add_argument("--cases", type=int, default=200)
    ap.add_argument("--plants", type=int, default=5)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    rows = corpus(a.seed, a.cases, a.plants)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        with open(a.out, "w", encoding="utf-8", newline="\n") as f:
            for row in rows:
                f.write(json.dumps(row) + "\n")
        print(f"wrote {len(rows)} records to {a.out}")
    else:
        print(f"{len(rows)} records (seed {a.seed}): {sum(r['clean'] for r in rows)} clean, {sum(not r['clean'] for r in rows)} plants")
