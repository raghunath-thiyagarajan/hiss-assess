# HISS catalogue file schema (shared contract for WP1 writer and WP2 code). UTF-8, comma separated, header row, fields with commas quoted. Lists inside a cell use semicolons.

controls.csv: control_id,domain,title,objective,requirement,rationale,level,profiles,triggers,owner_owned,owner_managed,owner_franchised,realities,evidence_expected,assessment_question,c1_link,basis
- control_id like HISS-H02-03 or HISS-F4-02; domain like F4 or H02 (domain codes: F1..F6, H01..H10)
- level: Baseline or Enhanced; profiles: semicolon list of S;M;G (Baseline = S;M;G)
- triggers: semicolon list from T1 card data electronically, T2 mobile or online keys, T3 BMS or CCTV on IP network, T4 cloud hosted PMS, T5 guests from a listed jurisdiction; blank if none (a trigger on an Enhanced control makes it mandatory for S)
- owner_*: one of group, property, vendor, franchisee
- realities: semicolon list from R1..R7
- evidence_expected: at least two artefacts separated by semicolons
- c1_link: finding family key or E/A tag from Capstone 1; basis: sourced, derived or judgement

crosswalk.csv: control_id,framework,target_id,target_title,strength,source,target_status,note
- framework: ISO27001, PCIDSS, CSF, CIS, CCM, SP1800-27, HTNG
- strength: D, P or J; source: required for D (named source), otherwise may be blank; target_status: VERIFIED, SECONDARY or NOT VERIFIED

obligations.csv: obligation_id,jurisdiction,instrument,provision,summary,hotel_trigger,status,fact_ref,control_ids
- jurisdiction tags: IN, AE-DXB, AE-AUH, AE-DIFC, AE-ADGM, AE, US-NY, US-FL, US, EU, EU-DE etc, UK
- status VERIFIED or SECONDARY only (NOT VERIFIED rows do not enter the file)

profiles.json: {"profiles":{"S":{...},"M":{...},"G":{...}},"triggers":{...},"operating_models":[...]}
realities.csv: reality_id,name,description
family_map.csv: family_key,family_name,control_ids,note   (12 Capstone 1 finding families)
requirements.csv: req_id,text,c1_ref,control_ids   (hotel requirements R01.. from Capstone 1 Table 10.1, L1..L9, P1..P5)
