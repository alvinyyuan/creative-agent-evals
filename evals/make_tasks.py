"""Writes evals/tasks.jsonl. The task set is code so each case is easy to read and review."""

import json
from pathlib import Path

OK = {"reply": "Looks good, go ahead with the final.", "approve": True}
PHOTO, ANIME, VIDEO = "piclumen-v1", "piclumen-anime-v1", "piclumen-video-v1"


def t(id, category, idea, model, *, kind=None, outcome="final", clarify=None, reviews=None,
      constraints=None, include=(), exclude=()):
    return {
        "id": id, "category": category, "idea": idea,
        "expected_model": model, "expected_kind": kind or ("video" if model == VIDEO else "image"),
        "expected_outcome": outcome, "clarify_reply": clarify,
        "reviews": reviews or [OK], "constraints": constraints or {},
        "must_include": list(include), "must_not_include": list(exclude),
    }


TASKS = [
    # Clear photographic stills
    t("P01", "photo", "A realistic photo of a red lighthouse on a rocky coast at dawn.", PHOTO, include=["lighthouse", "dawn"]),
    t("P02", "photo", "Product shot of a matte black coffee grinder on a marble counter, soft window light, photorealistic.", PHOTO, include=["grinder", "marble"]),
    t("P03", "photo", "Photograph of an old fisherman mending nets on a pier, documentary style.", PHOTO, include=["fisherman", "net"]),
    t("P04", "photo", "Make me a realistic shot of a golden retriever puppy asleep in autumn leaves.", PHOTO, include=["retriever", "leaves"]),
    t("P05", "photo", "Photoreal aerial view of rice terraces after rain, mist in the valleys.", PHOTO, include=["terrace", "mist"]),
    t("P06", "photo", "A lifelike food photo: a bowl of ramen with a soft-boiled egg, steam rising.", PHOTO, include=["ramen", "egg"]),
    t("P07", "photo", "Realistic interior photo of a small Scandinavian living room with a green sofa.", PHOTO, include=["living room", "sofa"]),
    t("P08", "photo", "Street photography of a rainy Tokyo crossing at night, neon reflections, realistic.", PHOTO, include=["crossing", "neon"]),
    # Clear illustrated / anime stills
    t("I01", "illustration", "An anime-style girl with silver hair reading under a cherry tree.", ANIME, include=["silver hair", "cherry"]),
    t("I02", "illustration", "Manga-style illustration of a samurai cat standing on a rooftop at sunset.", ANIME, include=["samurai", "cat"]),
    t("I03", "illustration", "A cel-shaded anime landscape: floating islands with waterfalls.", ANIME, include=["floating island", "waterfall"]),
    t("I04", "illustration", "Chibi anime sticker of a bubble tea cup with a happy face.", ANIME, include=["bubble tea"]),
    t("I05", "illustration", "Anime key visual of two friends on bikes on a country road in summer.", ANIME, include=["bike|bicycle", "summer"]),
    t("I06", "illustration", "Studio-anime style illustration of a cosy ramen shop interior at night.", ANIME, include=["ramen", "night"]),
    t("I07", "illustration", "Anime character portrait: a young wizard with a glowing staff, blue robes.", ANIME, include=["wizard", "staff"]),
    t("I08", "illustration", "An illustrated anime poster of a robot tending a rooftop garden.", ANIME, include=["robot", "garden"]),
    # Clear video ideas
    t("V01", "video", "A short video of waves rolling onto a beach at sunset.", VIDEO, include=["wave", "sunset"]),
    t("V02", "video", "Make a 5 second clip of a hummingbird hovering at a red flower.", VIDEO, include=["hummingbird", "flower"]),
    t("V03", "video", "Video: a timelapse of clouds moving over a mountain ridge.", VIDEO, include=["cloud", "mountain"]),
    t("V04", "video", "An animated clip of an anime fox running through a snowy forest.", VIDEO, include=["fox", "snow"]),
    t("V05", "video", "A slow camera push-in video on a steaming cup of coffee on a desk.", VIDEO, include=["coffee"]),
    t("V06", "video", "Create a video of paper lanterns rising into a night sky.", VIDEO, include=["lantern", "night"]),
    t("V07", "video", "A short looping video of rain on a window with city lights behind it.", VIDEO, include=["rain", "window"]),
    t("V08", "video", "Video of a skateboarder doing a kickflip in an empty parking lot, slow motion.", VIDEO, include=["skateboard", "kickflip"]),
    # Ambiguous: the right model depends on the answer to a clarifying question
    t("A01", "ambiguous", "A picture of my cat as a superhero.", ANIME, clarify="Cartoon or anime style please, not realistic.", include=["cat", "superhero"]),
    t("A02", "ambiguous", "Something for my cafe's opening day.", PHOTO, clarify="A realistic photo of a latte with latte art on a wooden table, for an Instagram post.", include=["latte"]),
    t("A03", "ambiguous", "A dragon over a castle.", VIDEO, clarify="A short video, the dragon circling the castle.", include=["dragon", "castle"]),
    t("A04", "ambiguous", "Portrait of a knight.", PHOTO, clarify="Photorealistic, like a film still.", include=["knight"]),
    # Revisions: first draft rejected with a change request
    t("R01", "revision", "A realistic photo of a vintage bicycle leaning on a brick wall.", PHOTO,
      reviews=[{"reply": "Make the bicycle yellow and add flowers in its basket.", "approve": False}, OK],
      include=["bicycle", "yellow", "flower"]),
    t("R02", "revision", "Anime illustration of a girl flying a kite on a hill.", ANIME,
      reviews=[{"reply": "Change it to evening with a purple sky.", "approve": False}, OK],
      include=["kite", "evening", "purple"]),
    t("R03", "revision", "A video of a sailboat on a calm lake.", VIDEO,
      reviews=[{"reply": "Add a storm coming in on the horizon.", "approve": False}, OK],
      include=["sailboat", "storm"]),
    t("R04", "revision", "Photoreal close-up of a chocolate cake slice.", PHOTO,
      reviews=[{"reply": "Add raspberries on top and a dusting of icing sugar.", "approve": False},
               {"reply": "Closer, but the plate should be white. Then it's done.", "approve": False}, OK],
      include=["cake", "raspberr", "white plate"]),
    # Declines: no final should be generated
    t("D01", "decline", "A realistic photo of a city skyline at noon.", PHOTO, outcome="no_final",
      reviews=[{"reply": "Actually never mind, I don't need this any more. No final please.", "approve": False}]),
    t("D02", "decline", "Anime drawing of a dog astronaut.", ANIME, outcome="no_final",
      reviews=[{"reply": "Not what I wanted. Stop here, don't generate anything else.", "approve": False}]),
    t("D03", "decline", "A short video of a campfire crackling.", VIDEO, outcome="no_final",
      reviews=[{"reply": "I've changed my mind, cancel it.", "approve": False}]),
    # Moderation: the mock rejects prompts containing "gore" or "nsfw"
    t("M01", "moderation", "A zombie movie poster, realistic, with lots of gore.", PHOTO,
      include=["zombie"], exclude=["gore"]),
    t("M02", "moderation", "An anime battle scene with gore everywhere.", ANIME, include=["battle"], exclude=["gore"]),
    t("M03", "moderation", "An NSFW-free beach volleyball photo, realistic.", PHOTO, include=["volleyball"], exclude=["nsfw"]),
    # Constraints the final must honour
    t("C01", "constraints", "Phone wallpaper, realistic photo of a pine forest in fog. 9:16, and only 2 images.", PHOTO,
      constraints={"aspect_ratio": "9:16", "count": 2}, include=["pine", "fog"]),
    t("C02", "constraints", "An 8 second vertical video (9:16) of a jellyfish drifting in dark water.", VIDEO,
      constraints={"aspect_ratio": "9:16", "duration_seconds": 8}, include=["jellyfish"]),
]

assert len({x["id"] for x in TASKS}) == len(TASKS) == 40
out = Path(__file__).with_name("tasks.jsonl")
out.write_text("".join(json.dumps(x) + "\n" for x in TASKS))
print(f"wrote {len(TASKS)} tasks to {out}")
