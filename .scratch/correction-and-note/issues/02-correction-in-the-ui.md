# 02: Correctie in the UI

**Type:** task

**Blocked by:** 01

**Status:** resolved

**What to build:** Spec decision 11. A pencil beside each correctable fact in the Dossier opens a small dialog for the value and the explanation (**Toelichting**), with a way to remove the Correctie. A corrected fact shows the label **gecorrigeerd**, with the original value (struck through, with its herkomst) and the explanation beside it. After a re-capture where the Listing's value changed, the fact shows a short notice ("De advertentie noemt nu 120 m²") and the choice to keep or remove the Correctie. Follow `DESIGN.md`. UI copy is Dutch.

- [x] Pencil and dialog for every correctable fact, including one the Listing leaves out
- [x] **gecorrigeerd** label, original value and Toelichting shown beside the fact
- [x] Remove the Correctie from the dialog
- [x] Notice when the Listing's value has changed since the Correctie was made
- [x] The Oordeel shows Achterhaald after a change
- [x] E2E: correct the living area and see the Verwachte verkoopprijs change

## Comments

- 2026-11-23: Built test-first through Playwright (`frontend/e2e/woning-correctie.spec.ts`, two woningen of their own in `backend/tests/e2e_app.py`: Kerkpad 6, and Kerkpad 8 whose advertentie goes from 128 to 120 m² on refetch with no perceeloppervlak). Kenmerken moved out of `CaseView.tsx` into `Kenmerken.tsx`: every correctable fact has a pencil, a fact the advertentie leaves out shows as **onbekend** (unnumbered, after the vakken). A corrected fact shows a **gecorrigeerd** chip, the original struck through with its stamp (Advertentie or Register), the Toelichting, and a Correctie stamp (new `correction` stamp kind and legend entry, `DESIGN.md` updated). **Correctie behouden** re-saves the same value and Toelichting, which records the advertentie's current value and clears the notice. Signalen's "Zie vak" links count corrected facts too. Achterhaald needed no frontend change: the Oordeel already words cause `case`. The header's fact line and the list still show the advertentie's values (they read the snapshot, not the Case).
