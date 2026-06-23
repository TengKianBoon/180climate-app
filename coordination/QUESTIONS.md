# QUESTIONS — blockers / ambiguities   ·   NON-EMPTY pulls a human turn

## Q1 — Branch protection on private repo (WO-000) · 2026-06-24

**Context:** GitHub's classic branch protection rules require GitHub Pro (or Team/Enterprise)
for private repositories. The free plan only supports branch protection on public repos.

The WO-000 acceptance criterion says "main protected." Everything else is done.

**Choose one:**

**A. Upgrade to GitHub Pro (~USD 4/month)**
   After upgrading, run this once:
   ```
   gh api repos/TengKianBoon/180climate-app/branches/main/protection \
     --method PUT \
     --field "required_status_checks={\"strict\":true,\"contexts\":[\"lint-test\"]}" \
     --field "enforce_admins=false" \
     --field "required_pull_request_reviews=null" \
     --field "restrictions=null"
   ```

**B. Make the repo public now** (you planned to flip it for the portfolio anyway)
   `gh repo edit 180climate-app --visibility public`
   Then run the same command from option A.

**C. Accept the limitation for now**
   Branch protection will be set when you flip to public for the portfolio.
   Treat Gate 0 as approved with this noted caveat.

Type your answer (A, B, or C) and the build resumes.
