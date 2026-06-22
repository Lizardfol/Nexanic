-- ============================================================
--  Nexonic — Knowledge Archive  /  Demo SQL Script
--  Használható: SQL Query fülön belül futtatva
-- ============================================================

-- Összes tudásbejegyzés listázása
SELECT
    id,
    title,
    category,
    location,
    person_name,
    date_recorded,
    language,
    duration_sec,
    verified
FROM knowledge_entries
ORDER BY date_recorded DESC;

-- ─────────────────────────────────────────────────────────────
-- Keresés: csak ellenőrzött (verified) bejegyzések
SELECT title, person_name, location, category
FROM knowledge_entries
WHERE verified = 1
ORDER BY title;

-- ─────────────────────────────────────────────────────────────
-- Statisztika: kategóriánkénti bejegyzésszám
SELECT
    category,
    COUNT(*) AS count,
    ROUND(AVG(duration_sec) / 60.0, 1) AS avg_min
FROM knowledge_entries
GROUP BY category
ORDER BY count DESC;

-- ─────────────────────────────────────────────────────────────
-- JOIN: bejegyzések és a hozzájuk tartozó tagek
SELECT
    k.title,
    k.category,
    GROUP_CONCAT(t.tag, ', ') AS tags
FROM knowledge_entries k
LEFT JOIN tags t ON t.entry_id = k.id
GROUP BY k.id
ORDER BY k.id;

-- ─────────────────────────────────────────────────────────────
-- Leghosszabb interview session
SELECT
    s.id,
    k.title,
    s.robot_id,
    s.questions_asked,
    ROUND((JULIANDAY(s.ended_at) - JULIANDAY(s.started_at)) * 1440, 1) AS duration_min
FROM sessions s
JOIN knowledge_entries k ON k.id = s.entry_id
ORDER BY duration_min DESC
LIMIT 5;

-- ─────────────────────────────────────────────────────────────
-- Új bejegyzés hozzáadása (minta)
-- INSERT INTO knowledge_entries
--   (title, category, location, person_name, date_recorded, summary, language, duration_sec, verified)
-- VALUES
--   ('Palóc fonás', 'Mesterségek', 'Eger', 'Varga Ilona', '2024-05-01',
--    'Hagyományos palóc fonási technikák leírása.', 'hu', 1200, 0);
