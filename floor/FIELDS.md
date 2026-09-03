# FIELDS - the record vocabulary the floor reads. Generated fold. DO NOT EDIT.
Regenerate: `python floor/engine.py --fields --write` (gates.py G-FIELDS enforces).
Folded from the fixtures, so it is exact for what the checks have been proven against and silent about anything else. Types are observed, not declared: ts = ISO-8601 timestamp, blank = null or empty string.

checks: 59 | fixtures: 281 | leaf paths: 306

## abo
| path | observed types | carried by fixtures of |
|---|---|---|
| `abo.determination_1.draw_ts` | ts | SV-060 |
| `abo.determination_1.result` | str | SV-060 |
| `abo.determination_2.draw_ts` | ts | SV-060 |
| `abo.determination_2.result` | str | SV-060 |
| `abo.draw_ts` | ts | SV-059 |
| `abo.subtype` | blank, str | SV-059 |
| `abo.subtype_reason_code` | str | SV-059 |
| `abo.type` | str | SV-059 |

## action
| path | observed types | carried by fixtures of |
|---|---|---|
| `action.kind` | str | SV-043 |
| `action.performed_by` | str | SV-043 |
| `action.role` | str | SV-043 |
| `action.ts` | ts | SV-043 |

## active_primary_offers
| path | observed types | carried by fixtures of |
|---|---|---|
| `active_primary_offers.KI-L` | list | SV-070 |
| `active_primary_offers.KI-L[]` | str | SV-070 |
| `active_primary_offers.KI-R` | list | SV-070 |
| `active_primary_offers.KI-R[]` | str | SV-070 |

## allocation
| path | observed types | carried by fixtures of |
|---|---|---|
| `allocation.closed_ts` | ts | SV-034 |
| `allocation.declines` | list | SV-075 |
| `allocation.declines[].center_id` | str | SV-075 |
| `allocation.declines[].classification` | str | SV-075 |
| `allocation.declines[].free_text` | str | SV-075 |
| `allocation.declines[].list_status` | str | SV-075 |
| `allocation.declines[].reason_code` | blank, str | SV-075 |
| `allocation.latest_offer_ts` | ts | SV-034 |
| `allocation.offers` | list | SV-034, SV-076 |
| `allocation.offers[].center_bypassed` | str | SV-076 |
| `allocation.offers[].center_id` | str | SV-076 |
| `allocation.offers[].offer_ref` | str | SV-034, SV-076 |
| `allocation.offers[].primary_list_exhausted_at_send` | str | SV-076 |
| `allocation.offers[].sent_ts` | ts | SV-034 |
| `allocation.organs` | list | SV-025 |
| `allocation.organs[]` | str | SV-025 |
| `allocation.start_ts` | ts | SV-025 |
| `allocation.unstable_donor_exception_ref` | str | SV-034 |

## as_of
| path | observed types | carried by fixtures of |
|---|---|---|
| `as_of` | ts | SV-020, SV-021, SV-022, SV-023, SV-024, SV-025, SV-027, SV-028, SV-029, SV-030, SV-031, SV-032, SV-033, SV-034, SV-035, SV-042, SV-082, SV-084 |

## audit
| path | observed types | carried by fixtures of |
|---|---|---|
| `audit.started_ts` | ts | SV-020 |

## authorization
| path | observed types | carried by fixtures of |
|---|---|---|
| `authorization.authorizing_party_relationship` | str | SV-071 |
| `authorization.categories` | list | SV-052 |
| `authorization.categories[]` | str | SV-052 |
| `authorization.donor_dob` | str | SV-001 |
| `authorization.donor_name` | str | SV-001 |
| `authorization.method` | str | SV-015, SV-054, SV-071, SV-072 |
| `authorization.organs_authorized` | list | SV-071 |
| `authorization.organs_authorized[]` | str | SV-071 |
| `authorization.recording_ref` | blank, str | SV-072 |
| `authorization.required_fields` | list | SV-071 |
| `authorization.required_fields[]` | str | SV-071 |
| `authorization.signed_ts` | ts | SV-071 |
| `authorization.tissues_authorized` | list | SV-054 |
| `authorization.tissues_authorized[]` | str | SV-054 |
| `authorization.witness_affiliation` | blank, str | SV-015, SV-071 |
| `authorization.witness_role` | str | SV-015 |

## body_diagram
| path | observed types | carried by fixtures of |
|---|---|---|
| `body_diagram.sites` | list | SV-005 |
| `body_diagram.sites[]` | str | SV-005 |

