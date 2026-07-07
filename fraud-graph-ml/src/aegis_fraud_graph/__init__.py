"""Aegis Fraud Graph — fraud-ring detection over transaction networks.

Pipeline: transactions -> directed graph -> per-account graph features ->
XGBoost illicit classifier -> ring clustering on the high-risk subgraph ->
contract-compliant fraud_graph JSON for the command centre.
"""

__version__ = "0.1.0"
