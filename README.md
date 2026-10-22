# Genial T31 Thermometer for Home Assistant

*for jackie*

A local Bluetooth integration for the Genial T31 continuous body thermometer.
It connects directly from Home Assistant or an ESPHome Bluetooth proxy and
does not require the Tempal phone app, a cloud account, or a device key.

## Features

- Automatic Bluetooth discovery and UI setup
- Body-temperature updates every few seconds while the thermometer is active
- Five-to-fifteen-minute rolling baseline, rise, and rate-of-change sensors
- Auxiliary temperature, battery percentage, and battery voltage sensors
- Connection status, RSSI, and last-reading timestamp
- Automatic unworn disconnects to reduce unnecessary BLE activity
- Automatic reconnection when the device becomes available again
- Home Assistant Bluetooth proxy support
- Fully local operation
- Protocol frame and checksum validation

## Requirements

- Home Assistant 2024.12 or newer
- A working Home Assistant Bluetooth adapter or ESPHome Bluetooth proxy
- A Genial T31 advertising as `Genial-T31`

The thermometer cannot be connected to the Tempal app and Home Assistant at
the same time. Close Tempal or disconnect the thermometer there before adding
it to Home Assistant.

## Installation with HACS

### HACS custom repository (available now)

1. Open HACS in Home Assistant.
2. Select **Integrations**.
3. Open the three-dot menu and choose **Custom repositories**.
4. Enter this repository's GitHub URL and select **Integration**.
5. Find **Genial T31 Thermometer** in HACS and install it.
6. Restart Home Assistant.

The project has also been prepared for submission to HACS's default catalog.
After that submission is reviewed and accepted, users can skip the custom
repository steps and find **Genial T31 Thermometer** directly in HACS.

## Manual installation

1. Download the latest release ZIP.
2. Copy `custom_components/genial_t31` into Home Assistant's
   `config/custom_components` directory.
3. Confirm that the final path is
   `config/custom_components/genial_t31/manifest.json`.
4. Restart Home Assistant.

## Setup and use

1. Disconnect the T31 from the Tempal app.
2. Wake the thermometer and place it within Bluetooth range.
3. In Home Assistant, open **Settings → Devices & services**.
4. Home Assistant should show a discovered **Genial T31 Thermometer**. Select
   **Add**. You can also choose **Add integration** and search for
   **Genial T31 Thermometer**.
5. Select the discovered thermometer and finish setup.

No PIN, OOB code, account, or cloud login is required.

The integration creates these entities:

- **Body temperature**: the measurement displayed by the Tempal app
- **Auxiliary temperature**: the secondary temperature field reported by the
  thermometer; disabled by default
- **Temperature baseline**: median of readings from five to fifteen minutes
  ago; unavailable during initial warm-up
- **Temperature rise**: degrees Celsius above the rolling baseline
- **Temperature rate**: two-minute rate of change in degrees Celsius per minute
- **Battery**: the device-reported charge percentage
- **Battery voltage**: reported battery voltage; disabled by default
- **Signal strength**: Bluetooth RSSI; disabled by default
- **Last reading**: time of the most recent valid temperature report
- **Connected**: on only while the device is connected and sending fresh data
- **Worn**: confirmed from sustained temperature, with an unknown state during
  the initial wear check

The thermometer normally sends temperature reports every one to six seconds.
If no valid data arrives for 45 seconds, the integration marks it disconnected
and attempts to reconnect when it is seen again.

### Unworn power saving

When body temperature remains below 89°F (31.67°C) for ten continuous minutes,
the integration treats the thermometer as unworn and disconnects Bluetooth.
Automatic reconnects are suppressed for 15 minutes to reduce unnecessary BLE
activity. Home Assistant then reconnects briefly to check the probe:

- If it has warmed above 89°F, normal continuous monitoring resumes.
- If it remains below 89°F for one minute, Home Assistant disconnects again and
  begins another 15-minute sleep interval.

The ten-minute initial confirmation avoids disconnecting during ordinary
placement and warm-up. Brief dips are cancelled as soon as the reported
temperature returns above 89°F. The **Worn** entity exposes the confirmed state
for cards and automations.

