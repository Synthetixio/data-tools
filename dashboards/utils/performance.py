import streamlit as st
import time
import logging
from typing import Dict, List, Tuple, TypedDict
from datetime import datetime, timedelta
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class BenchmarkData(TypedDict):
    query_name: str
    params: dict
    execution_times: List[float]
    errors: List[str]


def create_benchmark_data(query_name: str, params: dict) -> BenchmarkData:
    """Create a new benchmark data dictionary."""
    return {
        "query_name": query_name,
        "params": params,
        "execution_times": [],
        "errors": [],
    }


def calculate_stats(benchmark_data: BenchmarkData) -> Dict[str, float]:
    """Calculate statistics for a benchmark result."""
    times = benchmark_data["execution_times"]
    if not times:
        return {"avg_time": 0, "min_time": 0, "max_time": 0, "success_rate": 0}

    total_attempts = len(times) + len(benchmark_data["errors"])
    return {
        "avg_time": sum(times) / len(times),
        "min_time": min(times),
        "max_time": max(times),
        "success_rate": len(times) / total_attempts if total_attempts > 0 else 0,
    }


def time_query(api, query_name: str, *args, **kwargs) -> float:
    """Execute a query and measure its execution time."""
    start_time = time.time()
    getattr(api, query_name)(*args, **kwargs)
    end_time = time.time()
    return end_time - start_time


def generate_scenarios(api) -> List[Tuple[str, dict]]:
    """Generate test scenarios for benchmarking."""
    end_date = datetime.now()
    date_ranges = {
        "1d": end_date - timedelta(days=1),
        "7d": end_date - timedelta(days=7),
        "30d": end_date - timedelta(days=30),
    }

    queries = [
        method
        for method in dir(api)
        if method.startswith("get_") and callable(getattr(api, method))
    ]
    v3_queries = [query for query in queries if "v2" not in query]

    scenarios = [
        (
            query_name,
            {
                "start_date": start_date,
                "end_date": end_date,
                "chain": chain,
            },
        )
        for query_name in v3_queries
        for start_date_label, start_date in date_ranges.items()
        for chain in ["arbitrum_mainnet", "base_mainnet"]
    ]

    return scenarios


def run_benchmarks(api, num_runs: int = 3) -> Dict[str, BenchmarkData]:
    """Run benchmarks for all scenarios."""
    logger.info("Starting benchmark run")
    scenarios = generate_scenarios(api)
    results: Dict[str, BenchmarkData] = {}

    total_scenarios = len(scenarios)
    for idx, (query_name, params) in enumerate(scenarios, 1):
        scenario_key = f"{query_name} - {params}"
        logger.info(f"Running scenario {idx}/{total_scenarios}: {scenario_key}")

        benchmark_data = create_benchmark_data(query_name, params)
        results[scenario_key] = benchmark_data

        for run in range(num_runs):
            try:
                logger.debug(f"  Run {run + 1}/{num_runs}")
                execution_time = time_query(api, query_name, **params)
                benchmark_data["execution_times"].append(execution_time)
                logger.debug(f"  Completed in {execution_time:.4f} seconds")
            except Exception as e:
                error_msg = f"Error in run {run + 1}: {str(e)}"
                benchmark_data["errors"].append(error_msg)
                logger.error(error_msg)

    logger.info("Benchmark run completed")
    return results


def create_benchmark_dataframe(results: Dict[str, BenchmarkData]) -> pd.DataFrame:
    """Convert benchmark results to a pandas DataFrame."""
    data = []
    for scenario_key, benchmark_data in results.items():
        stats = calculate_stats(benchmark_data)
        params = benchmark_data["params"]

        row = {
            "query_name": benchmark_data["query_name"],
            "avg_time": stats["avg_time"],
            "min_time": stats["min_time"],
            "max_time": stats["max_time"],
            "success_rate": stats["success_rate"],
            "error_count": len(benchmark_data["errors"]),
        }
        row.update(params)
        data.append(row)

    return pd.DataFrame(data)


def print_report(results: Dict[str, BenchmarkData]):
    """Print a formatted report of benchmark results."""
    print("\nSynthetixAPI Benchmark Report")
    print("=============================")

    # Calculate overall statistics
    total_queries = len(results)
    total_successful = sum(1 for r in results.values() if r["execution_times"])
    total_errors = sum(len(r["errors"]) for r in results.values())

    print(f"\nSummary:")
    print(f"Total scenarios: {total_queries}")
    print(f"Successful scenarios: {total_successful}")
    print(f"Total errors: {total_errors}")
    print("\nDetailed Results:")
    print("----------------")

    for scenario_key, benchmark_data in results.items():
        print(f"\n{scenario_key}")
        if not benchmark_data["execution_times"]:
            print("  No successful executions")
            if benchmark_data["errors"]:
                print("  Errors encountered:")
                for error in benchmark_data["errors"]:
                    print(f"    - {error}")
            continue

        stats = calculate_stats(benchmark_data)
        print(f"  Average execution time: {stats['avg_time']:.4f} seconds")
        print(f"  Min execution time: {stats['min_time']:.4f} seconds")
        print(f"  Max execution time: {stats['max_time']:.4f} seconds")
        print(f"  Success rate: {stats['success_rate'] * 100:.1f}%")

        if benchmark_data["errors"]:
            print("  Errors encountered:")
            for error in benchmark_data["errors"]:
                print(f"    - {error}")


def save_results(df: pd.DataFrame, prefix: str = "benchmark_results") -> str:
    """Save benchmark results to a CSV file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{timestamp}.csv"
    df.to_csv(filename, index=False)
    return filename


if __name__ == "__main__":
    logger.info("Initializing benchmark script")

    db_config = get_db_config(streamlit=False)
    api = SynthetixAPI(db_config, environment="prod", streamlit=False)

    # Run benchmarks
    results = run_benchmarks(api)

    # Create DataFrame
    df = create_benchmark_dataframe(results)

    # Print report
    print_report(results)

    # Save results
    csv_filename = save_results(df)
    logger.info(f"Results saved to {csv_filename}")
