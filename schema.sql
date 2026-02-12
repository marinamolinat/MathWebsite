CREATE TABLE IF NOT EXISTS users (
    email TEXT PRIMARY KEY,
    firstName TEXT NOT NULL, 
    firstLastName TEXT NOT NULL, 
    secondLastName TEXT

);

CREATE TABLE IF NOT EXISTS students (
    email TEXT PRIMARY KEY,
    grade INTEGER NOT NULL CHECK (grade IN (5, 6, 7, 8, 9, 10, 11)),
    FOREIGN KEY (email) REFERENCES users(email) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS admins (
    email TEXT PRIMARY KEY,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (email) REFERENCES users(email) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS mathProblems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    writtenQuestion TEXT,
    imageCDN TEXT, 
    correctAnswer TEXT,
    isActive BOOLEAN DEFAULT 1,
    endsAt TIMESTAMP
);


CREATE TABLE IF NOT EXISTS mathProblemsGrades (
    problemId INTEGER,
    grade INTEGER CHECK (grade IN (5,6,7,8,9,10,11)),
    PRIMARY KEY (problemId, grade),
    FOREIGN KEY (problemId) REFERENCES mathProblems(id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS studentsAnswers(
    problemId INTEGER,
    email TEXT,
    answer TEXT NOT NULL,
    scoreReceived INTEGER, 
    createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
    PRIMARY KEY (problemId, email)
);


