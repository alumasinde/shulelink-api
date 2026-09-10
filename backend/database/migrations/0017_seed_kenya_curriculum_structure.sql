-- Seed the current Kenyan basic education structure as editable data.
-- These rows are configuration, not application logic; schools can add, rename,
-- deactivate or replace them without changing code.

INSERT IGNORE INTO education_levels (id,tenant_id,curriculum_version_id,code,name,sequence_no)
SELECT UUID(),v.tenant_id,v.id,x.code,x.name,x.sequence_no
FROM curriculum_versions v
JOIN (
    SELECT 'pre_primary' code,'Pre-Primary' name,1 sequence_no
    UNION ALL SELECT 'primary','Primary',2
    UNION ALL SELECT 'junior_school','Junior School',3
    UNION ALL SELECT 'senior_school','Senior School',4
) x
WHERE v.code='kenya_cbc_current';

INSERT IGNORE INTO grades (id,tenant_id,education_level_id,code,name,sequence_no)
SELECT UUID(),e.tenant_id,e.id,x.code,x.name,x.sequence_no
FROM education_levels e
JOIN (
    SELECT 'pre_primary' level_code,'pp1' code,'PP1' name,1 sequence_no UNION ALL
    SELECT 'pre_primary','pp2','PP2',2 UNION ALL
    SELECT 'primary','grade_1','Grade 1',1 UNION ALL SELECT 'primary','grade_2','Grade 2',2 UNION ALL
    SELECT 'primary','grade_3','Grade 3',3 UNION ALL SELECT 'primary','grade_4','Grade 4',4 UNION ALL
    SELECT 'primary','grade_5','Grade 5',5 UNION ALL SELECT 'primary','grade_6','Grade 6',6 UNION ALL
    SELECT 'junior_school','grade_7','Grade 7',1 UNION ALL SELECT 'junior_school','grade_8','Grade 8',2 UNION ALL
    SELECT 'junior_school','grade_9','Grade 9',3 UNION ALL
    SELECT 'senior_school','grade_10','Grade 10',1 UNION ALL SELECT 'senior_school','grade_11','Grade 11',2 UNION ALL
    SELECT 'senior_school','grade_12','Grade 12',3
) x ON x.level_code=e.code;

INSERT IGNORE INTO pathways (id,tenant_id,curriculum_version_id,code,name,description)
SELECT UUID(),v.tenant_id,v.id,x.code,x.name,x.description
FROM curriculum_versions v
JOIN (
    SELECT 'arts_sports_science' code,'Arts and Sports Science' name,'Senior School pathway' description UNION ALL
    SELECT 'social_sciences','Social Sciences','Senior School pathway' UNION ALL
    SELECT 'stem','Science, Technology, Engineering and Mathematics','Senior School pathway'
) x
WHERE v.code='kenya_cbc_current';

INSERT IGNORE INTO tracks (id,tenant_id,pathway_id,code,name,description)
SELECT UUID(),p.tenant_id,p.id,x.code,x.name,x.description
FROM pathways p
JOIN (
    SELECT 'arts_sports_science' pathway_code,'sports' code,'Sports' name,'Track within the Arts and Sports Science pathway' description UNION ALL
    SELECT 'arts_sports_science','performing_arts','Performing Arts','Track within the Arts and Sports Science pathway' UNION ALL
    SELECT 'arts_sports_science','visual_arts','Visual Arts','Track within the Arts and Sports Science pathway' UNION ALL
    SELECT 'social_sciences','languages_literature','Languages and Literature','Track within the Social Sciences pathway' UNION ALL
    SELECT 'social_sciences','humanities_business','Humanities and Business Studies','Track within the Social Sciences pathway' UNION ALL
    SELECT 'stem','pure_sciences','Pure Sciences','Track within the STEM pathway' UNION ALL
    SELECT 'stem','applied_sciences','Applied Sciences','Track within the STEM pathway' UNION ALL
    SELECT 'stem','technical_engineering','Technical and Engineering','Track within the STEM pathway' UNION ALL
    SELECT 'stem','careers_technology','Careers and Technology Studies','Track within the STEM pathway'
) x ON x.pathway_code=p.code;
