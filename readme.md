[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

![Project Maintenance](https://img.shields.io/badge/maintainer-Supergoudvis116-blue.svg?style=for-the-badge)

# Joule Cloud Connector

Custom component for Home Assistant. This component is designed to integrate the [Joule](https://jouleuk.co.uk/) systems with
Home Assistant to make your Joule device controllable from Home Assistant.

## Installation

You have two options for installation:

### HACS

#### Add HACS
- Setup HACS as described [here](https://hacs.xyz/docs/setup/download/)

#### Add the custom repository
- Go to the [HACS](https://hacs.xyz) panel
- Go to integrations
- Click on the 3 dots in the upper right corner
- Click on 'Custom repositories'
- Enter 'https://github.com/supergoudvis116/HA-Joule-connector'
- Select category 'Integration'
- Click Add
- Search for 'Joule Cloud Connector'
- Click 'Download'
- Restart your HomeAssistant server

#### Add the integration
- Click 'Settings'
- Click 'Devices & services'
- In the tab Integrations click on 'Add integration'
- Search for 'Joule Cloud Connector'

### Manually

#### Add the custom repository

- Copy "joule_connector" folder to the "/config/custom_components" folder
- Restart HA server

#### Add the integration
- See description above in section HACS

### WORKING ON:

- EVA TH250

###

Heavily inspired by [ojmicroline-thermostat](https://github.com/robbinjanssen/home-assistant-ojmicroline-thermostat)
Thank you for giving me a great starting point!
