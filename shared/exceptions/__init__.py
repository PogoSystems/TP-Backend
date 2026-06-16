class CourseNotFoundError(Exception):
    """Se lanza cuando un curso no existe en el sistema."""

    def __init__(self, course_id: int) -> None:
        super().__init__(f"Course with id={course_id} was not found.")
        self.course_id = course_id
