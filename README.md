# HISS-Assess: Hospitality Information Security Standard Assessment Toolkit

HISS-Assess is a small Python toolkit built for a university capstone in MS Cyber Security. It is the companion to HISS-RAT, the risk assessment toolkit from Capstone 1. HISS-RAT turns scan evidence into a risk register. HISS-Assess takes the HISS control catalogue, a self assessment of one hotel property and optional HISS-RAT findings. It produces maturity scores, compliance views against reference frameworks, legal readiness by jurisdiction, a gap report, a remediation roadmap and one self contained HTML dashboard.

The toolkit uses the Python standard library only. It works offline and makes no network calls.

Author: Raghunath Thiyagarajan, MS Cyber Security, REVA University.

Licence: MIT, see LICENSE. To cite the work, see CITATION.cff.

## About this repository

This repository is the toolkit that accompanies the Year 2 capstone, the Capstone 2 Final Report by Raghunath Thiyagarajan. The report describes the HISS Framework v1.0, a hotel specific information security standard with 80 controls, mapped to ISO/IEC 27001:2022, PCI DSS v4.0.1, NIST CSF 2.0, CIS Controls v8.1 and CSA CCM v4 and to legal duties in India, the UAE, the US and Europe. The framework is held here as plain files in `catalogue/` and written out as `docs/HISS_Standard_v1.md`. The report validates the toolkit on a six property hotel group, called the case group in the report. A link to the report will be added here when it is published.

The case data are anonymised. The six properties appear as PROP-A to PROP-F, systems carry property and role labels such as PROP-C-SQL-01, and no vendor product names, host names or addresses are included. The answers in the case are simulated from Capstone 1 evidence and are not findings about any property. See `docs/PRIVACY_NOTE.md`.

## Quick start

Install. Python 3.10 or later is needed. There are no packages to install. Download or clone the repository, open a terminal in its folder and check that the tool starts. On Windows use `py` in place of `python`.

```
cd hiss-assess
python run_all.py --help
```

One command. This assesses one property with the settings in `config/assessment_config.json`. The first run for a new property name writes a blank questionnaire and stops. Fill in the `maturity` column of `inputs/assessment_NAME.csv` and run the same command again.

```
python run_all.py --property NAME --config config/assessment_config.json
```

Tests. The suite uses only the standard library.

```
python -m unittest discover -s tests
```

Reproduce the case. The case figures in the report come from four runs. Each writes its own folder under `outputs/` and uses simulated answers with assumed weights.

```
python run_all.py --property PROP-A PROP-B PROP-C PROP-D PROP-E PROP-F --config config/case_config.json --out-dir outputs/case --no-standard
python run_all.py --property GROUP --config config/case_config.json --out-dir outputs/case_group --no-standard
python run_all.py --property GROUP --config config/case_whatif_config.json --out-dir outputs/whatif_group --no-standard
python run_all.py --property PROP-C GROUP --config config/case_config_v4_proposal.json --out-dir outputs/v4_proposal --no-standard
```

The first two commands give the six property runs and the group run for India only. The third gives the what if group run, which is the only one with more than one jurisdiction. The fourth checks the proposal for the roadmap settings. The folders are rewritten with the same content each time, apart from the property order in the group summary files, which follows the order of the names on the command line. Open `outputs/case_group/dashboard.html` in any browser to see the group view.

Limitations. All weights, caps, thresholds and wave cut offs are assumed values and the case answers are simulated, so the case results show how the toolkit behaves and say nothing about the real security of a property. The tool is not a certification scheme and the legal content is not legal advice. The full list is in the Limitations section below.

## What it does

