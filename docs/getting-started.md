# Getting Started

If not already done, the very first step to use `nolito` is to follow the [installation guide](installation.md).

## Configuring the Nolio API

Once `nolito` is installed, you will need to set up the application to use the Nolio API.
Follow the instructions on the [Nolio website API page](https://www.nolio.io/developers/)
and the [Nolio API portal](https://www.nolio.io/api/quickstart/) to do so.

Once you have configured the API, go to the "Applications" section and copy your client ID and secret to the `NOLIO_CLIENT_ID` and `NOLIO_CLIENT_SECRET` environment variables, respectively.

This can be configured in your `~/.bashrc` or `~/.zshrc` file:

```bash
export NOLIO_CLIENT_ID="your_client_id"
export NOLIO_CLIENT_SECRET="your_client_secret"
```

Once this is done, reload your shell (exit and re-open the terminal).

## First connection to the API

<!-- TODO: NolioApiClient hyperlink -->
When connecting to the API for the first time, you will need to authenticate `nolito` with the Nolio API.
You will be automatically prompted to do this when creating a `NolioApiClient` object:

```python
client = NolioApiClient()
```

The authentication should store a token in your system's keyring,
meaning that you will not need to do this again after the first connection.

## Common operations

Once we have a working `NolioApiClient` object (`client` above), we can use it to interact with the API.
The subsections below describe common operations that can be performed.

### Get athlete information

```python
client.get_athlete()
```

### Get athlete metrics

```python
client.get_metrics()
```

### Get trainings from the planned calendar

For the current day:

```python
client.get_daily_trainings()
```

For any day:

```python
client.get_daily_trainings(day="2026-07-15")
```

For a range of dates:

```python
client.get_planned_trainings(start="2026-07-28", end="2026-10-31")
```

### Get data from any API endpoint

The `NolioApiClient` offers a `get()` method to access any API endpoint and return its data as a dictionary or a list.
There is [a list of API endpoints](https://github.com/NolioApp/NolioAPI-Documentation/wiki/API-Routes)
on the [Nolio API wiki](https://github.com/NolioApp/NolioAPI-Documentation/wiki).

For example, do access the first 30 (default max limit) planned trainings, one can use:

```python
trainings = client.get("planned/training/")
```
