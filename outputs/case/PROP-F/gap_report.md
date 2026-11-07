# Gap report: PROP-F

Toolkit: HISS-Assess. Author: Raghunath Thiyagarajan.

Profile S, operating model owned, active triggers: T1, T3 and T5.

The answers in this run are simulated (A26). They show how the toolkit behaves and are not a finding about the property.

Weights, caps, effort sizes, wave cut offs, profile choices and trigger choices are assumed values (register A20 to A31). They were not measured or validated.

## Summary

- Applicable controls: 67 of 80 in the catalogue.
- Answered: 67. Mean effective maturity 0.93 of 4 (23.1 percent).
- Met (maturity 3 or above): 0 controls (0.0 percent). Unmet: 67.
- HISS-RAT scan caps lowered the maturity of 0 controls (capped by scan). 4 controls carry a cap that did not bind. In scope: 3 systems and 15 findings.

| Domain | Name | Mean maturity percent | Met | Unmet |
|---|---|---|---|---|
| F1 | Governance and multi property oversight | 20.0 | 0 | 5 |
| F2 | Risk, assets and compliance | 37.5 | 0 | 4 |
| F3 | People, shifts and shared devices | 25.0 | 0 | 5 |
| F4 | Identity and access | 25.0 | 0 | 4 |
| F5 | Configuration, vulnerability and cryptography | 25.0 | 0 | 4 |
| F6 | Detection, response and recovery | 18.8 | 0 | 4 |
| H01 | PMS and reservations | 25.0 | 0 | 4 |
| H02 | POS and payments | 25.0 | 0 | 6 |
| H03 | Guest Wi-Fi and in room tech | 33.3 | 0 | 3 |
| H04 | Door locks and key cards | 25.0 | 0 | 3 |
| H05 | Building management and IoT | 10.0 | 0 | 5 |
| H06 | CCTV | 18.8 | 0 | 4 |
| H07 | Vendor remote access | 18.8 | 0 | 4 |
| H08 | Guest data lifecycle | 20.8 | 0 | 6 |
| H09 | Cloud and SaaS | 25.0 | 0 | 4 |
| H10 | Third party and franchise management | 25.0 | 0 | 2 |

## Unmet controls by domain

### F1 Governance and multi property oversight

- HISS-F1-05 Exception and operational override register (Baseline). Maturity 0.
- HISS-F1-01 Group ISMS scope with property baselines (Baseline). Maturity 1.
- HISS-F1-02 Named security owner per property (Baseline). Maturity 1.
- HISS-F1-03 Hotel policy set (Baseline). Maturity 1.
- HISS-F1-04 Control applicability record (Baseline). Maturity 1.

### F2 Risk, assets and compliance

- HISS-F2-01 Asset and software inventory including engineering assets (Baseline). Maturity 1.
- HISS-F2-03 Obligations register per jurisdiction (Baseline). Maturity 1.
- HISS-F2-02 Property risk assessment cycle (Baseline). Maturity 2.
- HISS-F2-04 Annual HISS self assessment (Baseline). Maturity 2.

### F3 People, shifts and shared devices

- HISS-F3-01 First shift induction for all workers (Baseline). Maturity 1.
- HISS-F3-02 Leaver removal within the shift (Baseline). Maturity 1.
- HISS-F3-03 Front desk social engineering awareness (Baseline). Maturity 1.
- HISS-F3-04 Shared terminal rules (Baseline). Maturity 1. Capped by: Medium on PROP-F-ACC-01 (smb_signing); Medium on PROP-F-BO-01 (smb_signing); Medium on PROP-F-FBM-01 (smb_signing).
- HISS-F3-05 Acceptable use for hotel roles (Baseline). Maturity 1.

### F4 Identity and access

- HISS-F4-01 Individual logons on shared terminals (Baseline). Maturity 1.
- HISS-F4-02 Privileged access (Baseline). Maturity 1.
- HISS-F4-03 MFA for remote, admin and cloud access (Baseline). Maturity 1. Capped by: Medium on PROP-F-FBM-01 (rdp_no_nla).
- HISS-F4-04 Quarterly access review per property (Baseline). Maturity 1.

### F5 Configuration, vulnerability and cryptography

