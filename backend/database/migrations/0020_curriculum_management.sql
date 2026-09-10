-- Curriculum Management: central platform templates + tenant adoption metadata.
-- Platform curriculum is versioned and published centrally. Schools select a published
-- template and receive a tenant-local snapshot that remains editable without changing
-- the platform catalog or historical academic records.

CREATE TABLE IF NOT EXISTS platform_curriculum_templates (
    id CHAR(36) NOT NULL,
    code VARCHAR(100) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT NULL,
    country_code VARCHAR(10) NULL,
    framework_code VARCHAR(100) NOT NULL,
    version_no INT UNSIGNED NOT NULL DEFAULT 1,
    status VARCHAR(30) NOT NULL DEFAULT 'draft',
    effective_from DATE NULL,
    effective_to DATE NULL,
    is_default TINYINT(1) NOT NULL DEFAULT 0,
    created_by CHAR(36) NULL,
    updated_by CHAR(36) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_platform_curriculum_template_code_version (code,version_no),
    KEY ix_platform_curriculum_template_status (status,is_default)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS platform_curriculum_levels (
    id CHAR(36) NOT NULL,
    template_id CHAR(36) NOT NULL,
    code VARCHAR(80) NOT NULL,
    name VARCHAR(160) NOT NULL,
    sequence_no INT NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uq_platform_curriculum_level (template_id,code),
    CONSTRAINT fk_pcl_template FOREIGN KEY (template_id) REFERENCES platform_curriculum_templates(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS platform_curriculum_grades (
    id CHAR(36) NOT NULL,
    template_id CHAR(36) NOT NULL,
    education_level_id CHAR(36) NOT NULL,
    code VARCHAR(80) NOT NULL,
    name VARCHAR(160) NOT NULL,
    sequence_no INT NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uq_platform_curriculum_grade (template_id,code),
    CONSTRAINT fk_pcg_template FOREIGN KEY (template_id) REFERENCES platform_curriculum_templates(id) ON DELETE CASCADE,
    CONSTRAINT fk_pcg_level FOREIGN KEY (education_level_id) REFERENCES platform_curriculum_levels(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS platform_curriculum_learning_areas (
    id CHAR(36) NOT NULL,
    template_id CHAR(36) NOT NULL,
    code VARCHAR(100) NOT NULL,
    name VARCHAR(180) NOT NULL,
    description TEXT NULL,
    sequence_no INT NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uq_platform_curriculum_learning_area (template_id,code),
    CONSTRAINT fk_pcla_template FOREIGN KEY (template_id) REFERENCES platform_curriculum_templates(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS platform_curriculum_subjects (
    id CHAR(36) NOT NULL,
    template_id CHAR(36) NOT NULL,
    learning_area_id CHAR(36) NULL,
    code VARCHAR(100) NOT NULL,
    name VARCHAR(180) NOT NULL,
    subject_type VARCHAR(80) NOT NULL DEFAULT 'core',
    description TEXT NULL,
    sequence_no INT NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uq_platform_curriculum_subject (template_id,code),
    CONSTRAINT fk_pcs_template FOREIGN KEY (template_id) REFERENCES platform_curriculum_templates(id) ON DELETE CASCADE,
    CONSTRAINT fk_pcs_learning_area FOREIGN KEY (learning_area_id) REFERENCES platform_curriculum_learning_areas(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS platform_curriculum_subject_offerings (
    id CHAR(36) NOT NULL,
    template_id CHAR(36) NOT NULL,
    grade_id CHAR(36) NOT NULL,
    subject_id CHAR(36) NOT NULL,
    pathway_id CHAR(36) NULL,
    track_id CHAR(36) NULL,
    requirement_type VARCHAR(60) NOT NULL DEFAULT 'required',
    weekly_periods DECIMAL(5,2) NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_platform_curriculum_offering (template_id,grade_id,subject_id,pathway_id,track_id),
    CONSTRAINT fk_pcso_template FOREIGN KEY (template_id) REFERENCES platform_curriculum_templates(id) ON DELETE CASCADE,
    CONSTRAINT fk_pcso_grade FOREIGN KEY (grade_id) REFERENCES platform_curriculum_grades(id) ON DELETE CASCADE,
    CONSTRAINT fk_pcso_subject FOREIGN KEY (subject_id) REFERENCES platform_curriculum_subjects(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS platform_curriculum_pathways (
    id CHAR(36) NOT NULL,
    template_id CHAR(36) NOT NULL,
    code VARCHAR(100) NOT NULL,
    name VARCHAR(180) NOT NULL,
    description TEXT NULL,
    sequence_no INT NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uq_platform_curriculum_pathway (template_id,code),
    CONSTRAINT fk_pcp_template FOREIGN KEY (template_id) REFERENCES platform_curriculum_templates(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS platform_curriculum_tracks (
    id CHAR(36) NOT NULL,
    template_id CHAR(36) NOT NULL,
    pathway_id CHAR(36) NOT NULL,
    code VARCHAR(100) NOT NULL,
    name VARCHAR(180) NOT NULL,
    description TEXT NULL,
    sequence_no INT NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uq_platform_curriculum_track (template_id,pathway_id,code),
    CONSTRAINT fk_pct_template FOREIGN KEY (template_id) REFERENCES platform_curriculum_templates(id) ON DELETE CASCADE,
    CONSTRAINT fk_pct_pathway FOREIGN KEY (pathway_id) REFERENCES platform_curriculum_pathways(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS platform_curriculum_subject_combinations (
    id CHAR(36) NOT NULL,
    template_id CHAR(36) NOT NULL,
    grade_id CHAR(36) NULL,
    pathway_id CHAR(36) NULL,
    track_id CHAR(36) NULL,
    code VARCHAR(100) NOT NULL,
    name VARCHAR(180) NOT NULL,
    description TEXT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_platform_curriculum_combination (template_id,code),
    CONSTRAINT fk_pcc_template FOREIGN KEY (template_id) REFERENCES platform_curriculum_templates(id) ON DELETE CASCADE,
    CONSTRAINT fk_pcc_grade FOREIGN KEY (grade_id) REFERENCES platform_curriculum_grades(id) ON DELETE SET NULL,
    CONSTRAINT fk_pcc_pathway FOREIGN KEY (pathway_id) REFERENCES platform_curriculum_pathways(id) ON DELETE SET NULL,
    CONSTRAINT fk_pcc_track FOREIGN KEY (track_id) REFERENCES platform_curriculum_tracks(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS platform_curriculum_combination_subjects (
    id CHAR(36) NOT NULL,
    combination_id CHAR(36) NOT NULL,
    subject_id CHAR(36) NOT NULL,
    is_required TINYINT(1) NOT NULL DEFAULT 1,
    sort_order INT NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    UNIQUE KEY uq_platform_curriculum_combination_subject (combination_id,subject_id),
    CONSTRAINT fk_pccs_combination FOREIGN KEY (combination_id) REFERENCES platform_curriculum_subject_combinations(id) ON DELETE CASCADE,
    CONSTRAINT fk_pccs_subject FOREIGN KEY (subject_id) REFERENCES platform_curriculum_subjects(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS tenant_curriculum_profiles (
    id CHAR(36) NOT NULL,
    tenant_id CHAR(36) NOT NULL,
    platform_template_id CHAR(36) NOT NULL,
    template_code VARCHAR(100) NOT NULL,
    template_version INT UNSIGNED NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    selected_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    selected_by CHAR(36) NULL,
    allow_local_customization TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_tenant_curriculum_profile (tenant_id),
    KEY ix_tenant_curriculum_template (tenant_id,platform_template_id),
    CONSTRAINT fk_tcp_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT IGNORE INTO tenant_permissions (id,tenant_id,code,name)
SELECT UUID(),t.id,p.code,p.name FROM tenants t CROSS JOIN (
    SELECT 'curriculum.read' code,'View curriculum configuration' name
    UNION ALL SELECT 'curriculum.manage','Manage school curriculum configuration'
) p;

INSERT IGNORE INTO tenant_role_permissions (role_id,permission_id)
SELECT r.id,p.id FROM tenant_roles r JOIN tenant_permissions p ON p.tenant_id=r.tenant_id
WHERE r.code='school_admin' AND p.code IN ('curriculum.read','curriculum.manage');

INSERT IGNORE INTO tenant_role_permissions (role_id,permission_id)
SELECT r.id,p.id FROM tenant_roles r JOIN tenant_permissions p ON p.tenant_id=r.tenant_id
WHERE r.code='registrar' AND p.code='curriculum.read';

INSERT IGNORE INTO platform_permissions (id,code,name)
VALUES (UUID(),'curriculum.manage','Manage platform curriculum templates');

INSERT IGNORE INTO platform_role_permissions (platform_role_id,platform_permission_id)
SELECT r.id,p.id FROM platform_roles r CROSS JOIN platform_permissions p
WHERE r.code='platform_admin' AND p.code='curriculum.manage';

INSERT IGNORE INTO platform_curriculum_templates
(id,code,name,description,country_code,framework_code,version_no,status,is_default)
VALUES
('00000000-0000-0000-0000-00000000cbc1','kenya-cbc','Kenya CBC / CBE Basic Education','Baseline configurable Kenya Competency Based Curriculum template for Pre-Primary through Senior School.','KE','kenya_cbc',1,'published',1);

INSERT IGNORE INTO platform_curriculum_levels (id,template_id,code,name,sequence_no) VALUES
('10000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-00000000cbc1','pre_primary','Pre-Primary',1),
('10000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-00000000cbc1','primary','Primary',2),
('10000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-00000000cbc1','junior_school','Junior School',3),
('10000000-0000-0000-0000-000000000004','00000000-0000-0000-0000-00000000cbc1','senior_school','Senior School',4);

INSERT IGNORE INTO platform_curriculum_grades (id,template_id,education_level_id,code,name,sequence_no)
SELECT UUID(),'00000000-0000-0000-0000-00000000cbc1',l.id,x.code,x.name,x.seq FROM platform_curriculum_levels l JOIN (
SELECT 'pre_primary' level_code,'pp1' code,'PP1' name,1 seq UNION ALL SELECT 'pre_primary','pp2','PP2',2
UNION ALL SELECT 'primary','grade_1','Grade 1',1 UNION ALL SELECT 'primary','grade_2','Grade 2',2 UNION ALL SELECT 'primary','grade_3','Grade 3',3
UNION ALL SELECT 'primary','grade_4','Grade 4',4 UNION ALL SELECT 'primary','grade_5','Grade 5',5 UNION ALL SELECT 'primary','grade_6','Grade 6',6
UNION ALL SELECT 'junior_school','grade_7','Grade 7',1 UNION ALL SELECT 'junior_school','grade_8','Grade 8',2 UNION ALL SELECT 'junior_school','grade_9','Grade 9',3
UNION ALL SELECT 'senior_school','grade_10','Grade 10',1 UNION ALL SELECT 'senior_school','grade_11','Grade 11',2 UNION ALL SELECT 'senior_school','grade_12','Grade 12',3
) x ON x.level_code=l.code;

INSERT IGNORE INTO platform_curriculum_pathways (id,template_id,code,name,description,sequence_no) VALUES
('20000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-00000000cbc1','arts_sports_science','Arts and Sports Science','Senior School pathway',1),
('20000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-00000000cbc1','social_sciences','Social Sciences','Senior School pathway',2),
('20000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-00000000cbc1','stem','Science, Technology, Engineering and Mathematics (STEM)','Senior School pathway',3);

INSERT IGNORE INTO platform_curriculum_tracks (id,template_id,pathway_id,code,name,description,sequence_no) VALUES
('30000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-00000000cbc1','20000000-0000-0000-0000-000000000001','sports','Sports','Arts and Sports Science track',1),
('30000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-00000000cbc1','20000000-0000-0000-0000-000000000001','performing_arts','Performing Arts','Arts and Sports Science track',2),
('30000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-00000000cbc1','20000000-0000-0000-0000-000000000001','visual_arts','Visual Arts','Arts and Sports Science track',3),
('30000000-0000-0000-0000-000000000004','00000000-0000-0000-0000-00000000cbc1','20000000-0000-0000-0000-000000000002','languages_literature','Languages and Literature','Social Sciences track',1),
('30000000-0000-0000-0000-000000000005','00000000-0000-0000-0000-00000000cbc1','20000000-0000-0000-0000-000000000002','humanities_business','Humanities and Business Studies','Social Sciences track',2),
('30000000-0000-0000-0000-000000000006','00000000-0000-0000-0000-00000000cbc1','20000000-0000-0000-0000-000000000003','pure_sciences','Pure Sciences','STEM track',1),
('30000000-0000-0000-0000-000000000007','00000000-0000-0000-0000-00000000cbc1','20000000-0000-0000-0000-000000000003','applied_sciences','Applied Sciences','STEM track',2),
('30000000-0000-0000-0000-000000000008','00000000-0000-0000-0000-00000000cbc1','20000000-0000-0000-0000-000000000003','technical_engineering','Technical and Engineering','STEM track',3),
('30000000-0000-0000-0000-000000000009','00000000-0000-0000-0000-00000000cbc1','20000000-0000-0000-0000-000000000003','careers_technology','Careers and Technology Studies','STEM track',4);

INSERT IGNORE INTO platform_curriculum_learning_areas (id,template_id,code,name,sequence_no) VALUES
('40000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-00000000cbc1','languages_literature','Languages and Literature',1),
('40000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-00000000cbc1','mathematics','Mathematics',2),
('40000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-00000000cbc1','social_sciences','Social Sciences',3),
('40000000-0000-0000-0000-000000000004','00000000-0000-0000-0000-00000000cbc1','stem','STEM',4),
('40000000-0000-0000-0000-000000000005','00000000-0000-0000-0000-00000000cbc1','arts_sports','Arts and Sports Science',5),
('40000000-0000-0000-0000-000000000006','00000000-0000-0000-0000-00000000cbc1','integrated_learning','Integrated Learning and Community Service',6);

INSERT IGNORE INTO platform_curriculum_subjects (id,template_id,learning_area_id,code,name,subject_type,sequence_no)
SELECT UUID(),'00000000-0000-0000-0000-00000000cbc1',la.id,x.code,x.name,x.subject_type,x.seq
FROM platform_curriculum_learning_areas la JOIN (
SELECT 'languages_literature' area,'english' code,'English' name,'core' subject_type,1 seq UNION ALL
SELECT 'languages_literature','kiswahili','Kiswahili','core',2 UNION ALL
SELECT 'languages_literature','ksl','Kenya Sign Language (KSL)','elective',3 UNION ALL
SELECT 'languages_literature','literature_english','Literature in English','elective',4 UNION ALL
SELECT 'languages_literature','indigenous_languages','Indigenous Languages','elective',5 UNION ALL
SELECT 'languages_literature','fasihi_kiswahili','Fasihi ya Kiswahili','elective',6 UNION ALL
SELECT 'languages_literature','arabic','Arabic','elective',7 UNION ALL SELECT 'languages_literature','french','French','elective',8 UNION ALL
SELECT 'languages_literature','german','German','elective',9 UNION ALL SELECT 'languages_literature','mandarin','Mandarin Chinese','elective',10 UNION ALL
SELECT 'mathematics','core_mathematics','Core Mathematics','core',11 UNION ALL SELECT 'mathematics','essential_mathematics','Essential Mathematics','core',12 UNION ALL
SELECT 'social_sciences','cre','Christian Religious Education','elective',13 UNION ALL SELECT 'social_sciences','ire','Islamic Religious Education','elective',14 UNION ALL
SELECT 'social_sciences','hre','Hindu Religious Education','elective',15 UNION ALL SELECT 'social_sciences','business_studies','Business Studies','elective',16 UNION ALL
SELECT 'social_sciences','history_citizenship','History and Citizenship','elective',17 UNION ALL SELECT 'social_sciences','geography','Geography','elective',18 UNION ALL
SELECT 'stem','biology','Biology','elective',19 UNION ALL SELECT 'stem','chemistry','Chemistry','elective',20 UNION ALL SELECT 'stem','physics','Physics','elective',21 UNION ALL
SELECT 'stem','general_science','General Science','elective',22 UNION ALL SELECT 'stem','agriculture','Agriculture','elective',23 UNION ALL
SELECT 'stem','computer_studies','Computer Studies','elective',24 UNION ALL SELECT 'stem','home_science','Home Science','elective',25 UNION ALL
SELECT 'stem','aviation','Aviation','elective',26 UNION ALL SELECT 'stem','building_construction','Building Construction','elective',27 UNION ALL
SELECT 'stem','electricity','Electricity','elective',28 UNION ALL SELECT 'stem','metalwork','Metalwork','elective',29 UNION ALL
SELECT 'stem','power_mechanics','Power Mechanics','elective',30 UNION ALL SELECT 'stem','wood_technology','Wood Technology','elective',31 UNION ALL
SELECT 'stem','media_technology','Media Technology','elective',32 UNION ALL SELECT 'stem','marine_fisheries','Marine and Fisheries Technology','elective',33 UNION ALL
SELECT 'arts_sports','sports_recreation','Sports and Recreation','elective',34 UNION ALL SELECT 'arts_sports','music_dance','Music and Dance','elective',35 UNION ALL
SELECT 'arts_sports','theatre_film','Theatre and Film','elective',36 UNION ALL SELECT 'arts_sports','fine_arts','Fine Arts','elective',37 UNION ALL
SELECT 'integrated_learning','community_service_learning','Community Service Learning (CSL)','core',38 UNION ALL
SELECT 'integrated_learning','physical_education','Physical Education','co_curricular',39 UNION ALL SELECT 'integrated_learning','ict_skills','ICT Skills','co_curricular',40 UNION ALL
SELECT 'integrated_learning','ppi','Pastoral Programme Instruction (PPI)','co_curricular',41
) x ON x.area=la.code;

INSERT IGNORE INTO platform_curriculum_subject_offerings (id,template_id,grade_id,subject_id,requirement_type,weekly_periods)
SELECT UUID(),'00000000-0000-0000-0000-00000000cbc1',g.id,s.id,
CASE WHEN s.code IN ('english','kiswahili','community_service_learning','core_mathematics','essential_mathematics') THEN 'required' ELSE 'elective' END,
CASE WHEN s.code IN ('english','kiswahili','core_mathematics','essential_mathematics') THEN 5 WHEN s.code='community_service_learning' THEN 3 ELSE NULL END
FROM platform_curriculum_grades g JOIN platform_curriculum_subjects s
WHERE g.code IN ('grade_10','grade_11','grade_12') AND s.code IN ('english','kiswahili','core_mathematics','essential_mathematics','community_service_learning','sports_recreation','music_dance','theatre_film','fine_arts','literature_english','indigenous_languages','fasihi_kiswahili','ksl','arabic','french','german','mandarin','cre','ire','hre','business_studies','history_citizenship','geography','biology','chemistry','physics','general_science','agriculture','computer_studies','home_science','aviation','building_construction','electricity','metalwork','power_mechanics','wood_technology','media_technology','marine_fisheries');

INSERT IGNORE INTO platform_curriculum_subject_offerings (id,template_id,grade_id,subject_id,requirement_type,weekly_periods)
SELECT UUID(),'00000000-0000-0000-0000-00000000cbc1',g.id,s.id,'required',NULL
FROM platform_curriculum_grades g JOIN platform_curriculum_subjects s
WHERE g.code IN ('pp1','pp2','grade_1','grade_2','grade_3','grade_4','grade_5','grade_6','grade_7','grade_8','grade_9')
AND s.code IN ('english','kiswahili');