## capa
| path | observed types | carried by fixtures of |
|---|---|---|
| `capa.effectiveness.data_ref` | str | SV-082 |
| `capa.effectiveness.observed` | number | SV-082 |
| `capa.effectiveness.result` | str | SV-082 |
| `capa.expectation.baseline` | blank, number | SV-081 |
| `capa.expectation.horizon_ts` | ts | SV-081, SV-082 |
| `capa.expectation.metric` | blank, str | SV-081, SV-082 |
| `capa.expectation.narrative` | str | SV-081 |
| `capa.expectation.target` | blank, number | SV-081, SV-082 |
| `capa.expires` | ts | SV-081 |
| `capa.id` | str | SV-081, SV-082 |
| `capa.inverse` | str | SV-081 |
| `capa.owner_role` | blank, str | SV-081 |
| `capa.status` | str | SV-081, SV-082 |
| `capa.variance_class` | str | SV-081 |

## case
| path | observed types | carried by fixtures of |
|---|---|---|
| `case.closed_ts` | ts | SV-021 |

## case_id
| path | observed types | carried by fixtures of |
|---|---|---|
| `case_id` | str | SV-001, SV-002, SV-003, SV-004, SV-005, SV-010, SV-011, SV-012, SV-013, SV-014, SV-015, SV-020, SV-021, SV-022, SV-023, SV-024, SV-025, SV-026, SV-027, SV-028, SV-029, SV-030, SV-031, SV-032, SV-033, SV-034, SV-040, SV-043, SV-050, SV-051, SV-052, SV-053, SV-054, SV-055, SV-056, SV-057, SV-058, SV-059, SV-060, SV-061, SV-070, SV-071, SV-072, SV-073, SV-074, SV-075, SV-076, SV-077, SV-080 |

## chart
| path | observed types | carried by fixtures of |
|---|---|---|
| `chart.donor_dob` | str | SV-001, SV-002 |
| `chart.donor_id` | str | SV-002, SV-004, SV-010 |
| `chart.donor_name` | str | SV-001 |
| `chart.sent_to_processor_ts` | ts | SV-021 |

## check
| path | observed types | carried by fixtures of |
|---|---|---|
| `check.corrects_field` | str | SV-062 |
| `check.id` | str | SV-062 |
| `check.verification_fields` | list | SV-062 |
| `check.verification_fields[]` | str | SV-062 |

## competencies
| path | observed types | carried by fixtures of |
|---|---|---|
| `competencies.STF-052.driver.expires_ts` | ts | SV-043 |
| `competencies.STF-052.driver.granted_ts` | ts | SV-043 |
| `competencies.STF-052.tissue_recovery_technician.expires_ts` | ts | SV-043 |
| `competencies.STF-052.tissue_recovery_technician.granted_ts` | ts | SV-043 |

## contracts
| path | observed types | carried by fixtures of |
|---|---|---|
| `contracts` | list | SV-035 |
| `contracts[].decision_ref` | blank, str | SV-035 |
| `contracts[].id` | str | SV-035 |
| `contracts[].notice_deadline_ts` | ts | SV-035 |
| `contracts[].vendor_class` | str | SV-035 |

## controlled_vocabulary
| path | observed types | carried by fixtures of |
|---|---|---|
| `controlled_vocabulary.authorized_categories` | list | SV-052 |
| `controlled_vocabulary.authorized_categories[]` | str | SV-052 |

## cooling
| path | observed types | carried by fixtures of |
|---|---|---|
| `cooling.initial_ts` | ts | SV-028 |

## corrections
| path | observed types | carried by fixtures of |
|---|---|---|
| `corrections` | list | SV-051 |
| `corrections[].dated` | blank, str | SV-051 |
| `corrections[].field` | str | SV-051 |
| `corrections[].image_ref` | str | SV-051 |
| `corrections[].initialed_by` | str | SV-051 |
| `corrections[].method` | str | SV-051 |

## county_epidemiology
| path | observed types | carried by fixtures of |
|---|---|---|
| `county_epidemiology.channel` | str | SV-023 |
| `county_epidemiology.notified_ts` | ts | SV-023 |

## covid
| path | observed types | carried by fixtures of |
|---|---|---|
| `covid.collected_ts` | ts | SV-024 |
| `covid.lower_respiratory_specimen_ref` | str | SV-024 |
| `covid.result` | str | SV-024 |
| `covid.resulted_ts` | ts | SV-024 |
| `covid.specimen_type` | str | SV-024 |

## ddr
| path | observed types | carried by fixtures of |
|---|---|---|
| `ddr.submitted_ts` | ts | SV-031 |

## death
| path | observed types | carried by fixtures of |
|---|---|---|
| `death.pronounced_ts` | ts | SV-028 |

