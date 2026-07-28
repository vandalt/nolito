# Nolio API scripts

Scripts for the [Nolio](www.nolio.io) API.

I only recently learned that Nolio had an API and decided to play with it.
I have a few ideas of things I want to implement once I get the API working:

- [ ] Have scripts to read training schedule or plan and modify them (this is my main motivation as I have to merge cycling and running plan and am being lazy about doing it by hand).
- [ ] Have script to retrieve training data and so some analysis.
- [ ] Be able to use an AI agent to generate training plans efficiently, but while being able to quickly vet and modify them.

## References

- [Nolio API docs on GitHub](https://github.com/NolioApp/NolioAPI-Documentation/)
- [Nolio masterclass on using the API with AI](https://www.youtube.com/watch?v=l3FcOUnYdhs)

## Nolito (OAuth + planned sessions today)

This repository now includes a minimal package in `src/nolito` with:

1. OAuth Authorization Code flow for Nolio.
2. Secure token storage (OS keyring + metadata file).
3. Refresh token rotation handling.
4. Retrieval of today's planned sessions for the token owner.

Client setup is now internal: creating `NolioApiClient()` will load env settings, initialize secure token storage, and handle OAuth/refresh automatically.

### Required environment variables

```bash
export NOLIO_CLIENT_ID="your_client_id"
export NOLIO_CLIENT_SECRET="your_client_secret"
```

Optional:

```bash
export NOLIO_REDIRECT_URI="http://127.0.0.1:8765/callback"  # default already set
export NOLIO_API_BASE_URL="https://www.nolio.io/api/"
```

### Run the integration script

```bash
pip install -e .
python sandbox/get_planned_sessions.py
```
