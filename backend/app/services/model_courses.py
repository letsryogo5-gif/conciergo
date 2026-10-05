from uuid import uuid4

from app.model_course_sample_data import SAMPLE_MODEL_COURSES
from app.models import ModelCourse, ModelCourseRequest, Spot

_published_courses = [course.model_copy(deep=True) for course in SAMPLE_MODEL_COURSES]


def list_model_courses() -> list[ModelCourse]:
    return [course.model_copy(deep=True) for course in _published_courses]


def publish_model_course(
    request: ModelCourseRequest,
    available_spots: list[Spot],
) -> ModelCourse:
    spots_by_id = {spot.id: spot for spot in available_spots}
    missing_ids = [spot_id for spot_id in request.spot_ids if spot_id not in spots_by_id]
    if missing_ids:
        raise ValueError(f"スポットが見つかりません: {', '.join(missing_ids)}")

    course = ModelCourse(
        id=f"community-{uuid4().hex}",
        title=request.title,
        description=request.description,
        region=request.region,
        creator=request.creator,
        image_url=spots_by_id[request.spot_ids[0]].image_url,
        spot_ids=request.spot_ids.copy(),
        likes=0,
    )
    _published_courses.insert(0, course)
    return course.model_copy(deep=True)
