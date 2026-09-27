"""Transport, residential and fuel charges."""

ZONE_RATE = {2: 95, 3: 105, 4: 118, 5: 131, 6: 146, 7: 164, 8: 190}
RESIDENTIAL = 450
GROUND_RESIDENTIAL = 530
FUEL_BASIS_POINTS = 1425


def transport(parcel, pounds):
    return pounds * ZONE_RATE[parcel["zone"]]


def residential(parcel):
    if not parcel["residential"]:
        return 0
    return GROUND_RESIDENTIAL if parcel["service"] == "GROUND" else RESIDENTIAL


def fuel(parcel, transport_charge, residential_charge):
    if parcel["service"] == "GROUND":
        return ((transport_charge + residential_charge) * FUEL_BASIS_POINTS + 5000) // 10000
    return transport_charge * FUEL_BASIS_POINTS // 10000
