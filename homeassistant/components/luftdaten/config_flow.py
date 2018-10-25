"""Config flow to configure the Luftdaten component."""
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_SCAN_INTERVAL, CONF_SHOW_ON_MAP
from homeassistant.core import callback
from homeassistant.helpers import aiohttp_client

from .const import CONF_SENSOR_ID, DEFAULT_SCAN_INTERVAL, DOMAIN


@callback
def configured_sensors(hass):
    """Return a set of configured Luftdaten sensors."""
    return set(
        '{0}'.format(entry.data[CONF_SENSOR_ID])
        for entry in hass.config_entries.async_entries(DOMAIN))


@config_entries.HANDLERS.register(DOMAIN)
class LuftDatenFlowHandler(config_entries.ConfigFlow):
    """Handle a Luftdaten config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    async def _show_form(self, errors=None):
        """Show the form to the user."""
        data_schema = vol.Schema({
            vol.Required(CONF_SENSOR_ID): str,
            vol.Optional(CONF_SHOW_ON_MAP): bool,
        })

        return self.async_show_form(
            step_id='user',
            data_schema=data_schema,
            errors=errors or {}
        )

    async def async_step_import(self, import_config):
        """Import a config entry from configuration.yaml."""
        return await self.async_step_user(import_config)

    async def async_step_user(self, user_input=None):
        """Handle the start of the config flow."""
        from luftdaten import Luftdaten, exceptions

        if not user_input:
            return await self._show_form()

        sensor_id = user_input[CONF_SENSOR_ID]

        if sensor_id in configured_sensors(self.hass):
            return await self._show_form({CONF_SENSOR_ID: 'sensor_exists'})

        session = aiohttp_client.async_get_clientsession(self.hass)
        luftdaten = Luftdaten(
            user_input[CONF_SENSOR_ID], self.hass.loop, session)
        try:
            await luftdaten.get_data()
            valid = await luftdaten.validate_sensor()
        except exceptions.LuftdatenConnectionError:
            return await self._show_form(
                {CONF_SENSOR_ID: 'communication_error'})

        if not valid:
            return await self._show_form({CONF_SENSOR_ID: 'invalid_sensor'})

        scan_interval = user_input.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        user_input.update({
            CONF_SCAN_INTERVAL: scan_interval.seconds,
            CONF_SENSOR_ID: sensor_id,
        })

        return self.async_create_entry(title=sensor_id, data=user_input)
