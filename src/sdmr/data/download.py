"""Read versioned GBIF occurrence downloads into SDMR's stable schema."""

from __future__ import annotations

from dataclasses import dataclass
import io
from pathlib import Path
import zipfile

import pandas as pd

from .gbif import GBIF_COL_XR_CHECKLIST_KEY
from .raster import sha256_file


@dataclass
class GBIFDownloadResult:
    records: pd.DataFrame
    provenance: pd.DataFrame


_ALIASES = {
    "decimalLongitude": "longitude",
    "decimallongitude": "longitude",
    "decimalLatitude": "latitude",
    "decimallatitude": "latitude",
    "coordinateuncertaintyinmeters": "coordinateUncertaintyInMeters",
    "basisofrecord": "basisOfRecord",
    "occurrencestatus": "occurrenceStatus",
    "datasetkey": "datasetKey",
    "taxonkey": "taxonKey",
    "acceptedtaxonkey": "acceptedTaxonKey",
    "scientificname": "scientificName",
    "acceptedscientificname": "acceptedScientificName",
    "taxonrank": "taxonRank",
    "countrycode": "countryCode",
    "institutioncode": "institutionCode",
    "eventdate": "eventDate",
    "gbifid": "gbifID",
}


def _normalize_bulk_columns(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy()
    rename = {}
    for col in data.columns:
        if col in _ALIASES:
            rename[col] = _ALIASES[col]
        else:
            lower = str(col).lower()
            if lower in _ALIASES:
                rename[col] = _ALIASES[lower]
    data = data.rename(columns=rename)
    if "species" not in data:
        if "acceptedScientificName" in data:
            data["species"] = data["acceptedScientificName"]
        elif "scientificName" in data:
            data["species"] = data["scientificName"]
    return data


def _read_zip_table(path: Path) -> tuple[pd.DataFrame, str]:
    with zipfile.ZipFile(path) as archive:
        names = [n for n in archive.namelist() if not n.endswith("/")]
        parquet = [n for n in names if n.lower().endswith(".parquet")]
        if parquet:
            with archive.open(parquet[0]) as handle:
                try:
                    return pd.read_parquet(io.BytesIO(handle.read())), parquet[0]
                except ImportError as exc:
                    raise ImportError("Reading GBIF SIMPLE_PARQUET requires pyarrow; install sdmr[parquet].") from exc
        tabular = [
            n for n in names
            if Path(n).name.lower() in {"occurrence.txt", "occurrence.tsv", "occurrence.csv"}
            or n.lower().endswith((".tsv", ".txt", ".csv"))
        ]
        if not tabular:
            raise ValueError("ZIP does not contain a recognizable GBIF occurrence table")
        name = sorted(tabular, key=lambda n: ("occurrence" not in Path(n).name.lower(), len(n)))[0]
        with archive.open(name) as handle:
            data = pd.read_csv(handle, sep="\t", low_memory=False)
        return data, name


def load_gbif_download(
    path: str | Path,
    *,
    download_key: str = "",
    checklist_key: str = GBIF_COL_XR_CHECKLIST_KEY,
) -> GBIFDownloadResult:
    """Load a downloaded GBIF table/ZIP and attach immutable file provenance."""

    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(source)
    suffix = source.suffix.lower()
    member = ""
    if suffix == ".zip":
        frame, member = _read_zip_table(source)
    elif suffix in {".tsv", ".txt"}:
        frame = pd.read_csv(source, sep="\t", low_memory=False)
    elif suffix == ".csv":
        frame = pd.read_csv(source, low_memory=False)
    elif suffix in {".parquet", ".pq"}:
        try:
            frame = pd.read_parquet(source)
        except ImportError as exc:
            raise ImportError("Reading Parquet requires pyarrow; install sdmr[parquet].") from exc
    else:
        raise ValueError(f"Unsupported GBIF download format: {suffix}")

    records = _normalize_bulk_columns(frame)
    provenance = pd.DataFrame([{
        "path": str(source),
        "sha256": sha256_file(source),
        "bytes": int(source.stat().st_size),
        "archive_member": member,
        "download_key": str(download_key),
        "checklist_key": str(checklist_key),
        "n_rows": int(len(records)),
    }])
    return GBIFDownloadResult(records=records, provenance=provenance)
