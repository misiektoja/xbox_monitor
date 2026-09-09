"""Shared fixtures for the offline test suite.

Every test starts from the shipped defaults. Startup assigns module globals directly, load_dotenv writes into
os.environ and nothing takes any of it back, so without a reset one test's startup would leak into the next.
"""

import sys

import pytest

import xbox_monitor as monitor


# Names startup assigns from the config file, the environment or the command line, restored after every test
_STARTUP_GLOBALS = tuple(sorted(monitor._config_allowed_names())) + ("CLI_CONFIG_PATH", "EXPORTED_SECRET_KEYS", "LIVENESS_CHECK_COUNTER", "XBOX_AUTH_REFRESH_VERSION", "STDOUT_AT_START_OF_LINE", "MONITORING_ACTIVE")


@pytest.fixture(autouse=True)
# Restores module state, removes exported secrets and unwraps stdout, so no simulated startup outlives its test
def isolated_module_state(monkeypatch):
    for name in _STARTUP_GLOBALS:
        monkeypatch.setattr(monitor, name, getattr(monitor, name), raising=False)
    monkeypatch.setattr(monitor, "SECRET_SOURCES", {})
    # load_dotenv writes into os.environ and nothing removes it again, so a test that loads a dotenv would
    # otherwise leak its secrets into every later test through the exported-environment lookup at startup
    for secret in monitor.SECRET_KEYS:
        monkeypatch.delenv(secret, raising=False)
    original_stdout = sys.stdout
    yield
    sys.stdout = original_stdout


@pytest.fixture(autouse=True)
# Keeps startup from installing real signal handlers inside the test process
def no_signal_handlers(monkeypatch):
    monkeypatch.setattr(monitor.signal, "signal", lambda sig, handler: None)
    yield
