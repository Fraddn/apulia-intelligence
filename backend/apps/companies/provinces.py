from django.db import models


class Province(models.TextChoices):
    # In admins shows the full name of the province
    BA = "BA", "Bari"
    BT = "BT", "Barletta-Andria-Trani"
    BR = "BR", "Brindisi"
    FG = "FG", "Foggia"
    LE = "LE", "Lecce"
    TA = "TA", "Taranto"


PUGLIA_REGION_CODE = "016"

ISTAT_PROVINCE_CODES = {
    # Maps ISTAT province codes to Province enum values.
    "071": Province.FG,
    "072": Province.BA,
    "073": Province.TA,
    "074": Province.BR,
    "075": Province.LE,
    "110": Province.BT,
}
