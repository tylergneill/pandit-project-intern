# Pandit forms: how changes are made by hand

What we learned doing the first changes together (Nov 20, 2026), from the
KSTS research notes. Read this before filling any form on panditproject.org.

Everything here is done in Tyler's own Chrome (Claude in Chrome), where he
is signed in. The intern fills forms; **Tyler always clicks Save.**

## Creating a work

`Add data → Work`, or /node/add/work. The form has five steps:
Basics, Works, People/places/institutions, Scholarship and Resources,
Publish. The minimal record Tyler makes:

| Step | Field | Form name | Notes |
|---|---|---|---|
| Basics | Name | `title` | type it, don't set it by script |
| Basics | Authors | `field_author[]` | select2 search; see traps below |
| Basics | Alternative names | `field_alternative_name[0][value]` | add one naming the author when another author has a work of the same name |
| Basics | Language | `field_language[]` | Sanskrit = 45, Kashmiri = 77 |
| Works | Part of (Work) | `field_part_of_work[]` | on the **part** only; see below |
| Works | Translation of (Work) | `field_translation_of_work` | |
| Publish | Attribute revision to (Project) | `field_attributed_to_project[]` | SETI on PANDIT = 115247 |
| Publish | Revision log message | `revision_log[0][value]` | see below |

Setting a select2 field from the page's JavaScript (the autocomplete is
slow and offers wrong records first):

```js
jQuery('select[name="field_author[]"]')
  .append(new Option('Utpala', '85292', true, true))
  .trigger('change');
```

Then read the field back in a screenshot before going on.

## Parts and wholes

The part/whole link is stored only on the part (Works step → "Part of
(Work)"). The whole has no "has parts" field; its page lists the parts
by itself under "Contained as part (N)". So once the parts exist, a
whole's title that lists them ("Siddhitrayī [includes …]") should be
cleaned to the bare title.

The field's help text says to use it only with clear manuscript support.

## Revision log

Say what was done and on what basis, as a habit, even when it seems
obvious:

> Create separate work for Ajaḍapramātṛsiddhi, part of Utpala's Siddhitrayī (88958).

State the basis (an edition's title page, a catalogue) and never a guess.
Never leave a gap like "no author yet": create the author first.

## Order

There's an obvious DAG (Tyler's words): person, then work, then the
part-of, translation or commentary link. "Just go create the author first."
The to-do list's `Depends On` keeps that order.

## Traps

- **IDs, never names.** Autocomplete puts the wrong record first:
  "Utpala" offers Utpala Vaiṣṇava 85353 before Utpala 85292;
  "Siddhitray" offers Yāmuna's Siddhitrayī 89146 before Utpala's 88958.
- **Name collisions.** Yāmuna also has an Īśvarasiddhi, so Utpala's got an
  alias naming him.
- **Aliases that expand too far.** 89165 Mālinīvijayavārttika had the alias
  "Mālinīvijaya(uttara)tantra(vārttika)", which expands to the bare tantra
  title and pulled matches away from 116075 Mālinīvijayottaratantra.
- **Editions that don't exist.** Some editions (e.g. KSTS vols 87, 90)
  have no print entity in Pandit; stop short of edition links there.
- **Record addresses.** /entity/<id>/work aliases are missing for records
  created in bulk (the 114000s–116000s); /node/<id> always works.

## Cloudflare

A Cloudflare check appears on a timer, about every 15 minutes (not because
of how fast pages are fetched). When it shows, stop and ask Tyler to pass
it, then carry on.

## What a regular user can't do (escalate)

- Merging duplicate records (e.g. persons Bhāskarakaṇṭha 86415 and 87154).
- Legacy fields with no place in the edit form, like the "Additional
  description" on 88958 (filed as a GitHub issue on PanditProject/Website).
- Missing /entity aliases for bulk-imported records.

Escalations go to the PanditProject/Website GitHub issues or to an admin.
The intern writes the issue text in the chat; Tyler files it.

## Worked examples (Nov 20, 2026)

- **Siddhitrayī.** 88958 stood in for its three parts. Created part works
  117069 Īśvarasiddhi, 117070 Saṃbandhasiddhi, 117071 Ajaḍapramātṛsiddhi,
  each Part of 88958, author Utpala 85292; 88958 renamed to "Siddhitrayī".
- **Pañcastavī** 117077, with its parts.
- **Lalleśvarī.** Created person Lalleśvarī 117080 and the Kashmiri work
  Lal Vākh 117081; 96033 retitled Lalleśvarīvākyāni (Sanskrit, author
  87154, Translation of 117081). SETI row M00032 pairs both.
- **Kāmakalāvilāsa.** 96013 retitled (was misspelt, author in the title);
  author Puṇyānanda created as 117072.
