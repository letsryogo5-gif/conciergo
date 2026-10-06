import { useEffect, useMemo, useState } from "react";
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer, useMap } from "react-leaflet";
import type { LatLngTuple } from "leaflet";
import type { RouteDay } from "../types";

const ROUTE_COLORS = ["#bb715e", "#64816b", "#7385a2", "#a18a55"];

type RouteOverviewMapProps = {
  days: RouteDay[];
};

function FitRouteBounds({ positions }: { positions: LatLngTuple[] }) {
  const map = useMap();

  useEffect(() => {
    if (positions.length > 1) {
      map.fitBounds(positions, { padding: [28, 28], maxZoom: 11 });
    } else if (positions.length === 1) {
      map.setView(positions[0], 11);
    }
  }, [map, positions]);

  return null;
}

export function RouteOverviewMap({ days }: RouteOverviewMapProps) {
  const [selectedDay, setSelectedDay] = useState<number | null>(null);
  const routePositions = useMemo(
    () => days.map((day) => day.route_coordinates.map(
      (coordinate) => [coordinate.latitude, coordinate.longitude] as LatLngTuple,
    )),
    [days],
  );
  const visibleDayIndexes = useMemo(
    () => days
      .map((day, index) => ({ day, index }))
      .filter(({ day }) => selectedDay === null || day.day_number === selectedDay),
    [days, selectedDay],
  );
  const visiblePositions = useMemo(
    () => visibleDayIndexes.flatMap(({ index }) => routePositions[index]),
    [routePositions, visibleDayIndexes],
  );
  const center = visiblePositions[0] ?? ([36.2, 138.2] as LatLngTuple);

  return (
    <section className="route-map-panel" aria-label="OSRM道路ルートマップ">
      <div className="route-map-heading">
        <div><span className="eyebrow">OPEN ROAD ROUTE</span><strong>道のりを地図で見る</strong></div>
        <span>車移動の目安</span>
      </div>
      <div className="route-map-filters" role="group" aria-label="地図に表示する日程">
        <button
          aria-pressed={selectedDay === null}
          className={selectedDay === null ? "is-active" : ""}
          onClick={() => setSelectedDay(null)}
          type="button"
        >
          全日程
        </button>
        {days.map((day, index) => (
          <button
            aria-pressed={selectedDay === day.day_number}
            className={selectedDay === day.day_number ? "is-active" : ""}
            key={day.day_number}
            onClick={() => setSelectedDay(day.day_number)}
            type="button"
          >
            <i style={{ backgroundColor: ROUTE_COLORS[index % ROUTE_COLORS.length] }} />
            DAY {String(day.day_number).padStart(2, "0")}
          </button>
        ))}
      </div>
      <MapContainer
        center={center}
        className="route-overview-map"
        scrollWheelZoom={false}
        zoom={5}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitRouteBounds positions={visiblePositions} />
        {visibleDayIndexes.flatMap(({ day, index: dayIndex }) => {
          const color = ROUTE_COLORS[dayIndex % ROUTE_COLORS.length];
          const positions = routePositions[dayIndex];
          return [
              ...(positions.length > 1 ? [
                <Polyline key={`route-${day.day_number}`} positions={positions} pathOptions={{ color, weight: 5, opacity: 0.82 }} />
              ] : []),
              ...day.stops.map((stop, stopIndex) => (
                <CircleMarker
                  center={[stop.spot.latitude, stop.spot.longitude]}
                  key={stop.spot.id}
                  pathOptions={{ color: "#fff", fillColor: color, fillOpacity: 1, weight: 2 }}
                  radius={7}
                >
                  <Popup>
                    <strong>DAY {day.day_number} · {stopIndex + 1}. {stop.spot.region.split(",")[0]}</strong>
                    <br />
                    {stop.spot.title}
                  </Popup>
                </CircleMarker>
              )),
          ];
        })}
      </MapContainer>
      <p className="route-map-attribution-note">地図 © OpenStreetMap contributors · 道路経路 © OSRM / OpenStreetMap data</p>
    </section>
  );
}
