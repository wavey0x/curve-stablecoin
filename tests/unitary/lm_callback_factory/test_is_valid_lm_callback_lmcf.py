import boa

from tests.utils.constants import ZERO_ADDRESS


def test_valid_for_deployed_callback(factory, dummy_amm):
    lm_callback = factory.deploy_lm_callback(dummy_amm)

    assert factory.is_valid_lm_callback(lm_callback)
    assert factory.is_valid_gauge(lm_callback)
    assert factory.amm_for_callback(lm_callback) == dummy_amm.address


def test_invalid_for_unknown_addresses(factory):
    assert not factory.is_valid_lm_callback(ZERO_ADDRESS)
    assert not factory.is_valid_lm_callback(boa.env.generate_address("stranger"))
    assert not factory.is_valid_lm_callback(factory.address)


def test_invalid_for_directly_deployed_callback(
    factory, dummy_amm, lm_callback_deployer
):
    """A callback commits to its deployer, but only the registry confers trust."""
    deployer = boa.env.generate_address("direct_deployer")
    callback = lm_callback_deployer.deploy(dummy_amm, sender=deployer)

    assert callback.factory() == deployer
    assert not factory.is_valid_lm_callback(callback.address)
    assert not factory.is_valid_gauge(callback.address)


def test_invalid_across_factories(
    deploy_factory, owner, lm_callback_blueprint, dummy_amm
):
    """Each factory vouches only for its own deployments."""
    factory = deploy_factory(owner, lm_callback_blueprint)
    other_factory = deploy_factory(owner, lm_callback_blueprint)

    lm_callback = factory.deploy_lm_callback(dummy_amm)

    assert factory.is_valid_lm_callback(lm_callback)
    assert not other_factory.is_valid_lm_callback(lm_callback)
    assert not other_factory.is_valid_gauge(lm_callback)


def test_stays_valid_after_blueprint_change(factory, dummy_amm, owner, other_blueprint):
    """
    Validity is never revoked: a callback from a superseded blueprint keeps
    vouching for itself after the owner has moved on to a new one.
    """
    lm_callback = factory.deploy_lm_callback(dummy_amm)

    factory.set_blueprint(other_blueprint, sender=owner)

    assert factory.is_valid_lm_callback(lm_callback)
