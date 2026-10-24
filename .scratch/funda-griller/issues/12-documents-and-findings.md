# 12: Documents and Findings

**What to build:** The user uploads seller and agent PDFs (Vragenlijst, Lijst van zaken, anything else) against a Listing, and the funda brochure is attached automatically. The model extracts Findings such as asbestos, leaks, leased solar panels, erfpacht, subsidies and what stays or goes, each with a page reference and a seller-stated mark. Findings feed Flags and the Verdict, and re-upload or removal rebuilds the Case.

**Blocked by:** 09 (Verdict and Bid Advice)

**Status:** ready-for-agent

- [ ] Upload, list and remove Documents per Listing
- [ ] The funda brochure is downloaded (with a browser user agent) and attached as a Document
- [ ] Findings are extracted once per Document, cached, and each cites its page
- [ ] Findings are marked seller-stated and rendered distinctly from Source facts
- [ ] A Finding can raise a Flag through the rule set
- [ ] Removing or re-uploading a Document rebuilds the Case without leftover Findings
- [ ] An unreadable Document is reported as such, never silently treated as analysed
- [ ] Documents are stored locally and shown only in the app's own UI
- [ ] Tests use the fake LLM client; the real brochure from the prototype is used as a fixture
