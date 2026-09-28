"""Inputs of every graded run. Expected results live in expected.json, produced
from these inputs by model.py (see regenerate() below)."""

import math


def _oven():
    times = [60.0 * k for k in range(241)]
    ambient = [22.0 + 6.0 * math.sin(2 * math.pi * t / 5400.0) for t in times]
    power = [4200.0 if k % 40 < 30 else 2600.0 for k in range(240)]
    return {"net": [5.0e4, 3.0e5, 3.0, 4.0, 60.0], "times": times, "ambient": ambient,
            "power": power, "t1": 25.0, "t2": 25.0, "on": True, "thermostat": [178.0, 182.0]}


CASES = {
    "coupled_heater_on_ambient_ramps": {
        "net": [4.0e4, 2.5e5, 6.0, 9.0, 35.0], "times": [0, 300, 600, 900, 1500, 2100, 3000],
        "ambient": [18, 18.5, 19, 19, 21, 22, 20], "power": [900] * 6, "t1": 18, "t2": 18,
        "on": True, "thermostat": None},
    "heater_off_ambient_swings": {
        "net": [2.0e4, 1.0e5, 12.0, 9.0, 35.0], "times": [0, 200, 500, 800, 1400],
        "ambient": [20, 35, 5, 30, 22], "power": [700] * 4, "t1": 25, "t2": 30,
        "on": False, "thermostat": None},
    "unequal_intervals_and_power_changes": {
        "net": [3.0e4, 2.0e5, 8.0, 5.0, 50.0], "times": [0, 45, 50, 400, 1800, 1830, 5000],
        "ambient": [15, 15.2, 15.3, 16, 25, 25, 10], "power": [0, 1200, 300, 900, 0, 2500],
        "t1": 15, "t2": 15, "on": True, "thermostat": None},
    "wall_without_path_to_ambient": {
        "net": [2.0e4, 1.0e5, 10.0, 0.0, 40.0], "times": [0, 600, 1200, 2400],
        "ambient": [10, 20, 20, 5], "power": [500, 500, 0], "t1": 10, "t2": 30,
        "on": True, "thermostat": None},
    "chamber_without_path_to_ambient": {
        "net": [2.0e4, 1.0e5, 0.0, 15.0, 30.0], "times": [0, 300, 900, 2000],
        "ambient": [12, 30, 0, 18], "power": [800, 0, 400], "t1": 20, "t2": 15,
        "on": True, "thermostat": None},
    "insulated_enclosure": {
        "net": [1.0e4, 5.0e4, 0.0, 0.0, 25.0], "times": [0, 100, 400, 1000],
        "ambient": [20, 50, -10, 20], "power": [300, 0, 800], "t1": 20, "t2": 20,
        "on": True, "thermostat": None},
    "uncoupled_nodes_equal_rates": {
        "net": [1000.0, 3000.0, 2.0, 6.0, 0.0], "times": [0, 100, 250, 400, 900],
        "ambient": [20, 30, 10, 25, 25], "power": [50, 0, 80, 20], "t1": 20, "t2": 25,
        "on": True, "thermostat": None},
    "uncoupled_nodes_different_rates": {
        "net": [1000.0, 3000.0, 2.0, 9.0, 0.0], "times": [0, 100, 250, 400, 900],
        "ambient": [20, 30, 10, 25, 25], "power": [50, 0, 80, 20], "t1": 20, "t2": 25,
        "on": True, "thermostat": None},
    "nearly_uncoupled_equal_rates": {
        "net": [1000.0, 3000.0, 2.0, 6.0, 1.0e-7], "times": [0, 100, 250, 400, 900],
        "ambient": [20, 30, 10, 25, 25], "power": [50, 0, 80, 20], "t1": 20, "t2": 25,
        "on": True, "thermostat": None},
    "heater_off_without_thermostat_stays_off": {
        "net": [2.0e4, 1.0e5, 12.0, 9.0, 35.0], "times": [0, 500, 1000],
        "ambient": [5, 5, 5], "power": [900, 900], "t1": 2, "t2": 2,
        "on": False, "thermostat": None},
    "thermostat_single_switch_off": {
        "net": [4.0e4, 2.5e5, 6.0, 9.0, 35.0], "times": [0, 600, 1200, 1800],
        "ambient": [18, 18, 19, 19], "power": [1500, 1500, 1500], "t1": 18, "t2": 18,
        "on": True, "thermostat": [10.0, 35.0]},
    "thermostat_cycles_inside_one_interval": {
        "net": [1.0e4, 1.0e5, 6.0, 5.0, 30.0], "times": [0, 4000],
        "ambient": [20, 21], "power": [1200], "t1": 20, "t2": 20,
        "on": True, "thermostat": [29.0, 29.4]},
    "thermostat_crossing_between_samples_heater_on": {
        "net": [5000.0, 250000.0, 25.0, 5.0, 35.0], "times": [0, 1200, 1500],
        "ambient": [24.481, -18.753, -18.753], "power": [400, 400], "t1": 29.084, "t2": 33.172,
        "on": True, "thermostat": [5.0, 31.5]},
    "thermostat_dip_between_samples_heater_off": {
        "net": [10000.0, 50000.0, 25.0, 9.0, 80.0], "times": [0, 900, 1200],
        "ambient": [25.119, 52.231, 52.231], "power": [600, 600], "t1": 27.104, "t2": 22.997,
        "on": False, "thermostat": [25.6, 45.0]},
    "thermostat_switches_off_at_start": {
        "net": [4.0e4, 2.5e5, 6.0, 9.0, 35.0], "times": [0, 600, 1200],
        "ambient": [18, 18, 18], "power": [1500, 1500], "t1": 31.0, "t2": 25.0,
        "on": True, "thermostat": [28.0, 30.0]},
    "thermostat_switches_on_at_start": {
        "net": [4.0e4, 2.5e5, 6.0, 9.0, 35.0], "times": [0, 600, 1200],
        "ambient": [10, 10, 10], "power": [1500, 1500], "t1": 11.0, "t2": 12.0,
        "on": False, "thermostat": [12.0, 30.0]},
    "thermostat_heater_on_without_power_does_not_switch": {
        "net": [2.0e4, 1.0e5, 12.0, 9.0, 35.0], "times": [0, 600, 1200],
        "ambient": [5, 5, 5], "power": [0, 0], "t1": 20, "t2": 20,
        "on": True, "thermostat": [15.0, 25.0]},
    "thermostat_insulated_enclosure": {
        "net": [1.0e4, 5.0e4, 0.0, 0.0, 25.0], "times": [0, 1500, 3000],
        "ambient": [20, 20, 20], "power": [400, 150], "t1": 20, "t2": 20,
        "on": True, "thermostat": [26.0, 30.0]},
    "thermostat_uncoupled_equal_rates": {
        "net": [1000.0, 3000.0, 2.0, 6.0, 0.0], "times": [0, 400, 1200],
        "ambient": [20, 26, 22], "power": [60, 60], "t1": 20, "t2": 25,
        "on": True, "thermostat": [35.0, 40.0]},
    "oven_long_schedule": _oven(),
}
