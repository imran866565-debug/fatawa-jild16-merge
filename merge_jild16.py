#!/usr/bin/env python3
"""Merge Jild 16 tashreeh chunks into jild-16.json.

Re-runnable: reads every jild-16-chunk-*.json listed in the manifest,
merges in chunk order, validates (unique ids, page coverage vs manifest,
no empty jawab), writes jild-16.json, and updates the manifest statuses.

COMBINE RULES (from the Jild 16 coordinator's self-contained final
report, verified by the parent on disk: 277 items, 542/542 unique
pages, exactly the 5 duplicate-id pairs listed there, exactly 2 empty
jawab — chunk 04's masala-83-87 [220] and chunk 08's masala-211 [420],
both split-start halves). 8 combine cases are ONE mas'ala split
across chunks and must be COMBINED into a single item, NOT renamed
by the duplicate-id rule. After combining all 8 cases, the merged
file has 269 items (277 - 8) covering 542 unique pages. Combine
rules (parts ordered by min page; sawal as specified per rule; jawab
= all parts concatenated in page order; pages = UNION of all parts'
pages; notes = all parts' notes):
  masala 46-48:  02 'jild16-masala-46-48' [142, 143, 144] (sawal) +
              03 'jild16-masala-46-48' [145] (tail, empty sawal) —
              SAME id twice. Sawal from 02; jawab = 02 + 03
              concatenated. Pages [142-145].
  masala 83-87 (RENAME + combine — the one tricky case): chunk 04
              has TWO different masail: 'jild16-masala-83' [220]
              (the qawwal mas'ala — COMPLETE, keep as-is, do NOT
              touch) and 'jild16-masala-83-87' [220] (start half of
              the Bombay جامع مسجد group, question opening only,
              EMPTY jawab). Chunk 05's continuation of that group is
              MISLABELLED 'jild16-masala-83' [221, 222, 223] (title
              «مسئلہ ۸۳ تا ۸۷ — بمبئی جامع مسجد...»). FIRST RENAME
              chunk 05's 'jild16-masala-83' -> 'jild16-masala-83-87',
              then COMBINE it with chunk 04's 'jild16-masala-83-87'
              -> ONE item, pages [220, 221, 222, 223]. Sawal: keep
              chunk 05's (it summarises the whole question including
              the p. 220 opening); discard chunk 04's fragmentary
              opening (Jild 11 masala-16 rule). Jawab = chunk 05's
              (chunk 04's is empty). After this, the only
              'jild16-masala-83' left is chunk 04's qawwal mas'ala.
  masala 149: 06 'jild16-masala-149' [309, 310] (full sawal) +
              07 'jild16-masala-149' [311-317] (tail, 592-char sawal
              restatement) — SAME id twice. Sawal from 06; discard
              07's restatement (Jild 11 masala-16 rule). Jawab =
              06 + 07 concatenated. Pages [309-317].
  masala 211: 08 'jild16-masala-211' [420] (partial sawal, empty
              jawab) + 09 'jild16-masala-211' [421, 422] (full sawal
              + jawab) — SAME id twice. Sawal from 09 (full — it
              covers the whole question); discard 08's partial
              opening. Jawab = 09's (08's is empty). Pages
              [420, 421, 422].
  masala 359: 11 'jild16-masala-359' [569, 570] (sawal) + 12
              'jild16-masala-359' [571] (tail, empty sawal) — SAME
              id twice. Sawal from 11; jawab = 11 + 12 concatenated.
              Pages [569, 570, 571].
  masala 277 (cross-id): 09 'jild16-masala-277' [469, 470] (sawal;
              jawab cut mid-sentence on p. 470) + 10 'jild16-p470'
              [471, 472, 473] (empty sawal) -> ONE item keeping the
              id 'jild16-masala-277', pages [469-473]. Sawal from
              09; jawab = 09 + 10 concatenated.
  masala 319 (cross-id): 10 'jild16-masala-319' [515-520] (sawal) +
              11 'jild16-p521' [521, 522] (empty sawal) -> ONE item
              keeping the id 'jild16-masala-319', pages [515-522].
              Sawal from 10; jawab = 10 + 11 concatenated. The
              coordinator verified from the source that pp. 520-521
              carry the same شراء فاسد passage (the fifth point of
              masala-319's jawab), so chunk 11's p521 item IS the
              masala-319 tail, not a separate discussion.
  masala 428 (cross-id): 12 'jild16-masala-428' [614-624] (sawal;
              jawab ends mid-sentence on p. 624) + 13 'jild16-p625'
              [625] (empty sawal — the risala's closing تنبیہ) ->
              ONE item keeping the id 'jild16-masala-428', pages
              [614-625]. Sawal from 12; jawab = 12 + 13 concatenated.
For every combined item: pages = union of all parts' pages,
start_page = min, notes = all parts' notes combined.

PAGE-COUNT NOTE: the brief said "543 pages" — that counts DB rows.
The source has 543 rows but only 542 UNIQUE pages (p. 255 has two
rows, one printed page, both fragments covered — masala-128 ends on
row 1, masala-129 covers both rows in one item with p. 255 listed
once). Page coverage is validated against the 542 unique pages.

No other renames are needed: the printed numbering is continuous
through the volume, and the only other same-numbered items were
already distinguished by their translators (chunk 11's second 335
is 'jild16-p539'; chunk 12's printed «مسئلہ ۶۱۱» is kept as
'jild16-masala-611', a misprint for 411 — no collision). Any
duplicate id left after the 8 combines is a bug: fail loudly,
do NOT silently rename.

Distinct items that merely look similar are NOT combined — they
stay separate: chunk 11's 'jild16-p539' [539-543] (second printed
335) vs 'jild16-masala-335' [538-539]; chunk 13's 'jild16-khatima'
[636] (volume closing note); chunk 01's 'jild16-pesh-lafz' and
'jild16-hamd'; chunk 08's 'jild16-masala-185' [370-405] (one giant
36-page item already; do not split it). Page union across the
merged file is still exactly 542.
"""
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))

