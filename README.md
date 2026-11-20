# FairDeal Escrow

FairDeal Escrow is an Intelligent Contract for GenLayer. Two people lock the same amount of GEN into a deal. If they disagree about what happened, each side writes their claim in plain language. The contract asks a language model to judge the case, and the winner takes the locked funds. One appeal round is built in.

## How a deal moves

A deal starts when the buyer creates it and locks a stake. The seller then locks the same amount. Both sides submit one claim each. Once both claims are in, anyone can ask the contract to judge. The judge is a language model called through GenLayer consensus, so several validators run the same prompt and must agree on the verdict.

After the verdict, the deal can only be paid out in two ways. Either one side uses their single appeal, which asks the model to judge again with the first verdict and the appeal reason in view, or both sides waive the appeal. The payout goes to the winner in full, or split in half if the verdict is a split. The contract writes the paid status before it sends any funds.

If the seller never locks their stake, the buyer can cancel and get their stake back.

## Files

contracts/fairdeal.py holds the contract. tests/test_fairdeal.py holds the local tests, 15 cases that cover the full flow and every revert path.

## Test it locally

The tests use genlayer-test in Direct Mode with a mocked language model. Install genlayer-test, then run pytest from the repo root. The test file swaps only the contract header to a locally available SDK pin. The shipped contract itself targets Studio-next, and that header stays untouched.

## Deploy it on Studio

Open Studio, create a new Intelligent Contract, paste contracts/fairdeal.py, and deploy. Call create_deal with the seller address and a description, then fund_deal from the seller account, submit_claim from each side, judge, and finalize after the appeal is used or waived by both sides. get_deal returns the full state of any deal.

## Limits, stated plainly

The Studio deploy has not been run yet, so the payout path on live Studio still needs that check. The local tests prove the logic with a mocked model, not with a real one. Verdict quality depends on the model and on how clearly each side writes their claim. A claim can try to smuggle instructions into the prompt. The contract tells the model to ignore instructions inside claims and only accepts a verdict in a fixed shape, but no prompt wording can remove that risk entirely. There is no deadline for a seller who never funds, the buyer cancels by hand. The stake cap is 2 to the power of 128, far above any real stake, and it exists only so the winner payout can never overflow.

## License

MIT.
