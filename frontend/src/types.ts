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
