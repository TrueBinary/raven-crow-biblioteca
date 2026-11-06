# Raven Crow Editorial Visual Fidelity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bring the Raven Crow home closer to the approved mobile and desktop reference images without changing existing advertisement integrations.

**Architecture:** Keep the existing static HTML/CSS/JS site, news JSON feed, and navigation. Upgrade the frontpage renderer to use approved local editorial visuals when a matching asset exists, improve semantic metadata and article cards, and adapt header/hero/columns by breakpoint. Never insert fictional news or unlicensed remote photos.

**Tech Stack:** Vanilla JS, CSS, Python unittest, Render static deployment.

**Spec:** User reference images in conversation, mobile two-tier navigation and desktop one-row navigation, news-first editorial layout.

## Task 1: Responsive navigation
- [ ] Add tests that desktop hides menu toggle and uses a single horizontal row while mobile keeps two-tier header.
- [ ] Verify tests fail before implementation.
- [ ] Add breakpoint CSS and preserve search/menu keyboard behavior.
- [ ] Verify tests pass.

## Task 2: Editorial cards with grounded imagery
- [ ] Add tests for thumbnail and hero image support with local matching image path, accessible alt, and fallback.
- [ ] Verify tests fail.
- [ ] Implement image mapping based on available local carousel assets (never claim photos of people without evidence).
- [ ] Add date/read-time metadata, sidebar and hierarchy matching the reference.
- [ ] Verify tests pass.

## Task 3: Review and release
- [ ] Run all navigation and layout tests, JS syntax check, git diff check.
- [ ] Commit only scoped files, push main as user explicitly requested execution.
- [ ] Check Render deployment status and live pages, report any visual verification limitations.

**Scope exclusion:** Existing Adsterra banners, native ad, Pix, tracking, and article content remain unchanged.