- HISS-F5-01 Role hardening baselines (Baseline). Maturity 1. Capped by: Medium on PROP-F-ACC-01 (smb_signing); Medium on PROP-F-BO-01 (smb_signing); Medium on PROP-F-FBM-01 (smb_signing).
- HISS-F5-02 Patch windows that fit round the clock operation (Baseline). Maturity 1.
- HISS-F5-03 TLS, SSH and certificate management (Baseline). Maturity 1. Capped by: High on PROP-F-FBM-01 (weak_ciphers); Medium on PROP-F-ACC-01 (weak_certificates); Medium on PROP-F-FBM-01 (weak_certificates).
- HISS-F5-05 Malware protection (Baseline). Maturity 1.

### F6 Detection, response and recovery

- HISS-F6-03 Incident response with a notification clock matrix (Baseline). Maturity 0.
- HISS-F6-01 Central logs kept for the longest legal need (Baseline). Maturity 1.
- HISS-F6-04 Backup with offline copy and restore tests (Baseline). Maturity 1.
- HISS-F6-05 Manual front desk fallback (Baseline). Maturity 1.

### H01 PMS and reservations

- HISS-H01-03 Interface server in a protected zone (Baseline). Maturity 0.
- HISS-H01-01 Role based PMS access (Baseline). Maturity 1.
- HISS-H01-04 PMS vendor patch and support status (Baseline). Maturity 1.
- HISS-H01-02 Tokens not card numbers in the PMS (Baseline). Maturity 2.

### H02 POS and payments

- HISS-H02-02 Network separation of POS and payment terminals (Baseline). Maturity 0.
- HISS-H02-01 Cardholder data environment scope per property (Baseline). Maturity 1.
- HISS-H02-03 Payment terminal inspection (Baseline). Maturity 1.
- HISS-H02-05 Card data retention limits (Baseline). Maturity 1.
- HISS-H02-06 PCI DSS validation evidence (Baseline). Maturity 1.
- HISS-H02-04 Acquirer, gateway and aggregator agreements (Baseline). Maturity 2.

### H03 Guest Wi-Fi and in room tech

- HISS-H03-03 In room entertainment servers (Baseline). Maturity 1.
- HISS-H03-05 Guest device data wipe at checkout (Baseline). Maturity 1.
- HISS-H03-01 Guest network isolation (Baseline). Maturity 2.

### H04 Door locks and key cards

- HISS-H04-01 Lock server receives room number only (Baseline). Maturity 1.
- HISS-H04-02 Key encoder workstation hardening (Baseline). Maturity 1.
- HISS-H04-04 Lock vendor access and audit trail (Baseline). Maturity 1.

### H05 Building management and IoT

- HISS-H05-02 BMS and IoT segmentation (Enhanced). Maturity 0.
- HISS-H05-03 Default credential removal on engineering devices (Baseline). Maturity 0.
- HISS-H05-04 OEM access control (Baseline). Maturity 0.
- HISS-H05-01 Engineering asset inventory (Baseline). Maturity 1.
- HISS-H05-05 Protocol exposure and engineering workstation review (Enhanced). Maturity 1.

### H06 CCTV

- HISS-H06-01 Camera and recorder network separation (Enhanced). Maturity 0.
- HISS-H06-02 Footage retention and access (Baseline). Maturity 1.
- HISS-H06-03 Footage export logging (Baseline). Maturity 1.
- HISS-H06-04 CCTV signage and placement (Baseline). Maturity 1.

### H07 Vendor remote access

- HISS-H07-02 Named vendor accounts (Baseline). Maturity 0.
- HISS-H07-01 One approved remote access path (Baseline). Maturity 1.
- HISS-H07-03 Time windowed vendor access with approval (Baseline). Maturity 1.
- HISS-H07-05 Removal of unapproved remote tools (Baseline). Maturity 1.

### H08 Guest data lifecycle

- HISS-H08-01 Guest data map from booking to archive (Baseline). Maturity 0.
- HISS-H08-04 Retention and deletion schedule (Baseline). Maturity 0.
- HISS-H08-02 Identity document capture and masking (Baseline). Maturity 1.
- HISS-H08-05 Guest rights handling (Baseline). Maturity 1.
- HISS-H08-06 Minimisation in loyalty and marketing (Baseline). Maturity 1.
- HISS-H08-03 Legal guest register duties (Baseline). Maturity 2.

