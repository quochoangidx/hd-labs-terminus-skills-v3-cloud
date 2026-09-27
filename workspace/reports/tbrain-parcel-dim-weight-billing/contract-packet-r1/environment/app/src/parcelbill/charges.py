"""Transport, residential and fuel charges."""

ZONE_RATE = {2: 95, 3: 105, 4: 118, 5: 131, 6: 146, 7: 164, 8: 190}
RESIDENTIAL = 450
FUEL_BASIS_POINTS = 1425


def transport(parcel, pounds):
    return pounds * ZONE_RATE[parcel["zone"]]


def residential(parcel):
    return RESIDENTIAL if parcel["residential"] else 0


def fuel(transport_charge, residential_charge):
    return transport_charge * FUEL_BASIS_POINTS // 10000
