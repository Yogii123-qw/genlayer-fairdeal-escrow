"""Local Direct Mode tests for FairDealEscrow.

NOTE ON THE SDK PIN: the shipped contract (contracts/fairdeal.py) targets
Studio-next (v0.4.0 header, py-genlayer pin kzybg95x1gn21dw72m7hyg0maaap04n4nx55j9yt6fkdqxtz6bz0).
That pin is not inside any public GenVM release bundle, so local tests run a
copy with ONLY the header swapped to the locally available pin
(1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6), plus the era
replacements below for names that moved between SDK versions. The Studio
deploy remains the authoritative check for the shipped pin.
"""

import re
from pathlib import Path

V030_PIN = "1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6"

SELLER_WIN = '{"winner": "seller", "reasoning": "Seller delivered the agreed work."}'
BUYER_WIN = '{"winner": "buyer", "reasoning": "Buyer paid but received nothing."}'
SPLIT = '{"winner": "split", "reasoning": "Both sides share fault."}'


def _local_copy(tmp_path):
    src = Path("contracts/fairdeal.py").read_text()
    src = re.sub(r"# v[0-9.]+", "# v0.1.0", src, count=1)
    src = re.sub(
        r'"Depends": "py-genlayer:[^"]+"',
        '"Depends": "py-genlayer:%s"' % V030_PIN,
        src,
        count=1,
    )
    # The 1jb45-era SDK has no genlayer.types module and no gl.contract
    # submodule. Names live at top scope of genlayer itself, and the base
    # class is gl.Contract. Swap both for local testing only.
    src = src.replace("from genlayer.types import *", "from genlayer import *", 1)
    src = src.replace("gl.contract.Contract", "gl.Contract", 1)
    # The 1jb45-era SDK exports TreeMap at top scope, while the shipped pin
    # only provides it as gl.storage.TreeMap (verified in Studio: bare
    # TreeMap raises NameError at schema load). Map it back for local runs.
    src = src.replace("gl.storage.TreeMap", "TreeMap")
    target = tmp_path / "fairdeal_local.py"
    target.write_text(src)
    return str(target)


def _hex(addr):
    return "0x" + bytes(addr).hex()


def _deploy(direct_vm, direct_deploy, tmp_path):
    return direct_deploy(_local_copy(tmp_path))


def _funded_deal(direct_vm, contract, buyer, seller, amount=100):
    direct_vm.sender = buyer
    direct_vm.value = amount
    deal_id = contract.create_deal(_hex(seller), "Build a landing page")
    direct_vm.value = 0
    direct_vm.sender = seller
    direct_vm.value = amount
    contract.fund_deal(deal_id)
    direct_vm.value = 0
    return deal_id


def _both_claims(direct_vm, contract, buyer, seller, deal_id):
    direct_vm.sender = buyer
    contract.submit_claim(deal_id, "I paid and got nothing.")
    direct_vm.sender = seller
    contract.submit_claim(deal_id, "I delivered the page on time.")


def test_create_deal_stores_fields(direct_vm, direct_deploy, direct_alice, direct_bob, tmp_path):
    contract = _deploy(direct_vm, direct_deploy, tmp_path)
    direct_vm.sender = direct_alice
    direct_vm.value = 100
    deal_id = contract.create_deal(_hex(direct_bob), "Build a landing page")
    direct_vm.value = 0
    assert int(deal_id) == 0
    assert int(contract.get_deal_count()) == 1
    deal = contract.get_deal(0)
    assert deal["buyer"].lower() == _hex(direct_alice).lower()
    assert deal["seller"].lower() == _hex(direct_bob).lower()
    assert int(deal["amount"]) == 100
    assert deal["status"] == "AWAITING_SELLER"
    assert deal["description"] == "Build a landing page"


def test_create_zero_value_reverts(direct_vm, direct_deploy, direct_alice, direct_bob, tmp_path):
    contract = _deploy(direct_vm, direct_deploy, tmp_path)
    direct_vm.sender = direct_alice
    direct_vm.value = 0
    with direct_vm.expect_revert("greater than zero"):
        contract.create_deal(_hex(direct_bob), "Build a landing page")