## declaration
| path | observed types | carried by fixtures of |
|---|---|---|
| `declaration.pronouncing_clinician` | str | SV-012 |

## disease_transmission
| path | observed types | carried by fixtures of |
|---|---|---|
| `disease_transmission.confirmed_ts` | ts | SV-022 |
| `disease_transmission.info_received_ts` | ts | SV-022 |
| `disease_transmission.notified_to` | list | SV-022 |
| `disease_transmission.notified_to[]` | str | SV-022 |
| `disease_transmission.notified_ts` | ts | SV-022 |

## dnr
| path | observed types | carried by fixtures of |
|---|---|---|
| `dnr.submitted_ts` | ts | SV-032 |

## document
| path | observed types | carried by fixtures of |
|---|---|---|
| `document.approved_roles` | list | SV-041 |
| `document.approved_roles[]` | str | SV-041 |
| `document.id` | str | SV-041 |
| `document.required_approval_roles` | list | SV-041 |
| `document.required_approval_roles[]` | str | SV-041 |
| `document.status` | str | SV-041 |

## document_control
| path | observed types | carried by fixtures of |
|---|---|---|
| `document_control.current_revision_at_use.FRM-AUTH-01` | str | SV-040 |
| `document_control.current_revision_at_use.FRM-DRE-02` | str | SV-040 |

## document_of_gift
| path | observed types | carried by fixtures of |
|---|---|---|
| `document_of_gift.donor_dob` | str | SV-001 |
| `document_of_gift.donor_name` | str | SV-001 |

## donor
| path | observed types | carried by fixtures of |
|---|---|---|
| `donor.age_months` | number | SV-058 |
| `donor.breastfed_within_12_months` | str | SV-058 |

## donor_band
| path | observed types | carried by fixtures of |
|---|---|---|
| `donor_band.number` | str | SV-003 |

## donor_type
| path | observed types | carried by fixtures of |
|---|---|---|
| `donor_type` | str | SV-012 |

## donor_verification
| path | observed types | carried by fixtures of |
|---|---|---|
| `donor_verification.identifiers` | list | SV-004 |
| `donor_verification.identifiers[]` | str | SV-004 |
| `donor_verification.sources` | list | SV-004 |
| `donor_verification.sources[]` | str | SV-004 |
| `donor_verification.verified_by` | list | SV-011 |
| `donor_verification.verified_by[]` | str | SV-011 |
| `donor_verification.verified_ts` | ts | SV-004, SV-011 |

## dre
| path | observed types | carried by fixtures of |
|---|---|---|
| `dre.branches` | list | SV-050 |
| `dre.branches[].children` | list | SV-050 |
| `dre.branches[].children[].answer` | blank, str | SV-050 |
| `dre.branches[].children[].id` | str | SV-050 |
| `dre.branches[].parent_answer` | str | SV-050 |
| `dre.branches[].parent_id` | str | SV-050 |
| `dre.donor_dob` | str | SV-001 |
| `dre.donor_name` | str | SV-001 |
| `dre.subjects` | list | SV-058 |
| `dre.subjects[]` | str | SV-058 |

## edit
| path | observed types | carried by fixtures of |
|---|---|---|
| `edit.case_note_ref` | blank, str | SV-013 |
| `edit.class` | str | SV-013 |
| `edit.field` | str | SV-013 |
| `edit.ts` | ts | SV-013 |

## edits
| path | observed types | carried by fixtures of |
|---|---|---|
| `edits` | list | SV-014 |
| `edits[].editor_id` | str | SV-014 |
| `edits[].field` | str | SV-014 |
| `edits[].session_actor_id` | str | SV-014 |
| `edits[].ts` | blank, ts | SV-014 |

## entry
| path | observed types | carried by fixtures of |
|---|---|---|
| `entry.documented_ts` | ts | SV-056 |
| `entry.entered_ts` | ts | SV-056 |
| `entry.field` | str | SV-056 |

## feedback
| path | observed types | carried by fixtures of |
|---|---|---|
| `feedback.submitted_ts` | ts | SV-030, SV-031 |

## flow_sheet
| path | observed types | carried by fixtures of |
|---|---|---|
| `flow_sheet.segments` | list | SV-057 |
| `flow_sheet.segments[].end_ts` | ts | SV-057 |
| `flow_sheet.segments[].start_ts` | ts | SV-057 |
| `flow_sheet.segments[].vitals` | list | SV-057 |
| `flow_sheet.segments[].vitals[].name` | str | SV-057 |
| `flow_sheet.segments[].vitals[].value` | blank, number | SV-057 |
| `flow_sheet.vitals_per_segment` | number | SV-057 |

