{% autoescape off %}# Flind app

> This is the Flind web app. Most pages need a login. Agents get better results from the API than from reading app pages.

- Do not crawl the app. Shared dashboards and shared links are private to the people who got them.
- After a person logs in, the app gives in-page tools through WebMCP. An agent in the browser can call them, so it does not need to click through the UI.

## Use Flind from an agent

- [Agent sign-up and authentication]({{ site_url }}/auth.md): Create an account or authenticate an existing user.
- [Personal API keys]({{ site_url }}/settings/user-api-keys): Create a key here. The REST API uses a personal API key.
{% endautoescape %}
