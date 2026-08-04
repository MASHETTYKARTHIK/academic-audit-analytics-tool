-- Academic Audit Analytics Tool - SQLite schema
--
-- This schema models student outcomes at the level of a student's enrolment in
-- a specific course offering.  SQLite foreign-key enforcement must be enabled
-- on every connection with: PRAGMA foreign_keys = ON;

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS departments (
    department_id   INTEGER PRIMARY KEY,
    department_code TEXT NOT NULL UNIQUE
        CHECK (length(trim(department_code)) BETWEEN 2 AND 10),
    department_name TEXT NOT NULL UNIQUE
        CHECK (length(trim(department_name)) >= 3),
    created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS programs (
    program_id      INTEGER PRIMARY KEY,
    department_id   INTEGER NOT NULL,
    program_code    TEXT NOT NULL UNIQUE
        CHECK (length(trim(program_code)) BETWEEN 2 AND 20),
    program_name    TEXT NOT NULL,
    degree_level    TEXT NOT NULL
        CHECK (degree_level IN ('Undergraduate', 'Postgraduate', 'Doctoral')),
    duration_years  INTEGER NOT NULL CHECK (duration_years BETWEEN 1 AND 8),
    is_active       INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    UNIQUE (department_id, program_name)
);

CREATE TABLE IF NOT EXISTS academic_years (
    academic_year_id INTEGER PRIMARY KEY,
    year_label       TEXT NOT NULL UNIQUE
        CHECK (year_label GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]'),
    start_date       TEXT NOT NULL CHECK (date(start_date) IS NOT NULL),
    end_date         TEXT NOT NULL CHECK (date(end_date) IS NOT NULL),
    is_current       INTEGER NOT NULL DEFAULT 0 CHECK (is_current IN (0, 1)),
    CHECK (date(end_date) > date(start_date))
);

CREATE TABLE IF NOT EXISTS semesters (
    semester_id      INTEGER PRIMARY KEY,
    academic_year_id INTEGER NOT NULL,
    semester_number  INTEGER NOT NULL CHECK (semester_number BETWEEN 1 AND 12),
    semester_name    TEXT NOT NULL,
    start_date       TEXT NOT NULL CHECK (date(start_date) IS NOT NULL),
    end_date         TEXT NOT NULL CHECK (date(end_date) IS NOT NULL),
    FOREIGN KEY (academic_year_id) REFERENCES academic_years(academic_year_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    UNIQUE (academic_year_id, semester_number),
    CHECK (date(end_date) > date(start_date))
);

-- A batch is a student cohort admitted to one program in one academic year.
CREATE TABLE IF NOT EXISTS batches (
    batch_id          INTEGER PRIMARY KEY,
    program_id        INTEGER NOT NULL,
    admission_year_id INTEGER NOT NULL,
    batch_label       TEXT NOT NULL,
    FOREIGN KEY (program_id) REFERENCES programs(program_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (admission_year_id) REFERENCES academic_years(academic_year_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    UNIQUE (program_id, admission_year_id),
    UNIQUE (program_id, batch_label)
);

CREATE TABLE IF NOT EXISTS faculty (
    faculty_id        INTEGER PRIMARY KEY,
    department_id     INTEGER NOT NULL,
    employee_number   TEXT NOT NULL UNIQUE,
    first_name        TEXT NOT NULL,
    last_name         TEXT NOT NULL,
    email             TEXT NOT NULL UNIQUE COLLATE NOCASE,
    designation       TEXT NOT NULL,
    employment_status TEXT NOT NULL DEFAULT 'Active'
        CHECK (employment_status IN ('Active', 'On Leave', 'Inactive')),
    joined_on         TEXT NOT NULL CHECK (date(joined_on) IS NOT NULL),
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CHECK (instr(email, '@') > 1)
);

CREATE TABLE IF NOT EXISTS courses (
    course_id        INTEGER PRIMARY KEY,
    department_id    INTEGER NOT NULL,
    course_code      TEXT NOT NULL UNIQUE,
    course_title     TEXT NOT NULL,
    credits          INTEGER NOT NULL CHECK (credits BETWEEN 1 AND 8),
    maximum_marks    INTEGER NOT NULL DEFAULT 100 CHECK (maximum_marks > 0),
    minimum_pass_mark INTEGER NOT NULL DEFAULT 40 CHECK (
        minimum_pass_mark >= 0 AND minimum_pass_mark <= maximum_marks
    ),
    is_active        INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    UNIQUE (department_id, course_title)
);

CREATE TABLE IF NOT EXISTS students (
    student_id        INTEGER PRIMARY KEY,
    batch_id          INTEGER NOT NULL,
    student_number    TEXT NOT NULL UNIQUE,
    first_name        TEXT NOT NULL,
    last_name         TEXT NOT NULL,
    email             TEXT NOT NULL UNIQUE COLLATE NOCASE,
    date_of_birth     TEXT NOT NULL CHECK (date(date_of_birth) IS NOT NULL),
    gender            TEXT NOT NULL CHECK (gender IN ('Female', 'Male', 'Non-binary', 'Prefer not to say')),
    admission_date    TEXT NOT NULL CHECK (date(admission_date) IS NOT NULL),
    enrollment_status TEXT NOT NULL DEFAULT 'Active'
        CHECK (enrollment_status IN ('Active', 'Graduated', 'Withdrawn', 'Suspended')),
    FOREIGN KEY (batch_id) REFERENCES batches(batch_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CHECK (instr(email, '@') > 1)
);

-- A section represents a group of students within one batch (for example, A).
CREATE TABLE IF NOT EXISTS sections (
    section_id   INTEGER PRIMARY KEY,
    batch_id     INTEGER NOT NULL,
    section_name TEXT NOT NULL CHECK (length(trim(section_name)) BETWEEN 1 AND 10),
    capacity     INTEGER NOT NULL DEFAULT 60 CHECK (capacity BETWEEN 1 AND 250),
    FOREIGN KEY (batch_id) REFERENCES batches(batch_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    UNIQUE (batch_id, section_name)
);

-- A course offering is a single course taught to one section in one semester.
-- It is the point where course, faculty, semester, and student cohort meet.
CREATE TABLE IF NOT EXISTS course_offerings (
    offering_id  INTEGER PRIMARY KEY,
    course_id    INTEGER NOT NULL,
    semester_id  INTEGER NOT NULL,
    section_id   INTEGER NOT NULL,
    faculty_id   INTEGER NOT NULL,
    room_number  TEXT,
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (semester_id) REFERENCES semesters(semester_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (section_id) REFERENCES sections(section_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    UNIQUE (course_id, semester_id, section_id)
);

CREATE TABLE IF NOT EXISTS enrollments (
    enrollment_id     INTEGER PRIMARY KEY,
    student_id        INTEGER NOT NULL,
    offering_id       INTEGER NOT NULL,
    enrolled_on       TEXT NOT NULL DEFAULT CURRENT_DATE CHECK (date(enrolled_on) IS NOT NULL),
    enrollment_status TEXT NOT NULL DEFAULT 'Enrolled'
        CHECK (enrollment_status IN ('Enrolled', 'Dropped', 'Completed')),
    FOREIGN KEY (student_id) REFERENCES students(student_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (offering_id) REFERENCES course_offerings(offering_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    UNIQUE (student_id, offering_id)
);

CREATE TABLE IF NOT EXISTS marks (
    mark_id          INTEGER PRIMARY KEY,
    enrollment_id    INTEGER NOT NULL UNIQUE,
    internal_marks   REAL NOT NULL DEFAULT 0 CHECK (internal_marks >= 0),
    external_marks   REAL NOT NULL DEFAULT 0 CHECK (external_marks >= 0),
    total_marks      REAL NOT NULL CHECK (total_marks >= 0),
    grade            TEXT NOT NULL CHECK (grade IN ('O', 'A+', 'A', 'B+', 'B', 'C', 'P', 'F', 'I')),
    result_status    TEXT NOT NULL CHECK (result_status IN ('Pass', 'Fail', 'Incomplete')),
    published_on     TEXT NOT NULL DEFAULT CURRENT_DATE CHECK (date(published_on) IS NOT NULL),
    FOREIGN KEY (enrollment_id) REFERENCES enrollments(enrollment_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CHECK (total_marks = internal_marks + external_marks)
);

-- SQLite CHECK constraints cannot inspect related rows.  These triggers retain
-- the cohort and course-mark rules at the database boundary.
CREATE TRIGGER IF NOT EXISTS trg_enrollments_match_offering_batch_insert
BEFORE INSERT ON enrollments
FOR EACH ROW
WHEN NOT EXISTS (
    SELECT 1
    FROM students AS student
    JOIN course_offerings AS offering ON offering.offering_id = NEW.offering_id
    JOIN sections AS section ON section.section_id = offering.section_id
    WHERE student.student_id = NEW.student_id
      AND student.batch_id = section.batch_id
)
BEGIN
    SELECT RAISE(ABORT, 'student and course offering must belong to the same batch');
END;

CREATE TRIGGER IF NOT EXISTS trg_enrollments_match_offering_batch_update
BEFORE UPDATE OF student_id, offering_id ON enrollments
FOR EACH ROW
WHEN NOT EXISTS (
    SELECT 1
    FROM students AS student
    JOIN course_offerings AS offering ON offering.offering_id = NEW.offering_id
    JOIN sections AS section ON section.section_id = offering.section_id
    WHERE student.student_id = NEW.student_id
      AND student.batch_id = section.batch_id
)
BEGIN
    SELECT RAISE(ABORT, 'student and course offering must belong to the same batch');
END;

CREATE TRIGGER IF NOT EXISTS trg_marks_respect_course_rules_insert
BEFORE INSERT ON marks
FOR EACH ROW
WHEN EXISTS (
    SELECT 1
    FROM enrollments AS enrollment
    JOIN course_offerings AS offering ON offering.offering_id = enrollment.offering_id
    JOIN courses AS course ON course.course_id = offering.course_id
    WHERE enrollment.enrollment_id = NEW.enrollment_id
      AND (
          NEW.total_marks > course.maximum_marks
          OR (NEW.result_status = 'Pass' AND NEW.total_marks < course.minimum_pass_mark)
          OR (NEW.result_status = 'Fail' AND NEW.total_marks >= course.minimum_pass_mark)
      )
)
BEGIN
    SELECT RAISE(ABORT, 'marks do not satisfy the course result rules');
END;

CREATE TRIGGER IF NOT EXISTS trg_marks_respect_course_rules_update
BEFORE UPDATE OF enrollment_id, total_marks, result_status ON marks
FOR EACH ROW
WHEN EXISTS (
    SELECT 1
    FROM enrollments AS enrollment
    JOIN course_offerings AS offering ON offering.offering_id = enrollment.offering_id
    JOIN courses AS course ON course.course_id = offering.course_id
    WHERE enrollment.enrollment_id = NEW.enrollment_id
      AND (
          NEW.total_marks > course.maximum_marks
          OR (NEW.result_status = 'Pass' AND NEW.total_marks < course.minimum_pass_mark)
          OR (NEW.result_status = 'Fail' AND NEW.total_marks >= course.minimum_pass_mark)
      )
)
BEGIN
    SELECT RAISE(ABORT, 'marks do not satisfy the course result rules');
END;

-- Foreign keys are not indexed automatically by SQLite.  These indexes cover
-- the joins and grouping paths used by the planned analytics queries.
CREATE INDEX IF NOT EXISTS idx_programs_department ON programs(department_id);
CREATE INDEX IF NOT EXISTS idx_semesters_academic_year ON semesters(academic_year_id);
CREATE INDEX IF NOT EXISTS idx_batches_program ON batches(program_id);
CREATE INDEX IF NOT EXISTS idx_batches_admission_year ON batches(admission_year_id);
CREATE INDEX IF NOT EXISTS idx_faculty_department ON faculty(department_id);
CREATE INDEX IF NOT EXISTS idx_courses_department ON courses(department_id);
CREATE INDEX IF NOT EXISTS idx_students_batch ON students(batch_id);
CREATE INDEX IF NOT EXISTS idx_sections_batch ON sections(batch_id);
CREATE INDEX IF NOT EXISTS idx_offerings_course ON course_offerings(course_id);
CREATE INDEX IF NOT EXISTS idx_offerings_semester ON course_offerings(semester_id);
CREATE INDEX IF NOT EXISTS idx_offerings_section ON course_offerings(section_id);
CREATE INDEX IF NOT EXISTS idx_offerings_faculty ON course_offerings(faculty_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_student ON enrollments(student_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_offering ON enrollments(offering_id);
CREATE INDEX IF NOT EXISTS idx_marks_result_status ON marks(result_status);