def test_create_same_buyer_seller_reverts(direct_vm, direct_deploy, direct_alice, tmp_path):
    contract = _deploy(direct_vm, direct_deploy, tmp_path)
    direct_vm.sender = direct_alice
    direct_vm.value = 100
    with direct_vm.expect_revert("different from buyer"):
        contract.create_deal(_hex(direct_alice), "Build a landing page")


def test_fund_wrong_amount_reverts(direct_vm, direct_deploy, direct_alice, direct_bob, tmp_path):
    contract = _deploy(direct_vm, direct_deploy, tmp_path)
    direct_vm.sender = direct_alice
    direct_vm.value = 100
    deal_id = contract.create_deal(_hex(direct_bob), "Build a landing page")
    direct_vm.sender = direct_bob
    direct_vm.value = 99
    with direct_vm.expect_revert("must equal the buyer stake"):
        contract.fund_deal(deal_id)


def test_fund_by_non_seller_reverts(direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie, tmp_path):
    contract = _deploy(direct_vm, direct_deploy, tmp_path)
    direct_vm.sender = direct_alice
    direct_vm.value = 100
    deal_id = contract.create_deal(_hex(direct_bob), "Build a landing page")
    direct_vm.sender = direct_charlie
    direct_vm.value = 100
    with direct_vm.expect_revert("Only the seller can fund"):
        contract.fund_deal(deal_id)


def test_cancel_before_fund(direct_vm, direct_deploy, direct_alice, direct_bob, tmp_path):
    contract = _deploy(direct_vm, direct_deploy, tmp_path)
    direct_vm.sender = direct_alice
    direct_vm.value = 100
    deal_id = contract.create_deal(_hex(direct_bob), "Build a landing page")
    direct_vm.value = 0
    contract.cancel_deal(deal_id)
    assert contract.get_deal(deal_id)["status"] == "CANCELLED"
    direct_vm.sender = direct_bob
    direct_vm.value = 100
    with direct_vm.expect_revert("not waiting for the seller stake"):
        contract.fund_deal(deal_id)


def test_claims_flow_and_double_claim_reverts(direct_vm, direct_deploy, direct_alice, direct_bob, tmp_path):
    contract = _deploy(direct_vm, direct_deploy, tmp_path)
    deal_id = _funded_deal(direct_vm, contract, direct_alice, direct_bob)
    assert contract.get_deal(deal_id)["status"] == "FUNDED"
    direct_vm.sender = direct_alice
    contract.submit_claim(deal_id, "I paid and got nothing.")
    assert contract.get_deal(deal_id)["status"] == "FUNDED"
    with direct_vm.expect_revert("already submitted a claim"):
        contract.submit_claim(deal_id, "Second claim.")
    direct_vm.sender = direct_bob
    contract.submit_claim(deal_id, "I delivered the page on time.")
    assert contract.get_deal(deal_id)["status"] == "CLAIMS_READY"


def test_non_party_claim_reverts(direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie, tmp_path):
    contract = _deploy(direct_vm, direct_deploy, tmp_path)
    deal_id = _funded_deal(direct_vm, contract, direct_alice, direct_bob)
    direct_vm.sender = direct_charlie
    with direct_vm.expect_revert("not a party"):
        contract.submit_claim(deal_id, "I am not involved.")


def test_judge_then_finalize_blocked_until_waive(direct_vm, direct_deploy, direct_alice, direct_bob, tmp_path):
    contract = _deploy(direct_vm, direct_deploy, tmp_path)
    deal_id = _funded_deal(direct_vm, contract, direct_alice, direct_bob)
    _both_claims(direct_vm, contract, direct_alice, direct_bob, deal_id)
    direct_vm.mock_llm(r"neutral arbitrator", SELLER_WIN)
    contract.judge(deal_id)
    deal = contract.get_deal(deal_id)
    assert deal["status"] == "JUDGED"
    assert '"seller"' in deal["verdict"]
    with direct_vm.expect_revert("Finalize needs"):
        contract.finalize(deal_id)
    direct_vm.sender = direct_alice
    contract.waive_appeal(deal_id)
    direct_vm.sender = direct_bob
    contract.waive_appeal(deal_id)
    contract.finalize(deal_id)
    assert contract.get_deal(deal_id)["status"] == "PAID"


