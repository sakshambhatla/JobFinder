"""Generate unique 2-word run names (adjective/verb + noun).

Each name is hyphenated lowercase, e.g. ``"dancing-monkey"``.
The generator retries until it finds a combination not already used
by the given user.
"""

from __future__ import annotations

import random

ADJECTIVES = [
    "dancing", "jumping", "happy", "swift", "bold", "calm", "eager",
    "fierce", "gentle", "brave", "clever", "daring", "fancy", "golden",
    "humble", "jolly", "keen", "lively", "mighty", "noble", "proud",
    "quiet", "rapid", "shiny", "steady", "tender", "vivid", "warm",
    "zesty", "bright", "cosmic", "dizzy", "epic", "funky", "glossy",
    "hidden", "icy", "jade", "kind", "lunar", "mystic", "nifty",
    "olive", "plucky", "rustic", "silver", "turbo", "ultra", "witty",
]

NOUNS = [
    "monkey", "horse", "falcon", "turtle", "panda", "tiger", "eagle",
    "dolphin", "fox", "wolf", "bear", "hawk", "otter", "raven",
    "phoenix", "dragon", "bison", "cobra", "deer", "elk", "gecko",
    "heron", "ibis", "jaguar", "koala", "lynx", "moose", "newt",
    "osprey", "parrot", "quail", "robin", "stork", "toucan", "urchin",
    "viper", "walrus", "yak", "zebra", "badger", "crane", "dingo",
    "ferret", "gopher", "hornet", "iguana", "jackal", "kite", "lemur",
]

# Total combinations: 50 * 50 = 2,500 — well above the 20-per-user limit.


def generate_run_name(existing_names: set[str], max_attempts: int = 100) -> str:
    """Return a unique 2-word hyphenated name not in *existing_names*.

    Raises ``RuntimeError`` if a unique name cannot be found within
    *max_attempts* (extremely unlikely given the combinatorial space).
    """
    for _ in range(max_attempts):
        name = f"{random.choice(ADJECTIVES)}-{random.choice(NOUNS)}"
        if name not in existing_names:
            return name
    raise RuntimeError(
        f"Could not generate a unique run name after {max_attempts} attempts. "
        f"Consider deleting old runs."
    )
