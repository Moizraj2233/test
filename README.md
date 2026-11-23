Amazon Script Affiliate Link Finder

This tool is in `/amazon-link-tool/`. It accepts Creators API Client ID/Secret, an Associates tracking tag, marketplace, and a video script. It detects likely product names and returns up to three Creators API affiliate matches for each one. Credentials are used for the current request and are not stored.

## Deploy on Vercel

1. Import `Moizraj2233/test` into a Vercel project.
2. Keep the project root directory as `.` and deploy with the Hobby plan.
3. Open `https://<your-project>.vercel.app/amazon-link-tool/`.

Vercel's Python runtime runs the `/api/generate` endpoint. The site uses the API credentials entered in the form; never commit credentials into this repository. Product-name detection is heuristic, so review each match.
