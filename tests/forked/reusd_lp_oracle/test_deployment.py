import importlib.util
import json
from pathlib import Path

import boa

from tests.forked.settings import WEB3_PROVIDER_URL


ROOT = Path(__file__).resolve().parents[3]
DEPLOY_SCRIPT = (
    ROOT / "scripts/deploy/llamalend/ethereum/markets/reUSDsfrxUSDLP-crvUSD/deploy.py"
)


def test_deployment(tmp_path):
    assert WEB3_PROVIDER_URL is not None, (
        "Provider url is not set, add WEB3_PROVIDER_URL param to env"
    )
    spec = importlib.util.spec_from_file_location("reusd_lp_deploy", DEPLOY_SCRIPT)
    deploy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(deploy)
    report_path = tmp_path / "deployment.json"

    with boa.fork(WEB3_PROVIDER_URL, allow_dirty=True):
        deploy._deploy(
            deployer=boa.env.generate_address("deployer"),
            dry_run=True,
            report_path=report_path,
            factory_deployment=ROOT / "deployments/llamalend/ethereum/factory.jsonc",
            create_vote=False,
            etherscan_api_key=None,
            pinata_token=None,
        )
        report = json.loads(report_path.read_text())
        adapter = boa.load_partial(deploy.REUSD_CRVUSD_ADAPTER).at(
            report["reusd_adapter"]
        )
        oracle = boa.load_partial(deploy.CHAIN_ORACLE).at(report["price_oracle"])
        amm = boa.load_partial(deploy.AMM_SRC).at(report["amm"])

        assert [oracle.ORACLES(i) for i in range(3)] == [
            report["lp_oracle"],
            adapter.address,
            deploy.AGG,
        ]
        assert amm.price_oracle_contract() == oracle.address
        assert report["params"]["reusd_feed"] == adapter.REUSD_FEED()
        assert report["params"]["initial_reusd_price"] == adapter.price() <= 10**18
        assert report["params"]["initial_price"] == oracle.price() == oracle.price_w()
