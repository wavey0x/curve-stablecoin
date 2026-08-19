"""Standalone unit fixtures for `LMCallbackFactory`."""

import boa
import pytest

from tests.utils import filter_logs
from tests.utils.deployers import (
    LM_CALLBACK_FACTORY_DEPLOYER,
    compiler_args_default,
)

MOCK_LEND_FACTORY = """
# pragma version 0.4.3

flag ContractType:
    VAULT
    CONTROLLER
    AMM

struct ContractInfo:
    market_index: uint256
    contract_type: ContractType

check_contract: public(HashMap[address, ContractInfo])

@external
def register_amm(_amm: address):
    self.check_contract[_amm] = ContractInfo(
        market_index=1,
        contract_type=ContractType.AMM,
    )
"""

DUMMY_AMM = """
# pragma version 0.4.3

COLLATERAL_TOKEN: immutable(address)

@deploy
def __init__(_collateral_token: address):
    COLLATERAL_TOKEN = _collateral_token

@external
@view
def coins(_i: uint256) -> address:
    assert _i < 2
    if _i == 1:
        return COLLATERAL_TOKEN
    return empty(address)
"""

DUMMY_CALLBACK = """
# pragma version 0.4.3

interface IAMM:
    def coins(_i: uint256) -> address: view

FACTORY: immutable(address)
AMM: public(immutable(address))
COLLATERAL_TOKEN: public(immutable(address))

@deploy
def __init__(_amm: address):
    FACTORY = msg.sender
    AMM = _amm
    COLLATERAL_TOKEN = staticcall IAMM(_amm).coins(1)

@external
@view
def factory() -> address:
    return FACTORY
"""

# A second valid callback shape, distinguishable by its runtime code.
OTHER_CALLBACK = DUMMY_CALLBACK + """
MARKER: public(constant(uint256)) = 42
"""


@pytest.fixture
def owner():
    return boa.env.generate_address("owner")


@pytest.fixture
def non_owner():
    return boa.env.generate_address("non_owner")


@pytest.fixture
def market_factory():
    return boa.loads_partial(
        MOCK_LEND_FACTORY, compiler_args=compiler_args_default
    ).deploy()


@pytest.fixture
def make_amm(market_factory):
    amm_deployer = boa.loads_partial(DUMMY_AMM, compiler_args=compiler_args_default)

    def _make_amm():
        collateral_token = boa.env.generate_address("collateral_token")
        amm = amm_deployer.deploy(collateral_token)
        market_factory.register_amm(amm)
        return amm

    return _make_amm


@pytest.fixture
def dummy_amm(make_amm):
    return make_amm()


@pytest.fixture
def lm_callback_deployer():
    return boa.loads_partial(DUMMY_CALLBACK, compiler_args=compiler_args_default)


@pytest.fixture
def lm_callback_blueprint(lm_callback_deployer):
    return lm_callback_deployer.deploy_as_blueprint()


@pytest.fixture
def other_blueprint():
    """A valid but different blueprint, for testing blueprint rotation."""
    return boa.loads_partial(
        OTHER_CALLBACK, compiler_args=compiler_args_default
    ).deploy_as_blueprint()


@pytest.fixture
def deploy_factory(market_factory):
    """Deploy a factory with explicit arguments, for tests that vary them."""

    def _deploy_factory(owner, blueprint, lend_factory=market_factory):
        return LM_CALLBACK_FACTORY_DEPLOYER.deploy(owner, blueprint, lend_factory)

    return _deploy_factory


@pytest.fixture
def factory(deploy_factory, owner, lm_callback_blueprint):
    return deploy_factory(owner, lm_callback_blueprint)


@pytest.fixture
def paused_factory(factory, owner):
    factory.pause(sender=owner)
    assert factory.paused()
    return factory


@pytest.fixture
def single_factory_event():
    def _single_factory_event(factory, event_name):
        logs = filter_logs(factory, event_name)
        assert len(logs) == 1
        return logs[0]

    return _single_factory_event
