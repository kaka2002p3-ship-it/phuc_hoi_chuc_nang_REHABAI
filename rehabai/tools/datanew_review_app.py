"""Human review UI for datanew repetition candidates."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import os
import tempfile
import math

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
QUEUE = Path(os.environ.get("DATANEW_REVIEW_QUEUE", ROOT / "data/annotations/datanew_rep_review_queue.csv"))
REVIEWS = Path(os.environ.get("DATANEW_REVIEW_OUTPUT", ROOT / "data/annotations/datanew_rep_reviewed.csv"))
REVIEW_TITLE = os.environ.get("DATANEW_REVIEW_TITLE", "Duyệt từng lần tập datanew")
KEYS = ["video_id", "rep_id"]
LABELS = ["uncertain", "correct", "incorrect"]


@st.cache_data
def load_queue(path: str, modified_ns: int) -> pd.DataFrame:
    del modified_ns
    table = pd.read_csv(path)
    table["rep_id"] = table["rep_id"].astype(int)
    return table


def load_reviews() -> pd.DataFrame:
    if not REVIEWS.is_file():
        return pd.DataFrame(columns=KEYS + ["completion_label", "review_status", "annotator_id", "notes", "reviewed_at"])
    table = pd.read_csv(REVIEWS, dtype={"video_id": str, "annotator_id": str})
    table["rep_id"] = table["rep_id"].astype(int)
    return table


def save_review(record: dict) -> None:
    reviews = load_reviews()
    match = (reviews.video_id.eq(record["video_id"]) & reviews.rep_id.eq(record["rep_id"])) if len(reviews) else []
    if len(reviews) and match.any():
        for key, value in record.items(): reviews.loc[match, key] = value
    else:
        reviews = pd.concat([reviews, pd.DataFrame([record])], ignore_index=True)
    REVIEWS.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="datanew_review_", suffix=".csv", dir=REVIEWS.parent)
    os.close(fd)
    try:
        reviews.to_csv(name, index=False, encoding="utf-8-sig")
        os.replace(name, REVIEWS)
    finally:
        if os.path.exists(name): os.unlink(name)


st.set_page_config(page_title=REVIEW_TITLE, page_icon=":material/fact_check:", layout="wide")
st.title(REVIEW_TITLE)
st.caption("Nhãn từ người duyệt được lưu riêng; dữ liệu gợi ý không bị biến thành nhãn chuẩn tự động.")

if not QUEUE.is_file():
    st.error(f"Không tìm thấy hàng đợi: {QUEUE}")
    st.stop()

queue = load_queue(str(QUEUE), QUEUE.stat().st_mtime_ns)
reviews = load_reviews()
review_map = reviews.set_index(KEYS).to_dict("index") if len(reviews) else {}
queue["saved_label"] = [review_map.get((str(r.video_id), int(r.rep_id)), {}).get("completion_label", "pending") for r in queue.itertuples()]

with st.sidebar:
    st.header("Bộ lọc")
    reviewer = st.text_input("Mã người duyệt", placeholder="VD: PT_01", key="reviewer")
    exercise = st.selectbox("Bài tập", ["Tất cả"] + sorted(queue.exercise.unique().tolist()))
    reviewed = int(queue.saved_label.ne("pending").sum())
    status_options = ["Chưa duyệt", "Đã duyệt", "Tất cả"]
    default_status = 1 if reviewed == len(queue) and len(queue) else 0
    status = st.selectbox("Trạng thái", status_options, index=default_status)
    priority_values = sorted(pd.to_numeric(queue.get("review_priority", pd.Series(dtype="float64")), errors="coerce").dropna().astype(int).unique().tolist())
    priority_filter = st.selectbox("Mức ưu tiên", ["Tất cả"] + priority_values, index=0)

filtered = queue.copy()
if exercise != "Tất cả": filtered = filtered[filtered.exercise.eq(exercise)]
if status == "Chưa duyệt": filtered = filtered[filtered.saved_label.eq("pending")]
elif status == "Đã duyệt": filtered = filtered[filtered.saved_label.ne("pending")]
if priority_filter != "Tất cả" and "review_priority" in filtered.columns:
    filtered = filtered[pd.to_numeric(filtered.review_priority, errors="coerce").eq(int(priority_filter))]

row = st.container(horizontal=True)
row.metric("Tổng ứng viên", len(queue))
row.metric("Đã duyệt", reviewed)
row.metric("Còn lại", len(queue) - reviewed)
row.metric("Đang hiển thị", len(filtered))

if filtered.empty:
    if reviewed == len(queue) and status == "Chưa duyệt" and priority_filter == "Tất cả":
        st.success("Đã duyệt hết hàng đợi. Hãy chọn ‘Đã duyệt’ hoặc ‘Tất cả’ để xem lại các bản ghi.")
    else:
        st.info("Không còn bản ghi phù hợp với bộ lọc.")
    st.stop()

st.session_state.setdefault("position", 0)
st.session_state.position = min(st.session_state.position, len(filtered)-1)
nav = st.container(horizontal=True, horizontal_alignment="left")
if nav.button("Trước", icon=":material/arrow_back:", disabled=st.session_state.position == 0):
    st.session_state.position -= 1; st.rerun()
nav.write(f"{st.session_state.position + 1} / {len(filtered)}")
if nav.button("Sau", icon=":material/arrow_forward:", disabled=st.session_state.position >= len(filtered)-1):
    st.session_state.position += 1; st.rerun()

item = filtered.iloc[st.session_state.position]
key = (str(item.video_id), int(item.rep_id))
prior = review_map.get(key, {})

# Streamlit's video element rounds numeric times down to whole seconds. Expand
# the requested rep window to a valid integer-second interval so short clips
# such as 0.13–0.46 s do not produce start_time == end_time.
raw_start = max(0.0, float(item.get("start_time_s", 0.0)))
raw_end = max(raw_start, float(item.get("end_time_s", raw_start + 1.0)))
video_start = math.floor(raw_start)
video_end = max(video_start + 1, math.ceil(raw_end))

left, right = st.columns([3, 2])
with left:
    st.subheader(f"{item.exercise} · {item.video_id} · lần {int(item.rep_id)}")
    video = Path(str(item.source_video_path))
    if video.is_file():
        view_mode = st.radio(
            "Phạm vi video",
            ["Toàn bộ video", "Chỉ đoạn ứng viên"],
            horizontal=True,
            key=f"video_view_{item.video_id}_{int(item.rep_id)}",
            help="Nên xem toàn bộ video trước khi quyết định nhãn. Đoạn ứng viên chỉ dùng để xem nhanh.",
        )
        if view_mode == "Chỉ đoạn ứng viên":
            st.video(video, start_time=video_start, end_time=video_end, loop=True)
        else:
            st.video(video, loop=False)
    else:
        st.error(f"Không tìm thấy video: {video}")
time_hint = (f" · {float(item.get('start_time_s', 0.0)):.2f}–{float(item.get('end_time_s', 0.0)):.2f} giây"
             if "start_time_s" in item.index and "end_time_s" in item.index else "")
st.caption(f"Đoạn gợi ý: frame {int(item.start_frame)}–{int(item.end_frame)}{time_hint}. Hãy xem toàn bộ video trước khi quyết định.")

with right:
    st.subheader("Xác nhận nhãn")
    original_label = str(item.get("original_label", item.get("completion_label", "uncertain")))
    if "original_label" in item.index or "completion_label" in item.index:
        reason = item.get("suspicion_reasons", item.get("suspicion_reason", "Không có"))
        st.info(f"Nhãn trước khi rà lại: **{original_label}**\n\nLý do nghi ngờ: {reason}")
    default_label = prior.get("completion_label", original_label if original_label in LABELS else "uncertain")
    with st.form(f"review_{item.video_id}_{int(item.rep_id)}", enter_to_submit=False):
        label = st.segmented_control("Kết quả", LABELS, default=default_label, required=True, width="stretch")
        start_frame = st.number_input("Frame bắt đầu", min_value=0, value=int(prior.get("start_frame", item.start_frame)), step=1)
        end_frame = st.number_input("Frame kết thúc", min_value=0, value=int(prior.get("end_frame", item.end_frame)), step=1)
        notes = st.text_area("Ghi chú", value=str(prior.get("notes", "")))
        submitted = st.form_submit_button("Lưu và sang bản ghi tiếp theo", icon=":material/save:", type="primary")
    if submitted:
        reviewer_clean = reviewer.strip()
        if not reviewer_clean:
            st.error("Hãy nhập mã người duyệt trước khi lưu.")
        elif label not in LABELS:
            st.error("Nhãn không hợp lệ.")
        elif int(end_frame) <= int(start_frame):
            st.error("Frame kết thúc phải lớn hơn frame bắt đầu.")
        else:
            save_review({"video_id": key[0], "rep_id": key[1], "exercise": item.exercise,
                         "source_video_path": str(item.source_video_path), "start_frame": int(start_frame),
                         "end_frame": int(end_frame), "completion_label": label,
                         "review_status": "reviewed" if label in {"correct", "incorrect"} else "needs_review",
                         "annotator_id": reviewer_clean, "notes": notes.strip(),
                         "reviewed_at": datetime.now(timezone.utc).isoformat()})
            st.cache_data.clear(); st.session_state.position = min(st.session_state.position, max(len(filtered)-2, 0)); st.rerun()

with st.expander("Bằng chứng động học"):
    def value_or_dash(name: str, fmt: str = ""):
        value = item.get(name, None)
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return "—"
        return format(float(value), fmt) if fmt else str(value)

    evidence = pd.DataFrame({"Chỉ số": ["Tín hiệu nhỏ nhất", "Tín hiệu lớn nhất", "Biên độ", "Độ lệch chuẩn", "Pha gợi ý"],
                             "Giá trị": [value_or_dash("signal_min", ".4f"), value_or_dash("signal_max", ".4f"),
                                         value_or_dash("signal_range", ".4f"), value_or_dash("signal_std", ".4f"), str(item.get("phase_hint", "—"))]})
    st.dataframe(evidence, hide_index=True)
    st.warning("Các chỉ số này chỉ giúp tìm đoạn chuyển động, không chứng minh động tác đúng hay sai.")

if len(reviews):
    confirmed = reviews[reviews.completion_label.isin(["correct", "incorrect"])].copy()
    st.download_button("Tải manifest nhãn đã xác nhận", confirmed.to_csv(index=False).encode("utf-8-sig"),
                       file_name="datanew_confirmed_labels.csv", mime="text/csv", icon=":material/download:")
