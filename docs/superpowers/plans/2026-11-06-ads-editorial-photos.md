# Desktop Ad Placement and Editorial Photographs

**Goal:** Fix the empty 160x600 desktop ad region and replace text-heavy thumbnail covers with properly licensed illustrative photos whenever relevant.

## Boundaries
- Preserve existing approved Adsterra unit/key, Pix links, articles, schedules, and analytics.
- Do not upload files from other agents' uncommitted carousel work.
- Only publish Wikimedia Commons photo files after checking exact topic, permitted license, author and source. Label archival/context photos as illustrative.
- No simulated paid ads or promise of ad fill if the ad network/browser blocks the creative.

## Implementation
1. RED: Test homepage has Adsterra script in the static editorial sidebar, no JavaScript reparenting, and no second duplicate script.
2. GREEN: Move original ad markup into the homepage's static editorial sidebar; let the magazine script only update news stories, never relocate the ad.
3. RED: Tests for Wikimedia thumb host, selected Commons file titles, credits, and photo-only thumbnails.
4. GREEN: Curate genuine Commons archive photos for existing stories, expand conservative auto-discovery for future stories, save attribution and generate a linked credits page. Use Raven Crow logo as fallback rather than text embedded in generated article covers.
5. Verify full test suite, source code, live assets and deployment. Commit only scoped files.

**Style:** Newspaper-like black, white and coral-red; photographs cropped cleanly on desktop; existing responsive mobile design intact.
