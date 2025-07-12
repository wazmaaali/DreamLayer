# Changelog Contribution Guidelines 🚀

DreamLayer AI uses a **“show‑your‑work” changelog** so every new feature is immediately verifiable by reviewers and users.  
Follow these steps whenever you open a PR.

---

## 1. Folder layout

```text
docs/
 ├─ CHANGELOG.md            # Human‑readable log (version‑ordered)
 ├─ CHANGELOG_GUIDELINES.md # ← this file
 └─ assets/
     ├─ <version>/
     │   ├─ ui_01.png       # UI screenshots
     │   ├─ output_01.png   # generated images
     │   └─ …​
     └─ logs/
         └─ <version>.log   # full console / test run
```

> **Why keep assets in `docs/`?**  
> Relative links render on GitHub *and* on the published MkDocs site without extra config.

---

## 2. Changelog entry template

Copy‑paste the block below into **docs/CHANGELOG.md** and replace the placeholders.

```markdown
## [<version>] – YYYY‑MM‑DD

### Added / Changed
- …

### Fixed
- …

### Evidence
**UI Screenshot:** ![UI](assets/<version>/ui_01.png)

**Generated Image:** ![Gen](assets/<version>/output_01.png)

**Logs:**
```text
# docs/assets/logs/<version>.log  (snippet)
pytest -q
24 passed in 3.2s
…
```
```

---

## 3. Author checklist  *(add to `.github/PULL_REQUEST_TEMPLATE.md`)*

**Every Pull Request MUST contain:**

- [ ] **Screenshot of the UI configurations that were changed** (in `docs/assets/<version>/`)
- [ ] **Image that was generated with the change** (in `docs/assets/<version>/`)
- [ ] **Logs snippet that verifies the change is working** (in `docs/assets/logs/<version>.log`)
- [ ] **Tests** (optional but recommended)

**Additional requirements:**
- [ ] Added a section to **docs/CHANGELOG.md** using the template above.  
- [ ] Put screenshots in `docs/assets/<version>/`.  
- [ ] Added at least one generated‑output image.  
- [ ] Attached `docs/assets/logs/<version>.log` with the full test run.  
- [ ] Verified all image / log links render in the PR preview.

---

## 4. Tips for high‑signal evidence

| What              | Best practice                                                                                           |
|-------------------|----------------------------------------------------------------------------------------------------------|
| **Screenshots**   | Crop to the changed area; keep width ≤ 1600 px so PNG diffs stay small.                                  |
| **Gen images**    | Name deterministically (`output_<prompt‑slug>.png`) so they’re comparable across versions.               |
| **Logs**          | Capture with `pytest -q 2>&1 | tee docs/assets/logs/<version>.log` to save and print simultaneously.     |
| **Large logs**    | Embed only the head/tail in the changelog; keep the full file under `logs/`.                             |

---

## 5. Example entry (abridged)

```markdown
## [1.2.0] – 2025‑07‑11

### Added
- **Batch Generate** button allows queuing up to 10 prompts.
- New prompt parser for negative‑prompt syntax.

### Evidence
**UI Screenshot:** ![UI](assets/1.2.0/ui_01.png)

**Generated Image:** ![Gen](assets/1.2.0/output_beach.png)

**Logs:**
```text
================ 56 passed, 2 skipped in 5.77s =================
```
```

---

## 6. Make it discoverable

1. **README link**

   Add under the “Contributing” section of your root `README.md`:

   ```markdown
   ## Contributing

   - See [CHANGELOG Guidelines](docs/CHANGELOG_GUIDELINES.md) before opening a PR.
   ```

2. **MkDocs navigation**

   In `mkdocs.yml`:

   ```yaml
   nav:
     - Development:
       - Contributing: contributing.md
       - Changelog: changelog.md
       - Changelog Guidelines: changelog_guidelines.md   # ← add this line
   ```

Happy shipping! ♥
