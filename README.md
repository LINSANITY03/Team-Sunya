# AgriCycle 🌱
### Smart Crop Rotation Planning

AgriCycle is a data-driven crop rotation planning application designed to help farmers explore and identify suitable crop sequences within a given growing season.

The application generates possible crop rotation combinations, evaluates them against growing-season constraints, and ranks the valid combinations based on configurable farming priorities.

AgriCycle considers multiple decision-making criteria, including:

- **Profitability:** Prioritizing potential economic returns.
- **Food Security:** Considering the importance of food production.
- **Soil Health:** Supporting sustainable soil management.
- **Water Conservation:** Considering water-saving priorities.
- **Risk Reduction:** Accounting for farming risk preferences.

By combining crop characteristics, growing durations, rotation constraints and farmer-defined priorities, AgriCycle aims to make crop rotation planning more structured, transparent and accessible.

The goal is to support informed agricultural planning and encourage more sustainable farming decisions through data-driven recommendations.

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

### 7. Frontend (In Development)
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

