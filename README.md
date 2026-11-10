# daily-weather
Daily weather update images

Every morning at 8:00 AM Eastern, a GitHub Action (`.github/workflows/daily-weather.yml`) builds a US radar + forecast-high map from National Weather Service images, saves it in `images/`, and texts it with the safety message to the EZ Texting "Drivers" group.

- EZ Texting login lives in repo secrets `EZ_USER` and `EZ_PASS` (never in files).
- Test: Actions tab, "Daily weather text", "Run workflow", enter a phone number.
- Change the safety text in `scripts/send.py`.
