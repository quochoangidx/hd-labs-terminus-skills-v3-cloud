"""Channel and station magnitudes."""

from .amplitude import is_reading, log_record_amplitude
from .attenuation import minus_log_a0


def channel_magnitude(amplitude_nm, distance_km, correction):
    """Local magnitude from one channel's amplitude at a station.

    The logarithm of the record amplitude, plus the distance correction at the
    station's distance, plus the station's correction as it stands in the table
    (rules 4.1 and 4.2).  ``correction`` is the station's entry in the station
    table.
    """
    return log_record_amplitude(amplitude_nm) + minus_log_a0(distance_km) + float(correction)


def station_magnitude(amplitudes, distance_km, correction):
    """Local magnitude of one station from the amplitudes it read.

    ``amplitudes`` is the station's list of amplitude objects for the event --
    every horizontal channel of each of its recordings -- each with its
    ``channel``, ``amplitude_nm`` and ``noise_nm``.  The station's magnitude is
    the mean of the channel magnitudes of its readings (rule 4.3).
    """
    values = [
        channel_magnitude(item["amplitude_nm"], distance_km, correction)
        for item in amplitudes
        if is_reading(item)
    ]
    if not values:
        return None
    return sum(values) / len(values)
