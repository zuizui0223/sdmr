"""Resolve CHELSA v2.1 candidate predictors to reproducible COG URIs."""
from __future__ import annotations

import pandas as pd

CHELSA_V21_BASE = "https://os.zhdk.cloud.switch.ch/chelsav2/GLOBAL/climatologies/1981-2010"
_REQUIRED = {"predictor", "source", "version", "retrieval", "remote_name", "availability"}


def _clean(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def build_chelsa_cog_uri(
    *, remote_name: str, retrieval: str, summary: str = "", base_url: str = CHELSA_V21_BASE
) -> str:
    """Construct a CHELSA v2.1 historical COG URI from manifest metadata."""
    remote_name = _clean(remote_name)
    retrieval = _clean(retrieval)
    summary = _clean(summary)
    if not remote_name:
        raise ValueError("remote_name must not be empty")
    if retrieval == "annual_bio_cog":
        filename = f"CHELSA_{remote_name}_1981-2010_V.2.1.tif"
    elif retrieval == "annual_bio_summary_cog":
        if not summary:
            raise ValueError("annual_bio_summary_cog requires summary")
        if remote_name == "rsds":
            filename = f"CHELSA_{remote_name}_1981-2010_{summary}_V.2.1.tif"
        else:
            filename = f"CHELSA_{remote_name}_{summary}_1981-2010_V.2.1.tif"
    else:
        raise ValueError(f"Unsupported CHELSA retrieval mode: {retrieval!r}")
    return base_url.rstrip("/") + "/bio/" + filename


def resolve_chelsa_manifest(
    manifest: pd.DataFrame,
    *,
    base_url: str = CHELSA_V21_BASE,
    include_availability: tuple[str, ...] = ("current",),
    strict: bool = False,
) -> pd.DataFrame:
    """Resolve candidate rows to COG URIs and make omissions explicit.

    Rows not in ``include_availability`` or without a supported retrieval rule
    are returned with ``resolution_status != 'resolved'`` rather than silently
    disappearing. ``strict=True`` raises if any included row cannot be resolved.
    """
    missing = _REQUIRED - set(manifest.columns)
    if missing:
        raise KeyError(f"CHELSA manifest missing columns: {sorted(missing)}")
    rows = []
    include = set(include_availability)
    for record in manifest.to_dict(orient="records"):
        availability = _clean(record.get("availability")) or "current"
        retrieval = _clean(record.get("retrieval"))
        summary = _clean(record.get("summary"))
        remote_name = _clean(record.get("remote_name"))
        status = "resolved"
        uri = ""
        reason = ""
        if availability not in include:
            status = "excluded_availability"
            reason = f"availability={availability}"
        elif retrieval in {"", "unresolved"}:
            status = "unresolved"
            reason = "no verified current CHELSA COG rule"
        else:
            try:
                uri = build_chelsa_cog_uri(
                    remote_name=remote_name,
                    retrieval=retrieval,
                    summary=summary,
                    base_url=base_url,
                )
            except ValueError as exc:
                status = "unresolved"
                reason = str(exc)
        rows.append({**record, "resolution_status": status, "uri": uri, "resolution_reason": reason})
    out = pd.DataFrame(rows)
    if strict:
        bad = out[(out["availability"].fillna("current").isin(include)) & (out["resolution_status"] != "resolved")]
        if len(bad):
            names = ", ".join(bad["predictor"].astype(str))
            raise ValueError(f"Unresolved included CHELSA predictors: {names}")
    return out


def raster_specs_from_chelsa_manifest(manifest: pd.DataFrame, **kwargs):
    """Return RasterLayerSpec objects for currently resolved manifest rows."""
    from .raster import RasterLayerSpec

    resolved = resolve_chelsa_manifest(manifest, **kwargs)
    ok = resolved.loc[resolved["resolution_status"] == "resolved"]
    specs = [
        RasterLayerSpec(
            predictor=str(row.predictor),
            uri=str(row.uri),
            source=str(row.source),
            version=str(row.version),
        )
        for row in ok.itertuples(index=False)
    ]
    return specs, resolved
