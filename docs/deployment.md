# Deployment (Docker, Google Cloud Run) and data contributions

The app runs in a Docker container (`Dockerfile`, served by gunicorn). On Google Cloud Run the container's own
disk is **temporary** (wiped on every restart, redeploy or scale-down, and not shared between instances), so the
data contributions sent through the **Contribute data** page are written to a **private Cloud Storage bucket**,
mounted into the container as a folder.

```
Contributor ──► Cloud Run container ── writes Excel file ──► /mnt/submissions  ══ mounted ══►  gs://<bucket>
Maintainer PC ──► tools/fetch_submissions.py ──► downloads, verifies, deletes from the bucket, combines for review
```

Nothing is e-mailed and no personal data is collected (no name, no e-mail). The client IP address is only held in
memory for rate limiting and never stored.

## Settings (environment variables)

| Variable | Default | Purpose |
|---|---|---|
| `SUBMISSIONS_DIR` | `./submissions` | Folder where contributions are written. In production: the mounted bucket |
| `MAX_UPLOAD_MB` | `5` | Maximum size of an uploaded Excel file |
| `SUBMISSION_SECRET` | random per process | Key signing the anti-spam check. **Set it in production** (all instances must share it) |
| `PORT` | `8080` | Set by Cloud Run |

## Protection of the Contribute page

- Hidden honeypot field (filled in by bots → silently ignored).
- Anti-spam question (small sum) signed with `SUBMISSION_SECRET`; answers sent less than 5 s after the page was
  opened, or after 6 h, are refused.
- Rate limit per client IP: 5 submissions / 10 min and 30 / day (in memory, per container).
- Upload limits: `.xlsx` only, `MAX_UPLOAD_MB`, 500 buildings; requests larger than the limit are refused by the
  server (`MAX_CONTENT_LENGTH` in `app.py`).
- Uploaded workbooks are parsed with `defusedxml` (installed from `requirements.txt` and used automatically by
  openpyxl), which rejects malicious XML such as "XML bombs".
- Every value is type- and range-checked; unknown columns are refused; uploaded files are never stored as such:
  their values are re-written into a new clean workbook (no macros, no formulas: text is stored as text).
- Contributions never change the published dataset: the maintainer reviews them first.

## 1. Test the container locally (optional)

```bash
docker build -t nsbi-app .
docker run --rm -p 8080:8080 -e SUBMISSIONS_DIR=/mnt/submissions -v "%cd%/submissions:/mnt/submissions" nsbi-app
# open http://localhost:8080   (PowerShell: use ${PWD} instead of %cd%)
```

## 2. One-time Google Cloud setup

Replace `PROJECT_ID`, `REGION` (e.g. `europe-north1`, Finland) and the bucket name (globally unique).

```bash
gcloud config set project PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com

# Private bucket for the contributions
gcloud storage buckets create gs://nsbi-submissions --location=REGION --uniform-bucket-level-access --public-access-prevention

# Optional safety net: delete files older than 180 days (if never collected)
#   lifecycle.json: {"rule": [{"action": {"type": "Delete"}, "condition": {"age": 180}}]}
gcloud storage buckets update gs://nsbi-submissions --lifecycle-file=lifecycle.json

# Identity of the app, allowed to write into the bucket only
gcloud iam service-accounts create nsbi-app --display-name="NSBI web app"
gcloud storage buckets add-iam-policy-binding gs://nsbi-submissions --member=serviceAccount:nsbi-app@PROJECT_ID.iam.gserviceaccount.com --role=roles/storage.objectUser

# Secret key of the anti-spam check
python -c "import secrets; print(secrets.token_hex(32), end='')" > secret.txt
gcloud secrets create nsbi-submission-secret --data-file=secret.txt
del secret.txt          # (rm on macOS/Linux)
gcloud secrets add-iam-policy-binding nsbi-submission-secret --member=serviceAccount:nsbi-app@PROJECT_ID.iam.gserviceaccount.com --role=roles/secretmanager.secretAccessor
```

## 3. Deploy (and redeploy after each change)

From the project root (Cloud Build builds the image from the `Dockerfile`):

```bash
gcloud run deploy nsbi-smart-buildings --source . --region REGION --allow-unauthenticated --service-account nsbi-app@PROJECT_ID.iam.gserviceaccount.com --execution-environment gen2 --add-volume name=submissions,type=cloud-storage,bucket=nsbi-submissions --add-volume-mount volume=submissions,mount-path=/mnt/submissions --set-env-vars SUBMISSIONS_DIR=/mnt/submissions,MAX_UPLOAD_MB=5 --set-secrets SUBMISSION_SECRET=nsbi-submission-secret:latest --max-instances 3
```

Cloud Storage volume mounts require the second-generation execution environment (`gen2`). The dataset
(`data/smart_buildings_dataset.xlsx`) is part of the image: after adding accepted contributions to it,
commit and redeploy.

## 4. Collect the contributions

On your PC, once:

```bash
pip install -r tools/requirements-tools.txt
gcloud auth application-default login
```

Then whenever you want:

```bash
python tools/fetch_submissions.py --bucket nsbi-submissions          # download, verify, delete
python tools/fetch_submissions.py --bucket nsbi-submissions --keep   # download only
python tools/fetch_submissions.py --local-dir submissions            # when testing the app locally
```

Files are saved in `downloaded_submissions/<date-time>/` (git-ignored), together with
`combined_submissions.xlsx` (all submitted buildings, one per row, with submission id, date, channel and
comment). Review them, then copy accepted rows into the `buildings` sheet of the dataset (assign a
`building_id`), commit and redeploy.