## form
| path | observed types | carried by fixtures of |
|---|---|---|
| `form.document_id` | str | SV-040 |
| `form.revision_used` | str | SV-040 |
| `form.used_ts` | ts | SV-040 |

## hemodilution
| path | observed types | carried by fixtures of |
|---|---|---|
| `hemodilution.calc.blood_product_refs` | list | SV-026 |
| `hemodilution.calc.blood_product_refs[]` | str | SV-026 |
| `hemodilution.calc.blood_products` | list | SV-026 |
| `hemodilution.calc.blood_products[].ref` | str | SV-026 |
| `hemodilution.calc.blood_products[].ts` | ts | SV-026 |
| `hemodilution.calc.blood_products[].volume_ml` | number | SV-026 |
| `hemodilution.calc.blood_products_ml` | number | SV-026 |
| `hemodilution.calc.crystalloid_refs` | list | SV-026 |
| `hemodilution.calc.crystalloid_refs[]` | str | SV-026 |
| `hemodilution.calc.crystalloids` | list | SV-026 |
| `hemodilution.calc.crystalloids[].ref` | str | SV-026 |
| `hemodilution.calc.crystalloids[].ts` | ts | SV-026 |
| `hemodilution.calc.crystalloids[].volume_ml` | number | SV-026 |
| `hemodilution.calc.crystalloids_ml` | number | SV-026 |
| `hemodilution.logged.blood_product_refs` | list | SV-026 |
| `hemodilution.logged.blood_product_refs[]` | str | SV-026 |
| `hemodilution.logged.blood_products` | list | SV-026 |
| `hemodilution.logged.blood_products[].ref` | str | SV-026 |
| `hemodilution.logged.blood_products[].ts` | ts | SV-026 |
| `hemodilution.logged.blood_products[].volume_ml` | number | SV-026 |
| `hemodilution.logged.crystalloid_refs` | list | SV-026 |
| `hemodilution.logged.crystalloid_refs[]` | str | SV-026 |
| `hemodilution.logged.crystalloids` | list | SV-026 |
| `hemodilution.logged.crystalloids[].ref` | str | SV-026 |
| `hemodilution.logged.crystalloids[].ts` | ts | SV-026 |
| `hemodilution.logged.crystalloids[].volume_ml` | number | SV-026 |
| `hemodilution.sample_draw_ts` | ts | SV-026 |

## hla_abo
| path | observed types | carried by fixtures of |
|---|---|---|
| `hla_abo.coordinator_signatures` | list | SV-010 |
| `hla_abo.coordinator_signatures[]` | str | SV-010 |
| `hla_abo.lab_signature` | blank, str | SV-010 |
| `hla_abo.status` | str | SV-010 |

## inspection
| path | observed types | carried by fixtures of |
|---|---|---|
| `inspection.pre_inspection_ts` | ts | SV-055 |

## labs
| path | observed types | carried by fixtures of |
|---|---|---|
| `labs.inr.collected_ts` | ts | SV-025 |
| `labs.inr.resulted_ts` | ts | SV-025 |
| `labs.inr.value` | number | SV-025 |

## match_run
| path | observed types | carried by fixtures of |
|---|---|---|
| `match_run.centers` | list | SV-074 |
| `match_run.centers[]` | str | SV-074 |
| `match_run.id` | str | SV-074 |

## narrative
| path | observed types | carried by fixtures of |
|---|---|---|
| `narrative.sites` | list | SV-005 |
| `narrative.sites[]` | str | SV-005 |
| `narrative.text_ref` | str | SV-005 |

## offer_ref
| path | observed types | carried by fixtures of |
|---|---|---|
| `offer_ref` | blank, str | SV-070 |

## onsite
| path | observed types | carried by fixtures of |
|---|---|---|
| `onsite.arrived_ts` | ts | SV-033 |

## or_roster
| path | observed types | carried by fixtures of |
|---|---|---|
| `or_roster.physician_signatures` | list | SV-012 |
| `or_roster.physician_signatures[]` | str | SV-012 |
| `or_roster.recovering_physicians` | list | SV-012 |
| `or_roster.recovering_physicians[]` | str | SV-012 |
| `or_roster.roles` | list | SV-012 |
| `or_roster.roles[]` | str | SV-012 |

## or_summary
| path | observed types | carried by fixtures of |
|---|---|---|
| `or_summary.research_specimens` | list | SV-073 |
| `or_summary.research_specimens[]` | str | SV-073 |

## or_timeline
| path | observed types | carried by fixtures of |
|---|---|---|
| `or_timeline.draping_ts` | ts | SV-027 |
| `or_timeline.incision_ts` | ts | SV-027 |
| `or_timeline.prep_complete_ts` | ts | SV-027 |