1. Loads the catalogue from plain files and checks the schema and every cross reference.
2. Decides which controls apply to the property from its profile (S, M or G), the requirement level of each control and the active triggers.
3. Writes a blank questionnaire for the applicable controls when none exists yet.
4. Reads the answers (maturity 0 to 4 per control) and, if present, anonymised HISS-RAT findings that cap the maturity of linked controls.
5. Scores controls, domains and the property and rolls several properties up to a group view.
6. Builds a standard view: coverage of each clause of ISO/IEC 27001 Annex A, PCI DSS, NIST CSF, CIS Controls and CSA CCM, with source backed and indicative figures side by side and a list of clauses that no control reaches.
7. Scores readiness for verified legal obligations in the configured jurisdictions and lists secondary items as tracking.
8. Lists gaps by domain, standard and jurisdiction and compares the hotel requirements under ISO/IEC 27001 alone and under HISS.
9. Builds a roadmap with priorities and three waves.
10. Writes the HISS standard as Markdown from the catalogue so that text and data never diverge.

## Usage details

The one command from the Quick start works as follows.

```
python run_all.py --property NAME --config config/assessment_config.json
```

The first run for a property writes a blank questionnaire (`inputs/assessment_NAME.csv`) and a guide file with the question and expected evidence for each control (`inputs/assessment_NAME_questions.csv`). It then stops. Fill in the `maturity` column and run the same command again. The second run writes everything in `outputs/` and `docs/HISS_Standard_v1.md`. Open `outputs/dashboard.html` in any browser.

Several properties can be run together: `--property A B C`. Each property then gets its own folder under `outputs/` and a `group_summary.csv` and `group_results.json` are written next to them.

| Option | Meaning |
|---|---|
| `--catalogue DIR` | catalogue folder, default `catalogue/` |
| `--inputs-dir DIR` | folder with the assessment files, default `inputs/` |
| `--hissrat-dir DIR` | anonymised HISS-RAT files, default `inputs/hissrat/` when it exists |
| `--no-hissrat` | ignore HISS-RAT files |
| `--out-dir DIR` | output folder, default `outputs/` |
| `--docs-dir DIR` | folder for `HISS_Standard_v1.md`, default `docs/` |
| `--no-standard` | do not write the standard |
| `--template-only` | only write the blank questionnaire |
| `--allow-errors` | continue when the catalogue check reports errors |

To check only the catalogue: `python src/catalogue.py [folder] [--full]`. The `--full` flag adds the size checks of the design: 76 to 84 controls, 4 to 6 per domain, at least three controls per hotel reality. To write only the standard: `python src/render_standard.py [folder] [output file]`.

## Folder layout

```
hiss-assess/
  run_all.py              one command for the whole pipeline
  README.md  LICENSE  CITATION.cff
  catalogue/              controls, crosswalk, obligations, profiles, realities, family map, requirements (see SCHEMA.md)
  config/
    assessment_config.json   profile, operating model, triggers, jurisdictions and all weights (assumed values)
    framework_clauses.json   clause lists used only to find clauses that no control reaches
    family_patterns.json     finding family patterns for the HISS-RAT ingest
    domains.json             domain names
    system_roles.json        system role to HISS domain table for the role aware cap rule (assumed)
    case_config.json         settings of the validation case: India only, simulated answers (assumed values)
    case_whatif_config.json  same settings with Europe, the UAE and the US added as what if or judged jurisdictions
    case_config_v4_proposal.json  check of the two proposed changes to effort and wave cut off, not the base run
  inputs/                 assessment_<property>.csv (PROP-A to PROP-F and GROUP) and the hissrat/ folder
  outputs/                generated tables, results.json and dashboard.html
  docs/                   HISS_Standard_v1.md written by the tool, V6_review_form.md and PRIVACY_NOTE.md
  src/                    one module per task, all importable and free of side effects on import
  tests/fixtures/         sample catalogue, sample inputs and sample settings
```

Modules in `src/`: `catalogue.py` (load and check), `applicability.py`, `template.py` (questionnaire), `ingest_hissrat.py`, `score.py`, `gap.py`, `roadmap.py`, `sensitivity.py`, `render_standard.py`, `report.py`, `dashboard.py` with `dashboard_template.html`, `pipeline.py` (one run as a pure function), `settings.py` and `common.py`.