# result id -> list of selectors, in page order.
# Selector forms:
#   ('id', sid)            — every item with this id (1 or 2 halves)
#   ('id_start', sid, sp)  — the item with this id starting at page sp
#   ('file', fname)        — every item in this chunk file
COMBINES = {
    'jild16-masala-46-48': [
        ('id', 'jild16-masala-46-48'),
    ],
    'jild16-masala-83-87': [
        ('id', 'jild16-masala-83-87'),
    ],
    'jild16-masala-149': [
        ('id', 'jild16-masala-149'),
    ],
    'jild16-masala-211': [
        ('id', 'jild16-masala-211'),
    ],
    'jild16-masala-359': [
        ('id', 'jild16-masala-359'),
    ],
    'jild16-masala-277': [
        ('id', 'jild16-masala-277'),
        ('id', 'jild16-p470'),
    ],
    'jild16-masala-319': [
        ('id', 'jild16-masala-319'),
        ('id', 'jild16-p521'),
    ],
    'jild16-masala-428': [
        ('id', 'jild16-masala-428'),
        ('id', 'jild16-p625'),
    ],
}

# result id -> start_page of the part whose sawal to keep.
# Absent = sawal from the FIRST part (lowest min page).
# Rule 2 (83-87): keep chunk 05's sawal (start 221), discard chunk
# 04's fragmentary opening (start 220). Rule 4 (211): keep chunk
# 09's full sawal (start 421), discard chunk 08's partial opening
# (start 420). Both are the Jild 11 masala-16 rule.
SAWAL_FROM_START = {
    'jild16-masala-83-87': 221,
    'jild16-masala-211': 421,
}

