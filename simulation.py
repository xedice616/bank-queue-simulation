"""Bank queue simulation engine.

This module contains the simulation *logic only* -- it never prints a report.
It returns a plain dictionary of statistics so that the presentation layer
(main.py, added in a later stage) and the tests can consume the results
however they like.

The simulation models a bank that is open for `simulation_time` minutes with
`k` service counters. During each open minute a customer may arrive (with
probability `p`), waits in a FIFO Circular Queue, and is served by the first
counter that becomes free.
"""

import random
from dataclasses import dataclass
from typing import Any, Dict, List

from circular_queue import CircularQueue


# Capacity for the Circular Queue. At most `simulation_time` customers can ever
# arrive (one per minute), so 481 is large enough that a 480-minute run can
# never overflow, while is_full() still means something real.
QUEUE_CAPACITY: int = 481


@dataclass
class Customer:
    """A single bank customer.

    Lightweight on purpose: it just carries the three facts the simulation
    needs. `service_duration` is how many minutes this customer will occupy a
    counter once service begins.
    """

    customer_id: int
    arrival_time: int
    service_duration: int


def run_simulation(
    k: int,
    p: float,
    simulation_time: int = 480,
    seed: int = 42,
) -> Dict[str, Any]:
    """Run one bank simulation and return its statistics.

    Parameters
    ----------
    k:
        Number of service counters (positive integer).
    p:
        Probability that a customer arrives in any given minute (0.0 .. 1.0).
    simulation_time:
        Number of minutes the bank is open (default 480 = 8 hours). Arrivals
        happen during minutes 0 .. simulation_time - 1.
    seed:
        Seed for Python's random module. Re-seeding at the start of every call
        makes the run fully reproducible, and means two configurations that
        share the same `p` see the identical arrival/service pattern.

    Returns
    -------
    dict with keys:
        total_arrived, total_served, average_waiting_time,
        maximum_queue_length, remaining_customers,
        individual_customer_waiting_times, simulation_parameters
    """
    # --- Input validation: never silently accept bad parameters -------------
    if not isinstance(k, int) or isinstance(k, bool) or k <= 0:
        raise ValueError("k must be a positive integer")
    if not isinstance(p, (int, float)) or isinstance(p, bool) or not (0.0 <= p <= 1.0):
        raise ValueError("p must be a number between 0 and 1 inclusive")
    if not isinstance(simulation_time, int) or isinstance(simulation_time, bool) or simulation_time <= 0:
        raise ValueError("simulation_time must be a positive integer")

    # Re-seed at the beginning of every simulation for reproducibility.
    random.seed(seed)

    # --- State ---------------------------------------------------------------
    queue: CircularQueue = CircularQueue(QUEUE_CAPACITY)

    # Each counter is represented by the minute at which it next becomes free.
    # Starting everyone at 0 means "all counters are idle at minute 0".
    # A counter is available at minute t when counter_free_at[i] <= t.
    counter_free_at: List[int] = [0] * k

    waiting_times: List[int] = []  # one entry per served customer
    total_arrived: int = 0
    total_served: int = 0
    maximum_queue_length: int = 0
    next_customer_id: int = 1

    # --- Minute-by-minute loop ----------------------------------------------
    for current_minute in range(simulation_time):  # minutes 0 .. simulation_time-1

        # Step 1: a customer may arrive this minute. (No arrivals are generated
        # outside this loop, so none can occur after the final open minute.)
        if random.random() < p:
            customer = Customer(
                customer_id=next_customer_id,
                arrival_time=current_minute,
                service_duration=random.randint(2, 8),
            )
            next_customer_id += 1
            total_arrived += 1
            queue.enqueue(customer)

        # Step 2: record the peak queue length AFTER arrivals but BEFORE
        # dispatch -- this captures the true high-water mark of waiting people.
        if queue.size() > maximum_queue_length:
            maximum_queue_length = queue.size()

        # Step 3: dispatch. Give waiting customers to any free counters, in
        # FIFO order, until we run out of either free counters or customers.
        for counter_index in range(k):
            if queue.is_empty():
                break  # nobody left to serve
            if counter_free_at[counter_index] <= current_minute:
                # This counter is idle right now -> start the next customer.
                customer = queue.dequeue()
                waiting_time = current_minute - customer.arrival_time
                waiting_times.append(waiting_time)
                total_served += 1
                # The counter is busy for `service_duration` minutes; it frees
                # up that many minutes from now (may be after closing, which is
                # fine -- this customer already counts as served).
                counter_free_at[counter_index] = current_minute + customer.service_duration

    # --- Final statistics ----------------------------------------------------
    remaining_customers: int = queue.size()  # still waiting when the doors close

    # Guard against division by zero when nobody was served.
    if total_served > 0:
        average_waiting_time: float = sum(waiting_times) / total_served
    else:
        average_waiting_time = 0.0

    return {
        "total_arrived": total_arrived,
        "total_served": total_served,
        "average_waiting_time": average_waiting_time,
        "maximum_queue_length": maximum_queue_length,
        "remaining_customers": remaining_customers,
        "individual_customer_waiting_times": waiting_times,
        "simulation_parameters": {
            "k": k,
            "p": p,
            "simulation_time": simulation_time,
            "seed": seed,
        },
    }
