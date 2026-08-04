"""SQLAlchemy ORM models for the academic audit database schema.

The models mirror ``database/schema.sql``.  The schema file remains the source
of truth for database initialization, while these classes provide typed ORM
access for seed data, analytics, and future administrative workflows.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class shared by every mapped academic-audit entity."""


class Department(Base):
    """Academic department that owns programs, faculty, and courses."""

    __tablename__ = "departments"

    department_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    department_code: Mapped[str] = mapped_column(String(10), unique=True)
    department_name: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    programs: Mapped[list[Program]] = relationship(back_populates="department")
    faculty_members: Mapped[list[Faculty]] = relationship(back_populates="department")
    courses: Mapped[list[Course]] = relationship(back_populates="department")

    __table_args__ = (
        CheckConstraint(
            "length(trim(department_code)) BETWEEN 2 AND 10",
            name="ck_departments_code_length",
        ),
        CheckConstraint(
            "length(trim(department_name)) >= 3",
            name="ck_departments_name_length",
        ),
    )


class Program(Base):
    """Degree program offered by a department."""

    __tablename__ = "programs"

    program_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.department_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    program_code: Mapped[str] = mapped_column(String(20), unique=True)
    program_name: Mapped[str] = mapped_column(String(255))
    degree_level: Mapped[str] = mapped_column(String(20))
    duration_years: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")

    department: Mapped[Department] = relationship(back_populates="programs")
    batches: Mapped[list[Batch]] = relationship(back_populates="program")

    __table_args__ = (
        UniqueConstraint("department_id", "program_name", name="uq_program_department_name"),
        CheckConstraint(
            "degree_level IN ('Undergraduate', 'Postgraduate', 'Doctoral')",
            name="ck_programs_degree_level",
        ),
        CheckConstraint(
            "duration_years BETWEEN 1 AND 8", name="ck_programs_duration_years"
        ),
        CheckConstraint("is_active IN (0, 1)", name="ck_programs_is_active"),
        Index("idx_programs_department", "department_id"),
    )


