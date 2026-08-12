from argparse import ArgumentParser
from datetime import date, timedelta

from nolito import NolioApiClient

parser = ArgumentParser()
parser.add_argument(
    "-s", "--start", help="Start date in YYYY-MM-DD format, defaults to today"
)
parser.add_argument(
    "-e",
    "--end",
    help="End date in YYYY-MM-DD format, defaults to one year after start",
)
parser.add_argument(
    "-l",
    "--limit",
    help="Maximum numbers of trainings returned. Defaults to twice the number of days.",
)
parser.add_argument(
    "-o", "--output", help="Output file where the trainings should be saved."
)
parser.add_argument("--overwrite", action="store_true", help="Overwrite the output file if it exists.")
parser.add_argument(
    "-v",
    "--verbose",
    action="store_true",
    help="Print more details about the trainings",
)
args = parser.parse_args()

start = args.start or date.today().isoformat()  # noqa: DTZ011
end = args.end or (date.today() + timedelta(days=365)).isoformat()  # noqa: DTZ011
print(start, end)


client = NolioApiClient()
trainings = client.get_planned_trainings(start=start, end=end, limit=args.limit)
print(f"Found {len(trainings)} trainings")
if args.output is not None:
    trainings.to_json(args.output, overwrite=args.overwrite)
    print(f"Saved trainings to {args.output}")
if args.verbose:
    print(trainings)