# Every combined item must have a non-empty sawal after combining.
SAWAL_REQUIRED = set(COMBINES.keys())


def combine_parts(result_id, parts):
    parts = sorted(parts, key=lambda it: min(it['pages']))
    first = parts[0]
    sawal_start = SAWAL_FROM_START.get(result_id)
    if sawal_start is not None:
        sawal_parts = [p for p in parts if p['start_page'] == sawal_start]
        assert len(sawal_parts) == 1, \
            f'{result_id}: sawal source start_page {sawal_start} matched {len(sawal_parts)} parts'
        sawal = sawal_parts[0].get('tashreeh_sawal', '') or ''
    else:
        sawal = first.get('tashreeh_sawal', '') or ''
    combined = {
        'id': result_id,
        'title': first.get('title') or '',
        'volume_id': 52,
        'pages': sorted(set().union(*[set(p['pages']) for p in parts])),
        'start_page': min(min(p['pages']) for p in parts),
        'tashreeh_sawal': sawal,
        'tashreeh_jawab': ''.join((p.get('tashreeh_jawab', '') or '') for p in parts),
        'notes': [n for p in parts for n in (p.get('notes') or [])],
    }
    return combined


def select_parts(all_items, selectors):
    """Resolve selectors to the matching items (each used at most once)."""
    parts = []
    used = set()
    for sel in selectors:
        if sel[0] == 'id':
            hits = [it for it in all_items
                    if it['id'] == sel[1] and id(it) not in used]
        elif sel[0] == 'id_start':
            hits = [it for it in all_items
                    if it['id'] == sel[1] and it['start_page'] == sel[2]
                    and id(it) not in used]
        elif sel[0] == 'file':
            hits = [it for it in all_items
                    if it.get('_src_file') == sel[1] and id(it) not in used]
        else:
            raise ValueError(f'unknown selector {sel}')
        assert hits, f'no items matched selector {sel}'
        for it in hits:
            used.add(id(it))
        parts.extend(hits)
    return parts


