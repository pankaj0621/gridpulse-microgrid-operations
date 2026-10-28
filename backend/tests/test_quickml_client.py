import os
import unittest
from unittest.mock import Mock, patch

from app.quickml_client import QuickMLClient, QuickMLConfigurationError, clear_token_cache


QUICKML_ENV = {
    "QUICKML_ENDPOINT_URL": "https://quickml.example/predict",
    "QUICKML_ENDPOINT_KEY": "endpoint-key",
    "QUICKML_ORG_ID": "org-123",
    "QUICKML_ENVIRONMENT": "Development",
    "ZOHO_OAUTH_TOKEN_URL": "https://accounts.zoho.in/oauth/v2/token",
    "QUICKML_REFRESH_TOKEN": "refresh-token",
    "QUICKML_CLIENT_ID": "client-id",
    "QUICKML_CLIENT_SECRET": "client-secret",
}


class QuickMLClientTests(unittest.TestCase):
    def setUp(self):
        clear_token_cache()

    def tearDown(self):
        clear_token_cache()

    def test_refreshes_oauth_token_and_sends_catalyst_headers_for_batch(self):
        session = Mock()
        token_response = Mock()
        token_response.json.return_value = {"access_token": "access-123", "expires_in": 3600}
        prediction_response = Mock()
        prediction_response.json.return_value = {"predictions": [111.5, 202.25]}
        session.post.side_effect = [token_response, prediction_response]
        rows = [
            {"timestamp": "2026-10-24 10:00:00", "ambient_temp_c": 20, "humidity_pct": 45, "solar_irradiance_wm2": 100},
            {"timestamp": "2026-10-25 20:00:00", "ambient_temp_c": 21, "humidity_pct": 48, "solar_irradiance_wm2": 200},
        ]
        original_rows = [row.copy() for row in rows]

        with patch.dict(os.environ, QUICKML_ENV, clear=True):
            predictions = QuickMLClient.from_environment(session=session).predict(rows)

        self.assertEqual(predictions, [111.5, 202.25])
        self.assertEqual(session.post.call_count, 2)
        token_call = session.post.call_args_list[0]
        self.assertEqual(token_call.args[0], QUICKML_ENV["ZOHO_OAUTH_TOKEN_URL"])
        self.assertEqual(token_call.kwargs["data"]["grant_type"], "refresh_token")
        self.assertEqual(token_call.kwargs["data"]["refresh_token"], "refresh-token")
        inference_call = session.post.call_args_list[1]
        self.assertEqual(inference_call.args[0], QUICKML_ENV["QUICKML_ENDPOINT_URL"])
        self.assertEqual(inference_call.kwargs["json"], {"data": [
            {
                "timestamp": "2026-10-24 10:00:00",
                "ambient_temp_c": 20,
                "humidity_pct": 45,
                "solar_irradiance_wm2": 100,
                "hour": 10,
                "day_of_week": 6,
                "month": 10,
                "is_weekend": 1,
            },
            {
                "timestamp": "2026-10-25 20:00:00",
                "ambient_temp_c": 21,
                "humidity_pct": 48,
                "solar_irradiance_wm2": 200,
                "hour": 20,
                "day_of_week": 7,
                "month": 10,
                "is_weekend": 1,
            },
        ]})
        self.assertEqual(rows, original_rows)
        self.assertEqual(inference_call.kwargs["headers"]["Authorization"], "Zoho-oauthtoken access-123")
        self.assertEqual(inference_call.kwargs["headers"]["X-QUICKML-ENDPOINT-KEY"], "endpoint-key")
        self.assertEqual(inference_call.kwargs["headers"]["CATALYST-ORG"], "org-123")
        self.assertEqual(inference_call.kwargs["headers"]["Environment"], "Development")

    def test_reads_catalyst_result_field_for_predictions(self):
        session = Mock()
        token_response = Mock()
        token_response.json.return_value = {"access_token": "access-123", "expires_in": 3600}
        prediction_response = Mock()
        prediction_response.json.return_value = {
            "result": [111.5],
            "pipeLineType": "Prediction",
            "status": "Success",
        }
        session.post.side_effect = [token_response, prediction_response]

        with patch.dict(os.environ, QUICKML_ENV, clear=True):
            predictions = QuickMLClient.from_environment(session=session).predict([
                {"timestamp": "2026-10-24 10:00:00", "ambient_temp_c": 20, "humidity_pct": 45, "solar_irradiance_wm2": 100}
            ])

        self.assertEqual(predictions, [111.5])

    def test_reuses_unexpired_access_token_for_multiple_batches(self):
        session = Mock()
        token_response = Mock()
        token_response.json.return_value = {"access_token": "cached-access", "expires_in": 3600}
        inference_response = Mock()
        inference_response.json.return_value = {"predictions": [120.0]}
        session.post.side_effect = [token_response, inference_response, inference_response]

        with patch.dict(os.environ, QUICKML_ENV, clear=True):
            client = QuickMLClient.from_environment(session=session)
            self.assertEqual(client.predict([{"timestamp": "2026-10-24 00:00:00"}]), [120.0])
            self.assertEqual(client.predict([{"timestamp": "2026-10-24 01:00:00"}]), [120.0])

        self.assertEqual(session.post.call_count, 3)

    def test_rejects_partial_oauth_configuration_before_network_call(self):
        session = Mock()
        with patch.dict(os.environ, {"QUICKML_ENDPOINT_URL": QUICKML_ENV["QUICKML_ENDPOINT_URL"]}, clear=True):
            client = QuickMLClient.from_environment(session=session)
            with self.assertRaises(QuickMLConfigurationError):
                client.predict([{"timestamp": "2026-10-24 00:00:00"}])
        session.post.assert_not_called()

    def test_rejects_invalid_timestamp_before_network_call(self):
        session = Mock()
        with patch.dict(os.environ, QUICKML_ENV, clear=True):
            client = QuickMLClient.from_environment(session=session)
            with self.assertRaisesRegex(ValueError, "invalid timestamp"):
                client.predict([{"timestamp": "not-a-timestamp"}])
        session.post.assert_not_called()

    def test_rejects_wrong_length_and_non_finite_predictions(self):
        session = Mock()
        token_response = Mock()
        token_response.json.return_value = {"access_token": "access-456", "expires_in": 3600}
        wrong_count = Mock()
        wrong_count.json.return_value = {"predictions": [1.0]}
        session.post.side_effect = [token_response, wrong_count]
        rows = [{"timestamp": "2026-10-24 00:00:00"}, {"timestamp": "2026-10-24 01:00:00"}]

        with patch.dict(os.environ, QUICKML_ENV, clear=True):
            with self.assertRaisesRegex(ValueError, "count"):
                QuickMLClient.from_environment(session=session).predict(rows)

        clear_token_cache()
        session = Mock()
        token_response = Mock()
        token_response.json.return_value = {"access_token": "access-789", "expires_in": 3600}
        invalid_response = Mock()
        invalid_response.json.return_value = {"predictions": [float("inf")]}
        session.post.side_effect = [token_response, invalid_response]
        with patch.dict(os.environ, QUICKML_ENV, clear=True):
            with self.assertRaisesRegex(ValueError, "finite"):
                QuickMLClient.from_environment(session=session).predict(rows[:1])


if __name__ == "__main__":
    unittest.main()