def test_appeal_overturns_verdict(direct_vm, direct_deploy, direct_alice, direct_bob, tmp_path):
    contract = _deploy(direct_vm, direct_deploy, tmp_path)
    deal_id = _funded_deal(direct_vm, contract, direct_alice, direct_bob)
    _both_claims(direct_vm, contract, direct_alice, direct_bob, deal_id)
    direct_vm.mock_llm(r"neutral arbitrator", SELLER_WIN)
    contract.judge(deal_id)
    assert '"seller"' in contract.get_deal(deal_id)["verdict"]
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"neutral arbitrator", BUYER_WIN)
    direct_vm.sender = direct_alice
    contract.appeal(deal_id, "The seller page never loaded, here is the error log.")
    deal = contract.get_deal(deal_id)
    assert '"buyer"' in deal["verdict"]
    assert int(deal["appeal_count"]) == 1
    with direct_vm.expect_revert("Appeal already used"):
        contract.appeal(deal_id, "Second appeal.")


def test_finalize_split_after_appeal(direct_vm, direct_deploy, direct_alice, direct_bob, tmp_path):
    contract = _deploy(direct_vm, direct_deploy, tmp_path)
    deal_id = _funded_deal(direct_vm, contract, direct_alice, direct_bob)
    _both_claims(direct_vm, contract, direct_alice, direct_bob, deal_id)
    direct_vm.mock_llm(r"neutral arbitrator", SELLER_WIN)
    contract.judge(deal_id)
    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"neutral arbitrator", SPLIT)
    direct_vm.sender = direct_bob
    contract.appeal(deal_id, "Work was half done.")
    contract.finalize(deal_id)
    assert contract.get_deal(deal_id)["status"] == "PAID"


def test_finalize_twice_reverts(direct_vm, direct_deploy, direct_alice, direct_bob, tmp_path):
    contract = _deploy(direct_vm, direct_deploy, tmp_path)
    deal_id = _funded_deal(direct_vm, contract, direct_alice, direct_bob)
    _both_claims(direct_vm, contract, direct_alice, direct_bob, deal_id)
    direct_vm.mock_llm(r"neutral arbitrator", SELLER_WIN)
    contract.judge(deal_id)
    direct_vm.sender = direct_alice
    contract.waive_appeal(deal_id)
    direct_vm.sender = direct_bob
    contract.waive_appeal(deal_id)
    contract.finalize(deal_id)
    with direct_vm.expect_revert("no verdict to finalize"):
        contract.finalize(deal_id)


def test_judge_before_claims_ready_reverts(direct_vm, direct_deploy, direct_alice, direct_bob, tmp_path):
    contract = _deploy(direct_vm, direct_deploy, tmp_path)
    deal_id = _funded_deal(direct_vm, contract, direct_alice, direct_bob)
    direct_vm.mock_llm(r"neutral arbitrator", SELLER_WIN)
    with direct_vm.expect_revert("not ready for judgement"):
        contract.judge(deal_id)


def test_create_huge_stake_reverts(direct_vm, direct_deploy, direct_alice, direct_bob, tmp_path):
    contract = _deploy(direct_vm, direct_deploy, tmp_path)
    direct_vm.sender = direct_alice
    direct_vm.value = 2**129
    with direct_vm.expect_revert("too large"):
        contract.create_deal(_hex(direct_bob), "Build a landing page")


def test_claim_too_long_reverts(direct_vm, direct_deploy, direct_alice, direct_bob, tmp_path):
    contract = _deploy(direct_vm, direct_deploy, tmp_path)
    deal_id = _funded_deal(direct_vm, contract, direct_alice, direct_bob)
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("1 to 2000 characters"):
        contract.submit_claim(deal_id, "x" * 2001)
