# AI-Powered Smart Irrigation System Using Machine Learning and IoT

College dashboard for second-year **Artificial Intelligence and Data Science**.  
It monitors soil and weather readings, trains three classic classifiers, and prepares **safe** ESP32 pump control. The app is fully usable **without hardware** in demo mode.

## What this app does

- Shows a modern Streamlit dashboard (soil moisture, temperatures, humidity, rainfall, pump state).
- Labels **demo simulation** separately from **ESP32 serial/Wi-Fi** data. It never pretends simulated values came from a sensor.
- Trains **Decision Tree**, **Random Forest**, and **Logistic Regression** on a validated CSV with a proper train/test split.
- Saves trained pipelines with **joblib**.
- Keeps the water pump **off** in demo mode. Manual start needs confirmation. Runtime, cooldown, and sensor-failure locks are enforced.

## Project structure

```
smart-irrigation-system/
  app.py                      # Dashboard
  pages/                      # Live, ML, data, performance, pump, settings
  src/                        # Processing, models, simulator, hardware, safety
  data/sample_sensor_data.csv # Labeled example dataset
  models/                     # joblib files appear here after training
  tests/
```

## Setup (Windows)

Use Python 3.10 or newer.

```powershell
cd C:\Users\Immanuvel\smart-irrigation-system
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks activation:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## Run the dashboard

```powershell
streamlit run app.py
```

Open the local URL Streamlit prints (usually http://localhost:8501).

## What to test

1. **Dashboard** — metric cards, moisture chart, recent table, connection = demo/disconnected.
2. **Live Monitoring** — Take reading; source stays `demo`. Auto-advance only in demo mode.
3. **Machine Learning** — Train on the bundled example CSV. Confirm metrics appear only after training succeeds.
4. **Sensor Data** — Search, download CSV, optional upload (invalid files must be rejected).
5. **Model Performance** — Empty until a real training run exists, then compare the three models.
6. **Pump Control** — Start stays disabled in demo mode even if you confirm.
7. **Settings** — Changing source to Serial/Wi-Fi must still show **not connected** until a device actually responds.

## Example dataset labeling

`data/sample_sensor_data.csv` is **example data**.  
`irrigation_required = 1` when soil moisture is below 35% and rainfall is under 1.5 mm.  
Scores on this file describe the example labels, not a farm trial.

## Hardware notes (later stages)

Budget kit: ESP32, capacitive soil moisture sensor, **relay module**, low-voltage DC mini pump.

- Do **not** drive the pump from an ESP32 GPIO pin.
- Power the pump from its own supply and switch it with the relay.
- The app will not send pump commands until Settings marks hardware as configured **and** a live connection succeeds.

Expected later telemetry (CSV line):

```
moisture,soil_temp,air_temp,humidity,rainfall
42.1,24.0,29.5,61.0,0.0
```

## Tests

```powershell
python -m pytest -q
```

## Team / constraints

- Budget: below ₹2,000  
- Duration: about 4 weeks  
- Users: farmers, students, agricultural researchers  

## Disclaimer

This is an academic demonstration. Irrigation advice from the demo rule or a model trained on example data is **not** agronomic certification.
