# Local Runbook

## Build demo payload

```bash
python3 -m engine.cli build-demo
```

Expected status: `SHORTLIST_FROM_AVAILABLE_DATA`, `is_top5_hose=false`.

## Test engine

```bash
python3 -m unittest discover -s engine/tests -v
```

## Serve website

```bash
python3 website/server.py --port 8080
```

Health: `GET /api/health`.

## Build the GitHub Pages artifact

```bash
python3 scripts/build_pages.py --output .pages-site
python3 -m http.server 8081 --directory .pages-site
```

The static artifact disables API writes and adds `noindex,nofollow`. GitHub Pages deployment is automated by `.github/workflows/pages.yml`; see `docs/GITHUB_PAGES_DEPLOYMENT.md` for one-time settings and the custom-domain gate.

## Regenerate creatives

```bash
python3 growth/creatives/generate_creatives.py
```

## Production checklist

1. Replace the fixture through a provider adapter; never edit the public JSON by hand as the production process.
2. Reconcile full HOSE universe and exclusions.
3. Run tests and one shadow snapshot.
4. Publish the static client through GitHub Pages; deploy the lead/event API separately with TLS and access controls.
5. Add privacy retention/deletion operations.
6. Complete compliance and Meta eligibility review.
7. Verify every analytics event in the production collector.
8. Only then schedule Ads.
