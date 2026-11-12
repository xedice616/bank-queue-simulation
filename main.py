"""Experiment driver and reporting for the Bank Queue Simulation.

This file contains NO simulation logic -- it only calls run_simulation() from
simulation.py, collects the results, and presents them: a results table, the
minimum-counter search, and a short data-driven analysis.

Run with:  py main.py
"""

from typing import Any, Dict, List

from simulation import run_simulation

# The experiments required by the assignment.
ARRIVAL_PROBABILITIES: List[float] = [0.3, 0.6]
COUNTER_COUNTS: List[int] = [1, 2, 3]
SIMULATION_TIME: int = 480
SEED: int = 42

# Threshold and safe upper bound for the minimum-counter search.
WAIT_THRESHOLD: float = 5.0
# At most SIMULATION_TIME customers can ever arrive, so this many counters
# guarantees every customer is served instantly -- a safe search ceiling.
MAX_COUNTERS: int = SIMULATION_TIME


def run_experiments() -> List[Dict[str, Any]]:
    """Run the six required (p, k) configurations and return their results."""
    results: List[Dict[str, Any]] = []
    for p in ARRIVAL_PROBABILITIES:
        for k in COUNTER_COUNTS:
            results.append(
                run_simulation(k=k, p=p, simulation_time=SIMULATION_TIME, seed=SEED)
            )
    return results


def print_results_table(results: List[Dict[str, Any]]) -> None:
    """Print a readable, aligned results table using only str formatting."""
    header = (
        f"{'p':>5} | {'k':>3} | {'Arrived':>8} | {'Served':>7} | "
        f"{'Avg Wait':>9} | {'Max Queue':>9} | {'Remaining':>9}"
    )
    separator = "-" * len(header)

    print("RESULTS TABLE")
    print(separator)
    print(header)
    print(separator)
    for r in results:
        params = r["simulation_parameters"]
        print(
            f"{params['p']:>5.1f} | "
            f"{params['k']:>3} | "
            f"{r['total_arrived']:>8} | "
            f"{r['total_served']:>7} | "
            f"{r['average_waiting_time']:>9.2f} | "
            f"{r['maximum_queue_length']:>9} | "
            f"{r['remaining_customers']:>9}"
        )
    print(separator)


def find_minimum_counters(
    p: float,
    threshold: float = WAIT_THRESHOLD,
    max_counters: int = MAX_COUNTERS,
) -> int:
    """Return the smallest k whose average waiting time is below `threshold`.

    Searches upward from k=1, re-running the simulation (same seed) for each k,
    and stops as soon as the condition is met. Returns -1 if no k up to
    `max_counters` satisfies it (should not happen for reasonable inputs, but
    keeps the search safely bounded).
    """
    for k in range(1, max_counters + 1):
        result = run_simulation(
            k=k, p=p, simulation_time=SIMULATION_TIME, seed=SEED
        )
        if result["average_waiting_time"] < threshold:
            return k
    return -1


def print_minimum_counters() -> Dict[float, int]:
    """Print and return the minimum counters needed per arrival probability."""
    print("MINIMUM COUNTERS FOR AVERAGE WAITING TIME < 5 MINUTES")
    print("-" * 55)
    minimums: Dict[float, int] = {}
    for p in ARRIVAL_PROBABILITIES:
        k_min = find_minimum_counters(p)
        minimums[p] = k_min
        if k_min == -1:
            print(f"  p = {p:.1f}:  no solution within {MAX_COUNTERS} counters")
        else:
            print(f"  p = {p:.1f}:  minimum of {k_min} counter(s)")
    print()
    return minimums


def print_analysis(results: List[Dict[str, Any]]) -> None:
    """Print conclusions derived entirely from the actual results."""
    print("ANALYSIS")
    print("-" * 55)

    # Helper: fetch the result for a given (p, k) from the list.
    def get(p: float, k: int) -> Dict[str, Any]:
        for r in results:
            params = r["simulation_parameters"]
            if params["p"] == p and params["k"] == k:
                return r
        raise KeyError(f"no result for p={p}, k={k}")

    # 1. Effect of more counters on average waiting time (per probability).
    print("1. Effect of increasing counters on average waiting time:")
    for p in ARRIVAL_PROBABILITIES:
        waits = [get(p, k)["average_waiting_time"] for k in COUNTER_COUNTS]
        trend = ", ".join(
            f"k={k}: {w:.2f}" for k, w in zip(COUNTER_COUNTS, waits)
        )
        decreasing = all(waits[i] >= waits[i + 1] for i in range(len(waits) - 1))
        shape = "decreases" if decreasing else "does not strictly decrease"
        print(f"   p={p:.1f} -> {trend}  (waiting time {shape} as k grows)")
    print()

    # 2. Effect of higher arrival probability on queue length (per k).
    print("2. Effect of increasing arrival probability on maximum queue length:")
    for k in COUNTER_COUNTS:
        low = get(0.3, k)["maximum_queue_length"]
        high = get(0.6, k)["maximum_queue_length"]
        direction = "grows" if high > low else ("shrinks" if high < low else "is unchanged")
        print(f"   k={k} -> p=0.3: {low}, p=0.6: {high}  (max queue {direction})")
    print()

    # 3. Lowest average waiting time among the six configurations.
    best = min(results, key=lambda r: r["average_waiting_time"])
    bp = best["simulation_parameters"]
    print(
        f"3. Lowest average waiting time: p={bp['p']:.1f}, k={bp['k']} "
        f"({best['average_waiting_time']:.2f} minutes)"
    )

    # 4. Highest maximum queue length among the six configurations.
    worst = max(results, key=lambda r: r["maximum_queue_length"])
    wp = worst["simulation_parameters"]
    print(
        f"4. Highest maximum queue length: p={wp['p']:.1f}, k={wp['k']} "
        f"({worst['maximum_queue_length']} customers)"
    )

    # 5. Are there customers remaining at closing?
    leftover = [r for r in results if r["remaining_customers"] > 0]
    if leftover:
        details = ", ".join(
            f"p={r['simulation_parameters']['p']:.1f}/k={r['simulation_parameters']['k']}"
            f"={r['remaining_customers']}"
            for r in leftover
        )
        print(f"5. Customers remaining at closing in: {details}")
    else:
        print("5. No customers remained in the queue at closing in any configuration.")
    print()


def main() -> None:
    """Run all experiments and print the full report."""
    print("=" * 55)
    print("BANK QUEUE SIMULATION -- EXPERIMENT REPORT")
    print(f"(8-hour day = {SIMULATION_TIME} minutes, seed = {SEED})")
    print("=" * 55)
    print()

    results = run_experiments()
    print_results_table(results)
    print()
    print_minimum_counters()
    print_analysis(results)


if __name__ == "__main__":
    main()
