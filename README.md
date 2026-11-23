Amazon Script Affiliate Links — free Render deploy

The app accepts an Amazon Creators API Client ID and Secret, Associates tracking tag, marketplace, and a video script. It extracts product mentions and searches the Amazon Creators API, returning up to three possible matching affiliate listings per mention. It does not save credentials.

Deploy: https://render.com/deploy?repo=https%3A%2F%2Fgithub.com%2FMoizraj2233%2Ftest
Choose the Free plan. Render will ask you to sign in and authorize access to this repository, then deploy `render.yaml`.

Free Render web services sleep after 15 minutes without traffic and can take about a minute to wake. The app uses heuristic product-name extraction; review matches before publishing.