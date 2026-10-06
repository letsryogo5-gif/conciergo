import type { SourceReference } from "../types";

export type AttributionCredit = {
  label: string;
  url: string;
  licenseName?: string;
  licenseUrl?: string;
};

export const OPENSTREETMAP_CREDIT: AttributionCredit = {
  label: "© OpenStreetMap contributors",
  url: "https://www.openstreetmap.org/copyright",
  licenseName: "ODbL 1.0",
  licenseUrl: "https://opendatacommons.org/licenses/odbl/1-0/",
};

type AttributionCreditsProps = {
  credits: AttributionCredit[];
  className?: string;
  label?: string;
};

export function AttributionCredits({
  credits,
  className = "",
  label = "出典",
}: AttributionCreditsProps) {
  if (credits.length === 0) return null;

  return (
    <div className={`attribution-credits ${className}`.trim()} aria-label={label}>
      <span className="attribution-credits-label">{label}</span>
      {credits.map((credit) => (
        <span className="attribution-credit" key={`${credit.label}:${credit.url}`}>
          <a href={credit.url} target="_blank" rel="noreferrer">{credit.label}</a>
          {credit.licenseName && (
            <>
              <span aria-hidden="true"> · </span>
              {credit.licenseUrl
                ? <a href={credit.licenseUrl} target="_blank" rel="noreferrer">{credit.licenseName}</a>
                : <span>{credit.licenseName}</span>}
            </>
          )}
        </span>
      ))}
    </div>
  );
}

export function SourceAttributions({
  sources,
  label = "情報出典",
}: {
  sources: SourceReference[];
  label?: string;
}) {
  return (
    <AttributionCredits
      credits={sources.map((source) => ({
        label: `${source.publisher}「${source.title}」`,
        url: source.url,
        licenseName: source.license_name ?? undefined,
        licenseUrl: source.license_url ?? undefined,
      }))}
      label={label}
    />
  );
}

export function DataStatusBadge({ status }: { status: "sample" | "sourced" }) {
  return (
    <span className={`data-status-badge ${status}`}>
      {status === "sourced" ? "一部出典あり" : "サンプル情報"}
    </span>
  );
}

export function FeatureStatusBadge({
  mode,
  label,
}: {
  mode: "connected" | "sample";
  label: string;
}) {
  return (
    <span className={`feature-status-badge ${mode}`}>
      <span aria-hidden="true" />
      {label} · {mode === "connected" ? "外部連携" : "サンプル"}
    </span>
  );
}
