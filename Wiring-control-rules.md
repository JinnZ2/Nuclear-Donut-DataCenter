Nuclear Donut Cooling Controller: Mode Logic and Inspiration

⸻

idle()
Inspired by: Night cycle
Trigger: Low load + low temperature

pulse_cooling()
Inspired by: Respiratory rhythm
Trigger: Moderate thermal load + no emergency

evaporative()
Inspired by: Termite mound thermal convection
Trigger: High heat + available steam for cooling

geothermal()
Inspired by: Root absorption and subsurface circulation
Trigger: Dry environment + moderate temperature buildup

max_cooling()
Inspired by: Fight-or-flight biological response
Trigger: Emergency: core temp or load is critical

adaptive()
Inspired by: Homeostasis AI and integrated sensing
Trigger: Multi-sensor logic fusion across temperature, humidity, and load

emergency()
Inspired by: Hibernate/freeze survival mode
Trigger: Sensor failure, thermal spike, or unresponsive systems

⸻

Power Supply and Wiring Guide (Quick Copy-Paste Format)
	•	Main Power Input:
	•	12V DC 10A regulated supply for fans, controller board, and sensors
	•	Fuse: Inline 10A blade fuse near input
	•	Microcontroller:
	•	Arduino Uno or Raspberry Pi 4 (with GPIO breakout)
	•	Powered via 5V rail from buck converter or onboard supply
	•	Fan Wiring:
	•	Core zone fans: 4x 12V fans, each on PWM-capable pins via MOSFET
	•	Outer zone fans: Same, separate zone
	•	Ground all fans to system GND rail
	•	Use flyback diodes across MOSFETs for protection
	•	Sensor Wiring:
	•	DS18B20 temperature sensors: digital pin (with 4.7kΩ pull-up), 3.3–5V Vcc, GND
	•	Humidity sensor (DHT22 or similar): digital input pin
	•	Steam pressure: analog input via voltage divider (0-5V) or I2C if digital
	•	Energy load (ACS712 or INA219): I2C/analog connection, connected to load circuit
	•	Valve/Pump Control (Steam + Geothermal):
	•	Solenoid valves powered by 12V through N-channel MOSFETs
	•	Control line from digital pin (with 220Ω inline resistor)
	•	Use flyback diodes across valve terminals
	•	Emergency Relay:
	•	NC (normally closed) relay triggered from digital pin
	•	Disconnects heat source if emergency triggered
	•	Optional: LED status indicators and manual override switch
