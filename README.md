# GridPulse — Smart Microgrid Demand Forecasting

GridPulse is a Catalyst-ready operations dashboard for the HackSphere 3.0 demand-forecasting challenge. It combines a React/Vite interface, an AppSail-compatible Python API, a QuickML inference adapter, a telemetry CSV workflow, and a tested dispatch rule engine.

All app copy is in English. The UI identifies fallback forecasts, scenario weather, estimated battery SOC, and advisory-only dispatch signals so simulated values are not presented as live equipment data.

## Workspace

- `src/` — responsive React dashboard with Overview, Forecasts, Telemetry, and Grid Controls sections.
- `backend/` — FastAPI service, CSV validation, missing-value imputation, local SQLite storage, Catalyst Stratus/Data Store adapters, and QuickML integration.
- `predict.py` — challenge-compatible `predict(input_df)` adapter and CLI.
- `train_telemetry.csv` — supplied QuickML training dataset.
- `sample_test_input.csv` — supplied 1,000-row inference / contract dataset.
- `DESIGN.md` — visual direction and 21st.dev MCP references.

## Local setup

Requirements: Node.js 20+ and Python 3.13 (also compatible with Python 3.11+ locally).

1. Install frontend and contract-test packages:

   ```powershell
   npm install
   py -3.13 -m pip install -r requirements.txt
   py -3.13 -m pip install -r backend/requirements-dev.txt
   ```

2. Create a local environment file:

   ```powershell
   Copy-Item .env.example .env
   ```

3. Start the API in a terminal:

   ```powershell
   py -3.13 -m uvicorn main:app --app-dir backend --reload --port 8000
   ```

4. Start the website in another terminal:

   ```powershell
   npm run dev
   ```

Open the Vite URL shown in the terminal. If the API is not running, the dashboard stays usable in clearly labelled scenario mode. Telemetry upload and real API-backed inference need the API.

## QuickML configuration

The API reads secrets only from environment variables:

- `QUICKML_ENDPOINT_URL` — QuickML Development endpoint URL that accepts `{"data": [{...}]}` and returns `{"predictions": [number, ...]}` in input order.
- `QUICKML_ENDPOINT_KEY`, `QUICKML_ORG_ID`, `QUICKML_ENVIRONMENT` — endpoint key, Catalyst organization ID, and `Development`/`Production` environment required by the published endpoint.
- `QUICKML_REFRESH_TOKEN`, `QUICKML_CLIENT_ID`, `QUICKML_CLIENT_SECRET`, `ZOHO_OAUTH_TOKEN_URL` — server-side Zoho OAuth refresh configuration. The token URL must match your Zoho data centre. Keep these values only in AppSail environment variables.
- `CORS_ORIGINS` — comma-separated local and Slate origins allowed to call the API.
- `GRIDPULSE_DATABASE_PATH` — optional SQLite path for local development.
- `GRIDPULSE_STORAGE_MODE=local|catalyst` — select local SQLite or Catalyst storage.
- `GRIDPULSE_STRATUS_BUCKET` — existing Stratus bucket used by Catalyst mode.
- `GRIDPULSE_DATASTORE_UPLOADS_TABLE` and `GRIDPULSE_DATASTORE_FORECASTS_TABLE` — existing Data Store table names.
- `VITE_API_BASE_URL` — API origin bundled into the Slate website build.

Before inference, upload a feature-only or training CSV to the Telemetry page. A 24-hour weather sequence is staged from the selected CSV and sent to QuickML when **Run forecast** is selected. The API derives `hour`, `day_of_week` (Monday=1), `month`, and `is_weekend` from each timestamp, then sends those numeric fields with the three weather features expected by the trained time-feature model. The timestamp itself and the training target are not sent to QuickML. With fewer than 24 staged rows the UI sends a labelled illustrative scenario instead.

If QuickML is not configured, the backend and `predict.py` use the deterministic starter baseline. If a configured endpoint fails, the backend returns an explicit error rather than silently substituting demo values.

### Train and publish the QuickML model

1. In Catalyst QuickML, upload `train_telemetry.csv`.
2. Set `target_demand_kw` as the regression target; use `timestamp`, `ambient_temp_c`, `humidity_pct`, and `solar_irradiance_wm2` as model inputs.
3. Train and execute the regression pipeline, then create its Development endpoint. Development endpoints are for testing; publishing to Production is a separate step and is not needed for local Development integration.
4. Configure the endpoint key, organization ID, environment, and Zoho OAuth values as AppSail environment variables.
5. Verify the endpoint returns one finite number per input record in the same order.

The model must be trained and published inside the user's Catalyst account. This workspace does not contain the account-specific model URL or credentials, so no claim is made that QuickML has already been trained or deployed.

## Dispatch rules

- Use **Renewable Storage Mode** if predicted demand is `> 160 kW` **or** local time is from `18:00` through `22:00`, inclusive.
- Otherwise use **Main Grid Mode**.
- Raise the critical overload alert at `>= 200 kW` independently of the mode.
- The `Grid controls` page edits scenario rules for the dashboard. It does not send switching commands to physical equipment.
- Battery state of charge is a scenario estimate; the starter kit has no live SOC feed or battery capacity settings.

## Verification

```powershell
npm test
py -3.13 -m unittest discover -s backend/tests -v
py -3.13 test_eval.py
npm run build
```

The Python self-test is the required HackSphere submission check for `predict.py`.

## Catalyst deployment

See [`deployment/README.md`](deployment/README.md) for the full project-resource checklist, Data Store schema, QuickML OAuth setup, AppSail build ZIP deployment, and Slate direct upload flow. Build release ZIPs with `npm run package:release`. After AppSail has an origin, build Slate with `npm run package:slate -- --api-url https://YOUR-APPSAIL-ORIGIN`.

The AppSail ZIP bundles Python dependencies for Linux AMD64 / CPython 3.13. The Slate ZIP must be built after the final AppSail URL is known because Vite embeds `VITE_API_BASE_URL` in the frontend. Public deployment, account-owned QuickML publication, and Catalyst table/bucket creation still require actions in the owner's Catalyst project; this workspace does not claim a live deployment.