### H09 Cloud and SaaS

- HISS-H09-01 SaaS and cloud register (Baseline). Maturity 1.
- HISS-H09-03 Provider assurance (Baseline). Maturity 1.
- HISS-H09-04 Cloud administrator protection (Baseline). Maturity 1.
- HISS-H09-05 Data location and transfer check (Enhanced). Maturity 1.

### H10 Third party and franchise management

- HISS-H10-01 Supplier security clauses (Baseline). Maturity 1.
- HISS-H10-03 Security schedule in franchise and management agreements (Baseline). Maturity 1.

## Unmet by standard

Source backed figures use direct (D) rows with verified targets only. Indicative figures use every scored row. A clause is unmet when no applicable control mapped to it is met.

| Framework | Clauses | Reached | Unreached | Met (indicative) | Met (source backed) | Source backed percent | Indicative percent |
|---|---|---|---|---|---|---|---|
| ISO/IEC 27001:2022 Annex A | 93 | 54 | 37 | 0 | 0 | 3.5 | 8.9 |
| PCI DSS v4.0.1 | 12 | 12 | 0 | 0 | 0 | 18.8 | 22.9 |
| NIST CSF 2.0 | 22 | 17 | 4 | 0 | 0 | 0.0 | 13.6 |
| CIS Controls v8.1 | 18 | 16 | 1 | 0 | 0 | 18.1 | 21.5 |
| CSA CCM v4 | 17 | 15 | 2 | 0 | 0 | 5.9 | 15.8 |
| NIST SP 1800-27 | 8 | 8 | 0 | 0 | 0 | 18.8 | 23.4 |
| HTNG guidance | 5 | 3 | 0 | 0 | 0 | 16.7 | 29.2 |

Percentages count clauses that no HISS control reaches as zero where the clause list is known. Otherwise they cover reached clauses only.

Unmet clauses, CSA CCM v4: A&A, BCR, CCC, CEK, DCS, DSP, GRC, HRS, IAM, IVS, LOG, SEF, STA, TVM and UEM.

Clauses no HISS control reaches, CSA CCM v4 (2): AIS and IPY.

Unmet clauses, CIS Controls v8.1: 1, 1.1, 2, 2.1, 2.2, 2.5, 3, 3.2, 3.8, 3.10, 3.11, 4, 4.1, 5, 6, 6.8, 7, 8, 8.2, 10.1, 11, 11.2, 11.5, 12, 12.2, 13, 14, 14.1, 14.9, 15, 15.1, 15.4, 15.6, 17, 17.2 and 18.

Clauses no HISS control reaches, CIS Controls v8.1 (1): 9.

Unmet clauses, NIST CSF 2.0: DE.CM, GV.OC, GV.OV, GV.PO, GV.RM, GV.RR, GV.SC, ID.AM, ID.IM, ID.RA, PR.AA, PR.AT, PR.DS, PR.IR, PR.PS, RC.RP and RS.CO.

Clauses no HISS control reaches, NIST CSF 2.0 (4): RC.CO, RS.AN, RS.MA and RS.MI.

Unmet clauses, HTNG guidance: Converged network policy per user and device, Door lock solution criteria and Secure Payments Framework tokenisation.

Unmet clauses, ISO/IEC 27001:2022 Annex A: A.5.1, A.5.2, A.5.5, A.5.9, A.5.10, A.5.11, A.5.12, A.5.14, A.5.15, A.5.16, A.5.17, A.5.18, A.5.19, A.5.20, A.5.21, A.5.22, A.5.23, A.5.24, A.5.26, A.5.29, A.5.30, A.5.31, A.5.33, A.5.34, A.5.35, A.5.36, A.5.37, A.6.2, A.6.3, A.6.5, A.6.7, A.7.4, A.7.7, A.7.8, A.7.14, A.8.1, A.8.2, A.8.3, A.8.5, A.8.7 and 19 more.