Readings below 97°F are excluded from trend calculations. A baseline becomes
available after five minutes of continuous on-body readings. This warm-up gate
helps prevent an alert merely because a room-temperature probe was just put on.

## Dashboard card

The project includes a dashboard made entirely from built-in Home Assistant
cards, so no additional frontend package is required:

[`examples/dashboard-card.yaml`](examples/dashboard-card.yaml)

To add it:

1. Open the desired dashboard and select **Edit dashboard**.
2. Select **Add card → Manual**.
3. Paste the example YAML.
4. Replace its example entity IDs with the entities created on your system.

The example shows current temperature, battery, a one-hour temperature and
baseline graph, rise, rate of change, connection and worn states, and
last-reading time.

## Automation blueprints

Three reusable blueprints are included under
[`blueprints/automation/genial_t31`](blueprints/automation/genial_t31):

- **Sustained temperature alert** waits for a selected threshold and duration,
  runs user-selected notification actions, and applies a cooldown.
- **Rapid-rise fan or smart-plug response** waits for the five-minute baseline,
  confirms a configurable rate of rise and minimum body temperature, optionally
  notifies, runs selected fans or switches, turns them off, and applies a
  cooldown.
- **Stale or disconnected alert** waits through brief Bluetooth interruptions
  before running user-selected notification actions.

To import one after this project is on GitHub:

1. Open its YAML file on GitHub and copy the page URL.
2. In Home Assistant, open **Settings → Automations & scenes → Blueprints**.
3. Select **Import blueprint**, paste the GitHub URL, and import it.
4. Create an automation from the imported blueprint and select your entities,
   thresholds, targets, durations, and notification actions in the UI.

Numeric temperature defaults in the blueprints assume a Fahrenheit Home
Assistant installation. Celsius users should replace those defaults while
creating the automation. Rise and rate sensors deliberately remain in °C and
°C/min so temperature differences are not incorrectly treated as absolute
temperatures during unit conversion.

## Genial T31 versus Momcozy T31

The two products appear to share the same T31 hardware family, Bluetooth
service layout, packet framing, and core continuous-temperature behavior.
They are not interchangeable at the software level:

| | Genial T31 | Momcozy T31 |
|---|---|---|
| Local temperature data | Plaintext BLE frames | Encrypted BLE frames |
| Device/account key | Not required | Per-device OOB key required |
| Cloud account | Not required here | Normally needed to obtain the key |
| Home Assistant setup | Discover and add | Requires extracting/providing a key |
| Typical purchase cost | Often lower | Often higher due to branding/ecosystem |

For Home Assistant, the Genial model is recommended: it provides the same
practical continuous-temperature function, is commonly less expensive, and
its firmware offers a cleaner local protocol without account-bound telemetry
encryption. That makes installation, recovery, and long-term maintenance much
simpler. This recommendation concerns local smart-home use, not medical
certification or clinical accuracy.

## Troubleshooting

- **Device is not discovered:** wake it, move it closer to the Bluetooth
  adapter/proxy, and make sure Tempal is disconnected.
- **Connected is off:** check that temperature reports are changing. A BLE link
  without fresh valid telemetry is intentionally treated as disconnected.
- **Temperature is unavailable:** allow several seconds after connecting and
  ensure the probe is active.
- **Frequent disconnects:** add or reposition an ESPHome Bluetooth proxy.
- **Battery updates slowly:** the thermometer reports battery less frequently
  than temperature; the integration also requests it after initialization.

## Privacy and security

All operation is local. The integration contains no cloud endpoint, analytics,
account credential, captured device address, encryption key, or user-specific
configuration. Home Assistant stores the selected Bluetooth address in its own
configuration entry.

## Development

Run the protocol tests from the repository root:

```bash
python3 -m unittest discover -s tests -v
```

Contributions and reports from additional Genial T31 firmware revisions are
welcome. Please remove Bluetooth addresses and other personal information from
logs before publishing them.

## Disclaimer

This is an independent community project and is not affiliated with Genial,
Tempal, or Momcozy. It is intended for home automation and is not a substitute
for medical advice or a clinical monitoring system.