## organ_id
| path | observed types | carried by fixtures of |
|---|---|---|
| `organ_id` | str | SV-070 |

## organs
| path | observed types | carried by fixtures of |
|---|---|---|
| `organs` | list | SV-077 |
| `organs[].organ_id` | str | SV-077 |
| `organs[].organ_page_disposition` | str | SV-077 |
| `organs[].summary_page_disposition` | str | SV-077 |

## perfusion_screening
| path | observed types | carried by fixtures of |
|---|---|---|
| `perfusion_screening.centers` | list | SV-074 |
| `perfusion_screening.centers[]` | str | SV-074 |

## physical_assessment
| path | observed types | carried by fixtures of |
|---|---|---|
| `physical_assessment.injection_sites` | list | SV-061 |
| `physical_assessment.injection_sites[].classification` | str | SV-061 |
| `physical_assessment.injection_sites[].site` | str | SV-061 |
| `physical_assessment.injection_sites_assessed` | str | SV-061 |

## prep
| path | observed types | carried by fixtures of |
|---|---|---|
| `prep.start_ts` | ts | SV-055 |

## qapi
| path | observed types | carried by fixtures of |
|---|---|---|
| `qapi.last_board_presentation_ts` | ts | SV-084 |
| `qapi.next_board_presentation_ts` | ts | SV-084 |
| `qapi.plan_revised_ts` | ts | SV-084 |
| `qapi.plan_revision` | str | SV-084 |

## recovery
| path | observed types | carried by fixtures of |
|---|---|---|
| `recovery.cross_clamp_ts` | ts | SV-024, SV-030 |
| `recovery.end_ts` | ts | SV-020, SV-021, SV-032 |
| `recovery.items` | list | SV-053 |
| `recovery.items[].seq` | number | SV-053 |
| `recovery.items[].tissue` | str | SV-053 |
| `recovery.organ_recovery_ts` | ts | SV-030, SV-031 |
| `recovery.organs` | list | SV-024 |
| `recovery.organs[]` | str | SV-024 |
| `recovery.paired_sequence_numbers` | list | SV-053 |
| `recovery.paired_sequence_numbers[]` | number | SV-053 |
| `recovery.start_ts` | ts | SV-028, SV-029 |
| `recovery.tissues_recovered` | list | SV-054 |
| `recovery.tissues_recovered[]` | str | SV-054 |

## recovery_paperwork
| path | observed types | carried by fixtures of |
|---|---|---|
| `recovery_paperwork.donor_band_number` | str | SV-003 |
| `recovery_paperwork.page_count` | number | SV-003 |

## referral
| path | observed types | carried by fixtures of |
|---|---|---|
| `referral.dispatched_ts` | ts | SV-033 |
| `referral.hospital_ref` | str | SV-033 |
| `referral.received_ts` | ts | SV-020, SV-028, SV-032, SV-033 |

## refrigeration
| path | observed types | carried by fixtures of |
|---|---|---|
| `refrigeration.out_intervals` | list | SV-028 |
| `refrigeration.out_intervals[].in_ts` | ts | SV-028 |
| `refrigeration.out_intervals[].out_ts` | ts | SV-028 |

## register_id
| path | observed types | carried by fixtures of |
|---|---|---|
| `register_id` | str | SV-035, SV-042 |

## release
| path | observed types | carried by fixtures of |
|---|---|---|
| `release.contamination_pct` | number | SV-080 |
| `release.required_document_count` | number | SV-080 |
| `release.required_documents` | list | SV-080 |
| `release.required_documents[].name` | str | SV-080 |
| `release.required_documents[].status` | str | SV-080 |

## report
| path | observed types | carried by fixtures of |
|---|---|---|
| `report.id` | str | SV-085 |
| `report.metrics` | list | SV-085 |
| `report.metrics[].denominator` | str | SV-085 |
| `report.metrics[].family` | str | SV-085 |
| `report.metrics[].section` | number | SV-085 |
| `report.metrics[].value` | number | SV-085 |
| `report.metrics[].variant` | str | SV-085 |

## research_tab
| path | observed types | carried by fixtures of |
|---|---|---|
| `research_tab.specimens` | list | SV-073 |
| `research_tab.specimens[]` | str | SV-073 |

## risk
| path | observed types | carried by fixtures of |
|---|---|---|
| `risk.id` | str | SV-083 |
| `risk.owner_role` | str | SV-083 |
| `risk.priority` | number | SV-083 |
| `risk.review_ts` | blank, ts | SV-083 |

## risk_register
| path | observed types | carried by fixtures of |
|---|---|---|
| `risk_register.id` | str | SV-083 |
| `risk_register.owner_required_at_priority` | number | SV-083 |

