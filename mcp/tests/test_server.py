"""Unit tests for the vendored mcp_forall tool layer.

The tools now route through ``bharatvitals.runtime.client`` (a
``BharatVitalsClient``) instead of ``requests``, so the backend is mocked at
that boundary.

Run from the ``mcp/`` directory:
    uv run python -m unittest discover -s tests
"""

import unittest
from unittest.mock import Mock, patch

from bharatvitals import server


class ServerToolTests(unittest.TestCase):
    @patch("bharatvitals.runtime.client")
    def test_srs_life_table_forwards_expected_params(self, client):
        client.get.return_value = [{"state": "Kerala", "e0": 74.1}]

        result = server.srs_query_life_table(state="Kerala", period="2020-2024")

        self.assertEqual(result, {"count": 1, "rows": [{"state": "Kerala", "e0": 74.1}]})
        client.get.assert_called_once_with(
            "srs",
            "/life_table",
            {"state": "Kerala", "period": "2020-2024", "category": "", "limit": "10000"},
            timeout=server.REQUEST_TIMEOUT_SECONDS,
        )

    def test_srs_discovery_tools_are_available(self):
        self.assertTrue(hasattr(server, "srs_list_states"))
        self.assertTrue(hasattr(server, "srs_list_cod_tables"))
        self.assertTrue(hasattr(server, "srs_available_periods"))
        self.assertTrue(hasattr(server, "srs_list_cod_periods"))
        self.assertTrue(hasattr(server, "srs_list_bulletin_years"))
        self.assertTrue(hasattr(server, "srs_list_bulletin_indicators"))
        self.assertTrue(hasattr(server, "srs_list_stat_report_years"))
        self.assertTrue(hasattr(server, "srs_list_stat_report_indicators"))
        self.assertTrue(hasattr(server, "srs_health"))

    @patch("bharatvitals.runtime.client")
    def test_hmis_discovery_and_analysis_wrappers_forward_params(self, client):
        client.get.return_value = {"rows": [{"indicator": "Beds"}]}

        server.hmis_list_indicators(pattern="bed", geography="district")
        client.get.assert_called_with(
            "hmis",
            "/indicators",
            {"pattern": "bed", "geography": "district", "match": "fixed"},
            timeout=server.REQUEST_TIMEOUT_SECONDS,
        )

        server.hmis_periodicity(indicator="Malaria Cases", state="Kerala", method="lomb_scargle")
        client.get.assert_called_with(
            "hmis",
            "/periodicity",
            {
                "indicator": "Malaria Cases",
                "state": "Kerala",
                "method": "lomb_scargle",
                "detrend": "TRUE",
            },
            timeout=server.REQUEST_TIMEOUT_SECONDS,
        )

        server.hmis_decompose(indicator="Malaria Cases", state="Kerala", frequency=12)
        client.get.assert_called_with(
            "hmis",
            "/decompose",
            {
                "indicator": "Malaria Cases",
                "state": "Kerala",
                "frequency": "12",
                "s_window": "periodic",
            },
            timeout=server.REQUEST_TIMEOUT_SECONDS,
        )

        with self.assertRaisesRegex(ValueError, "method must be one of"):
            server.hmis_periodicity(indicator="X", method="fft")

    @patch("bharatvitals.runtime.client")
    def test_mccd_causes_and_categorize_forward_params(self, client):
        client.get.return_value = {"rows": [{"cause": "Ischaemic heart disease"}]}

        server.mccd_causes(pattern="coronary")
        client.get.assert_called_with(
            "mccd",
            "/causes",
            {"pattern": "coronary"},
            timeout=server.REQUEST_TIMEOUT_SECONDS,
        )

        server.mccd_categorize(table="cause", cause="IX.", state="Kerala", year="2018:2022")
        client.get.assert_called_with(
            "mccd",
            "/categorize",
            {"table": "cause", "cause": "IX.", "state": "Kerala", "year": "2018:2022"},
            timeout=server.REQUEST_TIMEOUT_SECONDS,
        )

        with self.assertRaisesRegex(ValueError, "table for categorize"):
            server.mccd_categorize(table="deaths")

    @patch("bharatvitals.runtime.client")
    def test_srs_discovery_wrappers_forward_expected_urls(self, client):
        client.get.return_value = [2014]

        self.assertEqual(server.srs_list_cod_periods(), {"count": 1, "rows": [2014]})
        client.get.assert_called_with(
            "srs",
            "/cod_periods",
            {},
            timeout=server.REQUEST_TIMEOUT_SECONDS,
        )

        self.assertEqual(server.srs_list_stat_report_indicators(), {"count": 1, "rows": [2014]})
        client.get.assert_called_with(
            "srs",
            "/stat_report_indicators",
            {},
            timeout=server.REQUEST_TIMEOUT_SECONDS,
        )

    @patch("bharatvitals.runtime.client")
    def test_api_health_probes_every_backend_and_isolates_failures(self, client):
        def side_effect(source, endpoint, params=None, *, timeout=None):
            if source == "hmis":
                raise RuntimeError("down")
            return {"status": "ok", "package": "x", "version": "1.0"}

        client.get.side_effect = side_effect

        results = server.api_health()

        self.assertEqual(set(results), {
            "hmisindia", "mccdindia", "censusindia", "srsindia", "crsindia",
        })
        self.assertIn("error", results["hmisindia"])
        self.assertEqual(results["mccdindia"]["status"], "ok")
        self.assertEqual(client.get.call_count, 5)

    def test_survey_tools_are_absent_from_server_and_guide(self):
        self.assertFalse(hasattr(server, "query_consumption"))
        self.assertFalse(hasattr(server, "query_healthsurvey"))
        guide = server.tool_guide()
        self.assertNotIn("query_consumption", guide)
        self.assertNotIn("query_healthsurvey", guide)

    @patch("bharatvitals.runtime.client")
    def test_census_discovery_and_query_tools_forward_expected_params(self, client):
        client.get.return_value = {"rows": [{"year": 2011}]}

        self.assertEqual(server.census_list_geographies(), {"rows": [{"year": 2011}]})
        self.assertEqual(
            server.census_search_variables(query="literacy"),
            {"rows": [{"year": 2011}]},
        )
        self.assertEqual(
            server.census_query(
                year=2011,
                geography="district",
                state="Maharashtra",
                variables=["population", "literacy_rate"],
            ),
            {"rows": [{"year": 2011}]},
        )

        client.get.assert_any_call(
            "census",
            "/geographies",
            {},
            timeout=server.REQUEST_TIMEOUT_SECONDS,
        )
        client.get.assert_any_call(
            "census",
            "/search",
            {"pattern": "literacy"},
            timeout=server.REQUEST_TIMEOUT_SECONDS,
        )

    @patch("bharatvitals.runtime.client")
    def test_census_population_and_projection_validation(self, client):
        client.get.return_value = {"rows": [{"population": 123}]}

        self.assertEqual(
            server.census_population(year=2011, geography="state"),
            {"rows": [{"population": 123}]},
        )
        self.assertEqual(
            server.census_population_projection(year=2031, geography="district", state="Maharashtra"),
            {"rows": [{"population": 123}]},
        )

        with self.assertRaisesRegex(ValueError, "Unsupported Census year"):
            server.census_population(year=1900, geography="state")

        with self.assertRaisesRegex(ValueError, "Supported geography"):
            server.census_population(year=2011, geography="city")

        with self.assertRaisesRegex(ValueError, "District-level population projections"):
            server.census_population_projection(year=2035, geography="district", state="Maharashtra")

    @patch("bharatvitals.runtime.client")
    def test_census_health_forwards_expected_url(self, client):
        client.get.return_value = {"status": "ok", "package": "censusindia"}

        self.assertEqual(server.census_health(), {"status": "ok", "package": "censusindia"})
        client.get.assert_called_once_with(
            "census",
            "/health",
            {},
            timeout=server.REQUEST_TIMEOUT_SECONDS,
        )

    def test_census_discovery_tools_are_available(self):
        self.assertTrue(hasattr(server, "census_list_geographies"))
        self.assertTrue(hasattr(server, "census_list_variables"))
        self.assertTrue(hasattr(server, "census_search_variables"))
        self.assertTrue(hasattr(server, "census_query"))
        self.assertTrue(hasattr(server, "census_population"))
        self.assertTrue(hasattr(server, "census_population_projection"))
        self.assertTrue(hasattr(server, "census_health"))
        self.assertTrue(not hasattr(server, "census_languages"))
        self.assertTrue(not hasattr(server, "census_social_composition"))
        self.assertTrue(not hasattr(server, "census_attach_geometry"))
        self.assertTrue(not hasattr(server, "census_summary"))


if __name__ == "__main__":
    unittest.main()
