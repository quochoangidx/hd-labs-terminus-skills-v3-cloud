`/app/src/orbitprop` propagates objects for our conjunction screener. Its `propagate(r0, v0, dt, mu)` converts the state to classical elements and solves Kepler's equation, so it only handles closed orbits and loses accuracy on nearly circular and nearly parabolic ones. The screener now feeds it every kind of two-body trajectory.

Make `propagate` return the exact two-body state `(r, v)` at time `dt` seconds after the state `(r0, v0)`, under a point mass with gravitational parameter `mu` (m^3/s^2), for any initial state with `r0` not at the origin: elliptic, circular, parabolic and hyperbolic orbits, and rectilinear ones whose velocity lies along the radius, as long as the trajectory does not reach the origin between the two times. `r0`, `v0`, `r` and `v` are 3-tuples of floats in metres and metres per second, and `dt` may be negative or zero.

Each component of `r` must be within `1e-10 * max(|r|, |r0|)` of the true position, and each component of `v` within `1e-10 * max(|v|, |v0|)` of the true velocity. Keep the package to the Python standard library and a call under 20 ms.

The checks cover low and high orbits, eccentricities from 0 to far above 1 including values within 1e-9 of 1, propagation across a fraction of an orbit up to ten thousand revolutions, both directions in time, and radial trajectories moving outward and inward.
