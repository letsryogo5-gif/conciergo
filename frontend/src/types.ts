export type Spot = {
  id: string;
  region: string;
  prefecture: string;
  title: string;
  description: string;
  image_url: string;
  video_url: string | null;
  category: string;
  local_food: string;
  local_species: string;
  latitude: number;
  longitude: number;
  tags: string[];
  creator: string;
  likes: number;
  local_trivia: string;
  is_world_heritage: boolean;
  heritage_name: string | null;
  wikipedia_query: string | null;
  data_status: "sample" | "sourced";
  sources: SourceReference[];
};

export type SourceReference = {
  publisher: string;
  title: string;
  url: string;
  verified_fields: string[];
  license_name: string | null;
  license_url: string | null;
};

export type WikipediaSummary = {
  title: string;
  extract: string;
  article_url: string;
};

export type MediaAsset = {
  id: string;
  media_type: "image" | "video";
  url: string;
  preview_url: string;
  page_url: string;
  source: "pixabay" | "pexels";
  description: string;
  duration_seconds: number | null;
  creator: string | null;
};

export type SpotMediaResults = {
  spot_id: string;
  query: string;
  media_type: "image" | "video";
  source: "providers" | "local_sample";
  items: MediaAsset[];
  fallback_url: string;
  providers: {
    provider: "pixabay" | "pexels";
    status: "not_configured" | "available" | "unavailable" | "empty";
    result_count: number;
  }[];
};

export type SpotDiscoveryResults = {
  items: Spot[];
  categories: string[];
  regions: string[];
  total: number;
  source: string;
};

export type GeocodingResult = {
  place_id: number;
  display_name: string;
  latitude: number;
  longitude: number;
  category: string;
  place_type: string;
};

export type LocalEvent = {
  id: string;
  spot_id: string;
  name: string;
  region: string;
  description: string;
  image_url: string;
  start_month: number;
  end_month: number;
  best_time: string;
  category: string;
  data_status: "sample" | "sourced";
  sources: SourceReference[];
};

export type AppStatus = {
  sample_mode: boolean;
  services: {
    google_maps: string;
    social: string;
  };
};

export type RouteStop = {
  arrival_time: string;
  departure_time: string;
  visit_minutes: number;
  travel_minutes_from_previous: number;
  distance_km_from_previous: number;
  spot: Spot;
};

export type RouteDay = {
  day_number: number;
  title: string;
  start_time: string;
  end_time: string;
  stops: RouteStop[];
  route_coordinates: RouteCoordinate[];
};

export type RouteCoordinate = {
  latitude: number;
  longitude: number;
};

export type RoutePlan = {
  sample_mode: boolean;
  algorithm: string;
  days: RouteDay[];
  total_spots: number;
  total_estimated_travel_minutes: number;
  note: string;
  occasion: LocalEvent | null;
  added_spot_ids: string[];
};

export type RouteRequest = {
  spot_ids: string[];
  event_id: string | null;
};

export type ModelCourse = {
  id: string;
  title: string;
  description: string;
  region: string;
  creator: string;
  image_url: string;
  spot_ids: string[];
  likes: number;
};

export type ModelCourseRequest = {
  title: string;
  description: string;
  region: string;
  creator: string;
  spot_ids: string[];
};

export type MemoryCoordinate = {
  latitude: number;
  longitude: number;
  spot_id: string;
  label: string;
};

export type MemoryPhoto = {
  id: string;
  image_url: string;
  caption: string;
  captured_at: string;
  latitude: number;
  longitude: number;
  spot_id: string;
};

export type TravelMemory = {
  id: string;
  title: string;
  region: string;
  visited_at: string;
  note: string;
  route: MemoryCoordinate[];
  photos: MemoryPhoto[];
};
