# Search discovery and answer-engine content

## Published content

- English: https://campong.online/projects/suay/
- Thai: https://campong.online/projects/suay/th/
- SUAY sitemap: https://campong.online/projects/suay/sitemap.xml
- Source and editable architecture: https://github.com/camponggogo/suay

Each language page has a self-canonical URL, reciprocal `hreflang` links, an `x-default` English URL, a unique descriptive title, social previews, visible project facts and FAQ answers. Primary content is static HTML and does not require JavaScript rendering. The project is described as a pilot, with shipping gateway features separated from proposed worker integration.

JSON-LD describes the WebSite, WebPage, SoftwareSourceCode, a visible installation TechArticle and FAQ content. It has no fabricated ratings, usage numbers, customers, prices or production-support claims. FAQ markup is for semantic consistency; Google does not generally show FAQ rich results for this kind of software project. Exact SHA-256 hashes permit the inert structured-data blocks within the existing CSP without allowing arbitrary inline scripts.

The domain's existing `/robots.txt` allows crawling. It and the company-wide sitemap remain unchanged so other projects' policies are preserved. The project sitemap lists only SUAY's 12 language pages and reciprocal language alternates. Dates describe actual page updates, not a fabricated publication history. A subdirectory robots file is intentionally not used because it would not control site crawling.

The public IndexNow key file is not a private API token. After a successful deployment, run `python deploy/submit_indexnow.py` once for changed pages. An accepted response means a notification was received; it does not prove that a search engine crawled or indexed the URLs. IndexNow does not submit pages to Google.

## Owner steps for measurement and indexing

1. Verify the website in Google Search Console and Bing Webmaster Tools using the owner's account. DNS ownership and account/terms steps require the owner; no verification token is invented or embedded here.
2. Submit the SUAY sitemap URL and inspect both language URLs. The domain already has a company sitemap; retain it rather than replacing it with the project sitemap.
3. Monitor indexing status, impressions, relevant queries and repository visits. Compare Thai and English queries after search engines have had time to crawl the site.
4. Track practical conversions: repository visits, stars, issue reports and reproducible trials. Do not treat raw traffic as proof that the software meets a business workload.

The landing page has a separate consent-based visitor analytics service. Behavioral collection requires visitor consent and is independent of the organization controller; no employee telemetry collector is added by these setup instructions.

## Sustainable reach

Use accurate GitHub About text and topics from GITHUB_LAUNCH.md. Keep the website, README, architecture and model support information consistent. Publish measured hardware results when available, including energy use and limits. Write implementation notes that answer specific organizational questions rather than creating near-duplicate keyword pages.

The maintainer can share a concise release announcement with communities they participate in. Include an honest pilot status, working demo/source links and an invitation to contribute. No community posts, emails, unsolicited messages, purchased backlinks, automated stars or fabricated endorsements have been sent by this task. Any outreach must follow the community's rules.

## Primary references

- Google AI features and websites: https://developers.google.com/search/docs/appearance/ai-features
- Google structured-data policies: https://developers.google.com/search/docs/appearance/structured-data/sd-policies
- Google robots.txt introduction: https://developers.google.com/search/docs/crawling-indexing/robots/intro
- IndexNow protocol: https://www.indexnow.org/documentation
- Bing sitemap discovery: https://blogs.bing.com/webmaster/2025/7/Keeping-Content-Discoverable-with-Sitemaps-in-AI-Powered-Search/

SEO fundamentals also apply to Google's AI search features. Google does not require a special AI text file or an additional schema for inclusion, and neither correct markup nor a sitemap guarantees visibility. No top ranking or AI citation is promised.

## Installation discovery update — 2026-10-20

The landing now contains four crawlable installation cards with ordered HTML steps, descriptive SVG alt text, launch commands and links to the actual component guides. English and Thai titles and visible FAQ answers explicitly distinguish coordinator, worker, client and gateway roles. JSON-LD mirrors the visible content; no HowTo rich-result eligibility or ranking guarantee is claimed.

Reference: [Google Search Central SEO Starter Guide](https://developers.google.com/search/docs/fundamentals/seo-starter-guide). Use clear headings, descriptive links and useful visible content rather than keyword stuffing. Account verification in Search Console remains an owner step.
