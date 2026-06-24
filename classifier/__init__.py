"""classifier — Intake classifier for 'describe your own' project type (ADR-0013-auto-routing).

This module contains the ONE permitted runtime LLM call at the input boundary.
It is NEVER imported by engines/ — the number/verdict path remains deterministic.
"""
