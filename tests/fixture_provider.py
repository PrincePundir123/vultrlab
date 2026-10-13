"""TEST ONLY: deterministic action proposals against actual browser observations."""
from guard.contracts import Proposal, Step, Workflow


class FixtureProvider:
    provider_name = "TEST_FIXTURE_NOT_AI"

    async def propose(self, observation, steps, repair=None, goal="Read supplier order status"):
        targets = {x["target"] for x in observation["targets"]}
        if observation.get("fields", {}).get("order_id") == "ORD-102":
            return Proposal(explanation="Test fixture saw captured order", done=True)
        if "order_details" in targets or "shipment_details" in targets:
            step = Step(action="read", target="shipment_details" if "shipment_details" in targets else "order_details")
        elif steps[-1]["action"] == "fill":
            step = Step(action="click", target="lookup_button" if "lookup_button" in targets else "search_button")
        else:
            step = Step(action="fill", target="order_lookup" if "order_lookup" in targets else "order_search", value_from="order_id")
        return Proposal(explanation="Deterministic TEST proposal; not an AI decision", done=False, step=step)

    async def compile(self, steps):
        return Workflow.model_validate({"steps": steps})
