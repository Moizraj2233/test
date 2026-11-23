Amazon Script Affiliate Tool — Render free deployment

This folder is a ready-to-deploy Render Blueprint. It uses only Python's standard library.

Deploy:
1. Put the files in this folder in a private GitHub repository.
2. Sign in to Render and create a new Blueprint from that repository.
3. Choose the free instance plan and deploy render.yaml.
4. Open the generated https://<service>.onrender.com URL.
5. Paste your Amazon Creators API Client ID, Secret, Associates tag, choose the marketplace, and paste your script.

Credentials are submitted only when you click Generate and are not written to disk by this app. Use HTTPS on the hosted Render URL. Free Render services sleep after 15 minutes idle and may take about a minute to wake.

The first version creates templated title ideas and a description; it does not use an AI writing API. Product detection is heuristic and results need a quick review before publishing.