## serology
| path | observed types | carried by fixtures of |
|---|---|---|
| `serology.confirmatory_result_ts` | ts | SV-023 |
| `serology.draw_ts` | ts | SV-002, SV-029 |
| `serology.reactive_marker` | str | SV-023 |
| `serology.reactive_result_ts` | ts | SV-023 |
| `serology.result_ref` | str | SV-002 |
| `serology.resulted_ts` | ts | SV-029 |
| `serology.source` | str | SV-029 |

## serology_report
| path | observed types | carried by fixtures of |
|---|---|---|
| `serology_report.donor_dob` | str | SV-002 |
| `serology_report.donor_id` | str | SV-002 |
| `serology_report.draw_ts` | ts | SV-002 |
| `serology_report.lab_ref` | str | SV-002 |

## shared_case
| path | observed types | carried by fixtures of |
|---|---|---|
| `shared_case.id` | str | SV-078 |
| `shared_case.processors` | list | SV-078 |
| `shared_case.processors[].processor_id` | str | SV-078 |
| `shared_case.processors[].results_received` | list | SV-078 |
| `shared_case.processors[].results_received[]` | str | SV-078 |
| `shared_case.results` | list | SV-078 |
| `shared_case.results[]` | str | SV-078 |

## signoff
| path | observed types | carried by fixtures of |
|---|---|---|
| `signoff.signed_by` | str | SV-056 |
| `signoff.ts` | ts | SV-056 |

## standards
| path | observed types | carried by fixtures of |
|---|---|---|
| `standards` | list | SV-042 |
| `standards[].adopted_edition` | str | SV-042 |
| `standards[].id` | str | SV-042 |
| `standards[].next_edition` | str | SV-042 |
| `standards[].next_edition_effective_ts` | ts | SV-042 |

## team_worksheet
| path | observed types | carried by fixtures of |
|---|---|---|
| `team_worksheet.roster` | list | SV-011 |
| `team_worksheet.roster[]` | str | SV-011 |

## tissue
| path | observed types | carried by fixtures of |
|---|---|---|
| `tissue.category` | str | SV-021 |

