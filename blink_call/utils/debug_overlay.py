import cv2


def draw_debug(frame, info: dict, color=(42, 90, 255)):
    """
    Draw debug information (bbox + text) on the image

    :param frame: Original image (BGR)
    :param result: Inference result dictionary
    :param color: Drawing color

    :return: The drawn image
    """
    if frame is None:
        return frame

    draw_frame = frame.copy()
    h, w = frame.shape[:2]

    bboxes = info.get("debug_bbox_xyxy", [])
    for bbox in bboxes:
        box = get_safe_bbox(bbox, w, h)
        if box is None:
            continue

        left, top, right, bottom = box
        cv2.rectangle(draw_frame, (left, top), (right, bottom), color, 2)

    debug_info = info.get("debug_info", "")
    if isinstance(debug_info, str) and debug_info:
        draw_text_block(draw_frame, debug_info, color)

    return draw_frame


def get_safe_bbox(bbox, w, h):
    if not (isinstance(bbox, (list, tuple)) and len(bbox) == 4):
        return None

    try:
        x1, y1, x2, y2 = (int(float(v)) for v in bbox)
    except (TypeError, ValueError):
        return None

    x1 = max(0, min(x1, w - 1))
    x2 = max(0, min(x2, w - 1))
    y1 = max(0, min(y1, h - 1))
    y2 = max(0, min(y2, h - 1))

    return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)


def draw_text_block(img, text, color):
    lines = text.split("\n")

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    thickness = 1

    margin = 10
    line_gap = 6

    h, w = img.shape[:2]

    sizes = [cv2.getTextSize(line, font, font_scale, thickness) for line in lines]
    total_height = sum(sz[0][1] + line_gap for sz in sizes) - line_gap

    y = h - margin - total_height

    for (line, ((tw, th), _)) in zip(lines, sizes):
        x = w - margin - tw
        y += th

        cv2.putText(
            img,
            line,
            (x, y),
            font,
            font_scale,
            color,
            thickness,
            cv2.LINE_AA,
        )

        y += line_gap
