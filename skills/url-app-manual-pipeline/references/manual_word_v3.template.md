---
title: "User Manual"
subtitle: "__APP_TARGET__"
author: "Documentation Draft"
date: "__MANUAL_DATE__"
---

```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```

# 1. Scope

This manual covers the visible primary controls on `__HOST__` (desktop):

- Top header/navigation controls
- Side navigation (if present)
- Main content card/list entry interactions

# 2. Prerequisites

- Browser can access: <__TEST_URL__>
- Recommended viewport width: at least 1280 px
- UI may differ by locale, login state, and experiments

# 3. Home Page Overview

![Application home page overview. Mark key regions: header, navigation, content area.](images/home-overview.png)

# 4. Links and Buttons Mapping

## 4.1 Top Navigation

| Control | Type | Function |
|---|---|---|
| Main Logo / Home Link | Link | Returns to the landing page. |
| Global Search Input (if present) | Input field | Accepts query text for global search. |
| Search Submit Control (if present) | Button | Executes search using entered keywords. |
| Profile / Account Entry (if present) | Link/Button | Opens login, account, or user menu actions. |
| Primary Utility Buttons | Button | Opens contextual actions such as notifications or settings. |

## 4.2 Left Navigation (Common Signed-out Items)

| Item | Type | Function |
|---|---|---|
| Home | Link | Navigates to default dashboard/feed/home view. |
| Discover / Explore | Link | Opens browsing categories or recommendations. |
| Saved / Library | Link | Opens saved content or collections. |
| History / Recent | Link | Shows previously visited items when available. |
| Settings / Help | Link | Opens support, preferences, or system settings. |

## 4.3 Home Feed Video Card

| Area | Type | Function |
|---|---|---|
| Preview / Thumbnail Area | Link | Opens detail page for the selected item. |
| Title Text | Link | Opens the same detail page. |
| Metadata Line | Link/Text | Provides context and may navigate to related pages. |
| More Options Control | Button | Opens row-level actions (save, hide, report, etc., site dependent). |

# 5. Example Task Flows

## 5.1 Flow A: Search for a Video

1. Enter keywords in the search input (example: `__SEARCH_QUERY__`).
2. Trigger the search action (button click or Enter).
3. Review the resulting list/grid page.

## 5.2 Flow B: Open a Video Watch Page

1. Find any content card or list row on the home page.
2. Click its preview or title.
3. Confirm the detail page is loaded.

# 6. Maintenance Notes

- This manual is generated from live DOM capture and can drift as UI changes.
- Re-generate screenshots after major UI updates.
- Validate captions/table labels for domain-specific wording before release.

# 7. Build

- Run this command in the same directory: `latexmk -pdf main.tex`
- Output: `main.pdf`
