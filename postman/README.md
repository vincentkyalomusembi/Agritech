# Postman API tests

Import the collection and environment into Postman to verify the external API keys used by Agritech.

## Files
- `Agritech_API_Tests.postman_collection.json`
- `Agritech_API_Tests.postman_environment.json`

## How to use
1. Open Postman.
2. Import the collection JSON.
3. Import the environment JSON.
4. Open the environment and fill in:
   - `openweather_api_key`
   - `gemini_api_key`
5. Select the environment before sending requests.

## Requests
- **OpenWeather - Test Key**
  - Sends a weather lookup for `{{weather_city}}`
  - Success usually returns `200 OK` with weather data

- **Gemini - Test Key**
  - Sends a short prompt to Gemini using `{{gemini_model}}`
  - Success usually returns `200 OK` with generated text

## Gemini model
- Default: `gemini-2.5-flash`
- If that model is unavailable for your key or region, try another supported text model from the Gemini models page.

## Notes
- The Gemini request uses the Google Generative Language REST endpoint.
- If a key is invalid, you will usually get `401` or `403`.
- If the quota is exceeded, you may get `429`.
