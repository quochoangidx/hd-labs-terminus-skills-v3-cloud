"""Channel and station magnitudes."""

from .amplitude import is_reading, log_record_amplitude
from .attenuation import minus_log_a0


def channel_magnitude(amplitude_nm, distance_km, correction):
    """Local magnitude from one channel's amplitude at a station.

    ``correction`` is the station's entry in the station table, added as it
    stands (rules 4.1 and 4.2).
    """
    return log_record_amplitude(amplitude_nm) + minus_log_a0(distance_km) + correction


def readings(amplitudes):
    """The amplitudes of ``amplitudes`` that are readings (rule 2.3)."""
    return [item for item in amplitudes if is_reading(item)]


def station_magnitude(amplitudes, distance_km, correction):
    """Local magnitude of one station, the mean over its readings (rule 4.3).

    ``amplitudes`` is every amplitude object the station carries for the event,
    over all of its recordings, each with its ``channel``, ``amplitude_nm`` and
    ``noise_nm``.  Only readings count, and the mean of their channel
    magnitudes is taken rather than the largest channel alone.
    """
    kept = readings(amplitudes)
    magnitudes = [
        channel_magnitude(item["amplitude_nm"], distance_km, correction) for item in kept
    ]
    return sum(magnitudes) / len(magnitudes)
