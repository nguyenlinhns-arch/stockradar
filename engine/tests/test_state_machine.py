import unittest

from engine.stockradar.models import SetupState
from engine.stockradar.state_machine import SetupFacts, derive_state, validate_transition


class StateMachineTests(unittest.TestCase):
    def test_ready_to_triggered_is_valid(self) -> None:
        validate_transition(SetupState.READY, SetupState.TRIGGERED)

    def test_invalidated_cannot_return_to_ready(self) -> None:
        with self.assertRaises(ValueError):
            validate_transition(SetupState.INVALIDATED, SetupState.READY)

    def test_invalidation_has_priority(self) -> None:
        state = derive_state(SetupFacts(invalidated=True, trigger_confirmed=True))
        self.assertEqual(state, SetupState.INVALIDATED)

    def test_extension_has_priority_over_trigger(self) -> None:
        state = derive_state(SetupFacts(extension_pct=9, trigger_confirmed=True))
        self.assertEqual(state, SetupState.EXTENDED)

    def test_near_trigger(self) -> None:
        state = derive_state(SetupFacts(distance_to_trigger_pct=2.5))
        self.assertEqual(state, SetupState.NEAR_TRIGGER)


if __name__ == "__main__":
    unittest.main()

