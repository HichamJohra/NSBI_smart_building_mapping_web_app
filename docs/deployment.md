# Deployment (Docker, Google Cloud Run) and data contributions

The app runs in a Docker container (`Dockerfile`, served by gunicorn: `app:server`). The dataset
(`data/smart_buildings_dataset.xlsx`) is part of the image: after changing it, commit and redeploy.

On Google Cloud Run the container's own disk is **temporary** (wiped on every restart, redeploy or scale-down, and
not shared between instances), so the data contributions sent through the **Contribute data** page are written to a
**private Cloud Storage bucket**, mounted into the container as a folder.

```
Contributor ──► Cloud Run container ── writes Excel file ──► SUBMISSIONS_DIR  ══ mounted ══►  private bucket
Maintainer PC ──► tools/fetch_submissions.py ──► downloads, verifies, deletes from the bucket, combines for review
```

Nothing is e-mailed and no personal data is collected (no name, no e-mail). The client IP address is only held in
memory for rate limiting and never stored.

Hosting: Google Cloud Run (Nordic region), redeployed automatically by a Cloud Build trigger on every push to `main`.
Project identifiers, service account names, bucket and secret names are kept in the maintainer's private notes,
not in this repository.

## Settings (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `SUBMISSIONS_DIR` | `./submissions` | Folder where contributions are written. In production: the mounted bucket |
| `MAX_UPLOAD_MB` | `5` | Maximum size of an uploaded Excel file |
| `SUBMISSION_SECRET` | random per process | Key signing the anti-spam check. **Set it in production** (from Secret Manager) |
| `PORT` | `8080` | Set by Cloud Run |

## Protection of the Contribute page

- Hidden honeypot field (filled in by bots → silently ignored).
- Anti-spam question (small sum) signed with `SUBMISSION_SECRET`; answers sent less than 5 s after the page was
  opened, or after 6 h, are refused.
- Rate limit per client IP: 5 submissions / 10 min and 30 / day (in memory, per container; hence one gunicorn
  worker with several threads, see `Dockerfile`).
- Upload limits: `.xlsx` only, `MAX_UPLOAD_MB`, 500 buildings; requests larger than the limit are refused by the
  server (`MAX_CONTENT_LENGTH` in `app.py`).
- Uploaded workbooks are parsed with `defusedxml` (used automatically by openpyxl), which rejects malicious XML.
- Every value is type- and range-checked; unknown columns are refused; uploaded files are never stored as such:
  their values are re-written into a new clean workbook (no macros, no formulas: text is stored as text).
- Contributions never change the published dataset: the maintainer reviews them first.

## Security principles

- Two dedicated service accounts, never the Compute Engine default account:
  - **runtime** account (identity of the public web app): only *Storage Object User* on the contributions bucket
    and *Secret Manager Secret Accessor* on the anti-spam secret; no project-wide roles;
  - **build** account (used by the Cloud Build trigger): *Cloud Run Admin*, *Artifact Registry Writer*,
    *Logs Writer*, plus *Service Account User* on the runtime account.
- The bucket is private (uniform bucket-level access, public access prevention).
- No keys or secrets in the repository; the secret lives in Secret Manager.

## 1. Test the container locally (optional)

```bash
docker build -t nsbi-app .
docker run --rm -p 8080:8080 -e SUBMISSIONS_DIR=/mnt/submissions -v "%cd%/submissions:/mnt/submissions" nsbi-app
# open http://localhost:8080   (PowerShell: use ${PWD} instead of %cd%)
```

## 2. One-time Google Cloud setup (Console)

1. **APIs:** enable Cloud Run Admin, Cloud Build, Artifact Registry, Secret Manager and Cloud Storage.
2. **Bucket:** Cloud Storage → Create bucket, region = the Cloud Run region, *Enforce public access prevention* on,
   uniform access control. Optional lifecycle rule: delete objects older than 180 days.
3. **Secret:** Secret Manager → Create secret, value = a long random string, e.g. generated with
   `python -c "import secrets; print(secrets.token_hex(32))"`. Do not save the value anywhere else.
4. **Service accounts:** IAM & Admin → Service accounts: create the runtime account (no roles) and the build account
   (roles above). Then grant the runtime account *Storage Object User* on the bucket (bucket → Permissions) and
   *Secret Manager Secret Accessor* on the secret (secret → Permissions), and grant the build account
   *Service Account User* on the runtime account.

## 3. Create the service with continuous deployment from GitHub

Cloud Run → Deploy container → **Continuously deploy from a repository** → Set up with Cloud Build:

1. GitHub repository of this app (Cloud Build GitHub app), branch `^main$`, build type **Dockerfile** (`/Dockerfile`).
2. Region (Nordic), **Allow public access**, request-based billing, min 0 / max 3 instances.
3. Container: port 8080, 512 MiB, 1 CPU.
   - **Variables & Secrets:** `SUBMISSIONS_DIR=/mnt/submissions`, `MAX_UPLOAD_MB=5`; reference the secret as
     environment variable `SUBMISSION_SECRET` (version *latest*).
   - **Volumes:** add a *Cloud Storage bucket* volume (the private bucket), mount it at `/mnt/submissions`.
4. Execution environment: **Second generation** (required for Cloud Storage volume mounts).
5. Security: service account = the runtime account. Create.
6. Cloud Build → Triggers → edit the generated trigger: service account = the build account; in the inline YAML add
   `logging: CLOUD_LOGGING_ONLY` under `options:` (required when a user-managed account runs the build). Save, Run.

Every merge into `main` (pull request from `dev`) then rebuilds and redeploys automatically (Cloud Build → History).
`requirements.txt` pins the versions tested locally; update them together after testing upgrades.

Alternative without GitHub: `gcloud run deploy SERVICE --source . --region REGION ...` from the project folder with
the Google Cloud CLI (uploads the local folder minus `.gcloudignore`), with the same volume, variables and secret
options (`--execution-environment gen2 --add-volume ... --add-volume-mount ... --set-env-vars ... --set-secrets ...`).

## 4. Collect the contributions

On your PC, once (requires the Google Cloud CLI for the login):

```bash
pip install -r tools/requirements-tools.txt
gcloud auth application-default login
```

Then whenever you want:

```bash
python tools/fetch_submissions.py --bucket BUCKET_NAME          # download, verify, delete
python tools/fetch_submissions.py --bucket BUCKET_NAME --keep   # download only
python tools/fetch_submissions.py --local-dir submissions       # when testing the app locally
```

Without the CLI, the files can also be downloaded by hand in the Console (Cloud Storage → bucket → select → Download)
and combined with `--local-dir`.

Files are saved in `downloaded_submissions/<date-time>/` (git-ignored), together with
`combined_submissions.xlsx` (all submitted buildings, one per row, with submission id, date, channel and
comment). Review them, then copy accepted rows into the `buildings` sheet of the dataset (assign a
`building_id`), commit and redeploy.
