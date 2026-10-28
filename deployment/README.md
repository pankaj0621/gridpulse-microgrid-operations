# GridPulse Catalyst Deployment

This deployment uses the stack specified in the HackSphere starter kit: Catalyst Slate for the web app, AppSail for the API, QuickML for demand inference, Stratus for uploaded CSVs, and Data Store for upload and forecast audit records.

## 1. Create the Catalyst resources

Use the Catalyst project and environment in which you intend to deploy. Create the following resources before switching AppSail to Catalyst storage:

1. Create a Stratus bucket, for example `gridpulse-telemetry`.
2. Create the two Data Store tables and columns in `datastore-schema.json`. Catalyst creates its system columns (`ROWID`, `CREATORID`, `CREATEDTIME`, `MODIFIEDTIME`) automatically; do not add those yourself.
3. Give the AppSail service profile read/write access to Stratus and Data Store.

The application writes the original uploaded CSV to `telemetry/YYYY/MM/` in Stratus. It records row counts, missing-value totals and object keys in `GridPulseTelemetryUploads`. Each successful forecast creates a summary row in `GridPulseForecastLogs`. The Data Store summary endpoint reads upload and forecast pages so that dashboard counters survive AppSail restarts.

## 2. Train and publish QuickML

In Catalyst QuickML, use the supplied `train_telemetry.csv`:

- Regression target: `target_demand_kw`.
- Inputs: `timestamp`, `ambient_temp_c`, `humidity_pct`, `solar_irradiance_wm2`.
- Publish the trained pipeline and use its endpoint URL and endpoint key.
- Create an OAuth refresh token with the `QuickML.deployment.READ` scope. Use the OAuth token URL for your Zoho data centre.

The endpoint adapter sends batches in the starter-kit shape `{"data": [{...}]}` and requires `{"predictions": [number, ...]}` with one finite value per input row, in order.

## 3. Deploy the AppSail API

The release packager creates `release/GridPulse_AppSail.zip`. It includes the API source and Python dependencies selected for Catalyst-managed Python 3.13 on Linux AMD64. This is the build ZIP for Catalyst Console direct upload.

1. In the Catalyst project, open **Serverless → AppSail → Deploy from Console**.
2. Choose **Catalyst-Managed Runtime**, select **Python 3.13**, and upload `GridPulse_AppSail.zip`.
3. Set the startup command to:

   ```sh
   sh -c 'python3 -m uvicorn main:app --host 0.0.0.0 --port ${X_ZOHO_CATALYST_LISTEN_PORT:-9000}'
   ```

4. Set AppSail environment variables:

   ```text
   GRIDPULSE_STORAGE_MODE=catalyst
   GRIDPULSE_STRATUS_BUCKET=<created bucket name>
   GRIDPULSE_DATASTORE_UPLOADS_TABLE=GridPulseTelemetryUploads
   GRIDPULSE_DATASTORE_FORECASTS_TABLE=GridPulseForecastLogs
   CORS_ORIGINS=<deployed Slate origin>
   QUICKML_ENDPOINT_URL=<published pipeline endpoint URL>
   QUICKML_ENDPOINT_KEY=<QuickML endpoint key>
   QUICKML_ORG_ID=<Catalyst organization ID required by the QuickML endpoint>
   QUICKML_ENVIRONMENT=Development or Production
   ZOHO_OAUTH_TOKEN_URL=<OAuth token URL for your Zoho data centre>
   QUICKML_REFRESH_TOKEN=<OAuth refresh token>
   QUICKML_CLIENT_ID=<OAuth client ID>
   QUICKML_CLIENT_SECRET=<OAuth client secret>
   ```

   Keep OAuth values only in AppSail’s environment configuration. Do not add them to the Slate build or any `VITE_*` variable.

5. After deployment, open `<AppSail origin>/api/health`. Confirm `status` is `ok`, `storage_mode` is `catalyst`, `storage_configured` and `quickml_configured` are `true`. If QuickML is missing setup, the health response lists the missing variable names without returning secret values.

## 4. Build and deploy Slate

Slate needs the AppSail origin embedded in the Vite build. After AppSail is deployed and its origin is known, run from the project root:

