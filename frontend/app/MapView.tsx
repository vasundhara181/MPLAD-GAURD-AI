"use client";

import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
} from "react-leaflet";

import "leaflet/dist/leaflet.css";

type MapProject = {
  project_id: string;
  project_name: string;
  state: string;
  district: string;
  latitude: number;
  longitude: number;
  overall_risk_score: number;
  risk_level: string;
  risk_signal_count: number;
  geo_anomaly?: boolean;
};


// ============================================================
// RISK COLOR
// ============================================================

function getRiskColor(level: string): string {
  switch (level) {
    case "CRITICAL":
      return "#ef4444";

    case "HIGH":
      return "#f97316";

    case "MEDIUM":
      return "#eab308";

    case "LOW":
      return "#22c55e";

    default:
      return "#94a3b8";
  }
}


// ============================================================
// MARKER SIZE
// ============================================================

function getMarkerRadius(level: string): number {
  switch (level) {
    case "CRITICAL":
      return 12;

    case "HIGH":
      return 10;

    case "MEDIUM":
      return 8;

    case "LOW":
      return 6;

    default:
      return 6;
  }
}


// ============================================================
// MAP COMPONENT
// ============================================================

export default function MapView({
  projects,
  center,
  zoom,
  heightClassName = "h-[600px]",
}: {
  projects: MapProject[];
  center?: [number, number];
  zoom?: number;
  heightClassName?: string;
}) {

  const mapCenter: [number, number] = center ?? [
    20.5937,
    78.9629,
  ];

  const mapZoom = zoom ?? 5;


  return (
    <div className={`${heightClassName} w-full overflow-hidden rounded-2xl`}>

      <MapContainer
        center={mapCenter}
        zoom={mapZoom}
        scrollWheelZoom={true}
        className="h-full w-full"
      >

        {/* ==================================================
            OPEN STREET MAP
        ================================================== */}

        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />


        {/* ==================================================
            PROJECT MARKERS
        ================================================== */}

        {projects.map((project) => {

          const riskColor = getRiskColor(
            project.risk_level
          );

          const markerRadius = getMarkerRadius(
            project.risk_level
          );


          return (
            <CircleMarker
              key={project.project_id}

              center={[
                Number(project.latitude),
                Number(project.longitude),
              ]}

              radius={project.geo_anomaly ? markerRadius + 3 : markerRadius}

              pathOptions={
                project.geo_anomaly
                  ? {
                      color: "#8b5cf6",
                      fillColor: riskColor,
                      fillOpacity: 0.75,
                      weight: 4,
                      dashArray: "3, 3",
                    }
                  : {
                      color: riskColor,
                      fillColor: riskColor,
                      fillOpacity: 0.75,
                      weight: 2,
                    }
              }
            >

              {/* ==========================================
                  PROJECT POPUP
              ========================================== */}

              <Popup>

                <div className="min-w-[220px] text-slate-900">

                  <h3 className="text-lg font-bold">
                    {project.project_id}
                  </h3>

                  <p className="mt-1 text-sm">
                    {project.project_name}
                  </p>

                  <hr className="my-2" />

                  <p>
                    <strong>District:</strong>{" "}
                    {project.district}
                  </p>

                  <p>
                    <strong>State:</strong>{" "}
                    {project.state}
                  </p>

                  <p>
                    <strong>Risk Score:</strong>{" "}
                    {Number(
                      project.overall_risk_score
                    ).toFixed(1)}
                    /100
                  </p>

                  <p>
                    <strong>Risk Level:</strong>{" "}
                    {project.risk_level}
                  </p>

                  <p>
                    <strong>Risk Signals:</strong>{" "}
                    {project.risk_signal_count}
                  </p>

                  {project.geo_anomaly && (
                    <p className="mt-1 text-violet-700 font-semibold">
                      ⬤ Overlaps another project&apos;s location (within 300 m)
                    </p>
                  )}

                </div>

              </Popup>

            </CircleMarker>
          );
        })}

      </MapContainer>

    </div>
  );
}