## Inputs

### Catalogue

Seven files in `catalogue/`. The column contract is in `catalogue/SCHEMA.md`. In short: `controls.csv` holds one row per control, `crosswalk.csv` one row per control and target clause with a strength of D, P or J, `obligations.csv` one row per legal duty with the status VERIFIED or SECONDARY, `profiles.json` the profiles, triggers and operating models, `realities.csv` the hotel realities, `family_map.csv` the link from the 12 Capstone 1 finding families to controls and `requirements.csv` the hotel requirements with their linked controls.

### Questionnaire

`inputs/assessment_<property>.csv` has four columns: `control_id`, `maturity`, `evidence_ref` and `comment`. Maturity is a whole number from 0 to 4 (0 not in place, 1 ad hoc, 2 documented, 3 implemented with evidence, 4 measured and reviewed). A blank maturity means not answered and counts as 0 by default. The toolkit reports rows for unknown or inapplicable controls, duplicate rows, values outside 0 to 4 and ratings of 3 or more with no evidence reference.

### HISS-RAT files (optional)

Optional hand classification for the ISO only comparison: `inputs/iso_only_manual.csv`. Put these Capstone 1 outputs in `inputs/hissrat/`: `systems_normalised.csv` (required), `findings_normalised.csv` and `risk_register.csv`. Without the findings file the `plugins_low_plus` column of the systems file is used. Without the risk register the role tier from the config is used. Only anonymised labels such as PROP-C-SQL-01 appear in these files.

### Settings

`config/assessment_config.json` holds defaults at the top level and overrides per property under `properties`. Keys:

| Key | Meaning |
|---|---|
| `profile` | S, M or G |
| `operating_model` | owned, managed or franchised (decides the accountable party of each control) |
| `triggers` | active triggers from T1 to T5 |
| `jurisdictions` | configured jurisdiction tags with a basis label such as actual or what if |
| `input_status` and `input_tag` | how the answers were obtained. Use `simulated` and `A26` for simulated answers. The label is printed on the dashboard and in the gap report |
| `met_threshold` and `target_maturity` | 3 and 3 by default |
| `unanswered_as` | maturity given to unanswered controls, 0 by default |
| `strength_weights` | D 1.0, P 0.5, J 0.25 |
| `finding_caps` | Critical 1, High 1, Medium 2 |
| `level_weights`, `tier_weights`, `effort_weights` | roadmap weights |
| `domain_default_tier`, `effort_by_domain`, `effort_by_control` | tier and effort where no scan evidence exists |
| `waves` and `wave_overrides` | priority cut offs and manual wave choices |
| `hissrat` | role to tier table, the properties whose systems are in scope and `role_aware` (true by default) |
| `iso_only_specific_req_ids` | requirement ids judged specific under ISO alone |

Every value is an assumption (see the limits below).

## Outputs

| File | Content |
|---|---|
| `applicability.csv` | every control with applicable yes or no, the reason, active triggers and the accountable party |
| `control_scores.csv` | one row per applicable control: self assessed maturity, cap, effective maturity, met |
| `domain_scores.csv` | mean maturity, met count and capped count per domain |
| `standard_view.csv` | coverage per target clause with source backed and indicative figures and the clauses no control reaches |
| `jurisdiction_readiness.csv` | readiness per obligation, tracking rows for secondary items and roll ups per jurisdiction |
| `gap_report.md` | unmet controls by domain, standard and jurisdiction, the ISO only comparison and the wave summary |
| `roadmap.csv` | ranked items with priority, wave, drivers and affected systems |
| `iso_only_comparison.csv` | each hotel requirement classed under ISO alone and under HISS |
| `results.json` | all results in one file, including catalogue statistics and sensitivity |
| `dashboard.html` | one self contained page with tabs for overview, domains, standards, jurisdictions, gaps and roadmap |
| `docs/HISS_Standard_v1.md` | the standard written from the catalogue |