def run_merge(manifest_path, base, write=False):
    manifest = json.load(open(manifest_path, encoding='utf-8'))
    all_items = []
    merged_chunks = []
    for entry in manifest['chunks']:
        nn = entry['chunk']
        if entry.get('status') == 'split-halves':
            print(f'chunk {nn}: split-halves placeholder — halves are separate entries, skipping')
            continue
        path = os.path.join(base, entry['file'])
        if not os.path.exists(path):
            print(f'chunk {nn}: not yet written')
            continue
        try:
            d = json.load(open(path, encoding='utf-8'))
        except json.JSONDecodeError as e:
            # File may still be streaming from its translator; skip it
            # for now instead of crashing the whole merge.
            print(f'chunk {nn}: not valid JSON yet ({e}) — skipping for now')
            continue
        items = d['masail']
        # Normalize: some translators omit start_page; derive it from pages.
        for it in items:
            if 'start_page' not in it:
                assert it.get('pages'), f'chunk {nn} item {it.get("id")} has no pages'
                it['start_page'] = it['pages'][0]
                print(f'chunk {nn}: derived start_page={it["start_page"]} for {it["id"]}')
            assert it['start_page'] == min(it['pages']), \
                f'chunk {nn} item {it["id"]}: start_page != first page'
            it['_src_file'] = entry['file']
        all_items.extend(items)
        merged_chunks.append(nn)
        entry['status'] = 'merged'
        print(f'chunk {nn}: {len(items)} items merged')
    print(f'items before combines: {len(all_items)}')
    assert len(all_items) == 277, f'expected 277 chunk items, got {len(all_items)}'
    # RULE 2 PRE-STEP: rename chunk 05's MISLABELLED 'jild16-masala-83'
    # [221-223] -> 'jild16-masala-83-87' BEFORE combining. Chunk 04's
    # qawwal 'jild16-masala-83' [220] must NOT be touched.
    renamed = 0
    for it in all_items:
        if it['id'] == 'jild16-masala-83' and it['start_page'] == 221:
            print(f"RENAME (rule 2 pre-step) {it['id']} (start {it['start_page']}) -> jild16-masala-83-87")
            it['id'] = 'jild16-masala-83-87'
            renamed += 1
    assert renamed == 1, f'rule 2 pre-step: expected to rename exactly 1 item, renamed {renamed}'
    qawwal = [it for it in all_items if it['id'] == 'jild16-masala-83']
    assert len(qawwal) == 1 and qawwal[0]['start_page'] == 220, \
        f"rule 2 pre-step: qawwal masala-83 [220] must remain exactly once, got {[(i['start_page']) for i in qawwal]}"
    print("rule 2 pre-step OK: qawwal 'jild16-masala-83' [220] untouched")
    # COMBINE the 8 cases (one mas'ala split across chunks).
    for result_id, selectors in COMBINES.items():
        parts = select_parts(all_items, selectors)
        combined = combine_parts(result_id, parts)
        assert combined['tashreeh_jawab'], f'{result_id}: combined jawab is empty!'
        if result_id in SAWAL_REQUIRED:
            assert combined['tashreeh_sawal'], f'{result_id}: combined sawal is empty!'
        assert combined['start_page'] == min(combined['pages']), f'{result_id}: start_page != min(pages)'
        used_ids = set(id(p) for p in parts)
        all_items = [it for it in all_items if id(it) not in used_ids]
        all_items.append(combined)
        print(f'COMBINED {result_id}: {len(parts)} parts, pages {combined["pages"][0]}-{combined["pages"][-1]} '
              f'({len(combined["pages"])} pages), sawal {len(combined["tashreeh_sawal"])} chars, '
              f'jawab {len(combined["tashreeh_jawab"])} chars, notes {len(combined["notes"])}')
    ids = [it['id'] for it in all_items]
    assert len(ids) == len(set(ids)), f'STILL DUPLICATE IDS: {[i for i in ids if ids.count(i) > 1]}'
    empty = [it['id'] for it in all_items if not it.get('tashreeh_jawab')]
    assert not empty, f'EMPTY JAWAB: {empty}'
    pages = set()
    for it in all_items:
        pages.update(it['pages'])
    expected = set()
    for entry in manifest['chunks']:
        if entry['chunk'] in merged_chunks:
            expected.update(range(entry['start_page'], entry['end_page'] + 1))
            expected.difference_update(entry['missing_pages'])
    missing_covered = expected - pages
    extra = pages - expected
    print(f'total items: {len(all_items)} | pages covered: {len(pages)} | expected: {len(expected)}')
    print(f'uncovered expected pages: {sorted(missing_covered)}')
    print(f'extra pages (outside merged chunks): {sorted(extra)}')
    assert not missing_covered, 'pages missing from merged chunks!'
    assert not extra, 'pages outside merged chunks!'
    assert len(all_items) == 269, f'expected 269 items after combines, got {len(all_items)}'
    assert len(pages) == 542, f'expected 542 pages, got {len(pages)}'
    # sort by start_page for the final file
    all_items.sort(key=lambda it: it['start_page'])
    for it in all_items:
        it.pop('_src_file', None)
    if write:
        with open(os.path.join(base, 'jild-16.json'), 'w', encoding='utf-8') as f:
            json.dump({'masail': all_items}, f, ensure_ascii=False, indent=1)
        with open(os.path.join(base, 'chunks-manifest-jild16.json'), 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
        print(f'WROTE jild-16.json: {len(all_items)} items, {len(pages)} pages, chunks merged: {merged_chunks}')
    return all_items, pages, merged_chunks


def main():
    manifest_path = os.path.join(BASE, 'chunks-manifest-jild16.json')
    run_merge(manifest_path, BASE, write=True)


if __name__ == '__main__':
    main()
