"""Unit tests for the bank simulation engine (simulation.py).

Where the outcome must be exact, we mock random.random() and random.randint()
so arrivals and service durations are fully deterministic -- that lets us assert
precise waiting times and FIFO order instead of guessing at random outcomes.

Run with:  py -m unittest test_simulation -v
"""

import unittest
from unittest.mock import patch

from simulation import run_simulation


class TestSimulationBasics(unittest.TestCase):

    def test_zero_probability_no_arrivals(self) -> None:
        """p = 0.0: nobody arrives and average waiting time is 0 (no crash)."""
        result = run_simulation(k=2, p=0.0, simulation_time=100)
        self.assertEqual(result["total_arrived"], 0)
        self.assertEqual(result["total_served"], 0)
        self.assertEqual(result["remaining_customers"], 0)
        self.assertEqual(result["average_waiting_time"], 0.0)
        self.assertEqual(result["individual_customer_waiting_times"], [])

    def test_guaranteed_arrivals(self) -> None:
        """p = 1.0: random.random() is always < 1.0, so exactly one customer
        arrives every single open minute."""
        result = run_simulation(k=1, p=1.0, simulation_time=50)
        self.assertEqual(result["total_arrived"], 50)

    def test_reproducibility(self) -> None:
        """Same parameters + same seed must give byte-for-byte identical output."""
        a = run_simulation(k=2, p=0.3, seed=42)
        b = run_simulation(k=2, p=0.3, seed=42)
        self.assertEqual(a, b)

    def test_accounting_identity(self) -> None:
        """Every arrival is either served or still waiting at closing:
        total_arrived == total_served + remaining_customers."""
        for p in (0.2, 0.5, 0.9):
            for k in (1, 2, 3):
                r = run_simulation(k=k, p=p)
                self.assertEqual(
                    r["total_arrived"],
                    r["total_served"] + r["remaining_customers"],
                    msg=f"accounting broke for k={k}, p={p}",
                )

    def test_empty_simulation_no_division_error(self) -> None:
        """A simulation with no served customers must not raise ZeroDivisionError
        and must report an average of 0.0."""
        result = run_simulation(k=1, p=0.0, simulation_time=10)
        self.assertEqual(result["average_waiting_time"], 0.0)


class TestSimulationInputValidation(unittest.TestCase):

    def test_invalid_counter_counts(self) -> None:
        for bad_k in (0, -1, 2.5, "3", True):
            with self.assertRaises(ValueError, msg=f"k={bad_k!r} should be rejected"):
                run_simulation(k=bad_k, p=0.3)

    def test_invalid_probabilities(self) -> None:
        for bad_p in (-0.1, 1.5, 2, "0.5", True):
            with self.assertRaises(ValueError, msg=f"p={bad_p!r} should be rejected"):
                run_simulation(k=1, p=bad_p)

    def test_invalid_simulation_durations(self) -> None:
        for bad_t in (0, -5, 10.0, "480"):
            with self.assertRaises(ValueError, msg=f"simulation_time={bad_t!r} should be rejected"):
                run_simulation(k=1, p=0.3, simulation_time=bad_t)

    def test_boundary_probabilities_accepted(self) -> None:
        # p exactly 0.0 and exactly 1.0 are valid and must not raise.
        self.assertEqual(run_simulation(k=1, p=0.0, simulation_time=5)["total_arrived"], 0)
        self.assertEqual(run_simulation(k=1, p=1.0, simulation_time=5)["total_arrived"], 5)


