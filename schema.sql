CREATE TABLE IF NOT EXISTS users (
    email TEXT PRIMARY KEY,
    firstName TEXT NOT NULL, 
    firstLastName TEXT NOT NULL, 
    secondLastName TEXT

);

CREATE TABLE IF NOT EXISTS students (
    email TEXT PRIMARY KEY,
    grade INTEGER NOT NULL CHECK (grade IN (5, 6, 7, 8, 9, 10, 11)),
    house TEXT NOT NULL CHECK (house IN ('Hood', 'Beatty', 'Nelson', 'Rodney')),
    FOREIGN KEY (email) REFERENCES users(email) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS admins (
    email TEXT PRIMARY KEY, 
    FOREIGN KEY (email) REFERENCES users(email) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS mathProblems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    textBody TEXT NOT NULL,
    imageCDN TEXT, 
    correctAnswer TEXT,
    pointsIfCorrect INTEGER NOT NULL,
    endsAt TEXT NOT NULL
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
    PRIMARY KEY (problemId, email),
    FOREIGN KEY (problemId) REFERENCES mathProblems(id) ON DELETE CASCADE
);