The dashboard has inline CSS and JavaScript only and uses no external addresses or fonts. It follows the light or dark setting of the system and is laid out to work at phone width.

## Scoring

```
effective maturity = min(self assessed maturity, finding cap)
met                = effective maturity >= 3
domain maturity    = mean effective maturity of applicable controls in the domain (also shown as percent of 4)
property maturity  = mean effective maturity of all applicable controls
group maturity     = plain mean of the property percentages

standard coverage (per target clause) = max over mapped applicable controls of  weight(strength) x maturity / 4
    weights: D 1.0, P 0.5, J 0.25
    source backed = D rows with a VERIFIED target only
    indicative    = all rows except NOT VERIFIED targets

jurisdiction readiness (per VERIFIED obligation) = mean effective maturity of its applicable linked controls / 4
    ready = every linked control met, not ready = none met, partial = some met
    SECONDARY obligations are listed as tracking and are not scored

priority = level weight x tier weight x maturity gap / effort weight
    maturity gap = target maturity - effective maturity (items with a gap of 0 are left out)
    tier weight  = Capstone 1 tier weight of the most critical affected system or the domain default
```

Default weights: level Baseline 2 and Enhanced 1, tier 1 to 4 as 5, 3, 2 and 1, effort S, M and L as 1, 2 and 3. Waves: priority 10 or more is wave 1 (0 to 90 days), 4 or more is wave 2 (3 to 6 months) and anything lower is wave 3 (6 to 12 months). The cut offs (`waves.wave1_min_priority` and `waves.wave2_min_priority`) and the effort sizes (`effort_weights`, `effort_by_domain` and `effort_by_control`) are settings in the config file and are assumed. The wave sensitivity table (in `results.json` under `roadmap.wave_sensitivity`, in the gap report and on the Roadmap tab) lists the items whose wave changes when both cut offs move by 20 percent down and up, with the number of items per wave in each case.

Applicability: Baseline controls apply to every profile. Enhanced controls apply to the profiles listed on the control, normally M and G. An Enhanced control that does not list the profile applies when one of its triggers is active, which makes it mandatory for a small property.

Finding caps (assumed rule, A25): a Critical or High finding on an in scope system caps a control at maturity 1 and a Medium finding caps it at 2. Low findings set no cap. A cap lowers the self assessed value and never raises it. In scope systems are the systems of the property being assessed or all systems for a group run. The cap is role aware: a finding caps a control only when the control is in the family map for the finding family and the control domain is allowed for the role of the affected system in `config/system_roles.json`. Foundation domains F1 to F6 are allowed for every role. For example a domain controller finding can cap vendor access and foundation controls but not a guest Wi-Fi control. A system whose role is not listed falls back to the earlier behaviour (the cap reaches every linked control) and a warning is written to the results. Set `hissrat.role_aware` to false in the config to switch the role rule off. The role to domain lists are judgement and are assumed.

Capped by scan: a control is capped only when its final maturity was lowered by a scan cap. The column `capped_by_scan` (control scores and domain scores) and the figure `overall.capped_by_scan` in `results.json` use this one meaning. The older column `capped` repeats the same value so earlier files keep working. A control that carries a cap which did not bind (the self assessed value was already at or below the cap) is counted separately as `controls_with_cap`.

Jurisdictions: an obligation is in scope when its tag equals a configured tag or one is the parent of the other (AE covers AE-DXB, US covers US-NY). When the trigger text of an obligation names T1 to T5 that trigger must be active.

Clauses are rolled up before they are listed as unreached: PCI DSS to the principal requirement, CSF to the category, CIS safeguards to the control number and CCM to the domain. Rows given at sub level (CIS safeguards and PCI sub requirements) are also summarised on their own as sub level clauses, so both views are shown. ISO rows with C. identifiers are management system clauses and are scored apart from Annex A.

