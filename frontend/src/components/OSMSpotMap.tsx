import { useEffect } from "react";
import L from "leaflet";
import { MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import type { GeocodingResult, Spot } from "../types";

type OSMSpotMapProps = {
  spots: Spot[];
  searchResults: GeocodingResult[];
  focusedResult: GeocodingResult | null;
  onSelectSpot: (spot: Spot) => void;
};

const savedSpotIcon = L.divIcon({
  className: "osm-saved-spot-icon",
  html: '<span><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 22s8-7.2 8-13A8 8 0 1 0 4 9c0 5.8 8 13 8 13Z" fill="currentColor"/><circle cx="12" cy="9" r="2.7" fill="white"/></svg></span>',
  iconSize: [32, 40],
  iconAnchor: [16, 39],
  popupAnchor: [0, -36],
});

const searchResultIcon = L.divIcon({
  className: "osm-search-result-icon",
  html: '<span><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 22s8-7.2 8-13A8 8 0 1 0 4 9c0 5.8 8 13 8 13Z" fill="currentColor"/><circle cx="12" cy="9" r="2.7" fill="white"/></svg></span>',
  iconSize: [32, 40],
  iconAnchor: [16, 39],
  popupAnchor: [0, -36],
});

function FitSpots({ spots, focusedResult }: { spots: Spot[]; focusedResult: GeocodingResult | null }) {
  const map = useMap();

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      map.invalidateSize({ pan: false });
      if (focusedResult) {
        map.flyTo([focusedResult.latitude, focusedResult.longitude], 12, { duration: 0.5 });
        return;
      }
      if (spots.length === 0) {
        map.setView([36.2, 138.2], 4.5);
        return;
      }

      const bounds = L.latLngBounds(spots.map((spot) => [spot.latitude, spot.longitude]));
      map.fitBounds(bounds, { padding: [34, 34], maxZoom: spots.length === 1 ? 9 : 8 });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [focusedResult, map, spots]);

  return null;
}

export function OSMSpotMap({ spots, searchResults, focusedResult, onSelectSpot }: OSMSpotMapProps) {
  return (
    <div className="osm-spot-map" aria-label="保存スポットのOpenStreetMap地図">
      <MapContainer
        center={[36.2, 138.2]}
        className="osm-spot-map-canvas"
        scrollWheelZoom
        zoom={4.5}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {spots.map((spot) => (
          <Marker
            eventHandlers={{ click: () => onSelectSpot(spot) }}
            icon={savedSpotIcon}
            key={spot.id}
            position={[spot.latitude, spot.longitude]}
            title={spot.title}
          >
            <Popup>
              <div className="osm-spot-popup">
                <strong>{spot.region.split(",")[0]}</strong>
                <span>{spot.prefecture} · {spot.local_food}</span>
                <button onClick={() => onSelectSpot(spot)} type="button">スポット詳細を見る</button>
              </div>
            </Popup>
          </Marker>
        ))}
        {searchResults.map((result) => (
          <Marker
            icon={searchResultIcon}
            key={result.place_id}
            position={[result.latitude, result.longitude]}
            title={result.display_name}
          >
            <Popup>{result.display_name}</Popup>
          </Marker>
        ))}
        <FitSpots focusedResult={focusedResult} spots={spots} />
      </MapContainer>
    </div>
  );
}
