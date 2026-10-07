# Le Hub Toulouse

A public information portal for employees at the Toulouse office. It shows nearby food trucks, current Refectory promotions available globally or in Toulouse, and the shared promotion codes submitted by employees.

The site is a Progressive Web App (PWA) published on GitHub Pages. It includes a `noindex` directive, but remains publicly accessible to anyone who knows its URL.

## How it works

- The React application reads static JSON files from `public/data`.
- The weekly food-truck schedule is stored in `public/data/food-trucks.json`. The current day is selected by default, while the other days and the complete schedule remain available.
- A Python collector uses Playwright to read Refectory's public current-offers page.
- Offers are normalized, limited to global and Toulouse offers, and published even when their promotion code is not known yet.
- A stable offer identifier keeps a contributed code attached to the offer for its full validity period, including week-long offers.
- Employee submissions are approved manually before being imported. Duplicate submissions confirm a code; conflicting codes stop the synchronization instead of overwriting an approved value.
- If Refectory extraction fails, the last valid published offers are preserved.

## Local development

```powershell
npm install
npm run dev
```

Run the automated checks and production build with:

```powershell
npm test
npm run build
python -m pip install -r automation/requirements.txt
python -m pytest automation/tests
```

Chromium is required to test the live Refectory collection:

```powershell
python -m playwright install chromium
python -m automation.refectory.export
python -m automation.refectory.contributions
```

With the local development server already running, the responsive, interactive, PWA, and WCAG browser checks can be run with:

```powershell
python automation/browser_qa.py
```

## Deployment and automation

Set the GitHub Pages source to **GitHub Actions** in the repository settings. The repository contains three workflows:

- `deploy-pages.yml` tests and builds the portal after application changes, then deploys the resulting Pages artifact. It can also be started manually.
- `refresh-offers.yml` fetches the latest Refectory offers, imports approved codes, commits actual data changes, builds a Pages artifact, and deploys it. cron-job.org dispatches it every day at **08:20 Europe/Paris**.
- `sync-contributed-codes.yml` imports newly approved codes and builds and deploys a Pages artifact only when the published data changes. cron-job.org dispatches it every 15 minutes between **08:00 and 18:00 Europe/Paris**.

The two externally scheduled workflows expose `workflow_dispatch` and contain no GitHub Actions `schedule` or `cron` trigger. cron-job.org calls GitHub's workflow-dispatch API with the repository's default branch as `ref`. Its fine-grained GitHub token must be stored only in cron-job.org and limited to this repository with **Actions: Read and write** permission.

The workflows use these existing GitHub Actions variables:

- `VITE_REFECTORY_FORM_URL`: public contribution-form URL embedded in the frontend;
- `REFECTORY_CODES_FEED_URL`: approved-code feed consumed by the Python importer.

No token or secret is stored in the repository. The maintenance script creates a commit only when published Refectory offers or approved codes actually change.

Data updates and deployments use separate concurrency groups. Refectory update jobs are serialized to avoid concurrent commits, while only deployment jobs wait in the GitHub Pages queue. A temporary approved-code feed failure is retried and does not fail the daily offer refresh; the dedicated code synchronization reports the failure and retries at the next external dispatch. The `github-pages` environment must not require reviewer approval for this unattended deployment setup.

## Updating food trucks

`public/data/food-trucks.json` contains the schedule sourced from the reference Google Sheet. Vendors, locations, and visits are stored separately so the same food truck can appear on several days or at several locations without duplicating its contact details.

After changing the schedule, run `npm test`, `npm run build`, and `python -m pytest automation/tests` to validate references, weekdays, and the rendered portal.
