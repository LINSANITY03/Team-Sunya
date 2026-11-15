# AgriCycle 🌱
### Smart Crop Rotation Planning

AgriCycle is a data-driven crop rotation planning application designed to help farmers explore and identify suitable crop sequences within a given growing season. AgriCycle is currently focused on Nepal. Due to the time constraints of the NASA Space Apps Challenge, we intentionally limited the initial geographical scope rather than attempting to develop a solution for multiple countries without sufficient regional data and validation.

The application generates possible crop rotation combinations, evaluates them against growing-season constraints, and ranks the valid combinations based on configurable farming priorities.

AgriCycle considers multiple decision-making criteria, including:

- **Profitability:** Prioritizing potential economic returns.
- **Food Security:** Considering the importance of food production.
- **Soil Health:** Supporting sustainable soil management.
- **Water Conservation:** Considering water-saving priorities.
- **Risk Reduction:** Accounting for farming risk preferences.

By combining crop characteristics, growing durations, rotation constraints and farmer-defined priorities, AgriCycle aims to make crop rotation planning more structured, transparent and accessible.

The goal is to support informed agricultural planning and encourage more sustainable farming decisions through data-driven recommendations. AgriCycle is a decision-support tool, not a replacement for farmers, agricultural experts, or traditional farming knowledge. Final farming decisions remain with the farmers, who can consider local experience, practical circumstances, and expert advice alongside the recommendations.

## Problem Statement

Small-scale farmers face challenges when planning crop rotations across growing seasons. Choosing which crops to cultivate, in what sequence, and within what timeframe requires considering multiple factors, including crop growing durations, available growing seasons, farming priorities, and resource constraints.

Making these decisions without a structured planning approach can make it difficult to compare alternative crop sequences and identify combinations that align with individual farming objectives.

Furthermore, crop rotation decisions involve balancing competing priorities. Farmers may need to consider profitability, food security, soil health, water conservation, and agricultural risk when deciding which crops to grow.

A crop sequence that appears suitable from one perspective may not necessarily be the best choice when other farming priorities are considered.

**The core problem:** Small-scale farmers need an accessible and structured way to explore, evaluate, and compare feasible crop rotation plans while considering growing-season constraints and their individual farming priorities.

## Our Solution

AgriCycle is a data-driven crop rotation planning application that helps farmers explore, evaluate, and compare possible crop rotation strategies based on growing-season constraints and individual farming priorities.

The application uses a structured recommendation pipeline that transforms crop information into ranked crop rotation alternatives.

The process consists of four main stages:

### 1. Crop Rotation Generation

AgriCycle generates possible crop sequences using available crop information and growing durations. It considers configurable growing-season limits, the minimum and maximum number of crops, and whether repeated crops are permitted.

### 2. Rotation Validation

Generated crop sequences are evaluated against predefined constraints, including:

- Growing-season duration.
- Minimum and maximum crop counts.
- Repeated crop restrictions.
- Excluded crops.
- Individual crop duration limits.

Only valid crop rotations proceed to the recommendation stage.

### 3. Multi-Criteria Scoring

Valid crop rotations are evaluated using a weighted scoring approach based on farming priorities.

The scoring framework considers five criteria:

- Profitability.
- Food security.
- Soil health.
- Water conservation.
- Risk reduction.

Farmers can assign different importance weights to these criteria, allowing the recommendation ranking to reflect their priorities.

### 4. Top-K Recommendations

AgriCycle ranks the evaluated crop rotations according to their overall weighted scores and selects the top K alternatives.

This allows farmers to compare multiple feasible crop rotation strategies rather than relying on a single recommendation.

### Expected Outcome

By combining crop rotation generation, constraint validation, multi-criteria scoring, and ranked recommendations, AgriCycle aims to provide a structured decision-support approach for crop rotation planning and encourage more informed agricultural decisions.

## Key Features

### 1. Crop Data Processing
- Cleans and preprocesses crop characteristics, crop calendar, weather, and soil datasets.
- Normalizes crop names and data types.
- Handles missing and duplicate records.

### 2. Crop Rotation Generation
- Generates possible crop rotation sequences.
- Considers crop growing durations.
- Supports configurable growing-season limits.
- Allows configurable minimum and maximum crop counts.
- Supports optional repeated crops.

