from scripts.evaluate_retrieval import EvalCase, evaluate_results, mean_reciprocal_rank, recall_at_k


def test_evaluate_results_scores_entity_and_file_hits():
    cases = [
        EvalCase("case_a", "query a", ["Target.entity"], []),
        EvalCase("case_b", "query b", [], ["app/target.py"]),
        EvalCase("case_c", "query c", ["Missing"], ["missing.py"]),
    ]
    responses = {
        "case_a": [
            {"metadata": {"entity_name": "Other", "source_file": "app/other.py"}},
            {"metadata": {"entity_name": "Target.entity", "source_file": "app/source.py"}},
        ],
        "case_b": [
            {"metadata": {"entity_name": "Any", "source_file": "app/target.py"}},
        ],
        "case_c": [
            {"metadata": {"entity_name": "Other", "source_file": "app/other.py"}},
        ],
    }

    outcomes = evaluate_results(cases, responses)

    assert [outcome.hit_rank for outcome in outcomes] == [2, 1, None]
    assert recall_at_k(outcomes) == 2 / 3
    assert mean_reciprocal_rank(outcomes) == (0.5 + 1.0 + 0.0) / 3
