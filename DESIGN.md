# GridPulse Design Direction

## Product goal

GridPulse gives microgrid operators a fast view of the next 24 hours of demand, the dispatch rules behind every transition, and any critical overload window. The interface must distinguish simulated data and advisory signals from live sensors or physical controls.

## Visual direction

- Futuristic operations console with a dark forest / graphite base, luminous mint demand signal, cyan support accents, amber storage threshold, and coral critical threshold.
- Readable display typography: Space Grotesk for headings, Inter for interface copy, and IBM Plex Mono for timestamps, units, and model telemetry.
- Glass-like layered cards, fine grid texture, restrained radial glows, isometric columns, and short motion transitions.
- The app's user-facing content remains English.
- Responsive shell uses a fixed desktop navigation rail and an accessible slide-in menu on smaller screens.

## 21st.dev MCP references

The 21st.dev MCP catalog was searched for the full interface and chart direction. The following components informed native React implementations in this project:

- [Interactive 3D Analytics Dashboard Card](https://21st.dev/@dhileepkumargm/components/interactive-3d-analytics-dashboard-card) — depth, gradient glass, and hover-responsive analytics cards.
- [Dashboard Sidebar](https://21st.dev/@arunjdass/components/dashboard-sidebar) — compact grouped application navigation.
- [LumaBar](https://21st.dev/@ruixen.ui/components/futuristic-nav) — active-state glow and lightweight navigation feedback.
- [Isometric Bars Chart](https://21st.dev/@abhishek-mallick/components/bars) — isometric demand columns and hover values.
- [3D Gradient Bar Chart](https://21st.dev/@sean0205/components/c-chart-6) — gradient 3D bar treatment adapted to 24 hourly values.
- [Glowing Card](https://21st.dev/@ravikatiyar162/components/glowing-card) and [Glare Cards](https://21st.dev/@daiwiikharihar/components/glare-cards) — restrained luminous metric surfaces.

The account's free component-code retrieval quota was exhausted during the current day, so new registry source bundles could not be fetched. The project therefore implements the catalog patterns in accessible native React/SVG instead of claiming that registry source files were imported. The 21st.dev MCP was used for catalog search and reference selection; direct component-code retrieval becomes available after the quota resets.

## Product sections

1. **Overview:** peak demand, transition time, overload count, a 24-hour isometric chart, dispatch timeline, and an explicitly simulated battery estimate.
2. **Forecasts:** threshold summaries, complete hourly feature/prediction table, keyboard-focusable chart columns, and CSV export.
3. **Telemetry:** CSV ingestion with schema validation, local manual weather entry, missing-value handling, and starter dataset reference.
4. **Grid controls:** editable scenario thresholds and time windows, persisted locally, with visible safety boundaries.

## Rules and limits

- Renewable Storage Mode is active when predicted demand is **greater than 160 kW** or the local hour is **18:00–22:00 inclusive**.
- Critical overload alert is raised at **200 kW or higher**, independently of grid mode.
- The dashboard never claims to operate a physical controller. No device connector or battery SOC sensor is included in the starter kit.
- Without a QuickML endpoint, forecasts use a clearly labelled deterministic fallback; scenario weather inputs are identified as illustrative.
- Uploaded telemetry is saved to a local SQLite database by the local AppSail service. A Catalyst-managed persistent store requires project-specific Catalyst service configuration and credentials before production use.