Clauses no HISS control reaches, ISO/IEC 27001:2022 Annex A (37): A.5.3, A.5.4, A.5.6, A.5.7, A.5.13, A.5.25, A.5.27, A.5.28, A.5.32, A.6.1, A.6.4, A.6.6, A.6.8, A.7.1, A.7.2, A.7.3, A.7.5, A.7.6, A.7.9, A.7.10, A.7.11, A.7.12, A.7.13, A.8.4, A.8.6, A.8.14, A.8.21, A.8.23, A.8.25, A.8.26, A.8.27, A.8.28, A.8.29, A.8.30, A.8.31, A.8.33 and A.8.34.

Unmet clauses, PCI DSS v4.0.1: 1, 2, 2.2.1, 3, 4, 4.2.1, 5, 6, 6.3.3, 7, 8, 8.4.3, 9, 10, 11, 12, 12.3.4, 12.8.2 and 12.8.4.

Unmet clauses, NIST SP 1800-27: Auditing logging and reporting, Guest Wi-Fi internet only tied to reservation, Lock server receives room number only, Protected zone for PMS and supporting systems, Protection against lateral movement and privilege escalation, Protection of personal information, Role based authentication and access control and Tokenization with allowlisting.

Crosswalk targets outside the clause list are scored in standard_view.csv but are not part of the framework percentages: ISO27001 C.4.3, ISO27001 C.5.3, ISO27001 C.6.1.3, ISO27001 C.6.1.2, ISO27001 C.8.2 and ISO27001 C.9.3.2.

## Unmet by jurisdiction

Only VERIFIED obligations are scored. SECONDARY obligations are tracked and are not scored.

| Jurisdiction | Basis | Obligations scored | Ready | Partial | Not ready | Tracking | Readiness percent |
|---|---|---|---|---|---|---|---|
| IN | actual | 14 | 0 | 0 | 14 | 1 | 20.7 |
| ALL | all configured jurisdictions | 14 | 0 | 0 | 14 | 1 | 20.7 |

| Obligation | Jurisdiction | Provision | State | Readiness percent | Unmet controls |
|---|---|---|---|---|---|
| OBL-IN-01 | IN | s.8(5) | not ready | 30.0 | HISS-F2-02; HISS-F5-01; HISS-F4-03; HISS-H10-01; HISS-F1-03 |
| OBL-IN-02 | IN | s.8(6) | not ready | 0.0 | HISS-F6-03 |
| OBL-IN-03 | IN | s.8(7) | not ready | 12.5 | HISS-H08-04; HISS-H08-05 |
| OBL-IN-04 | IN | ss.5 and 6 | not ready | 12.5 | HISS-H08-06; HISS-H08-01 |
| OBL-IN-05 | IN | s.9 | not ready | 25.0 | HISS-H08-06 |
| OBL-IN-06 | IN | Rights requests (PIB summary) | not ready | 25.0 | HISS-H08-05 |
| OBL-IN-07 | IN | Rule 7(1) | not ready | 0.0 | HISS-F6-03 |
| OBL-IN-08 | IN | Rule 7(2) | not ready | 0.0 | HISS-F6-03 |
| OBL-IN-09 | IN | Rule 6 | not ready | 30.0 | HISS-F6-01; HISS-H01-02; HISS-F6-04; HISS-F4-04; HISS-H08-02 |
| OBL-IN-10 | IN | Incident reporting and point of contact | not ready | 12.5 | HISS-F6-03; HISS-F1-02 |
| OBL-IN-11 | IN | Logs and clock synchronisation | not ready | 25.0 | HISS-F6-01 |
| OBL-IN-12 | IN | Duty of keepers of accommodation | not ready | 37.5 | HISS-H08-03; HISS-H08-02 |
| OBL-IN-14 | IN | Card on file restriction | not ready | 37.5 | HISS-H01-02; HISS-H02-05 |
| OBL-IN-15 | IN | Para 9(a); Annexure 1 paras 1.18 and 2.1 | not ready | 41.7 | HISS-H02-04; HISS-H02-06; HISS-H01-02 |

Tracking only (SECONDARY, not scored): OBL-IN-13 Accommodation reporting basis (as reported).

## ISO only comparison

Each hotel requirement is classed under ISO/IEC 27001 Annex A alone and under HISS (assumption A37). Under ISO alone: 0 specific, 21 generic, 0 absent. Under HISS: 21 specific, 0 generic, 0 absent. Requirements counted: 21.

