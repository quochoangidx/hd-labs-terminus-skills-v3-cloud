`/app/src/geodetic` computes geodesics on the WGS84 ellipsoid for our survey adjustment. Its `inverse(lat1, lon1, lat2, lon2)` still uses Vincenty's iteration, which is only good to a fraction of a millimetre and stops converging for nearly antipodal points. The adjustment now needs the true shortest path to micrometre accuracy.

Make `inverse` return `(s12, azi1, azi2)` for any two points whose latitudes lie strictly between -90 and 90 degrees, with any longitudes, all in degrees:

- `s12` is the length in metres of the shortest geodesic between the points on the ellipsoid with the semi-major axis and flattening in `/app/src/geodetic/ellipsoid.py`;
- `azi1` is that geodesic's azimuth at the first point and `azi2` its azimuth at the second point, in the direction of travel from the first point to the second (a forward azimuth, not the back azimuth), both in degrees clockwise from north within [-180, 180].

`s12` must be within 1e-6 m of the true length, and each azimuth within 1e-9 degrees of the true azimuth or, when it is larger, within the angle whose arc over a length of `s12` is 1e-6 m. This holds wherever the shortest geodesic is unique. For two coincident points `s12` is 0 and the azimuths are not checked. Keep the package to the Python standard library, and keep a call under 50 ms.

The checks use pairs from all over the ellipsoid, very short lines, lines along and close to the equator and to meridians, points close to the poles, and nearly antipodal pairs.
