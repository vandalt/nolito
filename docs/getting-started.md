# Getting Started

If not already done, the very first step to use `nolito` is to follow the [installation guide](installation.md).

(configuring-nolio-api)=
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

Optionally, you can also set `NOLIO_REDIRECT_URI` and `NOLIO_API_BASE_URL`.
They are shown below with the default values used by `nolito`:

```bash
export NOLIO_REDIRECT_URI="http://127.0.0.1:8765/callback"
export NOLIO_API_BASE_URL="https://www.nolio.io/api/"
```

Once this is done, reload your shell (exit and re-open the terminal).

## First connection to the API

When connecting to the API for the first time, you will need to authenticate `nolito` with the Nolio API.
You will be automatically prompted to do this when creating a
{py:class}`~nolito.client.NolioApiClient` object:

```python
client = NolioApiClient()
```

The authentication should store a token in your system's keyring,
meaning that you will not need to do this again after the first connection.
Nolio rotates refresh tokens on every refresh. If a refresh token has already
been consumed or revoked, Nolito removes it and starts the authorization flow
again.

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

### Create a training

`id_partner` identifies a training created by your application for later
updates or deletion. You can omit it when creating a `Training`: Nolito
allocates a monotonic local ID and sends it to Nolio.

```python
from nolito.training import Training

created = client.create_training(
    Training(
        sport_id=2,
        name="Intervals",
        date_start="2026-08-07",
    )
)
```

After Nolio creates the training, Nolito stores its `id_partner` in
`~/.config/nolito/partner-ids.sqlite3` (or beside the configured token metadata
file). Keep this database to update or delete trainings created by the same
OAuth application. Nolio may include `nolio_id` in a response; Nolito records
it when present, but `id_partner` is the identifier used for updates and
deletes. Explicit `id_partner` values are also supported and are stored in the
same registry.

### Manage registered trainings

The local registry can also store a complete training snapshot that was created
or imported elsewhere. Registered trainings are local data; these methods do
not fetch current data from Nolio.

```python
training = Training(id_partner=42, sport_id=2, name="Intervals")
client.register_training(training)

stored = client.get_registered_training(42)
all_stored = client.list_registered_trainings()
```

`register_training()` rejects duplicate partner IDs. `get_registered_training()`
raises `KeyError` when the ID is not in the local registry.

### Get data from any API endpoint

The `NolioApiClient` offers a `get()` method to access any API endpoint and return its data as a dictionary or a list.
There is [a list of API endpoints](https://github.com/NolioApp/NolioAPI-Documentation/wiki/API-Routes)
on the [Nolio API wiki](https://github.com/NolioApp/NolioAPI-Documentation/wiki).

For example, do access the first 30 (default max limit) planned trainings, one can use:

```python
trainings = client.get("planned/training/")
```
