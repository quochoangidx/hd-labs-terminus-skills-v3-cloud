"""Channel and station magnitudes."""

from .amplitude import is_reading, log_record_amplitude
from .attenuation import minus_log_a0


def channel_magnitude(amplitude_nm, distance_km, correction):
    """Local magnitude from one channel's amplitude at a station.

    The logarithm of the record amplitude, plus the distance correction at the
    station's distance, plus the station's correction (manual, rule 4.1).
    ``correction`` is the station's entry in the station table, added as it
    stands (rule 4.2).
    """
    return log_record_amplitude(amplitude_nm) + minus_log_a0(distance_km) + float(correction)


def readings(amplitudes):
    """The amplitudes of ``amplitudes`` that are readings (rule 2.3)."""
    return [item for item in amplitudes if is_reading(item)]


def station_magnitude(amplitudes, distance_km, correction):
    """Local magnitude of one station, the mean of its readings' channel
    magnitudes (manual, rule 4.3).

    ``amplitudes`` is the list of amplitude objects of every recording the
    station sent for the event, each with its ``channel``, ``amplitude_nm`` and
    ``noise_nm``; a site whose broadband and strong-motion sensors are processed
    separately sends one recording for each, and all of their channels are the
    station's (rule 1.2).
    """
    magnitudes = [
        channel_magnitude(item["amplitude_nm"], distance_km, correction)
        for item in readings(amplitudes)
    ]
    return sum(magnitudes) / len(magnitudes)
