from typing import Callable
from unittest.mock import patch

import pytest

import optuna
from optuna.integration import PyCmaSampler
from optuna.integration import SkoptSampler
from optuna.samplers import BaseSampler
from optuna.testing.samplers import FirstTrialOnlyRandomSampler


pytestmark = pytest.mark.integration


parametrize_sampler = pytest.mark.parametrize(
    "sampler_class", [optuna.integration.SkoptSampler, optuna.integration.PyCmaSampler]
)


@pytest.mark.parametrize(
    "sampler_class",
    [
        lambda: SkoptSampler(independent_sampler=FirstTrialOnlyRandomSampler()),
        lambda: PyCmaSampler(independent_sampler=FirstTrialOnlyRandomSampler()),
    ],
)
def test_suggested_value(sampler_class: Callable[[], BaseSampler]) -> None:

    sampler = sampler_class()
    # direction='minimize'
    study = optuna.create_study(sampler=sampler, direction="minimize")
    study.optimize(_objective, n_trials=10, catch=())
    for trial in study.trials:
        for param_name, param_value in trial.params.items():
            distribution = trial.distributions[param_name]
            param_value_in_internal_repr = distribution.to_internal_repr(param_value)
            assert distribution._contains(param_value_in_internal_repr)

    # direction='maximize'
    study = optuna.create_study(sampler=sampler, direction="maximize")
    study.optimize(_objective, n_trials=10, catch=())
    for trial in study.trials:
        for param_name, param_value in trial.params.items():
            distribution = trial.distributions[param_name]
            param_value_in_internal_repr = distribution.to_internal_repr(param_value)
            assert distribution._contains(param_value_in_internal_repr)


@parametrize_sampler
def test_sample_independent(sampler_class: Callable[[], BaseSampler]) -> None:

    sampler = sampler_class()
    study = optuna.create_study(sampler=sampler)

    # First trial.
    def objective0(trial: optuna.trial.Trial) -> float:

        p0 = trial.suggest_float("p0", 0, 10)
        p1 = trial.suggest_float("p1", 1, 10, log=True)
        p2 = trial.suggest_int("p2", 0, 10)
        p3 = trial.suggest_float("p3", 0, 9, step=3)
        p4 = trial.suggest_categorical("p4", ["10", "20", "30"])
        assert isinstance(p4, str)
        return p0 + p1 + p2 + p3 + int(p4)

    with patch.object(sampler, "sample_independent") as mock_object:
        mock_object.side_effect = [1, 2, 3, 3, "10"]

        study.optimize(objective0, n_trials=1)

        # In first trial, all parameters were suggested via `sample_independent`.
        assert mock_object.call_count == 5

    # Second trial.
    def objective1(trial: optuna.trial.Trial) -> float:

        # p0, p2 and p4 are deleted.
        p1 = trial.suggest_float("p1", 1, 10, log=True)
        p3 = trial.suggest_float("p3", 0, 9, step=3)

        # p5 is added.
        p5 = trial.suggest_float("p5", 0, 1)

        return p1 + p3 + p5

    with patch.object(sampler, "sample_independent") as mock_object:
        mock_object.side_effect = [0]

        study.optimize(objective1, n_trials=1)

        assert [call[1][2] for call in mock_object.mock_calls] == ["p5"]

    # Third trial.
    def objective2(trial: optuna.trial.Trial) -> float:

        p1 = trial.suggest_float("p1", 50, 100, log=True)  # The range has been changed.
        p3 = trial.suggest_float("p3", 0, 9, step=3)
        p5 = trial.suggest_float("p5", 0, 1)

        return p1 + p3 + p5

    with patch.object(sampler, "sample_independent") as mock_object:
        mock_object.side_effect = [90, 0.2]

        study.optimize(objective2, n_trials=1)

        assert [call[1][2] for call in mock_object.mock_calls] == ["p1", "p5"]


@pytest.mark.parametrize(
    "sampler_class",
    [
        lambda x: SkoptSampler(warn_independent_sampling=x),
        lambda x: PyCmaSampler(warn_independent_sampling=x),
    ],
)
def test_warn_independent_sampling(sampler_class: Callable[[bool], BaseSampler]) -> None:

    # warn_independent_sampling=True
    sampler = sampler_class(True)
    study = optuna.create_study(sampler=sampler)

    class_name = "optuna.integration.{}".format(sampler.__class__.__name__)
    method_name = "{}._log_independent_sampling".format(class_name)

    with patch(method_name) as mock_object:
        study.optimize(
            lambda t: t.suggest_float("p0", 0, 10) + t.suggest_float("q0", 0, 10), n_trials=1
        )
        assert mock_object.call_count == 0

    with patch(method_name) as mock_object:
        study.optimize(
            lambda t: t.suggest_float("p1", 0, 10) + t.suggest_float("q1", 0, 10), n_trials=1
        )
        assert mock_object.call_count == 2

    # warn_independent_sampling=False
    sampler = sampler_class(False)
    study = optuna.create_study(sampler=sampler)

    with patch(method_name) as mock_object:
        study.optimize(
            lambda t: t.suggest_float("p0", 0, 10) + t.suggest_float("q0", 0, 10), n_trials=1
        )
        assert mock_object.call_count == 0

    with patch(method_name) as mock_object:
        study.optimize(
            lambda t: t.suggest_float("p1", 0, 10) + t.suggest_float("q1", 0, 10), n_trials=1
        )
        assert mock_object.call_count == 0


def _objective(trial: optuna.trial.Trial) -> float:

    p0 = trial.suggest_float("p0", -3.3, 5.2)
    p1 = trial.suggest_float("p1", 2.0, 2.0)
    p2 = trial.suggest_float("p2", 0.0001, 0.3, log=True)
    p3 = trial.suggest_float("p3", 1.1, 1.1, log=True)
    p4 = trial.suggest_int("p4", -100, 8)
    p5 = trial.suggest_int("p5", -20, -20)
    p6 = trial.suggest_float("p6", 10, 20, step=2)
    p7 = trial.suggest_float("p7", 0.1, 1.0, step=0.1)
    p8 = trial.suggest_float("p8", 2.2, 2.2, step=0.5)
    p9 = trial.suggest_categorical("p9", ["9", "3", "0", "8"])
    assert isinstance(p9, str)

    return p0 + p1 + p2 + p3 + p4 + p5 + p6 + p7 + p8 + int(p9)
