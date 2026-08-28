# EDEEste MQTT for Home Assistant

HACS custom integration that reads electricity consumption from EDEEste Oficina Virtual and publishes it to your Home Assistant MQTT broker. It publishes retained MQTT Discovery configuration and states for current, projected, and previous monthly consumption (kWh), plus consumption days. Data refreshes hourly.

> **Disclaimer:** This project was written with assistance from artificial intelligence. Review the code and test it in your environment before relying on it for production use.

> **EDEEste disclaimer:** This is an independent, unofficial project and is not affiliated with, endorsed by, or supported by EDEEste. You are responsible for ensuring that your use complies with EDEEste's applicable terms and policies. Do not use it to circumvent access controls or access accounts other than your own.

## Install

1. In HACS, open **Integrations**, choose the overflow menu, then **Custom repositories**.
2. Add this repository, select category **Integration**, then search for and install **EDEEste MQTT**.
3. Restart Home Assistant.
4. Configure the [MQTT integration](https://www.home-assistant.io/integrations/mqtt/) with your broker; MQTT Discovery must be enabled (it is enabled by default).
5. In Home Assistant, add **EDEEste** under **Settings → Devices & services**.
6. Enter the email and password for your [Oficina Virtual EDEEste](https://oficinavirtual.edeeste.com.do/) account and select your discovery prefix (normally `homeassistant`).

The integration logs in at every Home Assistant restart, holds its own EDEEste session, and logs in again automatically when that session expires. Your account credentials are stored in Home Assistant's configuration entry; use the integration's **Configure** menu to change them.

## MQTT topics

With the default discovery prefix, retained messages are published below `homeassistant/sensor/edeeste_<entry-id>/...`. Each sensor gets a Discovery `config` topic, plus `state` and `attributes` topics, so entities are created automatically by Home Assistant's MQTT integration.

## Verify before installing

From the repository root, run:

```bash
python3 scripts/verify_edeeste.py
```

It prompts for your EDEEste email and password without echoing the password, performs the same login sequence as the integration, then prints the account NIC and consumption values. A successful result confirms the EDEEste authentication and data endpoint work; MQTT publication is then handled by Home Assistant's configured MQTT integration.

## Notes

- This integration submits the EDEEste ASP.NET login form before it calls the authenticated endpoint observed in the supplied HAR: `GET /Default.aspx/GetDetalle`.
- Never commit HAR files or session cookies. If a HAR with a live cookie has been shared, sign out of Oficina Virtual (or otherwise revoke the session) before publishing the repository.
- This project is licensed under the [MIT License](LICENSE).
