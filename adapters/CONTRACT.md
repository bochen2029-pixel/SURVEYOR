# adapters / the contract

**An adapter reads *beside* your record system. It never reads *through* it, and it never asks
your vendor for anything.**

That is not modesty, it is a design constraint with a receipt behind it: the reference site's own
words about incumbent integration were *"every little change costs us money"* `[H]`. A design that
needs vendor cooperation is a design that arrives priced, late, and dependent. So the contract
below assumes the worst case and is satisfied by a CSV on a network share.

---

## The four rules

1. **Read-only.** An adapter has no write path. Not a disabled one — an absent one. The quality
   record is written by people (law A5), and the source system is written by whoever writes it.
2. **Export-grade.** Whatever the system can already emit — scheduled CSV, a report export, a
   read replica, a nightly dump — is enough. If an adapter needs an API that must be purchased,
   built, or negotiated, it is out of contract.
3. **Roles, never names.** The emitted record addresses people by opaque, stable ids
   (`STF-014`, `HCL-207`). Names never enter the tape (law C1), and the floor has no check that
   needs one — `floor/FIELDS.md` is the whole vocabulary and it contains no name field.
4. **The clock battery runs first.** Timestamp jitter masquerades as findings: it produces
   sequence violations and SLA breaches out of nothing. Before an organ runs against a source,
   `clocks/` prints a registrability verdict for that source. **Registration precedes
   verification, as a gate, not a footnote** (SPEC §4).

## What an adapter emits

One JSON object per record, in the vocabulary of [`floor/FIELDS.md`](../floor/FIELDS.md) — which
is a *generated fold* over the fixtures, not a document someone maintains, so it is exact about
what the encoded checks actually read:

```json
{"record": { ...current state, flat-ish... },
 "history": [{"field": "...", "value": "...", "ts": "...", "actor_role": "...", "actor_id": "..."}],
 "as_of": "2026-06-15T12:00:00Z"}
```

Three fields carry more weight than their size suggests:

- **`as_of`** is the instant the emission speaks for. Clock checks read it when the completing
  event has not happened yet, which is how an alarm fires *before* a breach rather than after.
  An adapter that omits it turns every running clock into an abstention.
- **`history[].actor_id`** is what makes attribution checkable without a name. It is opaque and
  stable; the mapping from id to person stays in your building and never reaches this repository.
- **Timestamps are ISO-8601 with an offset.** `2026-08-20T08:40:00Z` and
  `2026-08-20T08:40:00+00:00` are the same instant, and the floor compares instants rather than
  strings precisely so an adapter may emit either.

## What an adapter must not do

- **Fill a blank.** A missing field must arrive missing. The floor's third state exists for this:
  a check that cannot judge says CANNOT-EVALUATE, and an adapter that substitutes a default has
  converted an honest silence into a false pass. This is the single most damaging thing an
  adapter can do and it always looks like helpfulness.
- **Normalise a vocabulary it was not given.** If the source says `LT KIDNEY`, emit that and map
  it in a declared table. Guessing `KI-L` is a judgement, and judgements belong in a file someone
  signed.
- **Reconcile two sources.** Emitting one record per source and letting the floor find the
  disagreement is the point (see SV-077, SV-073, SV-078). An adapter that quietly picks a winner
  has deleted the finding.
- **Reach the network.** `floor/`, `clocks/`, `ledger/` and `crosswalk/` are scanned for network
  and model imports on every gate run, and an adapter that runs inside this process is scanned
  with them.

## Registrability: the precondition

```bash
python clocks/anchors.py --case <one-emitted-record.json>
```

prints the record's clock lattice, the implied deadlines, and the binding path behind each one.
If it reports an infeasible network on a case everyone considers routine, the adapter's clocks are
wrong before any check is. That verdict belongs on the tape before the floor runs in anger.

## Status of this directory

**Empty by design, and that is a claim, not an omission.** A real binding needs export
specifications an OPO holds and a vendor's actual field names, and inventing either is precisely
the fabrication this project's citation gate exists to prevent. The contract above is what any
binding must satisfy; the first real one is written in the building that owns the export.
