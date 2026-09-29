import unittest
from unittest.mock import Mock, patch

import requests

from mcp_forall import server


def url(base, path):
    """Join a base API URL and a route path exactly like server._request_json."""
    return f"{base.rstrip('/')}/{path.lstrip('/')}"


class SurveyToolTests(unittest.TestCase):
    @staticmethod
    def response(payload, status_code=200, text=""):
        response = Mock()
        response.status_code = status_code
        response.text = text
        response.json.return_value = payload
        return response

    @patch("mcp_forall.server.requests.get")
    def test_consumption_forwards_operation_params_and_envelope(self, get):
        get.return_value = self.response({"shares": [{"round": "HCES"}]})

        result = server.query_consumption(
            "food_group_shares", {"by": "round", "round": 68}
        )

        self.assertEqual(result, {"shares": [{"round": "HCES"}]})
        get.assert_called_once_with(
            url(server.CONSUMPTION_API_URL, "shares/food-group"),
            params={"by": "round", "round": "68"},
            json=None,
            timeout=server.REQUEST_TIMEOUT_SECONDS,
        )

    @patch("mcp_forall.server.requests.post")
    def test_healthsurvey_sql_forwards_json(self, post):
        post.return_value = self.response({"rows": [{"n": 1}], "n_rows": 1})

        result = server.query_healthsurvey(
            "sql", sql="SELECT 1", max_rows=25
        )

        self.assertEqual(result["n_rows"], 1)
        post.assert_called_once_with(
            url(server.HEALTHSURVEY_API_URL, "sql"),
            params=None,
            json={"query": "SELECT 1", "max_rows": 25},
            timeout=server.REQUEST_TIMEOUT_SECONDS,
        )

    def test_required_survey_parameters_are_validated(self):
        with self.assertRaisesRegex(ValueError, "params.item"):
            server.query_consumption("item_trends", {})
        with self.assertRaisesRegex(ValueError, "params.table"):
            server.query_healthsurvey("diseases", {"table": "invalid"})
        with self.assertRaisesRegex(ValueError, "params.query"):
            server.query_healthsurvey("disease_lookup", {})

    @patch("mcp_forall.server.requests.get")
    def test_http_errors_identify_survey_api(self, get):
        get.return_value = self.response({}, status_code=503, text="offline")

        with self.assertRaisesRegex(ValueError, "consumption survey API returned HTTP 503"):
            server.query_consumption("overview")

    @patch("mcp_forall.server.requests.get")
    def test_srs_life_table_forwards_expected_params(self, get):
        get.return_value = self.response([{"state": "Kerala", "e0": 74.1}])

        result = server.srs_query_life_table(state="Kerala", period="2020-2024")

        self.assertEqual(result, {"count": 1, "rows": [{"state": "Kerala", "e0": 74.1}]})
        get.assert_called_once_with(
            url(server.SRS_API_URL, "life_table"),
            params={"state": "Kerala", "period": "2020-2024", "category": "", "limit": "10000"},
            json=None,
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

    @patch("mcp_forall.server.requests.get")
    def test_hmis_discovery_and_analysis_wrappers_forward_params(self, get):
        get.return_value = self.response({"rows": [{"indicator": "Beds"}]})

        server.hmis_list_indicators(pattern="bed", geography="district")
        get.assert_called_with(
            url(server.HMIS_API_URL, "indicators"),
            params={"pattern": "bed", "geography": "district", "match": "fixed"},
            json=None,
            timeout=server.REQUEST_TIMEOUT_SECONDS,
        )

        server.hmis_periodicity(indicator="Malaria Cases", state="Kerala", method="lomb_scargle")
        get.assert_called_with(
            url(server.HMIS_API_URL, "periodicity"),
            params={
                "indicator": "Malaria Cases",
                "state": "Kerala",
                "method": "lomb_scargle",
                "detrend": "TRUE",
            },
            json=None,
            timeout=server.REQUEST_TIMEOUT_SECONDS,
        )

        server.hmis_decompose(indicator="Malaria Cases", state="Kerala", frequency=12)
        get.assert_called_with(
            url(server.HMIS_API_URL, "decompose"),
            params={
                "indicator": "Malaria Cases",
                "state": "Kerala",
                "frequency": "12",
                "s_window": "periodic",
            },
            json=None,
            timeout=server.REQUEST_TIMEOUT_SECONDS,
        )

        with self.assertRaisesRegex(ValueError, "method must be one of"):
            server.hmis_periodicity(indicator="X", method="fft")

    @patch("mcp_forall.server.requests.get")
    def test_mccd_causes_and_categorize_forward_params(self, get):
        get.return_value = self.response({"rows": [{"cause": "Ischaemic heart disease"}]})

        server.mccd_causes(pattern="coronary")
        get.assert_called_with(
            url(server.MCCD_API_URL, "causes"),
            params={"pattern": "coronary"},
            json=None,
            timeout=server.REQUEST_TIMEOUT_SECONDS,
        )

        server.mccd_categorize(table="cause", cause="IX.", state="Kerala", year="2018:2022")
        get.assert_called_with(
            url(server.MCCD_API_URL, "categorize"),
            params={"table": "cause", "cause": "IX.", "state": "Kerala", "year": "2018:2022"},
            json=None,
            timeout=server.REQUEST_TIMEOUT_SECONDS,
        )

        with self.assertRaisesRegex(ValueError, "table for categorize"):
            server.mccd_categorize(table="deaths")

    @patch("mcp_forall.server.requests.get")
    def test_srs_discovery_wrappers_forward_expected_urls(self, get):
        get.return_value = self.response([2014])

        self.assertEqual(server.srs_list_cod_periods(), {"count": 1, "rows": [2014]})
        get.assert_called_with(
            url(server.SRS_API_URL, "cod_periods"),
            params=None,
            json=None,
            timeout=server.REQUEST_TIMEOUT_SECONDS,
        )

        self.assertEqual(server.srs_list_stat_report_indicators(), {"count": 1, "rows": [2014]})
        get.assert_called_with(
            url(server.SRS_API_URL, "stat_report_indicators"),
            params=None,
            json=None,
            timeout=server.REQUEST_TIMEOUT_SECONDS,
        )

    @patch("mcp_forall.server.requests.get")
    def test_api_health_probes_every_backend_and_isolates_failures(self, get):
        def side_effect(url, params=None, json=None, timeout=30):
            if server.HMIS_API_URL.rstrip("/") in url:
                raise requests.exceptions.ConnectionError("down")
            response = Mock()
            response.status_code = 200
            response.text = ""
            response.json.return_value = {"status": "ok", "package": "x", "version": "1.0"}
            return response

        get.side_effect = side_effect

        results = server.api_health()

        self.assertEqual(set(results), {
            "hmisindia", "mccdindia", "censusindia", "srsindia",
            "consumptionsurveyindia", "healthsurveyindia",
        })
        self.assertIn("error", results["hmisindia"])
        self.assertEqual(results["mccdindia"]["status"], "ok")
        self.assertEqual(get.call_count, 6)

    @patch("mcp_forall.server.requests.get")
    def test_census_discovery_and_query_tools_forward_expected_params(self, get):
        get.return_value = self.response({"rows": [{"year": 2011}]})

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

        get.assert_any_call(
            url(server.CENSUS_API_URL, "geographies"),
            params=None,
            json=None,
            timeout=server.REQUEST_TIMEOUT_SECONDS,
        )
        get.assert_any_call(
            url(server.CENSUS_API_URL, "search"),
            params={"pattern": "literacy"},
            json=None,
            timeout=server.REQUEST_TIMEOUT_SECONDS,
        )

    @patch("mcp_forall.server.requests.get")
    def test_census_population_and_projection_validation(self, get):
        get.return_value = self.response({"rows": [{"population": 123}]})

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

    @patch("mcp_forall.server.requests.get")
    def test_census_health_forwards_expected_url(self, get):
        get.return_value = self.response({"status": "ok", "package": "censusindia"})

        self.assertEqual(server.census_health(), {"status": "ok", "package": "censusindia"})
        get.assert_called_once_with(
            url(server.CENSUS_API_URL, "health"),
            params=None,
            json=None,
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