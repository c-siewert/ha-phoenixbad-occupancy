# Phoenixbad Occupancy for Home Assistant

This custom integration shows the live occupancy of the [Phoenixbad](https://phoenixbad.de/)
**indoor pool** (*Hallenbad*) and **sauna** in Home Assistant. It reads the same data the
website uses for its occupancy display, so you can check how busy it is before you go, or let
an automation tell you when the sauna gets quiet.

> [!NOTE]
> This is an unofficial integration. It is not affiliated with or supported by Phoenixbad.

<!-- ha-marketplace:exclude-start -->
## Installation

[![Open your Home Assistant instance and open a repository in the Marketplace.](https://my.home-assistant.io/badges/marketplace_repository.svg)](https://my.home-assistant.io/redirect/marketplace_repository/?owner=c-siewert&repository=ha-phoenixbad-occupancy&category=integration)

The button opens this repository in the **Marketplace** (Home Assistant 2026.11 and later)
or in HACS (earlier versions). If the repository isn't in the catalog yet, Home Assistant
offers to add it as a custom repository first. Then download it.

<details>
<summary>Manual steps with HACS (before Home Assistant 2026.11)</summary>

1. In Home Assistant, open **HACS**.
2. In the top right corner, select the three dots ⋮, then **Custom repositories**.
3. Enter `https://github.com/c-siewert/ha-phoenixbad-occupancy`, select the type **Integration**,
   and select **Add**.
4. Search for **Phoenixbad**, open it, and select **Download**.
5. Restart Home Assistant.

</details>

<details>
<summary>Manual installation without a store</summary>

1. Download the latest release from the
   [releases page](https://github.com/c-siewert/ha-phoenixbad-occupancy/releases).
2. Copy the folder `custom_components/phoenixbad` into the `custom_components` folder of your
   Home Assistant configuration directory (create it if it doesn't exist).
3. Restart Home Assistant.

</details>
<!-- ha-marketplace:exclude-end -->

## Configuration

To add the integration to your Home Assistant instance, use this My button:

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=phoenixbad)

<details>
<summary>Manual configuration steps</summary>

1. Go to **Settings** > **Devices & services**.
2. In the bottom right corner, select **Add integration**.
3. From the list, select **Phoenixbad**.
4. Select **Submit**.

</details>

Setup asks for nothing. It only checks that phoenixbad.de answers with occupancy data.
You can add the integration only once.

## Configuration options

To change the options, go to **Settings** > **Devices & services** > **Phoenixbad** and
select the cogwheel. The integration reloads when you save.

| Option | Default | Description |
|---|---|---|
| Pool: quiet below | 120 | The indoor pool counts as quiet below this many visitors. |
| Sauna: quiet below | 100 | The sauna counts as quiet below this many visitors. |

## Entities

The integration creates one device per area, **Phoenixbad indoor pool** and
**Phoenixbad sauna**. Each device has these entities:

| Entity | Example entity ID | Description |
|---|---|---|
| Visitors | `sensor.phoenixbad_indoor_pool_visitors` | People in the area right now. |
| Free spots | `sensor.phoenixbad_indoor_pool_free_spots` | Free spots as published by the website. |
| Occupancy | `sensor.phoenixbad_indoor_pool_occupancy` | Fill level in %. |
| Capacity | `sensor.phoenixbad_indoor_pool_capacity` | Diagnostic. Maximum number of visitors, see below. |
| Quiet | `binary_sensor.phoenixbad_indoor_pool_quiet` | On while visitors are below the quiet threshold. The attribute `threshold` shows the threshold. |

Home Assistant builds device names and entity IDs in the language your instance used when you
added the integration. With German as the language, for example, the device is called
**Phoenixbad Hallenbad** and the visitors sensor is `sensor.phoenixbad_hallenbad_besucher`.

### How visitors and capacity are calculated

The website publishes only the number of free spots and the fill level in %. The integration
derives the capacity from both, as `free spots / (1 − fill level)`, and calculates
`visitors = capacity − free spots`. Deriving the capacity on every update, instead of
hard-coding it, means a capacity change on the website doesn't silently skew the visitor
numbers.

The website rounds the fill level, and above about 90 % that rounding makes the derived
capacity too imprecise. Above 90 %, or when the website sends no fill level, the integration
keeps the last capacity it derived. Right after a restart it uses a default capacity of 695
for the pool and 300 for the sauna instead. The capacity sensor's attribute
`derived_from_website` is `false` while the capacity isn't derived from the current reading.

## Examples

### Get notified when the sauna is quiet

This automation sends a notification when the sauna gets quiet. Create a new automation,
select ⋮ > **Edit in YAML**, and paste:

```yaml
alias: Sauna is quiet
triggers:
  - trigger: state
    entity_id: binary_sensor.phoenixbad_sauna_quiet
    to: "on"
actions:
  # Replace with your own notify action, for example notify.mobile_app_<your_phone>.
  - action: notify.notify
    data:
      message: >-
        The sauna is quiet: {{ states('sensor.phoenixbad_sauna_visitors') }} visitors.
```

## Data updates

The integration polls phoenixbad.de every 10 minutes, with one request per area. If one area
can't be read, only that area's entities become unavailable, and the log shows one message
when it goes and one when it comes back.

### Custom update schedule

The interval is fixed to keep the load on the website low. To poll on your own schedule
instead, for example only while the bath is open:

1. Go to **Settings** > **Devices & services** and select **Phoenixbad**.
2. On the integration entry, select ⋮ > **System options**, turn off
   **Enable polling for changes**, and select **Update**.
3. Create an automation that updates one Phoenixbad entity. Updating one entity fetches the
   data for both areas.

The pool opens at 6:30 at the earliest (Tuesdays), and the sauna closes at midnight at the
latest (Fridays and Saturdays). This automation polls every 10 minutes in between:

```yaml
alias: Update Phoenixbad during opening hours
triggers:
  - trigger: time_pattern
    minutes: "/10"
conditions:
  - condition: time
    after: "06:30:00"
actions:
  - action: homeassistant.update_entity
    target:
      entity_id: sensor.phoenixbad_indoor_pool_visitors
```

Please don't poll more often than every 5 minutes. For more on this, see
[Defining a custom polling interval](https://www.home-assistant.io/common-tasks/general/#defining-a-custom-polling-interval).

## Known limitations

- The data comes from an internal endpoint of the website, not from a public API. If
  Phoenixbad changes its website, the integration can stop working until it is updated.
- The integration needs internet access. It doesn't work during a website outage.
- Above 90 % occupancy, the capacity isn't derived from the current reading (see
  [How visitors and capacity are calculated](#how-visitors-and-capacity-are-calculated)).
  If the website changes its capacity while it is that full, the visitor count is off until
  the fill level drops below 90 % again.

## Troubleshooting

<details>
<summary>Setup fails with "phoenixbad.de answered, but without occupancy data"</summary>

The website answered, but not in the expected format. The website has probably changed.
Check the [issues](https://github.com/c-siewert/ha-phoenixbad-occupancy/issues) and open a new one if
nobody has reported it yet.

</details>

<details>
<summary>Entities are unavailable</summary>

Check that [phoenixbad.de](https://phoenixbad.de/) shows the occupancy in your browser.
If it does, turn on debug logging: go to **Settings** > **Devices & services** >
**Phoenixbad**, select ⋮ > **Enable debug logging**, wait for the next update, then turn it
off again. Home Assistant offers the log as a download. Attach it to a
[new issue](https://github.com/c-siewert/ha-phoenixbad-occupancy/issues).

</details>

## Removing the integration

1. Go to **Settings** > **Devices & services** and select **Phoenixbad**.
2. Select ⋮ > **Delete**.
3. To remove the files as well, uninstall the integration in the Marketplace or HACS, or
   delete the folder `custom_components/phoenixbad` and restart Home Assistant.

The integration stores nothing outside Home Assistant.

## Development

Requires Python 3.14, like current Home Assistant.

```bash
pip install -r requirements_test.txt
pytest
```

## License

MIT, see [LICENSE](LICENSE).

The integration icon is based on the `swim` icon from
[Material Design Icons](https://pictogrammers.com/library/mdi/icon/swim/) by Pictogrammers,
licensed under the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0).
