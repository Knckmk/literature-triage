from __future__ import annotations

from cluster_labels import assign_cluster_labels, generate_cluster_label


def test_generate_cluster_label_uses_top_three_keywords():
    assert generate_cluster_label(
        ["rigid", "packing", "spanning", "graph"]
    ) == "Rigid / Packing / Spanning"


def test_generate_cluster_label_skips_duplicates():
    assert generate_cluster_label(["spanning", "spanning", "graph", "tree"]) == (
        "Spanning / Graph / Tree"
    )


def test_generate_cluster_label_empty_fallback():
    assert generate_cluster_label([]) == "Unlabeled Cluster"


def test_assign_cluster_labels_disambiguates_collisions():
    labels = assign_cluster_labels(
        {
            0: ["connected", "spanning", "subgraph", "approximation"],
            1: ["connected", "spanning", "subgraph", "rigid"],
        }
    )
    assert labels[0] == "Connected / Spanning / Subgraph"
    assert labels[1] != labels[0]
    assert "Rigid" in labels[1] or "(1)" in labels[1]
