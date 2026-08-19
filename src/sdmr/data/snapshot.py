"""Credential-free access to versioned GBIF monthly cloud occurrence snapshots.

GBIF publishes the same monthly occurrence snapshot to multiple public cloud
mirrors. SDMR treats the cloud provider as an I/O transport choice rather than a
scientific data choice: the snapshot date/DOI and SQL filter remain the evidence
contract, while provenance records the exact remote URI and query engine.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
from pathlib import Path
from typing import Literal, Sequence

import pandas as pd

from .raster import sha256_file

GBIF_AWS_REGIONS = (
    "us-east-1",
    "eu-central-1",
    "ap-southeast-2",
    "af-south-1",
    "sa-east-1",
)
GBIF_AZURE_ACCOUNT = "ai4edataeuwest"
GBIF_AZURE_CONTAINER = "gbif"
GBIF_CLOUD_PROVIDERS = ("aws", "azure")

# Long GBIF scans traverse hundreds of Parquet shards. Product-A v1 once failed
# late in the target-group scan with an SSL "unexpected EOF" on one S3 shard.
# DuckDB documents disabling keep-alive as useful for connection failures. The
# retry budget is deliberately bounded so a persistently bad shard fails rather
# than consuming hours. These settings change transport resilience only.
GBIF_HTTP_RETRIES = 8
GBIF_HTTP_RETRY_WAIT_MS = 500
GBIF_HTTP_RETRY_BACKOFF = 1.5
GBIF_HTTP_TIMEOUT_SECONDS = 120

PREFERRED_SNAPSHOT_COLUMNS = (
    "gbifid",
    "datasetkey",
    "occurrenceid",
    "kingdom",
    "phylum",
    "class",
    "order",
    "family",
    "genus",
    "species",
    "specieskey",
    "taxonkey",
    "scientificname",
    "acceptedscientificname",
    "taxonrank",
    "basisofrecord",
    "occurrencestatus",
    "decimallatitude",
    "decimallongitude",
    "coordinateuncertaintyinmeters",
    "year",
    "month",
    "day",
    "eventdate",
    "countrycode",
    "institutioncode",
    "issues",
    "license",
)


@dataclass(frozen=True)
class SnapshotBounds:
    west: float
    east: float
    south: float
    north: float

    def __post_init__(self):
        if not (-180 <= self.west <= 180 and -180 <= self.east <= 180):
            raise ValueError("longitude bounds must be in [-180, 180]")
        if not (-90 <= self.south <= self.north <= 90):
            raise ValueError("latitude bounds must satisfy -90 <= south <= north <= 90")


@dataclass
class GBIFSnapshotSubsetResult:
    path: Path
    provenance: pd.DataFrame


def _validate_snapshot_date(value: str) -> str:
    parsed = date.fromisoformat(str(value))
    if parsed.day != 1:
        raise ValueError("GBIF monthly snapshot date must be the first day of a month (YYYY-MM-01)")
    return parsed.isoformat()


def gbif_snapshot_s3_uri(snapshot_date: str, *, region: str = "us-east-1") -> str:
    snapshot_date = _validate_snapshot_date(snapshot_date)
    if region not in GBIF_AWS_REGIONS:
        raise ValueError(f"Unsupported GBIF AWS region: {region!r}")
    bucket = f"gbif-open-data-{region}"
    return f"s3://{bucket}/occurrence/{snapshot_date}/occurrence.parquet/*"


def gbif_snapshot_azure_uri(snapshot_date: str) -> str:
    """Azure diagnostic URI; anonymous Actions access is currently unavailable."""
    snapshot_date = _validate_snapshot_date(snapshot_date)
    return f"az://{GBIF_AZURE_CONTAINER}/occurrence/{snapshot_date}/occurrence.parquet/*"


def gbif_snapshot_uri(
    snapshot_date: str,
    *,
    cloud_provider: Literal["aws", "azure"] = "aws",
    region: str = "us-east-1",
) -> str:
    provider = str(cloud_provider).lower()
    if provider == "aws":
        return gbif_snapshot_s3_uri(snapshot_date, region=region)
    if provider == "azure":
        return gbif_snapshot_azure_uri(snapshot_date)
    raise ValueError(f"Unsupported GBIF cloud provider: {cloud_provider!r}")


def _sql_literal(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _bounds_sql(bounds: SnapshotBounds) -> str:
    lat = f"decimallatitude BETWEEN {float(bounds.south)} AND {float(bounds.north)}"
    if bounds.west <= bounds.east:
        lon = f"decimallongitude BETWEEN {float(bounds.west)} AND {float(bounds.east)}"
    else:
        lon = f"(decimallongitude >= {float(bounds.west)} OR decimallongitude <= {float(bounds.east)})"
    return f"({lat} AND {lon})"


def build_snapshot_filter_sql(
    *,
    species_names: Sequence[str] | None = None,
    kingdom: str | None = None,
    bounds: Sequence[SnapshotBounds] | None = None,
    require_coordinates: bool = True,
) -> str:
    scope_terms: list[str] = []
    names = [str(x).strip() for x in (species_names or ()) if str(x).strip()]
    if names:
        scope_terms.append("species IN (" + ",".join(_sql_literal(x) for x in sorted(set(names))) + ")")
    if kingdom:
        scope_terms.append("kingdom = " + _sql_literal(str(kingdom).strip()))
    if bounds:
        scope_terms.append("(" + " OR ".join(_bounds_sql(b) for b in bounds) + ")")
    if not scope_terms:
        raise ValueError("Snapshot extraction requires at least one taxonomic/spatial filter")
    terms = list(scope_terms)
    if require_coordinates:
        terms.extend(
            [
                "decimallatitude IS NOT NULL",
                "decimallongitude IS NOT NULL",
                "decimallatitude BETWEEN -90 AND 90",
                "decimallongitude BETWEEN -180 AND 180",
            ]
        )
    return " AND ".join(f"({term})" for term in terms)


def _query_sha256(uri: str, columns: Sequence[str], where_sql: str, transform_sql: str = "") -> str:
    payload = (uri + "\n" + ",".join(columns) + "\n" + where_sql + "\n" + transform_sql + "\n").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _quote_identifier(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def build_snapshot_select_query(
    *,
    uri: str,
    selected_columns: Sequence[str],
    where_sql: str,
    longitude_column: str,
    latitude_column: str,
    order_column: str,
    one_per_grid_cell_degrees: float | None = None,
) -> str:
    select_sql = ",".join(_quote_identifier(name) for name in selected_columns)
    source = f"read_parquet({_sql_literal(uri)}, union_by_name=true)"
    if one_per_grid_cell_degrees is None:
        return f"SELECT {select_sql} FROM {source} WHERE {where_sql}"
    cell = float(one_per_grid_cell_degrees)
    if cell <= 0:
        raise ValueError("one_per_grid_cell_degrees must be > 0")
    lon = _quote_identifier(longitude_column)
    lat = _quote_identifier(latitude_column)
    order = _quote_identifier(order_column)
    return (
        "SELECT * EXCLUDE (__sdmr_rn) FROM ("
        f"SELECT {select_sql}, ROW_NUMBER() OVER ("
        f"PARTITION BY FLOOR(({lon} + 180.0) / {cell}), FLOOR(({lat} + 90.0) / {cell}) "
        f"ORDER BY {order} NULLS LAST) AS __sdmr_rn "
        f"FROM {source} WHERE {where_sql}"
        ") WHERE __sdmr_rn = 1"
    )


def _apply_http_resilience_settings(con) -> None:
    con.execute("SET http_keep_alive=false")
    con.execute(f"SET http_retries={GBIF_HTTP_RETRIES}")
    con.execute(f"SET http_retry_wait_ms={GBIF_HTTP_RETRY_WAIT_MS}")
    con.execute(f"SET http_retry_backoff={GBIF_HTTP_RETRY_BACKOFF}")
    con.execute(f"SET http_timeout={GBIF_HTTP_TIMEOUT_SECONDS}")
    con.execute("SET enable_http_metadata_cache=true")
    con.execute("SET enable_external_file_cache=true")


def _configure_duckdb_cloud(con, *, cloud_provider: str, region: str) -> None:
    provider = str(cloud_provider).lower()
    if provider == "aws":
        con.execute("INSTALL httpfs")
        con.execute("LOAD httpfs")
        con.execute(f"SET s3_region={_sql_literal(region)}")
        _apply_http_resilience_settings(con)
        return
    if provider == "azure":
        con.execute("INSTALL azure")
        con.execute("LOAD azure")
        con.execute(
            "CREATE OR REPLACE SECRET sdmr_gbif_azure ("
            "TYPE azure, PROVIDER config, "
            f"ACCOUNT_NAME {_sql_literal(GBIF_AZURE_ACCOUNT)}, "
            f"SCOPE {_sql_literal('az://' + GBIF_AZURE_CONTAINER + '/')}"
            ")"
        )
        con.execute("SET azure_transport_option_type='curl'")
        _apply_http_resilience_settings(con)
        return
    raise ValueError(f"Unsupported GBIF cloud provider: {cloud_provider!r}")


def materialize_gbif_snapshot_subset(
    output_path: str | Path,
    *,
    snapshot_date: str,
    snapshot_doi: str,
    species_names: Sequence[str] | None = None,
    kingdom: str | None = None,
    bounds: Sequence[SnapshotBounds] | None = None,
    region: str = "us-east-1",
    cloud_provider: Literal["aws", "azure"] = "aws",
    one_per_grid_cell_degrees: float | None = None,
    overwrite: bool = False,
) -> GBIFSnapshotSubsetResult:
    if not str(snapshot_doi).strip():
        raise ValueError("snapshot_doi is required for auditable/citable cloud-snapshot use")
    if one_per_grid_cell_degrees is not None and float(one_per_grid_cell_degrees) <= 0:
        raise ValueError("one_per_grid_cell_degrees must be > 0")
    output = Path(output_path)
    if output.exists() and not overwrite:
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    uri = gbif_snapshot_uri(snapshot_date, cloud_provider=cloud_provider, region=region)
    where_sql = build_snapshot_filter_sql(
        species_names=species_names,
        kingdom=kingdom,
        bounds=bounds,
        require_coordinates=True,
    )

    try:
        import duckdb
    except ImportError as exc:
        raise ImportError("GBIF cloud snapshots require duckdb; install sdmr[cloud].") from exc

    con = duckdb.connect()
    duckdb_version = str(getattr(duckdb, "__version__", ""))
    effective_http: dict[str, str] = {}
    try:
        _configure_duckdb_cloud(con, cloud_provider=cloud_provider, region=region)
        schema = con.execute(f"DESCRIBE SELECT * FROM read_parquet({_sql_literal(uri)}, union_by_name=true)").fetchdf()
        available = {str(x).lower(): str(x) for x in schema["column_name"].tolist()}
        required = {"species", "decimallatitude", "decimallongitude"}
        if kingdom:
            required.add("kingdom")
        missing = sorted(required - set(available))
        if missing:
            raise ValueError(f"GBIF snapshot schema missing required columns: {missing}")
        selected = [available[name] for name in PREFERRED_SNAPSHOT_COLUMNS if name in available]
        order_column = available.get("gbifid", available["species"])
        query = build_snapshot_select_query(
            uri=uri,
            selected_columns=selected,
            where_sql=where_sql,
            longitude_column=available["decimallongitude"],
            latitude_column=available["decimallatitude"],
            order_column=order_column,
            one_per_grid_cell_degrees=one_per_grid_cell_degrees,
        )
        out_literal = _sql_literal(str(output.resolve()))
        con.execute(f"COPY ({query}) TO {out_literal} (FORMAT PARQUET, COMPRESSION ZSTD)")
        n_rows = int(con.execute(f"SELECT COUNT(*) FROM read_parquet({out_literal})").fetchone()[0])
        effective_http = {
            str(name): str(value)
            for name, value in con.execute(
                "SELECT name, value FROM duckdb_settings() WHERE name IN ("
                "'http_keep_alive','http_retries','http_retry_wait_ms','http_retry_backoff','http_timeout',"
                "'enable_http_metadata_cache','enable_external_file_cache')"
            ).fetchall()
        }
    finally:
        con.close()

    transform_sql = "" if one_per_grid_cell_degrees is None else f"one_per_grid_cell_degrees={float(one_per_grid_cell_degrees)}"
    provenance = pd.DataFrame(
        [
            {
                "source_type": "gbif_monthly_cloud_snapshot",
                "snapshot_date": _validate_snapshot_date(snapshot_date),
                "snapshot_doi": str(snapshot_doi).strip(),
                "cloud_provider": str(cloud_provider).lower(),
                "region": region if str(cloud_provider).lower() == "aws" else "azure-eu-west",
                "remote_uri": uri,
                "query_engine": "duckdb",
                "duckdb_version": duckdb_version,
                "where_sql": where_sql,
                "selected_columns": ",".join(selected),
                "sampling_mode": "one_per_grid_cell" if one_per_grid_cell_degrees is not None else "all_filtered_rows",
                "one_per_grid_cell_degrees": one_per_grid_cell_degrees,
                "query_sha256": _query_sha256(uri, selected, where_sql, transform_sql),
                "http_keep_alive": effective_http.get("http_keep_alive", ""),
                "http_retries": effective_http.get("http_retries", ""),
                "http_retry_wait_ms": effective_http.get("http_retry_wait_ms", ""),
                "http_retry_backoff": effective_http.get("http_retry_backoff", ""),
                "http_timeout": effective_http.get("http_timeout", ""),
                "path": str(output),
                "sha256": sha256_file(output),
                "bytes": int(output.stat().st_size),
                "n_rows": n_rows,
                "taxonomy_provenance": "GBIF interpreted taxonomy embedded in declared monthly snapshot",
            }
        ]
    )
    return GBIFSnapshotSubsetResult(path=output, provenance=provenance)
