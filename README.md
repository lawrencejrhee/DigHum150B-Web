# DigHum 150B Weekly Projects

Lawrence Rhee's site for the DigHum 150B weekly data-visualization projects,
UC Berkeley, Summer 2026. Each week (2 to 5) pairs one visualization tool with a
humanities topic.

**Live site:** https://lawrencejrhee.github.io/DigHum150B-Web/

Hand-built static HTML + CSS, no build step, served with GitHub Pages.

## Structure

```
index.html            Home / hub page with the assignment and week list
weeks/
  week2.html          Week 2: Tableau
  week3.html          Week 3: placeholder
  week4.html          Week 4: placeholder
  week5.html          Week 5: placeholder
assets/
  styles.css          One shared stylesheet (light/dark aware)
  images/             Image assets
.nojekyll             Serve files as-is (skip Jekyll processing)
```

## Editing a week

Each week page has an `<dl class="meta">` block near the top (tool / topic /
status) and a body you can rewrite. To embed a finished Tableau viz, publish
the workbook to [Tableau Public](https://public.tableau.com/), copy the embed
code from **Share → Embed Code**, and replace the `.viz-placeholder` block on
that week's page with the `<iframe>` inside the existing `<figure class="media">`.
