"""Idempotent development seed data for the academic audit database.

The seed represents a small cross-section of a university while exercising all
relationships used by the administrator analytics queries.  It is intended for
local development and demonstrations only; it never removes existing records.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from database.database import get_session, initialize_database


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SeedSummary:
    """Counts of the records available after seeding completes."""

    departments: int
    programs: int
    faculty: int
    students: int
    course_offerings: int
    enrollments: int
    marks: int


def _insert_rows(session: Session, statement: str, rows: Iterable[dict[str, Any]]) -> None:
    """Insert rows without changing an existing matching natural key."""
    values = list(rows)
    if values:
        session.execute(text(statement), values)


def _grade_for_mark(total_marks: float) -> str:
    """Return the grade associated with a total mark out of 100."""
    if total_marks >= 90:
        return "O"
    if total_marks >= 80:
        return "A+"
    if total_marks >= 70:
        return "A"
    if total_marks >= 60:
        return "B+"
    if total_marks >= 55:
        return "B"
    if total_marks >= 50:
        return "C"
    if total_marks >= 40:
        return "P"
    return "F"


def _count(session: Session, table_name: str) -> int:
    """Return a table row count for the final seed summary."""
    return int(session.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar_one())


def _seed_reference_data(session: Session) -> None:
    """Seed departments, programs, academic calendar, and staff."""
    _insert_rows(
        session,
        """
        INSERT OR IGNORE INTO departments (department_code, department_name)
        VALUES (:department_code, :department_name)
        """,
        [
            {"department_code": "CSE", "department_name": "Computer Science and Engineering"},
            {"department_code": "ECE", "department_name": "Electronics and Communication Engineering"},
            {"department_code": "MBA", "department_name": "School of Management"},
        ],
    )
    _insert_rows(
        session,
        """
        INSERT OR IGNORE INTO academic_years
            (year_label, start_date, end_date, is_current)
        VALUES (:year_label, :start_date, :end_date, :is_current)
        """,
        [
            {"year_label": "2023-2024", "start_date": "2023-07-01", "end_date": "2024-06-30", "is_current": 0},
            {"year_label": "2024-2025", "start_date": "2024-07-01", "end_date": "2025-06-30", "is_current": 1},
        ],
    )
    _insert_rows(
        session,
        """
        INSERT OR IGNORE INTO programs
            (department_id, program_code, program_name, degree_level, duration_years)
        SELECT department_id, :program_code, :program_name, 'Undergraduate', 4
        FROM departments WHERE department_code = :department_code
        """,
        [
            {"department_code": "CSE", "program_code": "BTECH-CSE", "program_name": "B.Tech Computer Science and Engineering"},
            {"department_code": "ECE", "program_code": "BTECH-ECE", "program_name": "B.Tech Electronics and Communication Engineering"},
            {"department_code": "MBA", "program_code": "MBA", "program_name": "Master of Business Administration"},
        ],
    )
    _insert_rows(
        session,
        """
        INSERT OR IGNORE INTO semesters
            (academic_year_id, semester_number, semester_name, start_date, end_date)
        SELECT academic_year_id, :semester_number, :semester_name, :start_date, :end_date
        FROM academic_years WHERE year_label = '2024-2025'
        """,
        [
            {"semester_number": 1, "semester_name": "Odd Semester", "start_date": "2024-07-01", "end_date": "2024-12-20"},
            {"semester_number": 2, "semester_name": "Even Semester", "start_date": "2025-01-06", "end_date": "2025-06-30"},
        ],
    )
    _insert_rows(
        session,
        """
        INSERT OR IGNORE INTO faculty
            (department_id, employee_number, first_name, last_name, email, designation, joined_on)
        SELECT department_id, :employee_number, :first_name, :last_name, :email,
               :designation, :joined_on
        FROM departments WHERE department_code = :department_code
        """,
        [
            {"department_code": "CSE", "employee_number": "CSE-101", "first_name": "Anita", "last_name": "Rao", "email": "anita.rao@university.edu", "designation": "Professor", "joined_on": "2012-07-01"},
            {"department_code": "CSE", "employee_number": "CSE-102", "first_name": "Vikram", "last_name": "Shah", "email": "vikram.shah@university.edu", "designation": "Associate Professor", "joined_on": "2016-07-01"},
            {"department_code": "ECE", "employee_number": "ECE-101", "first_name": "Meera", "last_name": "Nair", "email": "meera.nair@university.edu", "designation": "Professor", "joined_on": "2011-07-01"},
            {"department_code": "ECE", "employee_number": "ECE-102", "first_name": "Arjun", "last_name": "Iyer", "email": "arjun.iyer@university.edu", "designation": "Assistant Professor", "joined_on": "2019-07-01"},
            {"department_code": "MBA", "employee_number": "MBA-101", "first_name": "Kavita", "last_name": "Menon", "email": "kavita.menon@university.edu", "designation": "Professor", "joined_on": "2013-07-01"},
            {"department_code": "MBA", "employee_number": "MBA-102", "first_name": "Rahul", "last_name": "Kapoor", "email": "rahul.kapoor@university.edu", "designation": "Assistant Professor", "joined_on": "2020-07-01"},
        ],
    )


def _seed_academic_records(session: Session) -> None:
    """Seed batches, students, offerings, enrolments, and published marks."""
    programs = [
        ("BTECH-CSE", "CSE", ["Programming Fundamentals", "Discrete Mathematics", "Data Structures"]),
        ("BTECH-ECE", "ECE", ["Circuit Analysis", "Digital Electronics", "Signals and Systems"]),
        ("MBA", "MBA", ["Managerial Economics", "Marketing Management", "Financial Accounting"]),
    ]
    _insert_rows(
        session,
        """
        INSERT OR IGNORE INTO batches (program_id, admission_year_id, batch_label)
        SELECT program.program_id, academic_year.academic_year_id, :batch_label
        FROM programs AS program CROSS JOIN academic_years AS academic_year
        WHERE program.program_code = :program_code AND academic_year.year_label = '2024-2025'
        """,
        [
            {"program_code": code, "batch_label": f"{code} 2024"}
            for code, _, _ in programs
        ],
    )
    _insert_rows(
        session,
        """
        INSERT OR IGNORE INTO sections (batch_id, section_name, capacity)
        SELECT batch_id, :section_name, 30 FROM batches WHERE batch_label = :batch_label
        """,
        [
            {"batch_label": f"{code} 2024", "section_name": section_name}
            for code, _, _ in programs
            for section_name in ("A", "B")
        ],
    )
    _insert_rows(
        session,
        """
        INSERT OR IGNORE INTO courses
            (department_id, course_code, course_title, credits, maximum_marks, minimum_pass_mark)
        SELECT department_id, :course_code, :course_title, 4, 100, 40
        FROM departments WHERE department_code = :department_code
        """,
        [
            {"department_code": department, "course_code": f"{department}{index:03d}", "course_title": title}
            for _, department, courses in programs
            for index, title in enumerate(courses, start=101)
        ],
    )

    student_rows: list[dict[str, Any]] = []
    given_names = ("Aarav", "Diya", "Ishaan", "Kavya", "Rohan", "Nisha", "Aditya", "Sneha", "Varun", "Pooja")
    family_names = ("Patel", "Reddy", "Kumar", "Das", "Singh", "Gupta", "Joshi", "Bose", "Verma", "Rao")
    for program_number, (program_code, _, _) in enumerate(programs, start=1):
        for section_name in ("A", "B"):
            for student_number in range(1, 11):
                serial = (program_number - 1) * 20 + (0 if section_name == "A" else 10) + student_number
                student_rows.append(
                    {
                        "batch_label": f"{program_code} 2024",
                        "student_number": f"2024{program_number:02d}{serial:03d}",
                        "first_name": given_names[(serial - 1) % len(given_names)],
                        "last_name": family_names[(serial - 1) % len(family_names)],
                        "email": f"student{serial:03d}@university.edu",
                        "date_of_birth": date(2005, (serial % 12) + 1, (serial % 27) + 1).isoformat(),
                        "gender": "Female" if serial % 2 == 0 else "Male",
                        "admission_date": "2024-07-01",
                    }
                )
    _insert_rows(
        session,
        """
        INSERT OR IGNORE INTO students
            (batch_id, student_number, first_name, last_name, email, date_of_birth, gender, admission_date)
        SELECT batch_id, :student_number, :first_name, :last_name, :email, :date_of_birth,
               :gender, :admission_date
        FROM batches WHERE batch_label = :batch_label
        """,
        student_rows,
    )

    offering_rows: list[dict[str, Any]] = []
    for program_code, department, courses in programs:
        for section_name in ("A", "B"):
            for course_index, _ in enumerate(courses, start=101):
                offering_rows.append(
                    {
                        "course_code": f"{department}{course_index:03d}",
                        "batch_label": f"{program_code} 2024",
                        "section_name": section_name,
                        "employee_number": f"{department}-{101 if course_index % 2 else 102}",
                        "room_number": f"{department}-{course_index - 100}{section_name}",
                    }
                )
    _insert_rows(
        session,
        """
        INSERT OR IGNORE INTO course_offerings
            (course_id, semester_id, section_id, faculty_id, room_number)
        SELECT course.course_id, semester.semester_id, section.section_id, faculty.faculty_id,
               :room_number
        FROM courses AS course
        JOIN sections AS section ON section.section_name = :section_name
        JOIN batches AS batch ON batch.batch_id = section.batch_id
        JOIN semesters AS semester ON semester.semester_number = 1
        JOIN faculty ON faculty.employee_number = :employee_number
        WHERE course.course_code = :course_code AND batch.batch_label = :batch_label
        """,
        offering_rows,
    )
    _insert_rows(
        session,
        """
        INSERT OR IGNORE INTO enrollments (student_id, offering_id, enrolled_on, enrollment_status)
        SELECT student.student_id, offering.offering_id, '2024-07-08', 'Completed'
        FROM students AS student
        JOIN sections AS section ON section.batch_id = student.batch_id
        JOIN course_offerings AS offering ON offering.section_id = section.section_id
        WHERE student.email LIKE 'student%@university.edu'
          AND (
              (CAST(substr(student.student_number, -3) AS INTEGER) % 20
                   BETWEEN 1 AND 10 AND section.section_name = 'A')
              OR ((CAST(substr(student.student_number, -3) AS INTEGER) % 20 = 0
                   OR CAST(substr(student.student_number, -3) AS INTEGER) % 20
                      BETWEEN 11 AND 19) AND section.section_name = 'B')
          )
        """,
        [{}],
    )
    _insert_rows(
        session,
        """
        INSERT OR IGNORE INTO marks
            (enrollment_id, internal_marks, external_marks, total_marks, grade, result_status, published_on)
        SELECT enrollment_id, :internal_marks, :external_marks, :total_marks, :grade,
               :result_status, '2024-12-28'
        FROM enrollments WHERE enrollment_id = :enrollment_id
        """,
        _mark_rows(session),
    )


def _mark_rows(session: Session) -> list[dict[str, Any]]:
    """Build deterministic, varied marks for all seeded completed enrolments."""
    enrollment_ids = session.execute(
        text(
            """
            SELECT enrollment.enrollment_id
            FROM enrollments AS enrollment
            JOIN students AS student ON student.student_id = enrollment.student_id
            LEFT JOIN marks ON marks.enrollment_id = enrollment.enrollment_id
            WHERE student.email LIKE 'student%@university.edu'
              AND marks.mark_id IS NULL
            ORDER BY enrollment.enrollment_id
            """
        )
    ).scalars()
    rows: list[dict[str, Any]] = []
    for index, enrollment_id in enumerate(enrollment_ids, start=1):
        total_marks = float(32 + ((index * 11) % 64))
        internal_marks = round(total_marks * 0.3, 2)
        external_marks = round(total_marks - internal_marks, 2)
        rows.append(
            {
                "enrollment_id": enrollment_id,
                "internal_marks": internal_marks,
                "external_marks": external_marks,
                "total_marks": total_marks,
                "grade": _grade_for_mark(total_marks),
                "result_status": "Pass" if total_marks >= 40 else "Fail",
            }
        )
    return rows


def seed_database() -> SeedSummary:
    """Initialize and populate the local database with demonstration data.

    The function can safely run more than once.  Existing data is preserved and
    every insert uses the schema's natural unique keys to avoid duplicates.
    """
    initialize_database()
    with get_session() as session:
        _seed_reference_data(session)
        _seed_academic_records(session)
        summary = SeedSummary(
            departments=_count(session, "departments"),
            programs=_count(session, "programs"),
            faculty=_count(session, "faculty"),
            students=_count(session, "students"),
            course_offerings=_count(session, "course_offerings"),
            enrollments=_count(session, "enrollments"),
            marks=_count(session, "marks"),
        )
    LOGGER.info("Database seed completed: %s", summary)
    return summary


if __name__ == "__main__":
    print(seed_database())
