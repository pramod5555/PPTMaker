from __future__ import annotations

import json
import random
from collections import defaultdict

from common import deck_id, ensure_output_dir, load_dataset


def main() -> None:
    dataset = load_dataset()
    slides = dataset.get("slides", [])
    out_dir = ensure_output_dir()

    by_deck: dict[str, list[dict]] = defaultdict(list)
    for slide in slides:
        by_deck[deck_id(slide["slide_id"])].append(slide)

    decks = sorted(by_deck)

    # Deck-level split prevents adjacent pages from the same deck leaking into
    # both train and evaluation. With only 5 decks, keep the largest deck in
    # train and hold out smaller decks for smoke-test evaluation.
    split_decks = {
        "train": decks[: max(1, len(decks) - 2)],
        "eval": decks[max(1, len(decks) - 2) : max(1, len(decks) - 1)],
        "test": decks[max(1, len(decks) - 1) :],
    }

    split_payload = {}
    for split_name, deck_names in split_decks.items():
        split_slides = [slide for deck in deck_names for slide in by_deck[deck]]
        split_payload[split_name] = {
            "deck_ids": deck_names,
            "slide_count": len(split_slides),
            "slides": split_slides,
        }
        (out_dir / f"{split_name}.json").write_text(
            json.dumps(split_payload[split_name], indent=2), encoding="utf-8"
        )

    (out_dir / "splits.json").write_text(json.dumps(split_payload, indent=2), encoding="utf-8")

    rng = random.Random(42)
    shuffled = sorted(slides, key=lambda slide: slide["slide_id"])
    rng.shuffle(shuffled)
    n = len(shuffled)
    random_split_payload = {
        "train": {
            "slide_count": int(n * 0.7),
            "slides": shuffled[: int(n * 0.7)],
        },
        "eval": {
            "slide_count": int(n * 0.15),
            "slides": shuffled[int(n * 0.7) : int(n * 0.85)],
        },
        "test": {
            "slide_count": n - int(n * 0.85),
            "slides": shuffled[int(n * 0.85) :],
        },
    }
    (out_dir / "random_splits.json").write_text(
        json.dumps(random_split_payload, indent=2), encoding="utf-8"
    )

    for split_name, payload in split_payload.items():
        print(f"{split_name:<5} {payload['slide_count']:>4} slides  decks={payload['deck_ids']}")
    print(f"Wrote split files to {out_dir}")
    print(
        "random "
        f"{random_split_payload['train']['slide_count']} train / "
        f"{random_split_payload['eval']['slide_count']} eval / "
        f"{random_split_payload['test']['slide_count']} test slides"
    )


if __name__ == "__main__":
    main()
