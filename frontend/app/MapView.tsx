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
}: {
  projects: MapProject[];
}) {

  const center: [number, number] = [
    20.5937,
    78.9629,
  ];


  return (
    <div className="h-[600px] w-full overflow-hidden rounded-2xl">

      <MapContainer
        center={center}
        zoom={5}
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

              radius={markerRadius}

              pathOptions={{
                color: riskColor,
                fillColor: riskColor,
                fillOpacity: 0.75,
                weight: 2,
              }}
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

                </div>

              </Popup>

            </CircleMarker>
          );
        })}

      </MapContainer>

    </div>
  );
}