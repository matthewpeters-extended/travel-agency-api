# Travel Agency API

A REST API for browsing public travels and tours and booking one, with a private side for
staff to manage the catalog.

Stack: **FastAPI** + **SQLAlchemy** + **SQLite**, JWT auth via `python-jose`, password hashing
via `passlib`/`bcrypt`, rate limiting via `slowapi`.

## Quickstart

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python scripts/seed_admin.py        # creates admin@mytravelagency.dev / admin123
python scripts/seed_demo_data.py    # creates a sample public travel with two tours, and a customer

uvicorn app.main:app --reload --reload-dir app
```

Interactive docs (Swagger UI) at `http://127.0.0.1:8000/docs` once it is running.

Run the test suite with:

```bash
pytest
```

## The main components

The app is split by *what each piece knows about*, not by HTTP verb. The goal is that each
file has one job and does not need to understand how the others work internally.

**`app/models.py` is the data layer, and the one place this task differs structurally from the
other three in this series.** Every primary key is a UUID (`sqlalchemy.Uuid`), per the spec's
note, rather than an autoincrementing integer. `Role` is its own table in a proper many to many
relationship with `User` through the `user_roles` join table, rather than a single enum column
like the other practice APIs use; `User.has_role(name)` is the one method that actually reads
that relationship, so nothing else in the app needs to know the join table exists. `Tour.price`
is a plain integer, counted in cents, exactly as the spec asks: `99900` means `999.00`, and
there is no float anywhere near money.

**`app/deps.py` mirrors the authorization pattern from the library API**, with one change:
`require_role(*roles)` now checks `current_user.has_role(role)` for each allowed role instead
of comparing a single enum field, since a user here can hold more than one role at once.

**`app/routers/travels.py` and `app/routers/tours.py` each do the same split**, public read
endpoints with no authentication at the top, admin only write endpoints guarded by
`require_role("Admin")` below. The public list endpoints are the filtering and sorting surface
the spec asks for: `GET /travels` takes `q`, `min_days`, `max_days`, `sort`, and `order`; `GET
/tours` takes `travel_id`, `min_price`, `max_price`, `starting_after`, `starting_before`,
`sort`, and `order`. Both public list endpoints, and the matching `GET /{id}` endpoints, only
ever return records belonging to a travel marked `is_public`. A tour under a private travel is
treated as though it does not exist at all for anyone browsing, not merely hidden from search.

**`app/routers/tours.py` also holds `POST /tours/{id}/book`**, since booking is an action on a
tour, not a resource of its own with a full CRUD surface. It is open to any logged in user, not
just Admins, checks that the tour's travel is public (so a direct id guess cannot book something
never meant to be shown), and rejects booking a tour whose `ending_date` has already passed.

**`app/routers/bookings.py` is read only.** `GET /bookings/me` is scoped to the caller's own
rows no matter who they are; `GET /bookings` is the Admin only audit view across every booking,
which exists because the task's "private admin endpoints" framing implies staff need visibility
into what got booked, not just the ability to create the catalog.

**`app/routers/users.py` has no self registration**, matching the spec's framing of user
creation as an admin only endpoint. `POST /users` takes a list of role names and resolves them
against the fixed `Role` rows seeded at startup, returning `400` for a name that does not exist
rather than silently creating a new role on the fly. Deleting a user with existing bookings is
blocked, for the same reason the library API blocks deleting a book with borrow history: the
record that someone booked something should outlive the convenience of deleting their account.

**`app/main.py` seeds the `Admin` and `Customer` roles at startup**, idempotently, since the
spec treats roles as a fixed small set rather than something an admin creates through the API.
Bootstrapping the very first Admin account still needs `scripts/seed_admin.py`, for the same
chicken and egg reason the library API needs one: nothing can call an admin only endpoint
before an admin exists to call it.

**`tests/`** has 39 pytest feature tests covering role based access on every write endpoint,
that private travels and their tours are invisible to public browsing, filtering and sorting on
both list endpoints, the booking flow including its two rejection cases, and the delete guards
on travels, tours, and users that already have dependent rows.

## Decisions worth knowing about

* **A private travel is not just filtered out of search results; it returns a plain `404` from
  `GET /travels/{id}` and `GET /tours/{id}` too**, for anyone, including an Admin calling the
  public endpoint rather than using the object a create or update call already returned. The
  public browsing endpoints never reveal that a private record exists at all.
* **`Role` is a real table with a join table, not an enum**, because the spec lists it as its
  own model with an explicit many to many relationship, unlike the single role column the other
  three practice APIs use. The two are genuinely different shapes: an enum column means a user
  has exactly one role; this join table means a user could hold several at once, even though
  the seeded data here never exercises that case.
* **Booking has no concept of capacity or availability beyond the tour's own dates.** The spec
  only asks that users can book a tour, not that tours sell out, so adding a seat count would
  have been solving a problem nobody asked about yet.
* **Slugs are generated from the name and deduplicated with a numeric suffix** (`coastal-tour`,
  then `coastal-tour-2`) rather than requiring the caller to supply a unique one. An admin can
  still pass an explicit `slug` in the create or update payload if they want control over it.