## predicates
| check | trigger | predicate |
|---|---|---|
| SV-001 | on_close_attempt | `authorization.donor_name == chart.donor_name and authorization.donor_dob == chart.donor_dob and dre.donor_name == chart.donor_name and dre.donor_dob == chart.donor_dob and document_of_gift.donor_name == chart.donor_name and document_of_gift.donor_dob == chart.donor_dob` |
| SV-002 | on_write | `serology_report.donor_id == chart.donor_id and serology_report.donor_dob == chart.donor_dob and minutes_between(serology_report.draw_ts, serology.draw_ts) == 0` |
| SV-003 | on_close_attempt | `donor_band.number == recovery_paperwork.donor_band_number` |
| SV-004 | on_close_attempt | `distinct(donor_verification.identifiers) >= 2 and contains(donor_verification.sources, 'bedside_nurse') and contains(donor_verification.sources, 'hospital_wristband') and contains(donor_verification.sources, 'donor_band')` |
| SV-005 | on_close_attempt | `same_set(body_diagram.sites, narrative.sites)` |
| SV-010 | on_close_attempt | `distinct(hla_abo.coordinator_signatures) >= 2 and exists(hla_abo.lab_signature)` |
| SV-011 | on_close_attempt | `distinct(donor_verification.verified_by) >= 2 and subset(donor_verification.verified_by, team_worksheet.roster)` |
| SV-012 | on_close_attempt | `(donor_type == 'brain_dead' implies contains(or_roster.roles, 'anesthesiologist')) and (donor_type == 'dcd' implies contains(or_roster.roles, 'circulator')) and not contains(or_roster.recovering_physicians, declaration.pronouncing_clinician) and subset(or_roster.recovering_physicians, or_roster.physician_signatures)` |
| SV-013 | on_write | `edit.class != 'routine' implies exists(edit.case_note_ref)` |
| SV-014 | on_write | `every(edits, exists(editor_id) and exists(ts) and editor_id == session_actor_id)` |
| SV-015 | on_close_attempt | `authorization.witness_affiliation == 'hospital_care_team'` |
| SV-020 | continuous | `within(recovery.end_ts, audit.started_ts, 7d)` |
| SV-021 | continuous | `(tissue.category == 'fresh' implies within(recovery.end_ts, chart.sent_to_processor_ts, 10d)) and (tissue.category != 'fresh' implies within(recovery.end_ts, chart.sent_to_processor_ts, 30d))` |
| SV-022 | continuous | `within(disease_transmission.info_received_ts, disease_transmission.notified_ts, 24h)` |
| SV-023 | continuous | `within(serology.reactive_result_ts, county_epidemiology.notified_ts, 24h)` |
| SV-024 | continuous | `(exists(recovery.cross_clamp_ts) implies exists(covid.result)) and (exists(covid.result) implies (within(covid.collected_ts, recovery.cross_clamp_ts, 72h) and (not exists(recovery.cross_clamp_ts) or minutes_between(covid.collected_ts, recovery.cross_clamp_ts) >= 0))) and ((contains(recovery.organs, 'LU-L') or contains(recovery.organs, 'LU-R')) implies exists(covid.lower_respiratory_specimen_ref))` |
| SV-025 | continuous | `contains(allocation.organs, 'LI') implies (within(labs.inr.collected_ts, allocation.start_ts, 12h) and (not exists(allocation.start_ts) or minutes_between(labs.inr.collected_ts, allocation.start_ts) >= 0))` |
| SV-026 | on_write | `every(hemodilution.calc.blood_products, contains(hemodilution.logged.blood_product_refs, ref) and minutes_between(ts, hemodilution.sample_draw_ts) >= 0 and minutes_between(ts, hemodilution.sample_draw_ts) <= 48h) and every(hemodilution.logged.blood_products, minutes_between(ts, hemodilution.sample_draw_ts) < 0 or minutes_between(ts, hemodilution.sample_draw_ts) > 48h or contains(hemodilution.calc.blood_product_refs, ref)) and sum(hemodilution.calc.blood_products, volume_ml) == hemodilution.calc.blood_products_ml and every(hemodilution.calc.crystalloids, contains(hemodilution.logged.crystalloid_refs, ref) and minutes_between(ts, hemodilution.sample_draw_ts) >= 0 and minutes_between(ts, hemodilution.sample_draw_ts) <= 1h) and every(hemodilution.logged.crystalloids, minutes_between(ts, hemodilution.sample_draw_ts) < 0 or minutes_between(ts, hemodilution.sample_draw_ts) > 1h or contains(hemodilution.calc.crystalloid_refs, ref)) and sum(hemodilution.calc.crystalloids, volume_ml) == hemodilution.calc.crystalloids_ml` |
| SV-027 | continuous | `within(or_timeline.prep_complete_ts, or_timeline.incision_ts, 75m)` |
| SV-028 | continuous | `(not exists(cooling.initial_ts) implies within(death.pronounced_ts, recovery.start_ts, 15h)) and (exists(cooling.initial_ts) implies ((minutes_between(death.pronounced_ts, cooling.initial_ts) <= 12h implies within(death.pronounced_ts, recovery.start_ts, 24h)) and (minutes_between(death.pronounced_ts, cooling.initial_ts) > 12h implies within(death.pronounced_ts, recovery.start_ts, 15h)))) and sum(refrigeration.out_intervals, minutes_between(out_ts, in_ts)) <= 15h` |
| SV-029 | continuous | `serology.source == 'reused_from_organ_case' implies (within(serology.draw_ts, recovery.start_ts, 7d) and (not exists(recovery.start_ts) or minutes_between(recovery.start_ts, serology.draw_ts) <= 7d))` |
| SV-030 | continuous | `within(recovery.organ_recovery_ts, feedback.submitted_ts, 5bd)` |
| SV-031 | continuous | `within(feedback.submitted_ts, ddr.submitted_ts, 30d)` |
| SV-032 | continuous | `within(month_end_of(referral.received_ts), dnr.submitted_ts, 30d)` |
| SV-033 | continuous | `within(referral.received_ts, onsite.arrived_ts, 90m)` |
| SV-034 | continuous | `exists(allocation.unstable_donor_exception_ref) or (every_pair(allocation.offers, minutes_between(prev.sent_ts, next.sent_ts) >= 0 and minutes_between(prev.sent_ts, next.sent_ts) <= 30m) and within(allocation.latest_offer_ts, allocation.closed_ts, 30m))` |
| SV-035 | continuous | `every(contracts, minutes_between(as_of, notice_deadline_ts) > 120d or exists(decision_ref))` |
| SV-040 | on_write | `form.revision_used == document_control.current_revision_at_use[form.document_id]` |
| SV-041 | on_write | `document.status == 'effective' implies subset(document.required_approval_roles, document.approved_roles)` |
| SV-042 | continuous | `every(standards, not exists(next_edition) or adopted_edition == next_edition or minutes_between(as_of, next_edition_effective_ts) > 90d)` |
| SV-043 | on_write | `minutes_between(competencies[action.performed_by][action.role].granted_ts, action.ts) >= 0 and minutes_between(action.ts, competencies[action.performed_by][action.role].expires_ts) >= 0` |
| SV-050 | on_close_attempt | `count(dre.branches) > 0 and every(dre.branches, parent_answer == 'yes' implies every(children, exists(answer)))` |
| SV-051 | on_close_attempt | `every(corrections, method == 'single_line_through' and exists(initialed_by) and exists(dated))` |
| SV-052 | on_write | `subset(authorization.categories, controlled_vocabulary.authorized_categories)` |
| SV-053 | on_write | `every(recovery.items, occurrences(recovery.items, seq, seq) == 1 or (contains(recovery.paired_sequence_numbers, seq) and occurrences(recovery.items, seq, seq) == 2))` |
| SV-054 | on_close_attempt | `subset(recovery.tissues_recovered, authorization.tissues_authorized)` |
| SV-055 | on_write | `minutes_between(inspection.pre_inspection_ts, prep.start_ts) > 0` |
| SV-056 | on_write | `not exists(signoff.ts) or minutes_between(signoff.ts, entry.entered_ts) <= 0 or minutes_between(signoff.ts, entry.documented_ts) >= 0` |
| SV-057 | on_close_attempt | `every_pair(flow_sheet.segments, minutes_between(prev.end_ts, next.start_ts) == 1) and every(flow_sheet.segments, count(vitals) >= flow_sheet.vitals_per_segment and every(vitals, exists(value)))` |
| SV-058 | on_close_attempt | `(donor.age_months > 18 and donor.breastfed_within_12_months != 'yes') or (contains(dre.subjects, 'donor') and contains(dre.subjects, 'birth_mother'))` |
| SV-059 | on_write | `(abo.type == 'A' or abo.type == 'AB') implies (exists(abo.subtype) or exists(abo.subtype_reason_code))` |
| SV-060 | on_write | `minutes_between(abo.determination_1.draw_ts, abo.determination_2.draw_ts) != 0` |
| SV-061 | on_write | `(count(physical_assessment.injection_sites) > 0 or physical_assessment.injection_sites_assessed == 'yes') and every(physical_assessment.injection_sites, classification == 'medical' or classification == 'non_medical')` |
| SV-062 | on_mount | `not contains(check.verification_fields, check.corrects_field)` |
| SV-070 | on_write | `count(active_primary_offers[organ_id]) <= 1` |
| SV-071 | on_close_attempt | `count(authorization.required_fields) > 0 and every(authorization.required_fields, exists(authorization[value]))` |
| SV-072 | on_close_attempt | `authorization.method != 'phone' or exists(authorization.recording_ref)` |
| SV-073 | on_close_attempt | `same_set(research_tab.specimens, or_summary.research_specimens)` |
| SV-074 | on_write | `subset(perfusion_screening.centers, match_run.centers)` |
| SV-075 | on_write | `every(allocation.declines, exists(reason_code) and (classification == 'disqualifying' or classification == 'non_disqualifying') and (classification != 'disqualifying' or list_status == 'removed'))` |
| SV-076 | on_write | `every(allocation.offers, center_bypassed != 'yes' or primary_list_exhausted_at_send == 'yes')` |
| SV-077 | on_close_attempt | `count(organs) > 0 and every(organs, organ_page_disposition == summary_page_disposition)` |
| SV-078 | on_close_attempt | `count(shared_case.processors) >= 2 and every(shared_case.processors, subset(shared_case.results, results_received))` |
| SV-080 | on_close_attempt | `release.contamination_pct == 0 and count(release.required_documents) >= release.required_document_count and every(release.required_documents, status == 'complete')` |
| SV-081 | on_write | `exists(capa.owner_role) and exists(capa.expectation.metric) and exists(capa.expectation.baseline) and exists(capa.expectation.target) and exists(capa.expectation.horizon_ts) and exists(capa.expires) and exists(capa.inverse)` |
| SV-082 | continuous | `minutes_between(capa.expectation.horizon_ts, as_of) < 0 or (exists(capa.effectiveness.result) and (capa.effectiveness.result == 'met' or (capa.status == 'returned_to_committee' and exists(capa.effectiveness.data_ref))))` |
| SV-083 | on_write | `risk.priority < risk_register.owner_required_at_priority or (exists(risk.owner_role) and exists(risk.review_ts))` |
| SV-084 | continuous | `within(qapi.last_board_presentation_ts, qapi.next_board_presentation_ts, 366d)` |
| SV-085 | on_close_attempt | `every(report.metrics, exists(denominator) or occurrences(report.metrics, family, family) == occurrences(report.metrics, variant, variant))` |

