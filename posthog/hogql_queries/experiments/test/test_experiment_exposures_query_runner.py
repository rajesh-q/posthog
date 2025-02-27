from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.test import override_settings
from freezegun import freeze_time
from django.utils import timezone

from posthog.hogql_queries.experiments.experiment_exposures_query_runner import ExperimentExposuresQueryRunner
from posthog.models.experiment import Experiment
from posthog.models.feature_flag import FeatureFlag
from posthog.schema import ExperimentExposureQuery
from posthog.test.base import (
    APIBaseTest,
    ClickhouseTestMixin,
    flush_persons_and_events,
)
from posthog.test.test_journeys import journeys_for


@override_settings(IN_UNIT_TESTING=True)
class TestExperimentExposuresQueryRunner(ClickhouseTestMixin, APIBaseTest):
    def create_feature_flag(self, key="test-experiment"):
        return FeatureFlag.objects.create(
            name=f"Test experiment flag: {key}",
            key=key,
            team=self.team,
            filters={
                "groups": [{"properties": [], "rollout_percentage": None}],
                "multivariate": {
                    "variants": [
                        {
                            "key": "control",
                            "name": "Control",
                            "rollout_percentage": 50,
                        },
                        {
                            "key": "test",
                            "name": "Test",
                            "rollout_percentage": 50,
                        },
                    ]
                },
            },
            created_by=self.user,
        )

    def create_experiment(
        self,
        name="test-experiment",
        feature_flag=None,
        start_date=None,
        end_date=None,
    ):
        if feature_flag is None:
            feature_flag = self.create_feature_flag(name)
        if start_date is None:
            start_date = timezone.now()
        if end_date is None:
            end_date = timezone.now() + timedelta(days=14)

        # Only make timezone aware if not already aware
        if timezone.is_naive(start_date):
            start_date = timezone.make_aware(start_date)
        if timezone.is_naive(end_date):
            end_date = timezone.make_aware(end_date)

        return Experiment.objects.create(
            name=name,
            team=self.team,
            feature_flag=feature_flag,
            start_date=start_date,
            end_date=end_date,
        )

    def setUp(self):
        super().setUp()
        self.feature_flag = self.create_feature_flag()
        self.experiment = self.create_experiment(
            feature_flag=self.feature_flag,
            start_date=datetime(2024, 1, 1).replace(tzinfo=ZoneInfo("UTC")),
            end_date=datetime(2024, 1, 7).replace(tzinfo=ZoneInfo("UTC")),
        )

    @freeze_time("2024-01-07T12:00:00Z")
    def test_exposure_query_returns_correct_timeseries(self):
        ff_property = f"$feature/{self.feature_flag.key}"

        # Create test data using journeys
        journeys_for(
            {
                "user_control_1": [
                    {
                        "event": "$feature_flag_called",
                        "timestamp": "2024-01-02",
                        "properties": {
                            "$feature_flag_response": "control",
                            ff_property: "control",
                            "$feature_flag": self.feature_flag.key,
                        },
                    },
                ],
                "user_control_2": [
                    {
                        "event": "$feature_flag_called",
                        "timestamp": "2024-01-02",
                        "properties": {
                            "$feature_flag_response": "control",
                            ff_property: "control",
                            "$feature_flag": self.feature_flag.key,
                        },
                    },
                ],
                "user_control_3": [
                    {
                        "event": "$feature_flag_called",
                        "timestamp": "2024-01-03",
                        "properties": {
                            "$feature_flag_response": "control",
                            ff_property: "control",
                            "$feature_flag": self.feature_flag.key,
                        },
                    },
                ],
                "user_control_4": [
                    {
                        "event": "$feature_flag_called",
                        "timestamp": "2024-01-03",
                        "properties": {
                            "$feature_flag_response": "control",
                            ff_property: "control",
                            "$feature_flag": self.feature_flag.key,
                        },
                    },
                ],
                "user_test_1": [
                    {
                        "event": "$feature_flag_called",
                        "timestamp": "2024-01-02",
                        "properties": {
                            "$feature_flag_response": "test",
                            ff_property: "test",
                            "$feature_flag": self.feature_flag.key,
                        },
                    },
                ],
                "user_test_2": [
                    {
                        "event": "$feature_flag_called",
                        "timestamp": "2024-01-02",
                        "properties": {
                            "$feature_flag_response": "test",
                            ff_property: "test",
                            "$feature_flag": self.feature_flag.key,
                        },
                    },
                ],
                "user_test_3": [
                    {
                        "event": "$feature_flag_called",
                        "timestamp": "2024-01-02",
                        "properties": {
                            "$feature_flag_response": "test",
                            ff_property: "test",
                            "$feature_flag": self.feature_flag.key,
                        },
                    },
                ],
                "user_test_4": [
                    {
                        "event": "$feature_flag_called",
                        "timestamp": "2024-01-03",
                        "properties": {
                            "$feature_flag_response": "test",
                            ff_property: "test",
                            "$feature_flag": self.feature_flag.key,
                        },
                    },
                ],
                "user_test_5": [
                    {
                        "event": "$feature_flag_called",
                        "timestamp": "2024-01-03",
                        "properties": {
                            "$feature_flag_response": "test",
                            ff_property: "test",
                            "$feature_flag": self.feature_flag.key,
                        },
                    },
                ],
            },
            self.team,
        )

        flush_persons_and_events()

        query = ExperimentExposureQuery(
            kind="ExperimentExposureQuery",
            experiment_id=self.experiment.id,
        )

        query_runner = ExperimentExposuresQueryRunner(
            team=self.team,
            query=query,
        )

        response = query_runner.calculate()

        self.assertEqual(len(response.timeseries), 2)  # Two variants with data

        control_series = next(series for series in response.timeseries if series.variant == "control")
        test_series = next(series for series in response.timeseries if series.variant == "test")

        self.assertEqual(control_series.exposure_counts, [2, 4])  # Two people on day 1, cumulative four people by day 2
        self.assertEqual(len(control_series.days), 2)

        self.assertEqual(test_series.exposure_counts, [3, 5])  # Three people on day 1, cumulative five people by day 2
        self.assertEqual(len(test_series.days), 2)

        self.assertEqual(response.total_exposures["control"], 4)
        self.assertEqual(response.total_exposures["test"], 5)
