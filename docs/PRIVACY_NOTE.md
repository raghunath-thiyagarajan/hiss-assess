# Privacy note

The case data in this repository come from a real hotel group with six properties. The group has not agreed to be named, so every item that could identify it has been replaced before publication. This note says what was changed and how to keep the repository clean.

## What was anonymised

- Properties. The six properties are labelled PROP-A to PROP-F. The letters follow a fixed order that only the author holds. The mapping is not part of the repository. The group wide view is labelled GROUP.
- Systems. Every system label has the form property label, role code and a two digit number, for example PROP-C-SQL-01. Labels no longer carry town names or vendor names.
- Vendors and products. Product names of the group's own systems are replaced by roles. The reservation and property management product is shown as PMS. The finance package is shown as the accounting package (code ACCT). The guest internet product is shown as the guest internet platform (code GNET). The in room technology product is shown as the in room platform (codes IRS for the server and IRG for the gateway). The remote support product that appears in one vulnerability title is shown as the remote support tool.
- Role keys in the configuration files follow the same roles (pms, accounting, guest_internet, inroom and inroom_gw).
- Names. The real group name, the names of people connected with it, domain names, e-mail addresses, user names, IP addresses, MAC addresses and licence keys are not present anywhere in the repository.

## What was kept

Vulnerability titles that name public software, such as Microsoft Windows components, OpenSSL, Apache or OpenSSH, are kept because they describe common weaknesses and do not point to the group. The findings are counts and plugin titles only. Raw scan exports, report files from the scanner and any file listing real host names are not included and must never be added.

## Simulated answers

The self assessment answers used for the case are simulated from the Capstone 1 evidence by fixed rules and are tagged A26 simulated. They show how the toolkit behaves. They are not statements about any property.

## Keeping the repository clean

`tests/test_hygiene.py` scans every text file for IPv4 addresses, MAC addresses, domain like names, e-mail addresses, user paths, licence keys, blocked vendor and town words, AI product names, dashes and serial commas. The blocked words are held as digests, so the test does not contain the names it blocks. A person who runs the toolkit on their own data can list private terms such as a group name, one per line, in `tests/private_terms.txt`. That file is ignored by git and is used only on the local machine.

Run the scan before every commit.

```
python -m unittest discover -s tests
```
