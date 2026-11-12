# Content sources

Rule: link or ingest only material you have the right to use. Do not download or commit pirated or copyrighted books (Harrison, Robbins, Bailey and Love, Park, etc.).

## Official
- NBEMS FMGE page and Information Bulletin (syllabus, blueprint, scheme): https://natboard.edu.in/viewnbeexam?exam=fmge
- NMC UG curriculum (CBME): https://www.nmc.org.in/information-desk/for-colleges/ug-curriculum/

## Past papers
NBEMS does not officially release FMGE papers. Papers online are memory-based and compiled by coaching sites, so treat them as copyrighted compilations: link to them, do not copy them. Questions your brother recalls or writes himself can be added to `content/seed/` in the same JSON format.

## Open-licence study text (safe to ingest with attribution)
- OpenStax Anatomy and Physiology 2e (CC BY 4.0): https://openstax.org/details/books/anatomy-and-physiology-2e
- OpenStax Microbiology (CC BY 4.0): https://openstax.org/details/books/microbiology
- NCBI Bookshelf (check each title's licence; StatPearls chapters are CC BY-NC-ND, so use for reference/linking, not remixing): https://www.ncbi.nlm.nih.gov/books/
- Open Textbook Library, Medicine and health: https://open.umn.edu/opentextbooks/

## How the library is built
`python content/tools/fetch_open_books.py` downloads OpenStax Anatomy and Physiology 2e and Microbiology (CC BY 4.0) from GitHub, `python -m app.ingest` indexes them (about 7,000 passages), and the tutor and question generator work only from those passages. Every answer and generated question carries its book and section as the source. Attribution to OpenStax / Rice University is required and is shown in the app.

Gaps: OpenStax does not cover clinical subjects (Medicine, Surgery, OBG, Paediatrics, Pharmacology, Pathology, Forensic Medicine, Community Medicine, etc.). Fill those with your brother's notes and any other material you are allowed to use, in `content/raw/`.

## GitHub search results (checked 2026-11-12)
Used:
- openstax/osbooks-anatomy-physiology and openstax/osbooks-microbiology (CC BY 4.0).

Usable with care:
- medmcqa/medmcqa: the repo is code only (MIT). The 194k AIIMS / NEET PG MCQs with explanations are hosted on medmcqa.github.io and Hugging Face. Licence statements conflict (Apache-2.0 on the dataset card, CC BY-NC-SA on another page), so use it non-commercially with credit. Import with `python -m app.import_medmcqa train.json`. These are NEET PG / AIIMS questions, not FMGE papers, but the syllabus overlaps heavily.

Not used (no licence file, so all rights reserved by default). Ask the owner for permission first:
- Elrondthewise/FMGE-REPO: FMGE Anki deck for OBGYN (.apkg). Says educational use only, do not re-upload.
- nishchalnishant/bro: NEET PG notes in markdown for all subjects.
- vanderbilt-internal-medicine/vanderbilt-internal-medicine.github.io: internal medicine handbook, US-oriented.
- MedPocket/OxfordMH, MedPocket/BRS, MedPocket/medlib: look like copies of commercial books. Avoid.

## Adding your own material
Put notes or PDFs you own in `content/raw/` and run `python -m app.ingest`.