class AcademicYear(Base):
    """Academic calendar year containing one or more semesters."""

    __tablename__ = "academic_years"

    academic_year_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    year_label: Mapped[str] = mapped_column(String(9), unique=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    semesters: Mapped[list[Semester]] = relationship(back_populates="academic_year")
    admitted_batches: Mapped[list[Batch]] = relationship(
        back_populates="admission_year"
    )

    __table_args__ = (
        CheckConstraint(
            "year_label GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]'",
            name="ck_academic_years_label",
        ),
        CheckConstraint(
            "date(end_date) > date(start_date)", name="ck_academic_years_dates"
        ),
        CheckConstraint("is_current IN (0, 1)", name="ck_academic_years_current"),
    )


class Semester(Base):
    """A numbered teaching period within an academic year."""

    __tablename__ = "semesters"

    semester_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    academic_year_id: Mapped[int] = mapped_column(
        ForeignKey(
            "academic_years.academic_year_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    semester_number: Mapped[int] = mapped_column(Integer)
    semester_name: Mapped[str] = mapped_column(String(100))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)

    academic_year: Mapped[AcademicYear] = relationship(back_populates="semesters")
    course_offerings: Mapped[list[CourseOffering]] = relationship(
        back_populates="semester"
    )

    __table_args__ = (
        UniqueConstraint(
            "academic_year_id", "semester_number", name="uq_semester_year_number"
        ),
        CheckConstraint(
            "semester_number BETWEEN 1 AND 12", name="ck_semesters_number"
        ),
        CheckConstraint("date(end_date) > date(start_date)", name="ck_semesters_dates"),
        Index("idx_semesters_academic_year", "academic_year_id"),
    )


class Batch(Base):
    """Cohort admitted to one program in a given academic year."""

    __tablename__ = "batches"

    batch_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(
        ForeignKey("programs.program_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    admission_year_id: Mapped[int] = mapped_column(
        ForeignKey(
            "academic_years.academic_year_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    batch_label: Mapped[str] = mapped_column(String(100))

    program: Mapped[Program] = relationship(back_populates="batches")
    admission_year: Mapped[AcademicYear] = relationship(
        back_populates="admitted_batches"
    )
    sections: Mapped[list[Section]] = relationship(back_populates="batch")
    students: Mapped[list[Student]] = relationship(back_populates="batch")

    __table_args__ = (
        UniqueConstraint(
            "program_id", "admission_year_id", name="uq_batch_program_admission_year"
        ),
        UniqueConstraint("program_id", "batch_label", name="uq_batch_program_label"),
        Index("idx_batches_program", "program_id"),
        Index("idx_batches_admission_year", "admission_year_id"),
    )


class Faculty(Base):
    """Faculty member eligible to teach course offerings."""

    __tablename__ = "faculty"

    faculty_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.department_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    employee_number: Mapped[str] = mapped_column(String(50), unique=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255, collation="NOCASE"), unique=True)
    designation: Mapped[str] = mapped_column(String(100))
    employment_status: Mapped[str] = mapped_column(
        String(20), default="Active", server_default="Active"
    )
    joined_on: Mapped[date] = mapped_column(Date)

    department: Mapped[Department] = relationship(back_populates="faculty_members")
    course_offerings: Mapped[list[CourseOffering]] = relationship(
        back_populates="faculty_member"
    )

    __table_args__ = (
        CheckConstraint(
            "employment_status IN ('Active', 'On Leave', 'Inactive')",
            name="ck_faculty_employment_status",
        ),
        CheckConstraint("instr(email, '@') > 1", name="ck_faculty_email"),
        Index("idx_faculty_department", "department_id"),
    )


class Course(Base):
    """Catalogued course owned by an academic department."""

    __tablename__ = "courses"

    course_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.department_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    course_code: Mapped[str] = mapped_column(String(20), unique=True)
    course_title: Mapped[str] = mapped_column(String(255))
    credits: Mapped[int] = mapped_column(Integer)
    maximum_marks: Mapped[int] = mapped_column(Integer, default=100, server_default="100")
    minimum_pass_mark: Mapped[int] = mapped_column(
        Integer, default=40, server_default="40"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")

    department: Mapped[Department] = relationship(back_populates="courses")
    course_offerings: Mapped[list[CourseOffering]] = relationship(back_populates="course")

    __table_args__ = (
        UniqueConstraint("department_id", "course_title", name="uq_course_department_title"),
        CheckConstraint("credits BETWEEN 1 AND 8", name="ck_courses_credits"),
        CheckConstraint("maximum_marks > 0", name="ck_courses_maximum_marks"),
        CheckConstraint(
            "minimum_pass_mark >= 0 AND minimum_pass_mark <= maximum_marks",
            name="ck_courses_pass_mark",
        ),
        CheckConstraint("is_active IN (0, 1)", name="ck_courses_is_active"),
        Index("idx_courses_department", "department_id"),
    )


class Student(Base):
    """Student enrolled in a program batch."""

    __tablename__ = "students"

    student_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("batches.batch_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    student_number: Mapped[str] = mapped_column(String(50), unique=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255, collation="NOCASE"), unique=True)
    date_of_birth: Mapped[date] = mapped_column(Date)
    gender: Mapped[str] = mapped_column(String(30))
    admission_date: Mapped[date] = mapped_column(Date)
    enrollment_status: Mapped[str] = mapped_column(
        String(20), default="Active", server_default="Active"
    )

    batch: Mapped[Batch] = relationship(back_populates="students")
    enrollments: Mapped[list[Enrollment]] = relationship(back_populates="student")

    __table_args__ = (
        CheckConstraint(
            "gender IN ('Female', 'Male', 'Non-binary', 'Prefer not to say')",
            name="ck_students_gender",
        ),
        CheckConstraint(
            "enrollment_status IN ('Active', 'Graduated', 'Withdrawn', 'Suspended')",
            name="ck_students_status",
        ),
        CheckConstraint("instr(email, '@') > 1", name="ck_students_email"),
        Index("idx_students_batch", "batch_id"),
    )


class Section(Base):
    """Teaching section within a student batch."""

    __tablename__ = "sections"

    section_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("batches.batch_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    section_name: Mapped[str] = mapped_column(String(10))
    capacity: Mapped[int] = mapped_column(Integer, default=60, server_default="60")

    batch: Mapped[Batch] = relationship(back_populates="sections")
    course_offerings: Mapped[list[CourseOffering]] = relationship(
        back_populates="section"
    )

    __table_args__ = (
        UniqueConstraint("batch_id", "section_name", name="uq_section_batch_name"),
        CheckConstraint(
            "length(trim(section_name)) BETWEEN 1 AND 10",
            name="ck_sections_name_length",
        ),
        CheckConstraint("capacity BETWEEN 1 AND 250", name="ck_sections_capacity"),
        Index("idx_sections_batch", "batch_id"),
    )


class CourseOffering(Base):
    """A course taught by one faculty member to one section in one semester."""

    __tablename__ = "course_offerings"

    offering_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.course_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    semester_id: Mapped[int] = mapped_column(
        ForeignKey("semesters.semester_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    section_id: Mapped[int] = mapped_column(
        ForeignKey("sections.section_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    faculty_id: Mapped[int] = mapped_column(
        ForeignKey("faculty.faculty_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    room_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    course: Mapped[Course] = relationship(back_populates="course_offerings")
    semester: Mapped[Semester] = relationship(back_populates="course_offerings")
    section: Mapped[Section] = relationship(back_populates="course_offerings")
    faculty_member: Mapped[Faculty] = relationship(back_populates="course_offerings")
    enrollments: Mapped[list[Enrollment]] = relationship(back_populates="course_offering")

    __table_args__ = (
        UniqueConstraint(
            "course_id", "semester_id", "section_id", name="uq_offering_course_term_section"
        ),
        Index("idx_offerings_course", "course_id"),
        Index("idx_offerings_semester", "semester_id"),
        Index("idx_offerings_section", "section_id"),
        Index("idx_offerings_faculty", "faculty_id"),
    )


class Enrollment(Base):
    """A student's registration in one scheduled course offering."""

    __tablename__ = "enrollments"

    enrollment_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.student_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    offering_id: Mapped[int] = mapped_column(
        ForeignKey(
            "course_offerings.offering_id", onupdate="CASCADE", ondelete="RESTRICT"
        ),
        nullable=False,
    )
    enrolled_on: Mapped[date] = mapped_column(Date, server_default=func.current_date())
    enrollment_status: Mapped[str] = mapped_column(
        String(20), default="Enrolled", server_default="Enrolled"
    )

    student: Mapped[Student] = relationship(back_populates="enrollments")
    course_offering: Mapped[CourseOffering] = relationship(back_populates="enrollments")
    marks: Mapped[Optional[Marks]] = relationship(back_populates="enrollment", uselist=False)

    __table_args__ = (
        UniqueConstraint("student_id", "offering_id", name="uq_enrollment_student_offering"),
        CheckConstraint(
            "enrollment_status IN ('Enrolled', 'Dropped', 'Completed')",
            name="ck_enrollments_status",
        ),
        Index("idx_enrollments_student", "student_id"),
        Index("idx_enrollments_offering", "offering_id"),
    )


class Marks(Base):
    """Published marks and result for one course enrollment."""

    __tablename__ = "marks"

    mark_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(
        ForeignKey("enrollments.enrollment_id", onupdate="CASCADE", ondelete="RESTRICT"),
        unique=True,
        nullable=False,
    )
    internal_marks: Mapped[float] = mapped_column(
        Float, default=0.0, server_default="0"
    )
    external_marks: Mapped[float] = mapped_column(
        Float, default=0.0, server_default="0"
    )
    total_marks: Mapped[float] = mapped_column(Float)
    grade: Mapped[str] = mapped_column(String(2))
    result_status: Mapped[str] = mapped_column(String(20))
    published_on: Mapped[date] = mapped_column(Date, server_default=func.current_date())

    enrollment: Mapped[Enrollment] = relationship(back_populates="marks")

    __table_args__ = (
        CheckConstraint("internal_marks >= 0", name="ck_marks_internal_non_negative"),
        CheckConstraint("external_marks >= 0", name="ck_marks_external_non_negative"),
        CheckConstraint("total_marks >= 0", name="ck_marks_total_non_negative"),
        CheckConstraint(
            "grade IN ('O', 'A+', 'A', 'B+', 'B', 'C', 'P', 'F', 'I')",
            name="ck_marks_grade",
        ),
        CheckConstraint(
            "result_status IN ('Pass', 'Fail', 'Incomplete')",
            name="ck_marks_result_status",
        ),
        CheckConstraint(
            "total_marks = internal_marks + external_marks",
            name="ck_marks_total_components",
        ),
        Index("idx_marks_result_status", "result_status"),
    )
