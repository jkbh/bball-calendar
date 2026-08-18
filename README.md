## Export the TuS Lübeck schedule

Run:

```text
python main.py
```

This downloads league `53844` and cup `53854` from basketball-bund.net and writes
all TuS Lübeck games to `tus_luebeck.ics`. Import that file into your calendar application.

Options:

```text
python main.py --team "Another Team" --output games.ics --url API_URL
```

Pass `--url` more than once to combine additional competitions. Supplying it
replaces the default league and cup URLs.

## Automatic updates and subscription

GitHub Actions runs the exporter every day at 03:17 UTC. You can also start it
manually from the repository's **Actions** tab. The workflow commits the updated
calendar to the default branch.

Subscribe to this URL in a calendar application, replacing `OWNER/REPOSITORY`
with the GitHub repository path:

```text
https://raw.githubusercontent.com/OWNER/REPOSITORY/main/tus_luebeck.ics
```
