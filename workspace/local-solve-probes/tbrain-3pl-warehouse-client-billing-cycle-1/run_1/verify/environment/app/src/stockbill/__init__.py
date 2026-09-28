"""Warehouse client billing for pallet storage and handling (billing schedule WB-5)."""

from .statement import build_statement

__all__ = ["build_statement"]