No hand classification file was found. The automatic rule is circular because the ISO rows were written to cover the requirements, so supply inputs/iso_only_manual.csv (req_id, class, reason) as a sensitivity check.

Of 67 unmet controls, 1 have no direct or partial ISO27001 row, so an ISO only review would not point to them.

- HISS-H02-01 Cardholder data environment scope per property. Maturity 1. ISO27001 rows: J only.

## Roadmap waves

| Wave | Items | Baseline | Enhanced |
|---|---|---|---|
| Wave 1 (0 to 90 days) | 30 | 30 | 0 |
| Wave 2 (3 to 6 months) | 28 | 28 | 0 |
| Wave 3 (6 to 12 months) | 9 | 5 | 4 |

Priority = level weight x tier weight x maturity gap / effort weight. See roadmap.csv for every item.

Wave cut offs are 10 for wave 1 and 4 for wave 2 (assumed). Moving both by 20 percent changes the wave of 25 items (table below and results.json). Items per wave: base 30, 28, 9; cut offs x0.8 32, 26, 9; cut offs x1.2 15, 35, 17.

| Control | Title | Level | Priority | Base wave | Cut offs x0.8 | Cut offs x1.2 |
|---|---|---|---|---|---|---|
| HISS-F4-01 | Individual logons on shared terminals | Baseline | 10.0 | 1 | 1 | 2 |
| HISS-F4-02 | Privileged access | Baseline | 10.0 | 1 | 1 | 2 |
| HISS-F4-04 | Quarterly access review per property | Baseline | 10.0 | 1 | 1 | 2 |
| HISS-F5-02 | Patch windows that fit round the clock operation | Baseline | 10.0 | 1 | 1 | 2 |
| HISS-F5-05 | Malware protection | Baseline | 10.0 | 1 | 1 | 2 |
| HISS-F6-03 | Incident response with a notification clock matrix | Baseline | 10.0 | 1 | 1 | 2 |
| HISS-H01-01 | Role based PMS access | Baseline | 10.0 | 1 | 1 | 2 |
| HISS-H01-04 | PMS vendor patch and support status | Baseline | 10.0 | 1 | 1 | 2 |
| HISS-H02-01 | Cardholder data environment scope per property | Baseline | 10.0 | 1 | 1 | 2 |
| HISS-H02-03 | Payment terminal inspection | Baseline | 10.0 | 1 | 1 | 2 |
| HISS-H02-05 | Card data retention limits | Baseline | 10.0 | 1 | 1 | 2 |
| HISS-H02-06 | PCI DSS validation evidence | Baseline | 10.0 | 1 | 1 | 2 |
| HISS-H07-01 | One approved remote access path | Baseline | 10.0 | 1 | 1 | 2 |
| HISS-H07-03 | Time windowed vendor access with approval | Baseline | 10.0 | 1 | 1 | 2 |
| HISS-H07-05 | Removal of unapproved remote tools | Baseline | 10.0 | 1 | 1 | 2 |
| HISS-H08-01 | Guest data map from booking to archive | Baseline | 9.0 | 2 | 1 | 2 |
| HISS-H08-04 | Retention and deletion schedule | Baseline | 9.0 | 2 | 1 | 2 |
| HISS-H04-01 | Lock server receives room number only | Baseline | 4.0 | 2 | 2 | 3 |
| HISS-H04-02 | Key encoder workstation hardening | Baseline | 4.0 | 2 | 2 | 3 |
| HISS-H04-04 | Lock vendor access and audit trail | Baseline | 4.0 | 2 | 2 | 3 |
| HISS-H05-03 | Default credential removal on engineering devices | Baseline | 4.0 | 2 | 2 | 3 |
| HISS-H05-04 | OEM access control | Baseline | 4.0 | 2 | 2 | 3 |
| HISS-H06-02 | Footage retention and access | Baseline | 4.0 | 2 | 2 | 3 |
| HISS-H06-03 | Footage export logging | Baseline | 4.0 | 2 | 2 | 3 |
| HISS-H06-04 | CCTV signage and placement | Baseline | 4.0 | 2 | 2 | 3 |