class TestSimulationDeterministic(unittest.TestCase):
    """Exact-outcome tests driven by mocked randomness.

    patch target note: simulation.py does `import random` and then calls
    `random.random()` / `random.randint()`, so we patch those two names on the
    `simulation.random` module object. random.seed() is left untouched (it is
    harmless once the two generators are mocked).
    """

    def test_zero_waiting_time_at_idle_counter(self) -> None:
        """A customer who arrives while a counter is idle waits 0 minutes."""
        # Arrive only at minute 0, then never again; service lasts 4 minutes.
        arrivals = [0.0] + [1.0] * 9          # 0.0 < p -> arrive; 1.0 -> no arrival
        with patch("simulation.random.random", side_effect=arrivals), \
             patch("simulation.random.randint", return_value=4):
            result = run_simulation(k=1, p=0.5, simulation_time=10)

        self.assertEqual(result["total_arrived"], 1)
        self.assertEqual(result["total_served"], 1)
        self.assertEqual(result["individual_customer_waiting_times"], [0])

    def test_multiple_counters_work_independently(self) -> None:
        """Two counters serve two customers independently on consecutive minutes,
        and both customers are served immediately (no waiting)."""
        # c1 arrives at minute 0, c2 at minute 1; each needs 5 minutes.
        arrivals = [0.0, 0.0] + [1.0] * 8
        with patch("simulation.random.random", side_effect=arrivals), \
             patch("simulation.random.randint", return_value=5):
            result = run_simulation(k=2, p=0.5, simulation_time=10)

        # c1 -> counter 0 at minute 0; c2 -> counter 1 at minute 1.
        # Counter 0 is still busy at minute 1 (free at minute 5), so c2 can only
        # have been served by the *second*, independent counter.
        self.assertEqual(result["total_served"], 2)
        self.assertEqual(result["maximum_queue_length"], 1)
        self.assertEqual(result["individual_customer_waiting_times"], [0, 0])

    def test_exact_waiting_times_single_counter(self) -> None:
        """One counter, three customers arriving at minutes 0,1,2, each needing
        3 minutes. We assert the exact waiting times.

        Timeline (counter frees at start+duration):
          min0: c1 arrives, served now      -> wait 0, counter busy until 3
          min1: c2 arrives, counter busy    -> waits
          min2: c3 arrives, counter busy    -> waits   (queue: c2, c3)
          min3: counter free, serve c2      -> wait 3-1 = 2, busy until 6
          min6: counter free, serve c3      -> wait 6-2 = 4
        Expected waiting times: [0, 2, 4]
        """
        arrivals = [0.0, 0.0, 0.0] + [1.0] * 7   # arrivals at minutes 0,1,2 only
        with patch("simulation.random.random", side_effect=arrivals), \
             patch("simulation.random.randint", return_value=3):
            result = run_simulation(k=1, p=0.5, simulation_time=10)

        self.assertEqual(result["individual_customer_waiting_times"], [0, 2, 4])
        self.assertEqual(result["average_waiting_time"], (0 + 2 + 4) / 3)
        self.assertEqual(result["total_served"], 3)
        self.assertEqual(result["remaining_customers"], 0)

    def test_fifo_order_is_preserved(self) -> None:
        """Customers are served in arrival order, not reverse order.

        Same scenario as above. Under FIFO the waiting times are [0, 2, 4]
        (c2 before c3). Under LIFO they would be [0, 1, 5] (c3 served first).
        Asserting the exact [0, 2, 4] therefore proves FIFO ordering, since the
        two policies produce distinguishable results.
        """
        arrivals = [0.0, 0.0, 0.0] + [1.0] * 7
        with patch("simulation.random.random", side_effect=arrivals), \
             patch("simulation.random.randint", return_value=3):
            result = run_simulation(k=1, p=0.5, simulation_time=10)

        fifo_expected = [0, 2, 4]
        lifo_would_be = [0, 1, 5]
        self.assertEqual(result["individual_customer_waiting_times"], fifo_expected)
        self.assertNotEqual(result["individual_customer_waiting_times"], lifo_would_be)

    def test_closing_behavior_and_remaining_count(self) -> None:
        """No arrivals after the last open minute, and customers still waiting at
        closing are counted as remaining.

        k=1, arrive every minute (10 minutes), each service lasts 8 minutes.
          min0: c1 arrives, served           -> busy until 8
          min1..7: c2..c8 arrive and wait
          min8: c9 arrives; counter free     -> serve c2, busy until 16
          min9: c10 arrives; counter busy    -> waits
        Served = c1, c2 = 2. Arrived = 10. Remaining = 8.
        """
        with patch("simulation.random.random", return_value=0.0), \
             patch("simulation.random.randint", return_value=8):
            result = run_simulation(k=1, p=0.5, simulation_time=10)

        # Exactly one arrival per open minute, and none afterwards.
        self.assertEqual(result["total_arrived"], 10)
        self.assertEqual(result["total_served"], 2)
        self.assertEqual(result["remaining_customers"], 8)
        # Accounting identity still holds at closing.
        self.assertEqual(
            result["total_arrived"],
            result["total_served"] + result["remaining_customers"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