### 3. Rotation Validation
- Validates generated crop sequences against predefined constraints.
- Checks growing-season duration limits.
- Enforces crop count restrictions.
- Identifies repeated and excluded crops.
- Checks individual crop duration limits.

### 4. Multi-Criteria Scoring
- Evaluates crop rotations using configurable priority weights.
- Considers profitability, food security, soil health, water conservation, and risk reduction.
- Calculates weighted scores for comparing alternative rotations.

### 5. Top-K Recommendations
- Ranks crop rotations based on their overall scores.
- Returns the highest-scoring alternatives.
- Provides summary statistics for selected recommendations.

### 6. REST API
- Built using FastAPI.
- Exposes the crop rotation recommendation engine through API endpoints.
- Supports structured input and output.
- Separates API functionality from the underlying recommendation engine.

### 7. Frontend
- Farmer-friendly crop rotation configuration.
- Interactive recommendation dashboard.
- Comparison of recommended crop sequences.
- Visualization of recommendation scores.

## How It Works

AgriCycle follows a structured data processing and recommendation pipeline to generate and rank feasible crop rotation strategies.

### Step 1: Data Loading
Crop characteristics, crop calendar, weather, and soil datasets are retrieved through the data repository.

### Step 2: Data Preprocessing
The preprocessing module cleans and prepares the datasets by normalizing crop names, removing duplicate records, handling data types, and converting relevant date and numeric columns.

### Step 3: Crop Selection
Crop selection criteria are applied to identify eligible crops for rotation planning.

### Step 4: Crop Rotation Generation
The rotation strategy module generates possible crop sequences using permutations or combinations with repetition, depending on the configuration. Sequences exceeding the specified growing-season duration are discarded.

### Step 5: Rotation Validation
Generated candidates are validated against crop count restrictions, repetition rules, excluded crops, individual crop duration limits, and total growing-season constraints.

Invalid candidates are rejected, with reasons recorded for validation failures.

### Step 6: Multi-Criteria Scoring
Valid crop rotations are evaluated using a weighted scoring framework covering profitability, food security, soil health, water conservation, and risk reduction.

Priority weights are normalized, and the weighted criterion scores are combined to calculate an overall score for each rotation.

### Step 7: Top-K Recommendation
The scoring results are ranked in descending order. The Top-K selector returns the requested number of highest-scoring crop rotation alternatives, along with summary statistics.

### Step 8: API Response
The FastAPI backend exposes the recommendation engine through REST endpoints, allowing clients to submit planning parameters and receive structured crop rotation recommendations.

## Data Sources

### 1. NASA POWER — Weather and Solar Data

**Provider:** NASA Langley Research Center  
**Platform:** Prediction Of Worldwide Energy Resources (POWER)

AgriCycle uses NASA POWER's Daily Point API to obtain meteorological and solar-related data for a specified geographic location and time period.

**API Endpoint:**
https://power.larc.nasa.gov/api/temporal/daily/point

**Weather variables handled by AgriCycle:**
- Precipitation
- Mean temperature
- Maximum temperature
- Minimum temperature
- Relative humidity
- Wind measurements
- Solar radiation
- Wet-day information

**API capabilities:**
- Location-specific data using latitude and longitude.
- Daily time-series data.
- Configurable date ranges.
- Multiple meteorological and solar parameters.
- JSON and CSV data formats.

