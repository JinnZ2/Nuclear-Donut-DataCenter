CONTROLLER OVERVIEW

Goal: Python + Arduino system for managing cooling modes based on temperature, humidity, sensor status, and time.

⸻

 SYSTEM ARCHITECTURE

 Controller Board:
	•	Arduino Uno (or Nano for compact build)
	•	12V Power input (buck converter to 5V for logic)

 Sensors:
	•	DS18B20 — 6x digital temp sensors
	•	DHT22 — for ambient humidity
	•	CurrentSensor (ACS712) — for load monitoring
	•	ThermalSpike switch (normally closed thermal fuse)

 Actuators:
	•	4x 40mm Fans — PWM control via N-channel MOSFETs
	•	Heating element — via relay (or solid-state relay)
	•	Emergency buzzer + LED (status indicator)

⸻

WIRING PLAN

 Power Wiring:

 12V Input →
 ├──> Buck Converter (5V logic)
 ├──> Fans (through MOSFETs)
 └──> Relay → Heating Element

 sensor Wiring:

 DS18B20: Digital (D2-D7) + shared pull-up resistor  
DHT22: Digital pin D8  
ACS712: Analog A0  
Thermal Spike: Digital pin D9 (input w/ pull-down)  

Output Wiring:

Fan 1 → D10 (PWM via MOSFET)
Fan 2 → D11  
Fan 3 → D3  
Fan 4 → D5  
Relay → D6  
Buzzer/LED → D12  

Python like andyino controller (sim code)

// Mode Logic Trigger Definitions
enum Mode { IDLE, PULSE, EVAP, GEO, MAX, ADAPTIVE, EMERGENCY };
Mode currentMode = IDLE;

void updateMode() {
  float temp = readAverageTemp();
  float humidity = readHumidity();
  bool spike = digitalRead(THERMAL_SPIKE_PIN) == HIGH;

  if (spike) currentMode = EMERGENCY;
  else if (temp > 80 && humidity > 40) currentMode = EVAP;
  else if (temp > 85) currentMode = MAX;
  else if (temp > 60 && humidity < 20) currentMode = GEO;
  else if (temp > 40) currentMode = PULSE;
  else currentMode = IDLE;
}

// Fan Control Patterns
void applyFanPattern(Mode m) {
  switch (m) {
    case IDLE:
      setAllFans(0);
      break;
    case PULSE:
      pulseFansRhythmically();
      break;
    case EVAP:
      setAllFans(200);
      break;
    case GEO:
      fanVentCycle(150);
      break;
    case MAX:
      setAllFans(255);
      break;
    case ADAPTIVE:
      smartControl();
      break;
    case EMERGENCY:
      setAllFans(255);
      buzzAlert();
      break;
  }
}

void loop() {
  updateMode();
  applyFanPattern(currentMode);
  delay(500);
}


mode summary:


idle()           → low temp, nighttime, no load
pulse_cooling()  → rhythmic fan pulses (respiration)
evaporative()    → high humidity + heat → termite logic
geothermal()     → dry + heat → moist coil circulation
max_cooling()    → spike or overload
adaptive()       → blend of sensor logic
emergency()      → hibernate or shut down

( not perfect- made on notes on cellphone)

 
