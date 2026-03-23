from app.models import User


def normalize_name(name: str) -> str:
    return "".join(str(name or "").strip().lower().split())


def build_normalized_students(students: list[User]) -> list[tuple[str, User]]:
    result = []
    for student in students:
        key = normalize_name(student.name or "")
        if key:
            result.append((key, student))
    return result


def find_candidates(raw_name: str, normalized_students: list[tuple[str, User]]) -> list[User]:
    normalized = normalize_name(raw_name)
    if not normalized:
        return []
    matches = [
        student for key, student in normalized_students
        if normalized in key or key in normalized
    ]
    return list({s.id: s for s in matches}.values())
