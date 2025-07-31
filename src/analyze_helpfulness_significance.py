#!/usr/bin/env python
# Copyright (c) Meta Platforms, Inc. and affiliates
"""
Script to analyze statistical significance between docstring helpfulness scores
of different systems.

Usage:
    conda activate docstringgen
    python src/analyze_significance.py
"""

import json
import os
import argparse
import numpy as np
from scipy import stats
import pandas as pd
from typing import Dict, List, Tuple, Any


def load_results(filepath: str) -> Dict[str, Any]:
    """Load the helpfulness evaluation results from JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def get_system_scores(results: Dict[str, Any], system: str) -> Dict[str, List[int]]:
    """
    Extract scores for a specific system, organized by aspect.
    
    Returns:
        Dictionary mapping aspect to list of scores
    """
    system_results = [r for r in results["results"] if r["system"] == system]
    scores_by_aspect = {}
    
    for result in system_results:
        aspect = result["aspect"]
        score = result["score"]
        
        if aspect not in scores_by_aspect:
            scores_by_aspect[aspect] = []
        
        scores_by_aspect[aspect].append(score)
    
    return scores_by_aspect


def get_paired_scores(results: Dict[str, Any], system1: str, system2: str) -> Dict[str, Tuple[List[int], List[int]]]:
    """
    Extract paired scores for two systems, organized by aspect.
    Only includes components that have scores for both systems.
    
    Returns:
        Dictionary mapping aspect to tuple of (system1_scores, system2_scores)
    """
    # Get all component IDs evaluated by both systems
    system1_results = [r for r in results["results"] if r["system"] == system1]
    system2_results = [r for r in results["results"] if r["system"] == system2]
    
    system1_components = {(r["component_id"], r["aspect"]): r for r in system1_results}
    system2_components = {(r["component_id"], r["aspect"]): r for r in system2_results}
    
    # Find common component-aspect pairs
    common_pairs = set(system1_components.keys()).intersection(system2_components.keys())
    
    # Organize paired scores by aspect
    paired_scores = {}
    for component_id, aspect in common_pairs:
        if aspect not in paired_scores:
            paired_scores[aspect] = ([], [])
        
        paired_scores[aspect][0].append(system1_components[(component_id, aspect)]["score"])
        paired_scores[aspect][1].append(system2_components[(component_id, aspect)]["score"])
    
    return paired_scores


def run_significance_tests(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run statistical significance tests between specified system pairs.
    
    Returns:
        Dictionary with test results
    """
    system_pairs = [
        ("copy_paste_codellama34b", "docassist-codellama34b"),
        ("copy_paste_gpt4o_mini", "docassist-gpt4o_mini"),
        ("fim-codellama13b", "docassist-codellama34b")
    ]
    
    significance_results = {}
    
    for system1, system2 in system_pairs:
        pair_key = f"{system1} vs {system2}"
        significance_results[pair_key] = {}
        
        # Get paired scores for the two systems
        paired_scores = get_paired_scores(results, system1, system2)
        
        # Calculate overall paired scores across all aspects
        all_scores_sys1 = []
        all_scores_sys2 = []
        
        for aspect, (scores1, scores2) in paired_scores.items():
            all_scores_sys1.extend(scores1)
            all_scores_sys2.extend(scores2)
            
            # Run tests for each aspect
            if len(scores1) >= 5:  # Only run tests if we have enough samples
                # Perform Wilcoxon signed-rank test (non-parametric paired test)
                try:
                    w_stat, p_value = stats.wilcoxon(scores1, scores2)
                    is_significant = p_value < 0.05
                    better_system = system2 if np.mean(scores2) > np.mean(scores1) else system1
                    
                    significance_results[pair_key][aspect] = {
                        "mean_1": np.mean(scores1),
                        "mean_2": np.mean(scores2),
                        "p_value": p_value,
                        "is_significant": is_significant,
                        "better_system": better_system if is_significant else "No significant difference",
                        "n_samples": len(scores1)
                    }
                except ValueError as e:
                    # This can happen if the differences are all zero
                    significance_results[pair_key][aspect] = {
                        "mean_1": np.mean(scores1),
                        "mean_2": np.mean(scores2),
                        "p_value": 1.0,
                        "is_significant": False,
                        "better_system": "No significant difference",
                        "n_samples": len(scores1),
                        "note": "Test could not be performed: " + str(e)
                    }
        
        # Run test for overall scores
        if len(all_scores_sys1) >= 5:
            try:
                w_stat, p_value = stats.wilcoxon(all_scores_sys1, all_scores_sys2)
                is_significant = p_value < 0.05
                better_system = system2 if np.mean(all_scores_sys2) > np.mean(all_scores_sys1) else system1
                
                significance_results[pair_key]["overall"] = {
                    "mean_1": np.mean(all_scores_sys1),
                    "mean_2": np.mean(all_scores_sys2),
                    "p_value": p_value,
                    "is_significant": is_significant,
                    "better_system": better_system if is_significant else "No significant difference",
                    "n_samples": len(all_scores_sys1)
                }
            except ValueError as e:
                significance_results[pair_key]["overall"] = {
                    "mean_1": np.mean(all_scores_sys1),
                    "mean_2": np.mean(all_scores_sys2),
                    "p_value": 1.0,
                    "is_significant": False,
                    "better_system": "No significant difference",
                    "n_samples": len(all_scores_sys1),
                    "note": "Test could not be performed: " + str(e)
                }
    
    return significance_results