ISO only comparison: a requirement is generic under ISO alone when a linked control has an ISO27001 row of strength D or P and absent when it has only J rows or none. It is specific only when listed in `iso_only_specific_req_ids`. Under HISS it is specific when at least one catalogue control is linked and absent otherwise. This automatic rule is circular, because the ISO rows were written to cover the requirements, so nearly every requirement comes out generic. A hand classification is therefore read from `inputs/iso_only_manual.csv` when the file exists (columns `req_id`, `class` and `reason`, with class specific, generic or absent). It is written to the columns `iso_class_manual` and `manual_reason` of `iso_only_comparison.csv` and both counts are reported. The manual file is the sensitivity check on the automatic result.

Sensitivity: each weight is moved by 20 percent up and down in turn. The roadmap is rebuilt and the ranking of domains by total priority is compared with the base ranking by Spearman rank correlation. Strength weights are checked on the ranking of frameworks by indicative coverage. Results are in `results.json` and the dashboard footer.

## Tests and privacy scan

The test commands and the case reproduction commands are in the Quick start above. The suite covers the catalogue, the scoring logic, the ingest of HISS-RAT files, the outputs and a hygiene scan of the repository (no addresses, host names, vendor names, dates or dashes). The privacy scan can also look for private terms such as a real group name. List one term per line in `tests/private_terms.txt`. That file is untracked and is skipped by the scan.

## Sample catalogue

`tests/fixtures/sample_catalogue/` holds a small catalogue of 12 controls in 4 domains in the exact schema, with sample inputs and settings in `tests/fixtures/`. It is test data and not part of the HISS standard. Try the toolkit with it:

```
python run_all.py --property SAMPLEHOTEL --config tests/fixtures/sample_config.json --catalogue tests/fixtures/sample_catalogue --inputs-dir tests/fixtures/sample_inputs --out-dir outputs/sample --docs-dir outputs/sample
```

## Limitations

- All weights, caps, thresholds, effort sizes, wave cut offs, profile choices and trigger choices are assumed values from the assumption register (A20 to A31). They are not measured. Change them in `config/assessment_config.json`. The sensitivity check shows how far the rankings move when each weight changes by 20 percent.
- Answers used for the case group are simulated from the Capstone 1 evidence (A26). Simulated runs are tagged through `input_status` and `input_tag` and the tag is printed on the dashboard and in the gap report. A simulated run shows how the toolkit behaves. It is not a finding about a property.
- Jurisdictions other than India are what if or judged runs for the case group, which operates only in India. The basis column says which.
- Coverage uses the maximum over mapped controls, not a sum, so many weak mappings do not add up to a strong one. Weights of D, P and J are the author's choice.
- Only rows whose target is VERIFIED count as source backed. NOT VERIFIED crosswalk targets are shown but never scored. SECONDARY legal items are tracked and never scored.
- The clause lists in `config/framework_clauses.json` use shortened titles written for this toolkit. Check them against the source sheets before quoting them. SP 1800-27 and HTNG have no fixed clause list and are shown only as reached.
- HISS-RAT caps are only as strong as the scan evidence. Most Capstone 1 scans were uncredentialed, so a missing finding does not mean a system is secure.
- An unanswered control counts as maturity 0 so that gaps are not hidden. The completeness figure is shown next to every result.
- The tool is not a certification scheme and the legal content is not legal advice.

## Data privacy note

No raw addresses, host names, user names, domain names or licence keys are stored in this repository or written to the outputs. The case data are anonymised: properties are labelled PROP-A to PROP-F, systems appear as property and role labels such as PROP-C-SQL-01 and vendor product names are replaced by role names. Output files carry no absolute paths and no dates. Raw scan exports must not be added to the repository. See `docs/PRIVACY_NOTE.md`.
