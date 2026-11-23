# daily-weather
Daily weather update images

Every morning at 8:00 AM Eastern, a GitHub Action (`.github/workflows/daily-weather.yml`) builds a US radar + forecast-high map from National Weather Service images, saves it in `images/`, and texts it with the safety message to the EZ Texting "Drivers" group.

- EZ Texting login lives in repo secrets `EZ_USER` and `EZ_PASS` (never in files).
- Test: Actions tab, "Daily weather text", "Run workflow", enter a phone number.
- Change the safety text by editing `safety-message.txt`.
- Road alerts (NWS winter/wind warnings on major interstates + Caltrans chain controls) come from `scripts/roads.py`, max 6 lines.
- Change the header (subject line) by editing `subject-line.txt`; leave it empty for no header.

## Twilio (replacing EZ Texting)

When the repository secrets `TWILIO_ACCOUNT_SID`, `TWILIO_API_KEY`, `TWILIO_API_SECRET` and
`TWILIO_FROM` (the Twilio number, e.g. +18581234567) are set, the daily text goes through Twilio
instead of EZ Texting. Drivers are listed in the `DRIVER_NUMBERS` secret, one per line as
`Name,8581234567`, so their numbers never appear in this public repository. If `REPORT_NUMBER` is set,
a summary ("WEATHER: 92 delivered, 2 failed (...), 1 opted out (...)") is texted there after each send.