def format_significance_markdown(significance_results: Dict[str, Any]) -> str:
    """Format significance test results as markdown."""
    md = "## Statistical Significance Tests\n\n"
    md += "Statistical significance was assessed using the Wilcoxon signed-rank test with a significance level of p < 0.05.\n\n"
    
    for pair_key, pair_results in significance_results.items():
        md += f"### {pair_key}\n\n"
        
        # Create a table for this pair
        md += "| Aspect | System 1 Mean | System 2 Mean | p-value | Significant? | Better System | n |\n"
        md += "| ------ | ------------ | ------------ | ------- | ------------ | ------------- | --- |\n"
        
        # Add overall results first
        if "overall" in pair_results:
            overall = pair_results["overall"]
            md += f"| Overall | {overall['mean_1']:.2f} | {overall['mean_2']:.2f} | {overall['p_value']:.4f} | {overall['is_significant']} | {overall['better_system']} | {overall['n_samples']} |\n"
        
        # Add results for each aspect
        for aspect, results in pair_results.items():
            if aspect != "overall":
                md += f"| {aspect.capitalize()} | {results['mean_1']:.2f} | {results['mean_2']:.2f} | {results['p_value']:.4f} | {results['is_significant']} | {results['better_system']} | {results['n_samples']} |\n"
        
        md += "\n"
    
    return md


def update_markdown_report(stats_path: str, significance_md: str):
    """Update the markdown report to include significance test results."""
    with open(stats_path, 'r') as f:
        content = f.read()
    
    # Append significance test results
    updated_content = content + "\n" + significance_md
    
    with open(stats_path, 'w') as f:
        f.write(updated_content)


def main():
    parser = argparse.ArgumentParser(description="Analyze statistical significance of docstring helpfulness")
    parser.add_argument("--results-path", type=str, 
                        default="experiments/eval/results/helpfulness/helpfulness_evaluation_results.json",
                        help="Path to the helpfulness evaluation results JSON")
    parser.add_argument("--stats-path", type=str, 
                        default="experiments/eval/results/helpfulness/helpfulness_evaluation_stats.md",
                        help="Path to the helpfulness evaluation stats markdown file")
    parser.add_argument("--output-dir", type=str, 
                        default="experiments/eval/results/helpfulness",
                        help="Directory to store significance test results")
    args = parser.parse_args()
    
    # Check if result file exists
    if not os.path.exists(args.results_path):
        print(f"Error: Results file not found at {args.results_path}")
        return
    
    # Load results
    results = load_results(args.results_path)
    
    # Run significance tests
    significance_results = run_significance_tests(results)
    
    # Format results as markdown
    significance_md = format_significance_markdown(significance_results)
    
    # Save significance test results as separate file
    significance_path = os.path.join(args.output_dir, "significance_tests.md")
    with open(significance_path, 'w') as f:
        f.write(significance_md)
    
    # Update the stats markdown file
    if os.path.exists(args.stats_path):
        update_markdown_report(args.stats_path, significance_md)
    
    print(f"Significance test results saved to {significance_path}")
    if os.path.exists(args.stats_path):
        print(f"Updated stats report with significance tests at {args.stats_path}")


if __name__ == "__main__":
    main() 