from pathlib import Path
import csv, random
import numpy as np
from PIL import Image, ImageDraw

SHAPES = ["circle", "square", "triangle"]
LABEL = {s: i for i, s in enumerate(SHAPES)}


def draw_shape(draw, shape, bbox, fill=0):
    x0, y0, x1, y1 = bbox

    if shape == "circle":
        draw.ellipse(bbox, fill=fill)

    elif shape == "square":
        draw.rectangle(bbox, fill=fill)

    elif shape == "triangle":
        xm = (x0 + x1) / 2
        draw.polygon([(xm, y0), (x0, y1), (x1, y1)], fill=fill)

    else:
        raise ValueError(shape)


def make_global_mask(global_shape, size=128, margin=16):
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)

    bbox = (margin, margin, size - margin, size - margin)
    draw_shape(draw, global_shape, bbox, fill=255)

    return mask


def make_hierarchical_image(
    global_shape,
    local_shape,
    size=128,
    local_size=9,
    spacing=5,
    margin=16,
    jitter=2,
):
    img = Image.new("L", (size, size), 255)
    draw = ImageDraw.Draw(img)

    mask = make_global_mask(global_shape, size=size, margin=margin)
    mask_np = np.array(mask)

    step = local_size + spacing
    radius = local_size // 2

    for y in range(margin, size - margin, step):
        for x in range(margin, size - margin, step):
            jx = random.randint(-jitter, jitter)
            jy = random.randint(-jitter, jitter)

            cx = x + jx
            cy = y + jy

            x0, y0 = cx - radius, cy - radius
            x1, y1 = cx + radius, cy + radius

            if x0 < 0 or y0 < 0 or x1 >= size or y1 >= size:
                continue

            patch = mask_np[y0:y1, x0:x1]

            # Only draw local shape if it is mostly inside the global shape.
            if patch.mean() > 220:
                draw_shape(draw, local_shape, (x0, y0, x1, y1), fill=0)

    return img


def generate_split(out_dir, split_name, pairs, n_per_pair=500, seed=0):
    random.seed(seed)

    split_dir = Path(out_dir) / split_name
    img_dir = split_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    rows = []

    for global_shape, local_shape in pairs:
        for i in range(n_per_pair):
            img = make_hierarchical_image(global_shape, local_shape)

            fname = f"{global_shape}_{local_shape}_{i}.png"
            img.save(img_dir / fname)

            rows.append({
                "filename": fname,
                "global_shape": global_shape,
                "local_shape": local_shape,
                "global_label": LABEL[global_shape],
                "local_label": LABEL[local_shape],
            })

    with open(split_dir / "labels.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def main():
    # Hold out some global-local combinations for compositional generalization.
    train_pairs = [
        ("circle", "circle"),
        ("circle", "square"),
        ("square", "square"),
        ("square", "triangle"),
        ("triangle", "triangle"),
        ("triangle", "circle"),
    ]

    test_pairs_seen = train_pairs

    test_pairs_ood = [
        ("circle", "triangle"),
        ("square", "circle"),
        ("triangle", "square"),
    ]

    out_dir = "hierarchical_shapes"

    generate_split(out_dir, "train", train_pairs, n_per_pair=1000, seed=1)
    generate_split(out_dir, "test_seen", test_pairs_seen, n_per_pair=200, seed=2)
    generate_split(out_dir, "test_ood", test_pairs_ood, n_per_pair=200, seed=3)


if __name__ == "__main__":
    main()