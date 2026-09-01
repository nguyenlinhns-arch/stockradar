# GitHub Pages deployment

Target account: `nguyenlinhns-arch`  
Recommended repository: public `stockradar`  
Default preview URL: `https://nguyenlinhns-arch.github.io/stockradar/`

## Current research release

- V2.1.2 functional release: `3f61ad6f328d7dedf22bf5370778ede875360a01`.
- Verified workflow run: `33532527570` — SUCCESS.
- Static artifact: 26 application routes plus `404.html` dynamic ticker redirect.
- Public artifact: `data-api-mode="disabled"`, `noindex,nofollow`, MOCK/SHADOW only.

## What the workflow does

Every push to `main`:

1. rebuilds the deterministic MOCK payload;
2. runs the full Python regression suite;
3. copies only static website files into `.pages-site`;
4. disables the lead/event API in the public artifact;
5. adds `noindex,nofollow` while the product is still a demo;
6. deploys the artifact through the protected `github-pages` environment.

GitHub Pages is static hosting. It cannot run `website/server.py` or store signup data. The form therefore states that no information is received or saved until a separate HTTPS backend is connected.

## One-time repository settings

1. Create an empty public repository named `stockradar` under `nguyenlinhns-arch`.
2. Push this project to the `main` branch.
3. Open **Settings → Pages → Build and deployment → Source** and select **GitHub Actions**.
4. Wait for **Actions → Verify and deploy StockRadar Pages** to pass.
5. Open the URL shown in the deployment job.

## Custom domain gate

Do not point DNS at GitHub before the domain is verified and attached to the active Pages site.

After ownership of `stockradar.vn` is confirmed:

1. verify the domain in GitHub account settings;
2. set `stockradar.vn` under **Settings → Pages → Custom domain**;
3. configure the apex `A` records and the `www` CNAME with the DNS provider;
4. verify DNS resolution, then enable **Enforce HTTPS**;
5. remove the build-time `noindex,nofollow` only after brand, privacy, data and compliance gates pass.

## Backend gate

Before collecting leads or running Ads, deploy an HTTPS backend with:

- server-side validation and abuse controls;
- encrypted storage and least-privilege access;
- privacy notice, retention/deletion operations and consent evidence;
- an analytics endpoint with the event allowlist;
- a configured API base URL in the public pages build.
