"""Seed 50 small, locally generated demo illustrations and ten labeled posts."""
import asyncio
import json
import uuid
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.db import db
from app.services.ai import AIProvider

ROOT = Path(__file__).resolve().parent
IMAGE_DIR = ROOT / "data" / "images"
SUBJECTS = {
    "animals": ["red fox", "gray wolf", "golden dog", "brown bear", "white-tailed deer"],
    "food": ["red apple", "yellow banana", "vegetable pizza", "sourdough bread", "orange carrot"],
    "nature": ["pine forest", "snowy mountain", "sandy beach", "rocky desert", "forest waterfall"],
    "vehicles": ["red car", "blue bicycle", "passenger train", "commercial airplane", "sailboat"],
    "objects": ["wooden chair", "wall clock", "desk lamp", "open book", "digital camera"],
}
PALETTES = {
    "animals": ((220, 239, 225), (52, 104, 76)), "food": ((255, 241, 212), (182, 87, 45)),
    "nature": ((218, 237, 246), (53, 113, 139)), "vehicles": ((232, 229, 249), (83, 73, 149)),
    "objects": ((241, 231, 218), (126, 91, 60)),
}


def make_illustration(path: Path, category: str, subject: str):
    bg, fg = PALETTES[category]
    image = Image.new("RGB", (640, 400), bg)
    draw = ImageDraw.Draw(image)
    # Original geometric artwork keeps the corpus reproducible and compact.
    draw.rounded_rectangle((58, 48, 582, 352), radius=28, fill=(255, 255, 255), outline=fg, width=5)
    subject_color = fg
    if category == "animals":
        subject_color = {"red fox":(207,105,43),"gray wolf":(111,124,132),"golden dog":(202,154,77),"brown bear":(126,83,58),"white-tailed deer":(171,135,91)}[subject]
        draw.ellipse((206, 174, 424, 257), fill=subject_color)
        draw.ellipse((253, 97, 386, 225), fill=subject_color)
        if "deer" in subject:
            draw.line([(283,116),(270,83),(249,72),(268,91),(270,57),(281,94),(300,78),(283,107)],fill=subject_color,width=8)
            draw.line([(356,116),(369,83),(390,72),(371,91),(369,57),(358,94),(339,78),(356,107)],fill=subject_color,width=8)
        elif "bear" in subject:
            draw.ellipse((236, 91, 290, 146), fill=subject_color)
            draw.ellipse((349, 91, 403, 146), fill=subject_color)
        else:
            draw.polygon([(267,125),(251,70),(309,105)],fill=subject_color)
            draw.polygon([(334,105),(390,70),(372,130)],fill=subject_color)
        muzzle=(255,255,255) if "wolf" in subject else (245,226,192)
        draw.ellipse((289,164,351,209),fill=muzzle)
        draw.ellipse((282,143,295,156),fill=(255,255,255)); draw.ellipse((346,143,359,156),fill=(255,255,255))
        draw.ellipse((286,147,292,154),fill=(30,35,32)); draw.ellipse((350,147,356,154),fill=(30,35,32))
        draw.ellipse((314,173,328,184),fill=(35,35,35))
    elif category == "food":
        if "apple" in subject:
            draw.ellipse((245,100,395,245),fill=(202,70,58)); draw.ellipse((315,91,382,145),fill=(202,70,58)); draw.line((320,110,331,78),fill=(78,99,57),width=10); draw.ellipse((329,78,373,96),fill=(97,143,77))
        elif "banana" in subject:
            draw.arc((220,80,425,283),15,166,fill=(232,193,61),width=48); draw.line((240,117,229,99),fill=(135,105,50),width=8); draw.line((411,168,425,158),fill=(135,105,50),width=8)
        elif "pizza" in subject:
            draw.polygon([(239,100),(421,132),(323,260)],fill=(226,178,92),outline=(166,108,53)); draw.polygon([(251,112),(404,139),(325,239)],fill=(206,78,54))
            for x,y in [(303,146),(358,157),(328,195),(367,187)]: draw.ellipse((x,y,x+18,y+18),fill=(238,195,104))
        elif "bread" in subject:
            draw.rounded_rectangle((233,119,411,229),radius=53,fill=(187,131,77)); draw.arc((266,132,321,194),190,325,fill=(236,203,153),width=8); draw.arc((324,132,380,194),190,325,fill=(236,203,153),width=8)
        else:
            draw.polygon([(287,122),(355,115),(382,235),(258,235)],fill=(221,132,53)); draw.line((321,126,310,83),fill=(88,137,75),width=10); draw.line((322,120,352,83),fill=(101,157,82),width=9); draw.line((313,121,285,90),fill=(80,133,74),width=9)
    elif category == "nature":
        draw.rectangle((105,213,535,281),fill=(105,167,134))
        if "forest" in subject:
            for x,h in [(176,100),(247,135),(334,103),(418,147),(485,112)]:
                draw.polygon([(x,222-h),(x-37,222),(x+37,222)],fill=(56,113,78)); draw.rectangle((x-5,218,x+5,250),fill=(120,89,59))
        elif "mountain" in subject:
            draw.polygon([(118,227),(247,91),(338,227)],fill=(119,147,166)); draw.polygon([(247,91),(221,119),(254,113),(278,134)],fill=(250,250,246)); draw.polygon([(282,226),(412,112),(535,226)],fill=(91,123,140))
        elif "beach" in subject:
            draw.ellipse((413,101,469,157),fill=(235,185,81)); draw.rectangle((105,216,535,281),fill=(78,157,192)); draw.polygon([(105,216),(535,216),(535,237),(105,237)],fill=(225,192,135))
        elif "desert" in subject:
            draw.ellipse((416,97,474,155),fill=(234,169,81)); draw.ellipse((103,192,523,313),fill=(218,182,120)); draw.line((325,230,325,144),fill=(74,135,87),width=18); draw.line((325,191,288,168),fill=(74,135,87),width=14); draw.line((288,168,288,151),fill=(74,135,87),width=12)
        else:
            draw.rectangle((105,208,535,279),fill=(105,162,197)); draw.polygon([(243,110),(400,110),(361,232),(264,232)],fill=(175,200,211)); draw.line((328,163,328,253),fill=(250,255,255),width=37)
    elif category == "vehicles":
        if "car" in subject:
            draw.polygon([(196,198),(225,145),(367,145),(411,198),(437,204),(437,238),(188,238)],fill=(190,80,59)); draw.rectangle((241,154,352,192),fill=(171,214,222)); draw.ellipse((220,218,269,267),fill=(45,52,52)); draw.ellipse((354,218,403,267),fill=(45,52,52))
        elif "bicycle" in subject:
            draw.ellipse((197,184,292,279),outline=(62,96,142),width=9); draw.ellipse((357,184,452,279),outline=(62,96,142),width=9); draw.line((244,230,317,230,287,174,244,230,367,230,317,230),fill=(69,102,151),width=8); draw.line((367,230,396,176,417,176),fill=(69,102,151),width=8)
        elif "train" in subject:
            draw.rounded_rectangle((204,122,427,240),radius=20,fill=(80,123,150)); draw.rectangle((228,143,268,184),fill=(208,229,229)); draw.rectangle((282,143,322,184),fill=(208,229,229)); draw.rectangle((336,143,378,184),fill=(208,229,229)); draw.ellipse((231,216,271,256),fill=(50,54,54)); draw.ellipse((365,216,405,256),fill=(50,54,54))
        elif "airplane" in subject:
            draw.polygon([(425,174),(329,190),(282,251),(255,244),(282,184),(207,186),(181,210),(166,205),(194,164),(280,160),(302,105),(328,104),(325,160),(421,145)],fill=(100,128,166))
        else:
            draw.polygon([(210,236),(428,236),(393,266),(244,266)],fill=(115,139,159)); draw.line((318,110,318,233),fill=(85,104,122),width=10); draw.polygon([(306,120),(224,210),(306,210)],fill=(230,230,218)); draw.polygon([(330,139),(397,209),(330,209)],fill=(215,224,227))
    else:  # everyday objects
        if "chair" in subject:
            draw.rounded_rectangle((251,105,377,203),radius=15,fill=(164,117,72)); draw.rectangle((256,198,371,221),fill=(177,125,75)); draw.rectangle((265,221,279,266),fill=(122,85,54)); draw.rectangle((349,221,363,266),fill=(122,85,54))
        elif "clock" in subject:
            draw.ellipse((237,92,400,255),fill=(244,241,224),outline=(106,91,66),width=13); draw.line((319,173,319,123),fill=(51,61,57),width=8); draw.line((319,173,359,192),fill=(51,61,57),width=7)
        elif "lamp" in subject:
            draw.polygon([(267,118),(372,118),(350,175),(289,175)],fill=(217,169,87)); draw.line((319,174,319,242),fill=(96,105,94),width=11); draw.ellipse((269,236,369,255),fill=(96,105,94))
        elif "book" in subject:
            draw.polygon([(220,113),(316,135),(316,248),(220,226)],fill=(238,232,211),outline=(92,100,93)); draw.polygon([(316,135),(413,113),(413,226),(316,248)],fill=(253,250,235),outline=(92,100,93)); draw.line((242,151,292,161),fill=(139,149,137),width=5); draw.line((339,160,390,149),fill=(139,149,137),width=5)
        else:
            draw.rounded_rectangle((225,126,414,233),radius=23,fill=(77,91,98)); draw.rectangle((268,109,316,131),fill=(77,91,98)); draw.ellipse((284,140,369,225),fill=(35,45,48),outline=(193,199,186),width=8); draw.ellipse((309,164,346,201),fill=(130,158,159))
    label = subject.upper()
    try:
        font = ImageFont.truetype("arial.ttf", 27)
    except OSError:
        font = ImageFont.load_default()
    box = draw.textbbox((0, 0), label, font=font)
    draw.text(((640-(box[2]-box[0]))/2, 276), label, fill=fg, font=font)
    draw.text((82, 318), "ORIGINAL DEMO ILLUSTRATION", fill=fg)
    image.save(path, format="PNG", optimize=True)


