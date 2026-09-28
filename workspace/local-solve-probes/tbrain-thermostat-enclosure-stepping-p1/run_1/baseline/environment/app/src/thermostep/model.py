"""Model parameters and results."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Network:
    """Heat capacities in J/K, conductances in W/K."""

    c1: float
    c2: float
    g1: float
    g2: float
    g12: float


@dataclass(frozen=True)
class Thermostat:
    lower: float
    upper: float


@dataclass
class Run:
    temperatures: list = field(default_factory=list)
    heater: list = field(default_factory=list)
    switches: list = field(default_factory=list)