```powershell
npm run package:slate -- --api-url https://YOUR-APPSAIL-ORIGIN
```

This builds and validates `release/GridPulse_Slate_Build.zip` with the supplied API origin. In Catalyst Slate, use **Direct Upload**, upload that ZIP, select React/Vite, and deploy to the Development environment. Add the Slate deployment origin to AppSail’s `CORS_ORIGINS`, then redeploy AppSail if that value changed.

For Catalyst CLI instead, log in to the CLI, run `catalyst init slate` from the frontend project, link the Slate app to the Catalyst project, configure `VITE_API_BASE_URL` in Slate for the deployment environment, then run `catalyst deploy slate`. Slate CLI support and the React + Vite start command are documented in the official [Slate CLI guide](https://docs.catalyst.zoho.com/en/slate/help/deploy-from-cli/).

## 5. Build the release ZIPs

From the repository root:

```powershell
npm run package:release
```

This creates and validates:

- `release/GridPulse_Source.zip` — full source and supplied challenge data.
- `release/GridPulse_Slate_Source.zip` — Slate app source for CLI or source-based setup.
- `release/GridPulse_AppSail.zip` — AppSail build files plus Linux/Python 3.13 dependencies for Console direct upload.

The Slate build ZIP is generated separately after the AppSail URL exists. Release ZIPs exclude local `.env` files, SQLite data, caches, `node_modules`, and local build output.

## Local development

Use `.env.example` with `GRIDPULSE_STORAGE_MODE=local` for SQLite-backed development. In that mode, forecasts use the deterministic baseline until QuickML OAuth settings are provided. The dashboard labels baseline and scenario outputs. Catalyst mode does not silently fall back to SQLite if Stratus or Data Store fails.

## Production checklist

- Confirm QuickML is trained and published in the selected Catalyst project/environment.
- Confirm the refresh token has `QuickML.deployment.READ` and belongs to the same Zoho data centre as `ZOHO_OAUTH_TOKEN_URL`.
- Confirm the AppSail profile can access the configured Stratus bucket and both Data Store tables.
- Confirm `CORS_ORIGINS` contains the exact Slate origin and no wildcard.
- Build Slate only after the final AppSail origin is available.
- Check `/api/health`, upload a small UTF-8 CSV, verify its object in Stratus and audit row in Data Store, then run a 24-hour forecast and verify its audit row.
- Run `npm test`, `npm run test:backend`, `npm run test:submission`, and `npm run build` before publishing the final Slate deployment.

Catalyst provides different Data Store record quotas in Development and Production. Use the environment quotas displayed in the Catalyst console for the selected project when planning retention; this implementation stores one upload row per CSV and one forecast row per successful request rather than creating a Data Store row for every forecast point.

## Official documentation

- [Catalyst Slate](https://docs.catalyst.zoho.com/en/slate/help/introduction/)
- [Slate direct upload](https://docs.catalyst.zoho.com/en/slate/help/direct-upload/)
- [AppSail Python runtimes and build files](https://docs.catalyst.zoho.com/en/serverless/help/appsail/catalyst-managed-runtimes/key-concepts/)
- [AppSail Console deployment](https://docs.catalyst.zoho.com/en/serverless/help/appsail/catalyst-managed-runtimes/deploy-from-console/)
- [Python Catalyst SDK in AppSail](https://docs.catalyst.zoho.com/en/sdk/python/v1/serverless/appsail/execute-appsail/)
- [QuickML pipeline endpoint authentication](https://docs.catalyst.zoho.com/en/quickml/help/pipeline-endpoints/)
- [Stratus object uploads](https://docs.catalyst.zoho.com/en/sdk/python/v1/cloud-scale/stratus/upload-object/)
- [Data Store insert rows](https://docs.catalyst.zoho.com/en/sdk/python/v1/cloud-scale/data-store/insert-rows/)
- [Data Store pagination](https://docs.catalyst.zoho.com/en/sdk/python/v1/cloud-scale/data-store/get-rows/)
- [Data Store column types](https://docs.catalyst.zoho.com/en/cloud-scale/help/data-store/columns/)