**Official Resources:**
- [NASA POWER Portal](https://power.larc.nasa.gov/)
- [Daily API Documentation](https://power.larc.nasa.gov/docs/services/api/temporal/daily/)
- [NASA POWER Parameter Dictionary](https://power.larc.nasa.gov/docs/tutorials/parameters/)

### 2. ISRIC SoilGrids — Soil Data

**Provider:** ISRIC – World Soil Information  
**Dataset:** SoilGrids Global Soil Information  
**Data Repository:** https://files.isric.org/soilgrids/latest/  
**Official Website:** https://www.isric.org/explore/soilgrids

AgriCycle uses soil-related data from **ISRIC SoilGrids**, a global soil information system that provides machine-learning-based predictions of soil properties.

SoilGrids provides global soil property maps at approximately **250 m spatial resolution**, across six standard depth intervals. However, for simplicity we use 30-60 cm.

Available soil properties include:

- Soil pH
- Soil organic carbon
- Sand, silt, and clay content
- Bulk density
- Total nitrogen
- Water retained at different pressure. (wv0010, wv0033, wv1500)

**Data Preprocessing**

Within AgriCycle's preprocessing pipeline, soil data is processed by:

- Converting soil measurement (`Value`) and depth (`Depth`) columns into numeric formats.
- Removing duplicate records.
- Preparing the data for subsequent processing.

**Data License:** Creative Commons Attribution 4.0 International (CC BY 4.0).

**Attribution:** SoilGrids data is provided by ISRIC – World Soil Information. Please refer to the official SoilGrids documentation and license for attribution requirements.

### 3. NASA AppEEARS — MODIS Vegetation Data

**API:** https://appeears.earthdatacloud.nasa.gov/api  
**MODIS Product:** `MOD13Q1.061`  
**End Date:** `2025-12-12`

AgriCycle retrieves MODIS vegetation data through NASA AppEEARS, using the following layers:

- `250m_16_days_NDVI` — Normalized Difference Vegetation Index
- `250m_16_days_EVI` — Enhanced Vegetation Index
- `250m_16_days_pixel_reliability` — Pixel reliability information
- `250m_16_days_VI_Quality` — Vegetation Index quality information

These datasets provide vegetation-index observations at 250 m resolution every 16 days, supporting vegetation monitoring and crop analysis.

### 4. GeoJSON — Nepal Boundary Check

**Data Source:** [World Countries GeoJSON](https://datahub.io/core/geo-boundaries-world-110m/_r/-/countries.geojson)

AgriCycle uses GeoJSON country boundary data to perform a **Nepal boundary check**, verifying whether the user's geographic coordinates (latitude and longitude) fall within Nepal's national boundaries. This ensures location-based analysis is limited to the project's target country.

### 5. Open-Meteo — Elevation and Terrain Classification

**API:** https://api.open-meteo.com/v1/elevation

AgriCycle uses the Open-Meteo Elevation API to retrieve elevation data for a given latitude and longitude and classify the terrain into three categories:

| Elevation | Terrain |
|---|---|
| Below 1,000 m | Terai |
| 1,000–1,999 m | Hill |
| 2,000 m and above | Mountain |

This classification helps identify the terrain category associated with a selected geographic location.

### 6. Research Paper — Nepal Crop and Terrain Data

**Source:** [Diversified Crop Rotation: An Approach for Sustainable Agriculture Production (2021)](https://onlinelibrary.wiley.com/doi/10.1155/2021/8924087)

AgriCycle uses the crop rotation examples in Section 3 of this research paper as a reference to prepare a structured CSV dataset of crops and their corresponding terrain categories, such as **Terai, Hill, and Mountain**.

This CSV serves as a reference for identifying crops suitable for different geographical regions of Nepal during crop selection and rotation planning.

### 7. FAO — Nepal Crop Calendar Data

**Source:** [FAO Crop Calendar](https://cropcalendar.review.fao.org/#/home)

AgriCycle uses FAO's Crop Calendar platform to obtain available crop calendar information for Nepal, supporting crop planting and harvesting schedules and seasonal crop rotation planning.

### 8. FAO — Approximate Crop Rooting Depths

**Source:** [FAO — Annex 3: Rooting Depth](https://www.fao.org/4/y5749e/y5749e0j.htm)

AgriCycle uses FAO reference data to obtain approximate rooting depths for different crops. These values help characterize crop root systems and support soil-water availability analysis.

### 8. FAO EcoCrop — Crop pH Requirements

**Source:** [FAO EcoCrop Crop Database](https://ecocrop.apps.fao.org/ecocrop/srv/en/cropFindForm)

AgriCycle uses the FAO EcoCrop database to obtain the preferred soil pH ranges for different crops. This information helps assess whether the soil pH at a selected location is suitable for the corresponding crops during crop selection and rotation planning.

### 9. YouTube — Crop Rotation Research and Brainstorming

**Resource:** [Crop Rotation – YouTube Video](https://www.youtube.com/watch?v=ahfrgVNCUjc&list=PLPFdktLEPx4c&index=1)

This video was used as an educational and brainstorming resource to understand crop rotation concepts and explore ideas for AgriCycle's crop rotation planning approach.

### 10. Leaflet & OpenStreetMap — Interactive Maps and Location Selection

**Source:** [Leaflet](https://leafletjs.com/) | [OpenStreetMap](https://www.openstreetmap.org/)

AgriCycle uses the Leaflet JavaScript library to display interactive maps powered by OpenStreetMap data. This allows users to explore geographical locations, select a location on the map, and obtain its latitude and longitude coordinates for location-based agricultural analysis.

**Attribution:** © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright).

## Technology stack

| Category | Technology |
|---|---|
| Backend Framework | FastAPI |
| Frontend Framework | React |
| Programming Language | Python |
| Data Processing | Pandas, numpy, rasterio, geopandas |
| Data Exploration and Prototyping | Jupyter Notebook |
| API Architecture | REST API |
| Version Control | Git and GitHub |
| Interactive Maps | Leaflet |
| Map Data | OpenStreetMap |

## System Architecture

AgriCycle follows a modular architecture consisting of three main components: Frontend, Backend, and Crop Rotation Engine.

### 1. Backend — FastAPI

The backend acts as the communication layer between the frontend and the crop rotation engine.

Built using FastAPI, it is responsible for:
- Exposing REST API endpoints.
- Receiving and validating user requests.
- Managing data access through repositories.
- Invoking the crop rotation engine.
- Returning structured recommendation results to the frontend.

The engine contains the core logic responsible for generating, validating, scoring, and ranking crop rotation combinations.

Its main modules include:

- **Data Loader:** Loads crop, crop calendar, weather, and soil datasets.
- **Preprocessing:** Cleans datasets, normalizes crop names, and prepares numerical and date values.
- **Crop Selection:** Handles crop eligibility and selection criteria.
- **Rotation Strategy:** Generates possible crop sequences based on crop durations and growing-season constraints.
- **Rotation Validator:** Checks crop sequences against rotation constraints.
- **Scoring:** Calculates weighted scores based on farmer priorities, including profitability, food security, soil health, water saving, and low risk.
- **Top-K Selector:** Returns the highest-ranked crop rotation recommendations.

### 2. Frontend — React

The frontend acts as the user-facing interface of AgriCycle, allowing farmers to interact with the crop rotation planning system, provide location and farming preferences, and explore the generated crop rotation recommendations.

Built using **React.js and JavaScript**, the frontend is designed to provide a simple, accessible, and interactive experience for farmers.

Its main responsibilities include:

- Providing an interface for farmers to configure crop rotation planning parameters.
- Allowing users to select geographical locations through an interactive map.
- Collecting location details and farmer-defined farming priorities.
- Communicating with the FastAPI backend through REST API requests.
- Displaying recommendation job statuses and data-source retrieval progress.
- Presenting ranked crop rotation recommendations returned by the backend.
- Allowing users to compare alternative crop rotation sequences and their evaluation scores.

The frontend uses the following technologies:

- **React.js:** Builds the user interface using reusable components.
- **JavaScript:** Handles application logic and user interactions.
- **React DOM:** Renders React components into the web application.
- **React Router DOM:** Manages application navigation and routing.
- **Leaflet:** Provides interactive map functionality for geographical location selection.
- **React Leaflet:** Integrates Leaflet maps and map components into the React application.
- **React Scripts:** Provides development and build tooling for the React application.

### Frontend Workflow

1. The farmer opens the AgriCycle web application.
2. The farmer selects a geographical location using the interactive map.
3. The farmer provides the required farming parameters and preference weights.
4. The frontend sends the recommendation request to the FastAPI backend.
5. The frontend displays the recommendation job status while the backend processes the request.
6. Once processing is complete, the frontend retrieves the generated recommendations.
7. The farmer explores and compares the ranked crop rotation alternatives.

**Development Status:** The frontend is currently under development. The technologies and workflow described above represent the frontend architecture and intended user experience; not all planned interface features are necessarily implemented yet.

### 3. Architecture Workflow

1. The farmer provides location details and farming preferences through the frontend.
2. The frontend sends the request to the FastAPI backend.
3. The backend validates the request and accesses the required data.
4. The crop rotation engine processes the available data and generates candidate rotations.
5. Invalid rotations are filtered out.
6. Valid rotations are scored according to farmer priorities.
7. The Top-K selector identifies the highest-ranked rotations.
8. The backend returns the results to the frontend for presentation.

## Installation & Setup

Follow these steps to run AgriCycle locally.

### Clone the Repository

```bash
git clone https://github.com/LINSANITY03/Team-Sunya
cd backend
```

### Install project dependencies and create the virtual environment

```
uv sync
```

### Point the cd to main.py

```
uv run fastapi dev main.py
```

for the frontend

```
cd frontend
npm install
npm
```
### API access should be under these endpoint.
```
API: http://127.0.0.1:8000
Swagger UI: http://127.0.0.1:8000/docs
ReDoc: http://127.0.0.1:8000/redoc
```

## API Documentation

AgriCycle provides REST API endpoints built with **FastAPI** to support location-based crop rotation recommendations.

### Available Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/rotations/recommend` | Submit a location and initiate a crop rotation recommendation job. |
| GET | `/rotations/{recommendation_id}` | Retrieve recommendation job status, data-source statuses, and generated recommendations. |
| GET | `/rotations/` | Retrieve paginated recommendation jobs and their results. |
| GET | `/health/` | Check whether the API is running. |
| GET | `/` | Root endpoint. |

### 1. Submit Crop Rotation Recommendation

**Endpoint:** `POST /rotations/recommend`

Accepts geographical coordinates, validates the request, creates a recommendation job, and schedules external data retrieval in the background.

**Request Body:**

\`\`\`json
{
  "field_id": "field_001",
  "latitude": 29.382175,
  "longitude": 81.870117,
  "irrigation": false,
  "bd_reject": 1.75,
  "clay_max_root_crops": 55,
  "min_soil_depth_ratio": 0.5,
  "min_wet_high": 0.55,
  "min_wet_low": 0.25,
  "n_ok_g_per_kg": 2,
  "rain_eff": 0.8,
  "water_reject_ratio": 0.2,
  "cyclic": true,
  "default_family_gap": 2,
  "harvest_mismatch_tol_days": 20,
  "max_candidates": 50000,
  "max_fallow_days": 120,
  "max_horizon_days": 800,
  "max_single_crop_days": 300,
  "require_legume": false,
  "rotation_length": 3,
  "start_date": "2026-11-01",
  "turnaround_days": 10,
  "food_security": 0.15,
  "low_risk": 0.3,
  "profit": 0.5,
  "soil_health": 0.15,
  "water_saving": 0.15
}
\`\`\`

**Optional Query Parameter:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `d_recommendation_id` | UUID | No | Optional recommendation identifier. |

**Response:** `202 Accepted`

### 2. Get Recommendation Status

**Endpoint:** `GET /rotations/{recommendation_id}`

Retrieves:
- Recommendation job status.
- External data-source retrieval statuses.
- Generated crop rotation recommendations.

**Path Parameter:**

| Parameter | Type | Required |
|---|---|---|
| `recommendation_id` | String | Yes |

**Response:** `200 OK`

### 3. Get All Recommendation Jobs

**Endpoint:** `GET /rotations/`

Returns paginated recommendation jobs and their results.

**Query Parameters:**

| Parameter | Type | Default | Constraints |
|---|---|---|---|
| `page` | Integer | 1 | Minimum: 1 |
| `limit` | Integer | 10 | 1–100 |

**Response:** `200 OK`

### 4. Health Check

**Endpoint:** `GET /health/`

Checks whether the AgriCycle API is running.

**Response:** `200 OK`

### 5. Root Endpoint

**Endpoint:** `GET /`

Provides the root API endpoint.

**Response:** `200 OK`

### Interactive API Documentation

AgriCycle uses FastAPI's automatically generated API documentation.

Once the backend is running, access:

- **Swagger UI:** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc
- **OpenAPI Schema:** http://127.0.0.1:8000/openapi.json

### Validation Errors

The API returns `422 Unprocessable Entity` when request parameters or request-body data fail validation.

## Example Usage

AgriCycle generates crop rotation recommendations based on geographical location and available agricultural data.

### 1. Submit a Recommendation Request

Send a POST request with the selected location's latitude and longitude.

**Request:**

```bash
curl -X POST "http://127.0.0.1:8000/rotations/recommend" \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 27.676546,
    "longitude": 84.463889
  }'
```

**Response**

```bash
{
  "status": "accepted",
  "message": "Recommendation request accepted for processing.",
  "recommendation_id": "bd1b15f2-1358-43f6-b0f3-99a9cb0d6180",
  "job_status": "PENDING"
}
```

### 2. Retrieve Recommendation Results

Send a GET request with the recommendation_id.

**Request:**

```bash
curl -X 'GET' \
  'http://localhost:8000/rotations/6d333e32-b44a-4b8a-8366-13b76e284389' \
  -H 'accept: */*'
```

**Response**

```bash
{
  "recommendation_id": "6d333e32-b44a-4b8a-8366-13b76e284389",
  "status": "COMPLETED",
  "location": {
    "latitude": 27.676546,
    "longitude": 84.463889
  },
  "data_sources": {
    "ELEVATION": {
      "status": "SUCCESS",
      "error_message": null,
      "data_available": true
    },
    "MODIS": {
      "status": "SUCCESS",
      "error_message": null,
      "data_available": true
    },
    "NASA_POWER": {
      "status": "SUCCESS",
      "error_message": null,
      "data_available": true
    },
    "SOILGRIDS": {
      "status": "SUCCESS",
      "error_message": null,
      "data_available": true
    }
  },
  "error_message": null,
  "created_at": "2026-11-15T11:20:51.356279",
  "updated_at": "2026-11-15T14:28:27.224742",
  "results": [
    {
      "rank": 1,
      "score": 0.771,
      "sequence": "Rice > Mungbean > Mustard",
      "rotation_data": {
        "rank": 1,
        "sequence": "Rice > Mungbean > Mustard",
        "score": 0.771,
        "soil_fit": 0.97,
        "water_fit": 0.42,
        "timing": 0.89,
        "rotation_health": 0.8,
        "ndvi_support": 0.86,
        "profit": 1,
        "food": 0.67,
        "total_days": 303,
        "fallow_days": 13,
        "warnings": "",
        "events": [
          {
            "crop": "Rice",
            "sow": "2026-03-01",
            "harvest": "2026-06-29",
            "fallow_d": 0,
            "calendar_idx": 272,
            "water_ratio": 0.21174176892013427,
            "demand_mm": 2155.0609014678575,
            "water_mode": "water_balance",
            "ndvi": 0.6619216977083321
          },
          {
            "crop": "Mungbean",
            "sow": "2026-07-09",
            "harvest": "2026-09-22",
            "fallow_d": 0,
            "calendar_idx": 40,
            "water_ratio": 0.8393062441474067,
            "demand_mm": 931.8622386159477,
            "water_mode": "water_balance",
            "ndvi": 0.8656706777778406
          },
          {
            "crop": "Mustard",
            "sow": "2026-10-15",
            "harvest": "2026-12-29",
            "fallow_d": 13,
            "calendar_idx": 197,
            "water_ratio": 0.20406136567726965,
            "demand_mm": 716.3624615422256,
            "water_mode": "water_balance",
            "ndvi": 0.7726505722506893
          }
        ]
    }
```

### 3. Retreive all Recommendation jobs

Return paginated recommendation jobs and their results.

**Request:**

```bash
curl -X 'GET' \
  'http://localhost:8000/rotations/?page=1&limit=2' \
  -H 'accept: */*'
```

**Response**

```bash
{
  "total": 5,
  "page": 1,
  "limit": 2,
  "total_pages": 3,
  "returned": 2,
  "recommendations": [
    {
      "recommendation_id": "bd1b15f2-1358-43f6-b0f3-99a9cb0d6180",
      "status": "PENDING",
      "location": {
        "latitude": 27.676546,
        "longitude": 84.463889
      },
      "created_at": "2026-11-15T17:04:32.164942",
      "updated_at": "2026-11-15T17:04:32.164947",
      "error_message": null,
      "data_sources": {
        "ELEVATION": {
          "status": "PENDING",
          "data_available": false,
          "error_message": null
        },
        "MODIS": {
          "status": "PENDING",
          "data_available": false,
          "error_message": null
        },
        "NASA_POWER": {
          "status": "PENDING",
          "data_available": false,
          "error_message": null
        },
        "SOILGRIDS": {
          "status": "PENDING",
          "data_available": false,
          "error_message": null
        }
      }
    },
    {
      "recommendation_id": "6d333e32-b44a-4b8a-8366-13b76e284389",
      "status": "COMPLETED",
      "location": {
        "latitude": 27.676546,
        "longitude": 84.463889
      },
      "created_at": "2026-11-15T11:20:51.356279",
      "updated_at": "2026-11-15T14:28:27.224742",
      "error_message": null,
      "data_sources": {
        "ELEVATION": {
          "status": "SUCCESS",
          "data_available": true,
          "error_message": null
        },
        "MODIS": {
          "status": "SUCCESS",
          "data_available": true,
          "error_message": null
        },
        "NASA_POWER": {
          "status": "SUCCESS",
          "data_available": true,
          "error_message": null
        },
        "SOILGRIDS": {
          "status": "SUCCESS",
          "data_available": true,
          "error_message": null
        }
      }
    }
  ]
}
```

## Project Structure

AgriCycle is organized into separate modules to keep the API, recommendation engine, data access, and configuration easy to maintain.

```text
backend/
│
├── src/
│   ├── main.py                 # FastAPI application entry point
│   ├── core/                 # API endpoints
│   │   ├── config.py           # Application configuration    
│   │
│   ├── api/  
│   │   └── routes.py            # API endpoints 
│   │       ├── health.py         
│   │       ├── rotations.py    
│   │
│   ├── database/                # sqlite connection
│   │   ├── health.py         
│   │   ├── rotations.py    
│   │
│   ├── repositories/            # Data access and retrieval
│   │   └── crop_repository.py
│   │
│   └── engine/                 # Crop rotation recommendation logic
│       ├── config.py
│       ├── data_loader.py
│       ├── farmer_priorities.py
│       ├── field_profile.py
│       ├── rotation_strategy.py
│       ├── preprocessing.py
│       ├── rotation_strategy.py
│       └── site.py
│
├── data/                       # Agricultural datasets
├── notebooks/                  # Data exploration and experiments
│
├── .env.example                # Example environment variables
│   # outtside the root folder
├── pyproject.toml              # Project dependencies and settings
├── uv.lock                     # Locked dependency versions
└── README.md                   # Project documentation
```

```
frontend/
│
├── public/                     # Static assets and public files
│
├── src/
│   ├── components/             # Reusable UI components
│   │
│   ├── pages/                  # Application pages
│   │
│   ├── api.js                  # API requests to the FastAPI backend
│   │
│   ├── constants.js            # Farmer priorities, input defaults,
│   │
│   ├── App.js                  # Main application component
│   └── index.js                # Frontend entry point
│
├── .env.example                # Example environment variables
├── package.json                # Frontend dependencies and scripts
└── README.md                   # Frontend documentation
```

## Limitations & Future Improvements

### Current Limitations

- **Geographical Focus:** AgriCycle is currently designed for Nepal. Its crop datasets, terrain classifications, and agricultural references are based on Nepalese farming conditions. Although some of these crops may also be cultivated in other countries, the recommendations have not been validated for those regions. Applying AgriCycle elsewhere would require adapting its crop database, local growing calendars, climate and soil information, and regional agricultural requirements.

- **Limited Recommendation Factors:** The current rotation-generation process primarily considers crop growing durations and growing-season constraints. More environmental and agricultural factors need to be integrated into the recommendation process.

- **Weather and Soil Integration:** Weather and soil datasets are collected and preprocessed, but their full integration into crop rotation scoring and selection is still a work in progress.

- **Scoring Accuracy:** The recommendation system uses weighted criteria such as profitability, food security, soil health, water conservation, and risk. The current scoring system depends on supplied criterion scores and does not independently calculate actual farm profitability, crop yield, or resource consumption.

- **Data Availability and Accuracy:** External datasets may have different spatial resolutions, update frequencies, and levels of accuracy. Regional estimates may not fully represent conditions on an individual farm.

- **Frontend Development:** The user interface is still under development. The backend recommendation API is operational, but the complete farmer-facing experience is not yet finished.

### Future Improvements

- **Expand Geographical Coverage:** Extend AgriCycle to other countries and regions by incorporating local crop varieties, agricultural calendars, climate conditions, soil characteristics, and farming practices.

- **Improve Crop Suitability Assessment:** Integrate location-specific climate, elevation, soil properties, and crop requirements into crop selection.

- **Enhance Recommendation Scoring:** Develop more reliable scoring models using agricultural research, field data, and expert-validated criteria.

- **Economic Analysis:** Incorporate crop yields, market prices, production costs, and profitability estimates.

- **Water and Soil Assessment:** Improve water availability and soil health analysis to support more sustainable crop rotation planning.

- **Expand Agricultural Datasets:** Include more crop varieties and region-specific agricultural information.

- **Complete and Enhance the Frontend:** Develop interactive maps, recommendation dashboards, and crop rotation comparisons to improve the farmer experience.

- **Interactive Crop Rotation Visualization:** Introduce visual timelines and interactive diagrams to help farmers understand crop sequences, growing periods, harvest dates, fallow intervals, and transitions between crops. Allow users to explore and compare different rotation alternatives more intuitively.

- **Real-World Validation:** Collaborate with agricultural experts and farmers to evaluate and improve the recommendations using real-world farming data.

### Long-Term Vision

Our goal is to develop AgriCycle into a reliable, location-aware crop rotation planning tool that helps farmers explore suitable crop combinations and make more informed, sustainable farming decisions.

## Team & Acknowledgements

### Our Team

AgriCycle was developed by a team participating in the **NASA Space Apps Challenge 2026**.

| Team Member | Role | Contributions |
|---|---|---|
| Pujan Thing | Team lead | Full-stack |
| Suyog Giri | Frontend | UI/UX |

### Acknowledgements

We would like to thank the following organizations and resources for providing valuable data, research, and tools that contributed to the development of AgriCycle.

- **NASA POWER:** Meteorological and solar data.
- **NASA AppEEARS / MODIS:** Satellite-derived vegetation indices.
- **ISRIC SoilGrids:** Global soil property data.
- **Open-Meteo:** Elevation data.
- **FAO:** Crop calendar, crop characteristics, and rooting depth references.
- **FAO EcoCrop:** Crop soil pH requirement information.
- **World Countries GeoJSON:** Geographic boundary data used for Nepal location validation.
- **Research Publications:** Agricultural research used as a reference for Nepalese crop rotation and terrain information.
- **Leaflet:** JavaScript library used to display interactive maps and support geographic coordinate selection. Licensed under the BSD 2-Clause License.
- **OpenStreetMap Contributors:** Map data used in the frontend for displaying geographic locations and selecting coordinates. Licensed under the Open Database License (ODbL).

We also acknowledge the open-source community and the developers of the tools and libraries that made this project possible.

### Special Thanks

We appreciate the NASA Space Apps Challenge for providing an opportunity to explore real-world challenges through innovation, collaboration, and the use of open data.

## References & Licensing

AgriCycle uses publicly available datasets, APIs, research publications, and open-source resources. We acknowledge the original providers and their respective licensing terms.

| Source | Resource | License / Attribution |
|---|---|---|
| NASA POWER | Meteorological and solar data | NASA data usage and attribution guidelines |
| NASA AppEEARS / MODIS | Vegetation indices | NASA LP DAAC data use and citation guidelines |
| ISRIC SoilGrids | Soil property data | CC BY 4.0 |
| Open-Meteo | Elevation data | Open-Meteo terms of use |
| FAO | Crop calendar and agricultural references | Refer to individual FAO resource terms |
| FAO EcoCrop | Crop characteristics and pH requirements | Refer to FAO database terms |
| World Countries GeoJSON | Country boundary data | Refer to the source repository license |
| Research Publications | Nepal crop rotation references | Cite the original publications |
| Leaflet | Interactive mapping library | BSD 2-Clause License |
| OpenStreetMap | Map data and map tiles | Open Database License (ODbL) |

### Important Notice

- All external datasets and resources remain subject to their respective licenses and terms of use.
- Appropriate attribution should be given to the original data providers.
- AgriCycle is an independent project developed for the NASA Space Apps Challenge 2026.
- AgriCycle is not an official NASA product and is not endorsed by NASA.
