import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_API_KEY = "dev-secret-key"
DEFAULT_EVAL_PATH = "tests/fixtures/eval_queries.json"


@dataclass(frozen=True)
class EvalCase:
    id: str
    query: str
    expected_entities: list[str]
    expected_files: list[str]


@dataclass(frozen=True)
class EvalOutcome:
    id: str
    query: str
    hit_rank: int | None
    top_entities: list[str]
    top_files: list[str]
    latency_ms: float = 0.0

    @property
    def hit(self) -> bool:
        return self.hit_rank is not None

    @property
    def reciprocal_rank(self) -> float:
        return 0.0 if self.hit_rank is None else 1.0 / self.hit_rank


def load_cases(path: str) -> list[EvalCase]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    cases: list[EvalCase] = []
    for item in data:
        cases.append(
            EvalCase(
                id=item["id"],
                query=item["query"],
                expected_entities=item.get("expected_entities", []),
                expected_files=item.get("expected_files", []),
            )
        )
    return cases


def find_hit_rank(results: list[dict[str, Any]], expected_entities: list[str], expected_files: list[str]) -> int | None:
    expected_entity_set = set(expected_entities)
    expected_file_set = set(expected_files)
    for index, result in enumerate(results, start=1):
        metadata = result.get("metadata", {})
        entity_name = metadata.get("entity_name")
        source_file = metadata.get("source_file")
        if entity_name in expected_entity_set or source_file in expected_file_set:
            return index
    return None


def evaluate_results(
    cases: list[EvalCase],
    responses: dict[str, list[dict[str, Any]]],
    latencies: dict[str, float] | None = None,
) -> list[EvalOutcome]:
    latencies = latencies or {}
    outcomes: list[EvalOutcome] = []
    for case in cases:
        results = responses.get(case.id, [])
        hit_rank = find_hit_rank(results, case.expected_entities, case.expected_files)
        outcomes.append(
            EvalOutcome(
                id=case.id,
                query=case.query,
                hit_rank=hit_rank,
                top_entities=[result.get("metadata", {}).get("entity_name", "") for result in results],
                top_files=[result.get("metadata", {}).get("source_file", "") for result in results],
                latency_ms=latencies.get(case.id, 0.0),
            )
        )
    return outcomes


def recall_at_k(outcomes: list[EvalOutcome]) -> float:
    if not outcomes:
        return 0.0
    return sum(1 for outcome in outcomes if outcome.hit) / len(outcomes)


def mean_reciprocal_rank(outcomes: list[EvalOutcome]) -> float:
    if not outcomes:
        return 0.0
    return sum(outcome.reciprocal_rank for outcome in outcomes) / len(outcomes)


def query_api(
    api_url: str,
    api_key: str,
    query: str,
    top_k: int,
    threshold: float,
    enable_graph: bool,
) -> list[dict[str, Any]]:
    payload = {
        "query": query,
        "top_k": top_k,
        "options": {
            "enable_graph_expansion": enable_graph,
            "max_hops": 2,
            "similarity_threshold": threshold,
        },
    }
    response = httpx.post(
        f"{api_url.rstrip('/')}/query",
        headers={"X-API-Key": api_key},
        json=payload,
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json().get("results", [])


def percentile(values: list[float], percent: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * percent))))
    return ordered[index]


def run_cases(
    cases: list[EvalCase],
    api_url: str,
    api_key: str,
    top_k: int,
    threshold: float,
    enable_graph: bool,
) -> list[EvalOutcome]:
    responses: dict[str, list[dict[str, Any]]] = {}
    latencies: dict[str, float] = {}
    for case in cases:
        started = time.perf_counter()
        responses[case.id] = query_api(
            api_url=api_url,
            api_key=api_key,
            query=case.query,
            top_k=top_k,
            threshold=threshold,
            enable_graph=enable_graph,
        )
        latencies[case.id] = (time.perf_counter() - started) * 1000
    return evaluate_results(cases, responses, latencies)


def print_report(outcomes: list[EvalOutcome], top_k: int, label: str = "Graph ON") -> None:
    recall = recall_at_k(outcomes)
    mrr = mean_reciprocal_rank(outcomes)
    latencies = [outcome.latency_ms for outcome in outcomes if outcome.latency_ms > 0]
    print(f"Mode: {label}")
    print(f"Recall@{top_k}: {recall:.3f}")
    print(f"MRR: {mrr:.3f}")
    print(f"Latency P50: {percentile(latencies, 0.50):.0f} ms")
    print(f"Latency P95: {percentile(latencies, 0.95):.0f} ms")
    print()
    for outcome in outcomes:
        rank = "-" if outcome.hit_rank is None else str(outcome.hit_rank)
        first_entity = outcome.top_entities[0] if outcome.top_entities else "-"
        first_file = outcome.top_files[0] if outcome.top_files else "-"
        print(
            f"{outcome.id}: hit_rank={rank} latency_ms={outcome.latency_ms:.0f} "
            f"top_entity={first_entity} top_file={first_file}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Knowledge Hub retrieval quality.")
    parser.add_argument("--path", default=DEFAULT_EVAL_PATH, help="Path to eval query JSON.")
    parser.add_argument("--api-url", default=os.getenv("KNOWLEDGE_HUB_URL", DEFAULT_API_URL))
    parser.add_argument("--api-key", default=os.getenv("API_KEY", DEFAULT_API_KEY))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--threshold", type=float, default=0.35)
    parser.add_argument("--min-recall", type=float, default=0.8)
    parser.add_argument("--min-mrr", type=float, default=0.5)
    parser.add_argument("--no-graph", action="store_true")
    parser.add_argument("--ablation", action="store_true", help="Also run a vector-only comparison.")
    args = parser.parse_args()

    cases = load_cases(args.path)
    outcomes = run_cases(
        cases=cases,
        api_url=args.api_url,
        api_key=args.api_key,
        top_k=args.top_k,
        threshold=args.threshold,
        enable_graph=not args.no_graph,
    )
    print_report(outcomes, args.top_k, label="Graph OFF" if args.no_graph else "Graph ON")

    if args.ablation and not args.no_graph:
        print()
        print("-" * 80)
        vector_only = run_cases(
            cases=cases,
            api_url=args.api_url,
            api_key=args.api_key,
            top_k=args.top_k,
            threshold=args.threshold,
            enable_graph=False,
        )
        print_report(vector_only, args.top_k, label="Graph OFF")

    recall = recall_at_k(outcomes)
    mrr = mean_reciprocal_rank(outcomes)
    if recall < args.min_recall or mrr < args.min_mrr:
        print(
            f"Evaluation failed: recall={recall:.3f} min_recall={args.min_recall:.3f}, "
            f"mrr={mrr:.3f} min_mrr={args.min_mrr:.3f}"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
