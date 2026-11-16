"""Patient-facing names; artifact class IDs and source labels stay immutable."""

DISPLAY_EXERCISE_NAMES = {
    1: "Vai - Nâng vật",
    # Artifact v2 historically calls ID 2 ELBOW_EXTENSION, while the reviewed
    # datanew temporal task calls its active phase ELBOW_FLEXION.  The patient
    # performs a full flexion/extension cycle, so the neutral display name
    # avoids pretending that the two independently versioned tasks are equal.
    2: "Khuỷu tay - Gập/duỗi khuỷu tay",
    3: "Cổ tay - Gập/duỗi cổ tay",
    4: "Bàn tay - Mở bàn tay",
    6: "Cổ - Nghiêng cổ sang hai bên",
}

EXERCISE_SEMANTICS = {
    2: {
        "production_code": "ELBOW_EXTENSION",
        "research_aliases": ["ELBOW_FLEXION"],
        "display_name_vi": DISPLAY_EXERCISE_NAMES[2],
        "integration_status": "separate_tasks_not_yet_promoted",
    },
    4: {
        "production_code": "HAND_OPENING",
        "research_aliases": ["HAND_OPENING"],
        "display_name_vi": DISPLAY_EXERCISE_NAMES[4],
        "integration_status": "production_artifact_only",
    },
}