async def main():
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    provider = AIProvider()
    image_rows = []
    for category, subjects in SUBJECTS.items():
        for index, subject in enumerate(subjects, 1):
            words = subject.split()
            attrs = {
                "animals": ["wildlife", "natural habitat", "animal"],
                "food": ["ingredient", "fresh", "food"],
                "nature": ["landscape", "outdoors", "environment"],
                "vehicles": ["transport", "travel", "machine"],
                "objects": ["everyday object", "interior", "still life"],
            }[category]
            caption = f"A clear illustration of a {subject} in a simple {category} scene."
            for copy in (1, 2):
                image_id = f"img-{category}-{index:02d}-{copy:02d}"
                path = IMAGE_DIR / f"{image_id}.png"
                make_illustration(path, category, subject)
                # One deliberately uncertain record demonstrates the review gate.
                confidence = 0.38 if image_id == "img-animals-02-01" else 0.96
                image_rows.append((image_id, f"{subject.title()} illustration {copy}", category, subject,
                    caption, json.dumps(attrs), confidence, f"data/images/{path.name}", "original-demo-illustration"))
    with db.transaction() as conn:
        for table in ("suggestions", "ai_calls", "jobs", "posts", "images"):
            conn.execute(f"DELETE FROM {table} WHERE tenant_id='demo'")
        conn.executemany("""INSERT INTO images(id,title,category,expected_subject,caption_hint,attributes_json,
          demo_confidence,image_url,source,status) VALUES (?,?,?,?,?,?,?,?,?,'pending')""", image_rows)
    cases = []
    examples = [
        ("Red fox habitat", "Field notes on the red fox, Vulpes vulpes, and its forest habitat.", "animals", "red fox", "img-animals-01-02"),
        ("A gray wolf pack", "How gray wolves travel and hunt across their native range.", "animals", "gray wolf", "img-animals-02-02"),
        ("Caring for a golden dog", "A guide to the golden dog as a loyal household companion.", "animals", "golden dog", "img-animals-03-02"),
        ("Brown bears in spring", "Brown bears forage after waking from winter dormancy.", "animals", "brown bear", "img-animals-04-02"),
        ("The white-tailed deer", "White-tailed deer move through woodland at dawn.", "animals", "white-tailed deer", "img-animals-05-02"),
        ("Growing a pine forest", "Pine forests shelter diverse plants and wildlife.", "nature", "pine forest", "img-nature-01-02"),
        ("A snowy mountain trail", "Walk a trail below a high snowy mountain peak.", "nature", "snowy mountain", "img-nature-02-02"),
        ("A perfect sourdough loaf", "Bake sourdough bread with a crisp crust and open crumb.", "food", "sourdough bread", "img-food-04-02"),
        ("Bicycles in the city", "Blue bicycles give commuters an easy way around town.", "vehicles", "blue bicycle", "img-vehicles-02-02"),
        ("Choosing a desk lamp", "A desk lamp makes close reading easier after sunset.", "objects", "desk lamp", "img-objects-03-02"),
    ]
    for title, body, category, subject, expected_image in examples:
        vector, meta = await provider.embed(f"{title}. {body}. {subject}. {category}.")
        post_id = "post-" + expected_image.removeprefix("img-")
        with db.transaction() as conn:
            conn.execute("""INSERT INTO posts(id,title,body,expected_category,expected_subject,vector_json)
              VALUES (?,?,?,?,?,?)""", (post_id, title, body, category, subject, json.dumps(vector)))
            conn.execute("""INSERT INTO ai_calls(id,provider,operation,model,post_id,status,cost_usd,duration_ms)
              VALUES (?,?, 'post_embedding', ?,?,'succeeded',?,?)""", (str(uuid.uuid4()), meta["provider"], meta["model"], post_id, meta["cost_usd"], meta["duration_ms"]))
        cases.append({"post_id": post_id, "expected_image_id": expected_image})
    (ROOT / "data" / "eval_set.json").write_text(json.dumps(cases, indent=2) + "\n", encoding="utf-8")
    print(f"Seeded {len(image_rows)} original demo illustrations and {len(cases)} labeled evaluation posts.")
    print("Run POST /jobs/vision to classify the corpus before matching.")


if __name__ == "__main__":
    asyncio.run(main())
