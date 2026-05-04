from datetime import date, datetime, timedelta

from .extensions import db
from .models import (
    Region, Prison, Department, User,
    Template, TemplateSection, TemplateCriterion,
    AnnualPlan, PlanItem,
    Mission, MissionRegion, MissionPrisonReport,
    MissionResponse, Observation, ObservationAction, AuditLog,
    SCORE_LABELS
)


# =========================================================
# بيانات مرجعية
# =========================================================

REGIONS = [
    'الرياض',
    'مكة المكرمة',
    'المدينة المنورة',
    'القصيم',
    'المنطقة الشرقية',
    'عسير',
    'تبوك',
    'حائل',
    'الحدود الشمالية',
    'جازان',
    'نجران',
    'الباحة',
    'الجوف',
]


PRISONS = {
    'الرياض': [
        'سجن الحائر',
        'سجن الملز',
        'إصلاحية الرياض',
        'سجن النساء بالرياض',
    ],
    'مكة المكرمة': [
        'سجن مكة العام',
        'إصلاحية جدة',
        'سجن الطائف',
        'سجن رابغ',
    ],
    'المدينة المنورة': [
        'سجن المدينة العام',
        'إصلاحية ينبع',
        'سجن العلا',
    ],
    'القصيم': [
        'سجن بريدة',
        'إصلاحية عنيزة',
        'سجن الرس',
    ],
    'المنطقة الشرقية': [
        'سجن الدمام',
        'إصلاحية الأحساء',
        'سجن الجبيل',
        'سجن الخبر',
    ],
    'عسير': [
        'سجن أبها',
        'إصلاحية خميس مشيط',
        'سجن بيشة',
    ],
    'تبوك': [
        'سجن تبوك العام',
        'سجن الوجه',
    ],
    'حائل': [
        'سجن حائل العام',
        'إصلاحية حائل',
    ],
    'الحدود الشمالية': [
        'سجن عرعر العام',
        'سجن رفحاء',
    ],
    'جازان': [
        'سجن جازان العام',
        'سجن صبيا',
    ],
    'نجران': [
        'سجن نجران العام',
        'سجن شرورة',
    ],
    'الباحة': [
        'سجن الباحة العام',
        'سجن بلجرشي',
    ],
    'الجوف': [
        'سجن سكاكا العام',
        'سجن القريات',
    ],
}


DEPARTMENTS = [
    ('إدارة تقنية المعلومات', 'IT'),
    ('إدارة السلامة', 'SAFETY'),
    ('إدارة العمليات', 'OPS'),
    ('إدارة المخزون والعهد', 'WAREHOUSE'),
    ('إدارة الموارد البشرية', 'HR'),
    ('الإدارة المالية', 'FIN'),
    ('إدارة الصيانة والمرافق', 'MAINT'),
    ('إدارة الأمن والسلامة', 'SECURITY'),
    ('إدارة الخدمات الطبية', 'MEDICAL'),
]


REGION_STAFF = {
    'الرياض': {
        'region_manager': ('العقيد فهد بن ناصر العتيبي', 'العقيد / مدير شعبة المراجعة الداخلية بمنطقة الرياض'),
        'prison_director': ('العميد خالد بن عبدالله الدوسري', 'العميد / مدير سجون منطقة الرياض'),
        'executors': [
            ('الرائد تركي بن سعد القحطاني', 'الرائد / أخصائي مراجعة داخلية'),
            ('النقيب عبدالمجيد بن صالح السبيعي', 'النقيب / أخصائي مراجعة ميدانية'),
            ('الملازم أول نواف بن إبراهيم الحربي', 'الملازم أول / عضو فريق مراجعة'),
        ],
    },
    'مكة المكرمة': {
        'region_manager': ('العقيد ماجد بن عوض الحارثي', 'العقيد / مدير شعبة المراجعة الداخلية بمنطقة مكة المكرمة'),
        'prison_director': ('العميد سامي بن راشد الزهراني', 'العميد / مدير سجون منطقة مكة المكرمة'),
        'executors': [
            ('الرائد عبدالله بن سالم المالكي', 'الرائد / أخصائي مراجعة داخلية'),
            ('النقيب بدر بن محمد الغامدي', 'النقيب / أخصائي مراجعة ميدانية'),
            ('الملازم أول ريان بن فهد الثقفي', 'الملازم أول / عضو فريق مراجعة'),
        ],
    },
    'المدينة المنورة': {
        'region_manager': ('العقيد يوسف بن حامد الأحمدي', 'العقيد / مدير شعبة المراجعة الداخلية بمنطقة المدينة المنورة'),
        'prison_director': ('العميد منصور بن عايض الجهني', 'العميد / مدير سجون منطقة المدينة المنورة'),
        'executors': [
            ('الرائد سلطان بن فهد المطيري', 'الرائد / أخصائي مراجعة داخلية'),
            ('النقيب نايف بن عبدالعزيز الحربي', 'النقيب / أخصائي مراجعة ميدانية'),
            ('الملازم أول مشعل بن صالح العوفي', 'الملازم أول / عضو فريق مراجعة'),
        ],
    },
    'القصيم': {
        'region_manager': ('العقيد وليد بن صالح الرشيدي', 'العقيد / مدير شعبة المراجعة الداخلية بمنطقة القصيم'),
        'prison_director': ('العميد عبدالله بن محمد التميمي', 'العميد / مدير سجون منطقة القصيم'),
        'executors': [
            ('الرائد بدر بن سعود الشمري', 'الرائد / أخصائي مراجعة داخلية'),
            ('النقيب فواز بن عبدالرحمن الحربي', 'النقيب / أخصائي مراجعة ميدانية'),
            ('الملازم أول بندر بن خالد المطيري', 'الملازم أول / عضو فريق مراجعة'),
        ],
    },
    'المنطقة الشرقية': {
        'region_manager': ('العقيد فيصل بن سعد الدوسري', 'العقيد / مدير شعبة المراجعة الداخلية بالمنطقة الشرقية'),
        'prison_director': ('العميد ناصر بن عبدالعزيز القحطاني', 'العميد / مدير سجون المنطقة الشرقية'),
        'executors': [
            ('الرائد محمد بن إبراهيم الهاجري', 'الرائد / أخصائي مراجعة داخلية'),
            ('النقيب راكان بن فهد الدوسري', 'النقيب / أخصائي مراجعة ميدانية'),
            ('الملازم أول خالد بن عبدالمحسن القحطاني', 'الملازم أول / عضو فريق مراجعة'),
        ],
    },
    'عسير': {
        'region_manager': ('العقيد سعيد بن عبدالله الشهري', 'العقيد / مدير شعبة المراجعة الداخلية بمنطقة عسير'),
        'prison_director': ('العميد عائض بن محمد الأسمري', 'العميد / مدير سجون منطقة عسير'),
        'executors': [
            ('الرائد يحيى بن علي عسيري', 'الرائد / أخصائي مراجعة داخلية'),
            ('النقيب عبدالله بن فهد الشهري', 'النقيب / أخصائي مراجعة ميدانية'),
            ('الملازم أول مازن بن صالح الأسمري', 'الملازم أول / عضو فريق مراجعة'),
        ],
    },
    'تبوك': {
        'region_manager': ('العقيد عبدالإله بن عواد البلوي', 'العقيد / مدير شعبة المراجعة الداخلية بمنطقة تبوك'),
        'prison_director': ('العميد بندر بن سالم البلوي', 'العميد / مدير سجون منطقة تبوك'),
        'executors': [
            ('الرائد نايف بن عودة البلوي', 'الرائد / أخصائي مراجعة داخلية'),
            ('النقيب أحمد بن سليمان العطوي', 'النقيب / أخصائي مراجعة ميدانية'),
            ('الملازم أول فهد بن محمد البلوي', 'الملازم أول / عضو فريق مراجعة'),
        ],
    },
    'حائل': {
        'region_manager': ('العقيد عبدالعزيز بن فهد الشمري', 'العقيد / مدير شعبة المراجعة الداخلية بمنطقة حائل'),
        'prison_director': ('العميد محمد بن عواد الشمري', 'العميد / مدير سجون منطقة حائل'),
        'executors': [
            ('الرائد صالح بن خلف الشمري', 'الرائد / أخصائي مراجعة داخلية'),
            ('النقيب مشاري بن ناصر الشمري', 'النقيب / أخصائي مراجعة ميدانية'),
            ('الملازم أول بدر بن فهد الشمري', 'الملازم أول / عضو فريق مراجعة'),
        ],
    },
    'الحدود الشمالية': {
        'region_manager': ('العقيد ممدوح بن سالم العنزي', 'العقيد / مدير شعبة المراجعة الداخلية بمنطقة الحدود الشمالية'),
        'prison_director': ('العميد عبدالمحسن بن فهد العنزي', 'العميد / مدير سجون منطقة الحدود الشمالية'),
        'executors': [
            ('الرائد نايف بن فواز العنزي', 'الرائد / أخصائي مراجعة داخلية'),
            ('النقيب زياد بن حمد العنزي', 'النقيب / أخصائي مراجعة ميدانية'),
            ('الملازم أول خالد بن عايد العنزي', 'الملازم أول / عضو فريق مراجعة'),
        ],
    },
    'جازان': {
        'region_manager': ('العقيد إبراهيم بن علي حكمي', 'العقيد / مدير شعبة المراجعة الداخلية بمنطقة جازان'),
        'prison_director': ('العميد حسن بن محمد عريشي', 'العميد / مدير سجون منطقة جازان'),
        'executors': [
            ('الرائد ياسر بن أحمد عسيري', 'الرائد / أخصائي مراجعة داخلية'),
            ('النقيب محمد بن يحيى حكمي', 'النقيب / أخصائي مراجعة ميدانية'),
            ('الملازم أول علي بن ناصر مدخلي', 'الملازم أول / عضو فريق مراجعة'),
        ],
    },
    'نجران': {
        'region_manager': ('العقيد صالح بن مانع اليامي', 'العقيد / مدير شعبة المراجعة الداخلية بمنطقة نجران'),
        'prison_director': ('العميد فهد بن عبدالله اليامي', 'العميد / مدير سجون منطقة نجران'),
        'executors': [
            ('الرائد محمد بن سالم آل زمانان', 'الرائد / أخصائي مراجعة داخلية'),
            ('النقيب عبدالله بن هادي اليامي', 'النقيب / أخصائي مراجعة ميدانية'),
            ('الملازم أول راشد بن محمد آل مخلص', 'الملازم أول / عضو فريق مراجعة'),
        ],
    },
    'الباحة': {
        'region_manager': ('العقيد خالد بن عبدالله الغامدي', 'العقيد / مدير شعبة المراجعة الداخلية بمنطقة الباحة'),
        'prison_director': ('العميد عبدالرحمن بن صالح الزهراني', 'العميد / مدير سجون منطقة الباحة'),
        'executors': [
            ('الرائد سعيد بن عبدالله الغامدي', 'الرائد / أخصائي مراجعة داخلية'),
            ('النقيب سامي بن أحمد الزهراني', 'النقيب / أخصائي مراجعة ميدانية'),
            ('الملازم أول عبدالعزيز بن ناصر الغامدي', 'الملازم أول / عضو فريق مراجعة'),
        ],
    },
    'الجوف': {
        'region_manager': ('العقيد فواز بن عبدالله الشراري', 'العقيد / مدير شعبة المراجعة الداخلية بمنطقة الجوف'),
        'prison_director': ('العميد نايف بن صالح الرويلي', 'العميد / مدير سجون منطقة الجوف'),
        'executors': [
            ('الرائد عبدالعزيز بن عايد الشراري', 'الرائد / أخصائي مراجعة داخلية'),
            ('النقيب ماجد بن سالم الرويلي', 'النقيب / أخصائي مراجعة ميدانية'),
            ('الملازم أول سلطان بن محمد الشراري', 'الملازم أول / عضو فريق مراجعة'),
        ],
    },
}


DEPARTMENT_USERS = [
    ('dept_it_mgr', 'المهندس عبدالله بن عبدالعزيز السالم', 'department_manager', 'المرتبة الثانية عشرة / مدير إدارة تقنية المعلومات', 'إدارة تقنية المعلومات'),
    ('dept_it_user', 'المهندس فيصل بن خالد الحربي', 'department_user', 'المرتبة العاشرة / مختص أنظمة', 'إدارة تقنية المعلومات'),

    ('dept_safety_mgr', 'المقدم خالد بن عبدالمحسن الشهري', 'department_manager', 'المقدم / مدير إدارة السلامة', 'إدارة السلامة'),
    ('dept_safety_user', 'النقيب سلطان بن عبدالله الغامدي', 'department_user', 'النقيب / مختص سلامة', 'إدارة السلامة'),

    ('dept_ops_mgr', 'العقيد راشد بن محمد القحطاني', 'department_manager', 'العقيد / مدير إدارة العمليات', 'إدارة العمليات'),
    ('dept_ops_user', 'الرائد ناصر بن سعد الدوسري', 'department_user', 'الرائد / مختص عمليات', 'إدارة العمليات'),

    ('dept_wh_mgr', 'بدر بن صالح العتيبي', 'department_manager', 'المرتبة الحادية عشرة / مدير إدارة المخزون والعهد', 'إدارة المخزون والعهد'),
    ('dept_wh_user', 'فهد بن إبراهيم المطيري', 'department_user', 'المرتبة التاسعة / مختص عهد ومخزون', 'إدارة المخزون والعهد'),

    ('dept_hr_mgr', 'نورة بنت عبدالله السبيعي', 'department_manager', 'المرتبة الحادية عشرة / مدير إدارة الموارد البشرية', 'إدارة الموارد البشرية'),
    ('dept_hr_user', 'سارة بنت خالد الدوسري', 'department_user', 'المرتبة الثامنة / أخصائي موارد بشرية', 'إدارة الموارد البشرية'),

    ('dept_fin_mgr', 'عبدالمجيد بن ناصر الحربي', 'department_manager', 'المرتبة الثانية عشرة / مدير الإدارة المالية', 'الإدارة المالية'),
    ('dept_fin_user', 'تركي بن فهد العتيبي', 'department_user', 'المرتبة التاسعة / محاسب', 'الإدارة المالية'),

    ('dept_maint_mgr', 'المهندس ماجد بن صالح العمري', 'department_manager', 'المرتبة الحادية عشرة / مدير إدارة الصيانة والمرافق', 'إدارة الصيانة والمرافق'),
    ('dept_maint_user', 'المهندس راكان بن عبدالعزيز التميمي', 'department_user', 'المرتبة التاسعة / مهندس مرافق', 'إدارة الصيانة والمرافق'),

    ('dept_sec_mgr', 'المقدم عبدالعزيز بن فهد المطيري', 'department_manager', 'المقدم / مدير إدارة الأمن والسلامة', 'إدارة الأمن والسلامة'),
    ('dept_sec_user', 'النقيب محمد بن سعود الرشيدي', 'department_user', 'النقيب / مختص أمن وسلامة', 'إدارة الأمن والسلامة'),

    ('dept_med_mgr', 'الدكتور سامي بن علي الزهراني', 'department_manager', 'استشاري / مدير إدارة الخدمات الطبية', 'إدارة الخدمات الطبية'),
    ('dept_med_user', 'عبدالله بن محمد الشهري', 'department_user', 'المرتبة التاسعة / منسق خدمات طبية', 'إدارة الخدمات الطبية'),
]


# =========================================================
# أدوات مساعدة
# =========================================================

def add_log(user_id, action, entity_type, entity_id, notes):
    db.session.add(
        AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            notes=notes
        )
    )


def add_action(observation, user, old_status, new_status, note, closure_reason=None, escalation_reason=None):
    db.session.add(
        ObservationAction(
            observation=observation,
            user=user,
            action_type='status_update',
            old_status=old_status,
            new_status=new_status,
            note=note,
            closure_reason=closure_reason,
            escalation_reason=escalation_reason,
        )
    )


def create_user(username, full_name, role, job_title, region=None, department=None, org_unit_type='regional'):
    user = User(
        username=username,
        full_name=full_name,
        role=role,
        job_title=job_title,
        region=region,
        department=department,
        org_unit_type=org_unit_type
    )
    user.set_password('123456')
    db.session.add(user)
    return user


def get_first_criterion(template, section_index=0, criterion_index=0):
    if not template.sections:
        return None

    if len(template.sections) <= section_index:
        return None

    section = template.sections[section_index]

    if not section.criteria:
        return None

    if len(section.criteria) <= criterion_index:
        return section.criteria[0]

    return section.criteria[criterion_index]


def build_template(template, sections_config):
    for section_order, section_data in enumerate(sections_config, start=1):
        section = TemplateSection(
            template=template,
            title=section_data['title'],
            weight_percentage=section_data['weight'],
            sort_order=section_order
        )
        db.session.add(section)
        db.session.flush()

        for criterion_order, text in enumerate(section_data['criteria'], start=1):
            db.session.add(
                TemplateCriterion(
                    section=section,
                    text=text,
                    sort_order=criterion_order
                )
            )

    db.session.flush()


def add_responses(prison_report, template, score_pattern):
    index = 0

    for section in template.sections:
        for criterion in section.criteria:
            label = score_pattern[index % len(score_pattern)]
            db.session.add(
                MissionResponse(
                    mission_prison_report=prison_report,
                    criterion=criterion,
                    score_label=label,
                    score_value=SCORE_LABELS[label]
                )
            )
            index += 1

    db.session.flush()
    prison_report.refresh_score()


def add_observation(
    prison_report,
    user,
    department,
    title,
    description,
    observation_type='other',
    criterion=None,
    category='عام',
    severity='متوسطة',
    priority='مهمة',
    sla_option='7bd',
    due_days=7,
    status='new',
    remediation_recommendation=None,
    department_response=None,
    prison_director_action=None,
    closure_reason=None,
    escalated=False,
    escalation_reason=None,
):
    old_status = 'new'

    obs = Observation(
        mission_prison_report=prison_report,
        observation_type=observation_type,
        criterion=criterion,
        title=title,
        description=description,
        category=category or 'عام',
        department=department,
        severity=severity,
        priority=priority,
        sla_option=sla_option,
        due_date=date.today() + timedelta(days=due_days),
        status=status,
        remediation_recommendation=remediation_recommendation,
        department_response=department_response,
        prison_director_action=prison_director_action,
        closure_reason=closure_reason,
        escalated=escalated,
        escalation_reason=escalation_reason,
        escalation_at=datetime.utcnow() if escalated else None,
        closed_at=datetime.utcnow() if status in ['closed', 'resolved', 'remediated', 'closed_by_decision'] else None,
    )

    db.session.add(obs)
    db.session.flush()

    add_log(
        user.id,
        'add_observation',
        'observation',
        obs.id,
        f'إضافة ملاحظة: {title}'
    )

    add_action(
        observation=obs,
        user=user,
        old_status=old_status,
        new_status=status,
        note=f'تم إنشاء الملاحظة وتحديد حالتها: {status}',
        closure_reason=closure_reason,
        escalation_reason=escalation_reason,
    )

    return obs


def create_prison_report(
    mission_region,
    prison,
    assignees,
    status,
    visit_offset_days,
    visit_day_name,
    visit_start_time,
    visit_end_time,
    visit_count,
    visited_entity,
    summary,
    recommendations,
    score_pattern,
):
    prison_report = MissionPrisonReport(
        mission_region=mission_region,
        prison=prison,
        status=status,
        visit_date=date.today() + timedelta(days=visit_offset_days),
        visit_day_name=visit_day_name,
        visit_start_time=visit_start_time,
        visit_end_time=visit_end_time,
        visit_count=visit_count,
        visited_entity=visited_entity,
        report_summary=summary,
        recommendations=recommendations,
        submitted_at=datetime.utcnow() if status == 'submitted' else None,
    )

    db.session.add(prison_report)
    db.session.flush()

    prison_report.assignees = assignees

    add_responses(
        prison_report=prison_report,
        template=mission_region.mission.template,
        score_pattern=score_pattern
    )

    add_log(
        assignees[0].id,
        'save_execution',
        'mission_prison_report',
        prison_report.id,
        f'تحديث بيانات تنفيذ تقرير {prison.name}'
    )

    return prison_report


# =========================================================
# Seed رئيسي
# =========================================================

def seed_if_empty():
    if User.query.first():
        return

    # -----------------------------------------------------
    # المناطق
    # -----------------------------------------------------
    regions = {}

    for region_name in REGIONS:
        region = Region(name=region_name)
        db.session.add(region)
        regions[region_name] = region

    db.session.flush()

    # -----------------------------------------------------
    # الإدارات المختصة
    # -----------------------------------------------------
    departments = {}

    for department_name, department_code in DEPARTMENTS:
        department = Department(name=department_name, code=department_code)
        db.session.add(department)
        departments[department_name] = department

    db.session.flush()

    # -----------------------------------------------------
    # السجون
    # -----------------------------------------------------
    prisons = {}

    for region_name, prison_names in PRISONS.items():
        for prison_name in prison_names:
            prison = Prison(
                name=prison_name,
                region=regions[region_name]
            )
            db.session.add(prison)
            prisons[prison_name] = prison

    db.session.flush()

    # -----------------------------------------------------
    # المستخدمون المركزيون
    # -----------------------------------------------------
    central_admin = create_user(
        username='central_admin',
        full_name='ماجد بن عبدالله المطيري',
        role='central_admin',
        job_title='المرتبة الثانية عشرة / مختص أول بإدارة المراجعة الداخلية',
        org_unit_type='central'
    )

    central_operator = create_user(
        username='central_operator',
        full_name='محمد بن فهد الحربي',
        role='central_operator',
        job_title='المرتبة الحادية عشرة / مختص متابعة وتقارير بإدارة المراجعة الداخلية',
        org_unit_type='central'
    )

    central_operator_2 = create_user(
        username='central_operator_2',
        full_name='رزان بنت عبدالعزيز العتيبي',
        role='central_operator',
        job_title='المرتبة العاشرة / مختص نظم وتحليل بإدارة المراجعة الداخلية',
        org_unit_type='central'
    )

    central_director = create_user(
        username='central_director',
        full_name='عبدالله بن ناصر السبيعي',
        role='central_director',
        job_title='مدير إدارة المراجعة الداخلية',
        org_unit_type='central'
    )

    dg = create_user(
        username='dg',
        full_name='سلمان بن عبدالرحمن الشهراني',
        role='director_general',
        job_title='المدير العام',
        org_unit_type='central'
    )

    # -----------------------------------------------------
    # مستخدمو الإدارات المختصة
    # -----------------------------------------------------
    department_users = {}

    for username, full_name, role, job_title, department_name in DEPARTMENT_USERS:
        user = create_user(
            username=username,
            full_name=full_name,
            role=role,
            job_title=job_title,
            department=departments[department_name],
            org_unit_type='central'
        )
        department_users[username] = user

    # -----------------------------------------------------
    # مستخدمو المناطق
    # -----------------------------------------------------
    region_managers = {}
    prison_directors = {}
    executors = {}

    for index, region_name in enumerate(REGIONS, start=1):
        region = regions[region_name]
        staff = REGION_STAFF[region_name]

        region_manager_name, region_manager_title = staff['region_manager']
        prison_director_name, prison_director_title = staff['prison_director']

        region_managers[region_name] = create_user(
            username=f'region_mgr_{index}',
            full_name=region_manager_name,
            role='region_manager',
            job_title=region_manager_title,
            region=region
        )

        prison_directors[region_name] = create_user(
            username=f'prison_dir_{index}',
            full_name=prison_director_name,
            role='prison_director',
            job_title=prison_director_title,
            region=region
        )

        executors[region_name] = []

        for executor_index, executor_data in enumerate(staff['executors'], start=1):
            executor_name, executor_title = executor_data

            executor = create_user(
                username=f'executor_{index}_{executor_index}',
                full_name=executor_name,
                role='executor',
                job_title=executor_title,
                region=region
            )

            executors[region_name].append(executor)

    db.session.flush()

    # -----------------------------------------------------
    # النماذج
    # -----------------------------------------------------
    safety_template = Template(
        name='نشاط مراجعة السلامة في السجون',
        code='SAFETY-001',
        description='نموذج رقابي لمراجعة إجراءات السلامة والجاهزية التشغيلية داخل السجون.',
        is_active=True
    )

    treasury_template = Template(
        name='جولة تفتيشية لنشاط الأمانات النقدية والعينية',
        code='TREASURY-001',
        description='نموذج تفتيشي لمراجعة الأمانات النقدية والعينية والعهد والسجلات المرتبطة بها.',
        is_active=True
    )

    security_template = Template(
        name='مراجعة إجراءات الأمن الداخلي والانضباط',
        code='SECURITY-001',
        description='نموذج رقابي لمراجعة إجراءات الأمن الداخلي والانضباط ومتابعة البلاغات.',
        is_active=True
    )

    services_template = Template(
        name='مراجعة خدمات النزلاء والتجهيزات التشغيلية',
        code='SERVICES-001',
        description='نموذج لمراجعة الخدمات الأساسية والتجهيزات التشغيلية ذات العلاقة بالنزلاء.',
        is_active=True
    )

    db.session.add_all([
        safety_template,
        treasury_template,
        security_template,
        services_template,
    ])
    db.session.flush()

    build_template(
        safety_template,
        [
            {
                'title': 'الالتزام الإجرائي',
                'weight': 25,
                'criteria': [
                    'وجود خطة سلامة محدثة ومعتمدة',
                    'الالتزام بالتعاميم والتعليمات المنظمة للسلامة',
                    'توثيق الجولات السابقة ومتابعة نتائجها',
                    'وجود سجل محدث للحوادث والملاحظات',
                ],
            },
            {
                'title': 'الجاهزية التشغيلية',
                'weight': 45,
                'criteria': [
                    'جاهزية طفايات الحريق وتوزيعها بالشكل المناسب',
                    'سلامة التمديدات الكهربائية وعدم وجود مخاطر ظاهرة',
                    'وضوح مخارج الطوارئ وخلوها من العوائق',
                    'عمل أنظمة الإنذار والتنبيه بالشكل المطلوب',
                    'توافر أدوات الإسعاف الأولي في المواقع المحددة',
                    'جاهزية خطط الإخلاء والتدريب عليها',
                ],
            },
            {
                'title': 'التوثيق والمتابعة',
                'weight': 30,
                'criteria': [
                    'إقفال الملاحظات السابقة وفق المدد المحددة',
                    'اكتمال ملفات المتابعة والإثباتات',
                    'رفع التقارير في الوقت المحدد',
                    'وجود آلية تصعيد للملاحظات الحرجة',
                ],
            },
        ]
    )

    build_template(
        treasury_template,
        [
            {
                'title': 'الضبط والرقابة',
                'weight': 35,
                'criteria': [
                    'وجود سجل عهد نقدية وعينية محدث',
                    'تطابق العهد المسجلة مع الجرد الفعلي',
                    'فصل مهام الاستلام والتسليم والمراجعة',
                    'وجود محاضر جرد دورية معتمدة',
                ],
            },
            {
                'title': 'إدارة العهد والأمانات',
                'weight': 40,
                'criteria': [
                    'توثيق عمليات الاستلام والتسليم بشكل نظامي',
                    'حفظ الأمانات في مواقع آمنة ومقيدة الصلاحية',
                    'معالجة الفروقات وفق إجراءات واضحة',
                    'توفر صلاحيات محددة للمسؤولين عن العهد',
                    'توثيق إجراءات تسليم الأمانات عند الإفراج أو النقل',
                ],
            },
            {
                'title': 'التوثيق والتقارير',
                'weight': 25,
                'criteria': [
                    'اكتمال المرفقات والمستندات المؤيدة',
                    'رفع تقارير الجرد ضمن المدد المعتمدة',
                    'متابعة الملاحظات السابقة حتى الإقفال',
                ],
            },
        ]
    )

    build_template(
        security_template,
        [
            {
                'title': 'الإجراءات الأمنية',
                'weight': 35,
                'criteria': [
                    'الالتزام بإجراءات الدخول والخروج',
                    'توثيق البلاغات الأمنية ومتابعتها',
                    'وجود توزيع مناوبات معتمد ومحدث',
                    'التأكد من جاهزية أدوات التفتيش',
                ],
            },
            {
                'title': 'المراقبة والسيطرة',
                'weight': 40,
                'criteria': [
                    'جاهزية كاميرات المراقبة في النقاط الحساسة',
                    'وضوح آلية التعامل مع الحالات الطارئة',
                    'متابعة غرف التحكم والتوثيق',
                    'وجود سجلات للبلاغات والتدخلات',
                ],
            },
            {
                'title': 'التقارير والتصعيد',
                'weight': 25,
                'criteria': [
                    'سرعة رفع البلاغات المهمة',
                    'توثيق إجراءات المعالجة',
                    'التزام الجهات المعنية بالردود',
                ],
            },
        ]
    )

    build_template(
        services_template,
        [
            {
                'title': 'الخدمات الأساسية',
                'weight': 35,
                'criteria': [
                    'توفر الخدمات الأساسية وفق المعايير',
                    'توثيق الطلبات والملاحظات المتعلقة بالنزلاء',
                    'وضوح آلية متابعة الطلبات',
                    'التعامل مع الحالات العاجلة وفق الإجراءات',
                ],
            },
            {
                'title': 'التجهيزات التشغيلية',
                'weight': 40,
                'criteria': [
                    'جاهزية المرافق المستخدمة يوميًا',
                    'وجود خطة صيانة ومتابعة للأعطال',
                    'توثيق البلاغات الفنية',
                    'متابعة الأعطال المتكررة',
                    'تحديث سجلات التجهيزات',
                ],
            },
            {
                'title': 'المتابعة والتحسين',
                'weight': 25,
                'criteria': [
                    'إغلاق الملاحظات السابقة',
                    'قياس رضا المستفيدين داخليًا',
                    'رفع توصيات تحسين دورية',
                ],
            },
        ]
    )

    db.session.flush()

    # -----------------------------------------------------
    # الخطة السنوية
    # -----------------------------------------------------
    annual_plan = AnnualPlan(
        title='الخطة السنوية لأعمال المراجعة الداخلية والرقابة بالسجون 2026',
        year=2026,
        notes='خطة تشغيلية تجريبية واقعية تشمل جولات سلامة وأمانات وأمن داخلي وخدمات تشغيلية.'
    )

    db.session.add(annual_plan)
    db.session.flush()

    plan_items = [
        ('مراجعة السلامة - الربع الأول', safety_template, 15, ['الرياض', 'مكة المكرمة', 'عسير']),
        ('تفتيش الأمانات النقدية والعينية - الربع الثاني', treasury_template, 45, ['المنطقة الشرقية', 'القصيم', 'المدينة المنورة']),
        ('مراجعة الأمن الداخلي والانضباط - منتصف العام', security_template, 75, ['تبوك', 'حائل', 'الحدود الشمالية', 'الجوف']),
        ('مراجعة خدمات النزلاء والتجهيزات التشغيلية - الربع الثالث', services_template, 110, ['جازان', 'نجران', 'الباحة']),
        ('جولة متابعة للملاحظات الحرجة', safety_template, 150, REGIONS),
    ]

    for title, template, offset_days, item_regions in plan_items:
        plan_item = PlanItem(
            plan=annual_plan,
            title=title,
            template=template,
            planned_date=date.today() + timedelta(days=offset_days),
            notes='بند مجدول ضمن الخطة السنوية قابل للتحويل إلى مهمة تنفيذية.',
            auto_create=False,
            allow_region_to_select_prisons=True
        )
        db.session.add(plan_item)
        db.session.flush()

        plan_item.regions = [regions[name] for name in item_regions]

    db.session.flush()

    # -----------------------------------------------------
    # المهمات التشغيلية المتنوعة
    # -----------------------------------------------------
    mission_specs = [
        {
            'reference_no': 'IA-2026-001',
            'title': 'مراجعة السلامة على السجون الرئيسة للربع الأول',
            'template': safety_template,
            'mission_classification': 'annual_plan',
            'priority_level': 'high',
            'assignment_mode': 'region_manager_selects',
            'status': 'in_progress',
            'regions': ['الرياض', 'مكة المكرمة', 'عسير'],
            'planned_offset': -10,
            'due_offset': 10,
        },
        {
            'reference_no': 'IA-2026-002',
            'title': 'جولة تفتيشية على الأمانات النقدية والعينية',
            'template': treasury_template,
            'mission_classification': 'quarterly_plan',
            'priority_level': 'critical',
            'assignment_mode': 'central_defined',
            'status': 'awaiting_remediation',
            'regions': ['المنطقة الشرقية', 'القصيم', 'المدينة المنورة'],
            'planned_offset': -25,
            'due_offset': -3,
        },
        {
            'reference_no': 'IA-2026-003',
            'title': 'مراجعة إجراءات الأمن الداخلي والانضباط',
            'template': security_template,
            'mission_classification': 'ad_hoc',
            'priority_level': 'medium',
            'assignment_mode': 'central_with_region_completion',
            'status': 'under_central_review',
            'regions': ['تبوك', 'حائل', 'الحدود الشمالية', 'الجوف'],
            'planned_offset': -18,
            'due_offset': 5,
        },
        {
            'reference_no': 'IA-2026-004',
            'title': 'مراجعة خدمات النزلاء والتجهيزات التشغيلية',
            'template': services_template,
            'mission_classification': 'follow_up',
            'priority_level': 'normal',
            'assignment_mode': 'region_manager_selects',
            'status': 'ready_for_dg',
            'regions': ['جازان', 'نجران', 'الباحة'],
            'planned_offset': -35,
            'due_offset': -8,
        },
        {
            'reference_no': 'IA-2026-005',
            'title': 'جولة متابعة وطنية للملاحظات الحرجة والمتأخرة',
            'template': safety_template,
            'mission_classification': 'follow_up',
            'priority_level': 'critical',
            'assignment_mode': 'central_defined',
            'status': 'closed',
            'regions': REGIONS,
            'planned_offset': -80,
            'due_offset': -40,
        },
    ]

    score_patterns = [
        ['ممتاز', 'جيد جدًا', 'جيد جدًا', 'مقبول', 'جيد جدًا'],
        ['جيد جدًا', 'مقبول', 'جيد جدًا', 'سيئ', 'مقبول'],
        ['مقبول', 'سيئ', 'جيد جدًا', 'مقبول', 'سيئ جدًا'],
        ['ممتاز', 'ممتاز', 'جيد جدًا', 'جيد جدًا', 'مقبول'],
        ['سيئ', 'مقبول', 'سيئ جدًا', 'سيئ', 'مقبول'],
    ]

    visit_days = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس']
    visit_times = [
        ('08:30', '11:00'),
        ('09:00', '12:15'),
        ('10:00', '13:00'),
        ('11:00', '14:00'),
    ]

    for mission_index, spec in enumerate(mission_specs, start=1):
        mission = Mission(
            reference_no=spec['reference_no'],
            title=spec['title'],
            template=spec['template'],
            mission_classification=spec['mission_classification'],
            priority_level=spec['priority_level'],
            assignment_mode=spec['assignment_mode'],
            planned_date=date.today() + timedelta(days=spec['planned_offset']),
            due_date=date.today() + timedelta(days=spec['due_offset']),
            task_instructions='تنفيذ المهمة وفق النموذج المعتمد، وتوثيق الملاحظات والمرفقات، ورفع نتائج التنفيذ حسب الصلاحية.',
            status=spec['status'],
            created_by=central_admin.id,
        )

        if spec['status'] in ['ready_for_dg', 'closed']:
            mission.final_summary = (
                'تم استكمال مراجعة تقارير المناطق المستهدفة، وتلخيص نتائج التنفيذ والملاحظات الجوهرية '
                'مع تحديد مستويات الخطورة وحالة المعالجة لكل منطقة.'
            )
            mission.internal_audit_opinion = (
                'ترى إدارة المراجعة الداخلية ضرورة الاستمرار في متابعة الملاحظات المتكررة، '
                'وتحسين التوثيق، وتفعيل مؤشرات الالتزام بالمعالجة ضمن المدد المحددة.'
            )
            mission.final_recommendations = (
                'اعتماد نتائج المهمة، وتوجيه الجهات المختصة باستكمال التحسينات، '
                'ورفع تقرير متابعة خلال الفترة القادمة للملاحظات ذات الأثر العالي.'
            )
            mission.sent_to_dg_at = datetime.utcnow() - timedelta(days=3)

        if spec['status'] == 'closed':
            mission.dg_decision = 'اعتماد التقرير النهائي وإغلاق المهمة مع متابعة التوصيات ضمن خطة التحسين القادمة.'

        db.session.add(mission)
        db.session.flush()

        add_log(
            central_admin.id,
            'create_mission',
            'mission',
            mission.id,
            f'إنشاء المهمة {mission.reference_no}'
        )

        for region_position, region_name in enumerate(spec['regions'], start=1):
            region = regions[region_name]

            if spec['status'] == 'closed':
                mission_region_status = 'submitted_to_central'
            elif spec['status'] in ['ready_for_dg', 'under_central_review', 'awaiting_remediation']:
                mission_region_status = 'submitted_to_central'
            elif region_position % 3 == 0:
                mission_region_status = 'pending_region_setup'
            else:
                mission_region_status = 'assigned'

            mission_region = MissionRegion(
                mission=mission,
                region=region,
                status=mission_region_status,
                allow_region_to_select_prisons=(spec['assignment_mode'] == 'region_manager_selects'),
                region_notes=f'نطاق التنفيذ في منطقة {region_name}.',
                report_summary='ملخص منطقة مبدئي بناءً على نتائج السجون المنفذة.',
                recommendations='استكمال معالجة الملاحظات ومتابعة الجهات المختصة ضمن SLA.',
                prison_director_comments='تم الاطلاع على الملاحظات المرفوعة وتوجيه الجهات المختصة باستكمال اللازم.',
                central_review_notes='تمت مراجعة نتائج المنطقة ضمن التقرير المجمع للمهمة.',
                sent_to_central_at=datetime.utcnow() - timedelta(days=2) if mission_region_status == 'submitted_to_central' else None,
            )

            db.session.add(mission_region)
            db.session.flush()

            add_log(
                region_managers[region_name].id,
                'create_mission_region',
                'mission_region',
                mission_region.id,
                f'تجهيز نطاق منطقة {region_name}'
            )

            region_prisons = list(region.prisons)

            if mission_region_status == 'pending_region_setup':
                continue

            selected_prisons = region_prisons[:min(2, len(region_prisons))]

            for prison_position, prison in enumerate(selected_prisons, start=1):
                if spec['status'] == 'closed':
                    report_status = 'submitted'
                elif spec['status'] in ['ready_for_dg', 'under_central_review', 'awaiting_remediation']:
                    report_status = 'submitted'
                elif prison_position % 2 == 0:
                    report_status = 'assigned'
                else:
                    report_status = 'in_progress'

                assigned_users = executors[region_name][:2]

                if spec['assignment_mode'] == 'central_defined':
                    assigned_users = [executors[region_name][0], executors[region_name][1]]

                visit_start, visit_end = visit_times[(mission_index + prison_position) % len(visit_times)]

                prison_report = create_prison_report(
                    mission_region=mission_region,
                    prison=prison,
                    assignees=assigned_users,
                    status=report_status,
                    visit_offset_days=-(mission_index + prison_position),
                    visit_day_name=visit_days[(mission_index + prison_position) % len(visit_days)],
                    visit_start_time=visit_start,
                    visit_end_time=visit_end,
                    visit_count=prison_position,
                    visited_entity='إدارة السجن، الإدارة المختصة، نقاط التشغيل ذات العلاقة',
                    summary=f'تم تنفيذ الزيارة على {prison.name} ورصد مستوى الالتزام وفق النموذج المعتمد.',
                    recommendations='يوصى باستكمال المعالجة للملاحظات المفتوحة ورفع الإثباتات قبل تاريخ الاستحقاق.',
                    score_pattern=score_patterns[(mission_index + prison_position) % len(score_patterns)]
                )

                template = mission.template

                safety_dept = departments.get('إدارة السلامة')
                it_dept = departments.get('إدارة تقنية المعلومات')
                ops_dept = departments.get('إدارة العمليات')
                wh_dept = departments.get('إدارة المخزون والعهد')
                maint_dept = departments.get('إدارة الصيانة والمرافق')
                sec_dept = departments.get('إدارة الأمن والسلامة')

                criterion_1 = get_first_criterion(template, 1, 0)
                criterion_2 = get_first_criterion(template, 1, 1)
                criterion_3 = get_first_criterion(template, 2, 0)

                if mission_index == 1:
                    add_observation(
                        prison_report=prison_report,
                        user=assigned_users[0],
                        department=safety_dept,
                        criterion=criterion_1,
                        observation_type='criterion',
                        title=f'قصور في جاهزية وسائل السلامة - {prison.name}',
                        description='لوحظ وجود نقص في بعض متطلبات السلامة التشغيلية، مع الحاجة إلى تحديث سجلات الفحص الدوري.',
                        category='سلامة',
                        severity='عالية',
                        priority='عاجلة',
                        sla_option='7bd',
                        due_days=7,
                        status='sent_to_department',
                        remediation_recommendation='استكمال النواقص ورفع محاضر الفحص والصور الداعمة.',
                        department_response='جاري استكمال الفحص وإعادة توزيع وسائل السلامة حسب المواقع ذات الأولوية.'
                    )

                    add_observation(
                        prison_report=prison_report,
                        user=assigned_users[1],
                        department=maint_dept,
                        criterion=criterion_2,
                        observation_type='criterion',
                        title=f'ملاحظة على التمديدات والتجهيزات - {prison.name}',
                        description='توجد مواقع تحتاج إلى صيانة وقائية وتحديث لبعض لوحات التوجيه والتنبيه.',
                        category='مرافق وتجهيزات',
                        severity='متوسطة',
                        priority='مهمة',
                        sla_option='14bd',
                        due_days=14,
                        status='in_remediation',
                        remediation_recommendation='تنفيذ الصيانة الوقائية ورفع تقرير إقفال للمواقع المتأثرة.',
                        department_response='تمت جدولة أعمال الصيانة وجاري إرفاق الإثباتات بعد الانتهاء.'
                    )

                elif mission_index == 2:
                    add_observation(
                        prison_report=prison_report,
                        user=assigned_users[0],
                        department=wh_dept,
                        criterion=criterion_1,
                        observation_type='criterion',
                        title=f'فروقات في سجلات العهد - {prison.name}',
                        description='تم رصد اختلافات محدودة بين السجل الورقي والسجل الإلكتروني لبعض العهد.',
                        category='توثيق',
                        severity='حرجة' if prison_position == 1 else 'عالية',
                        priority='عاجلة جدًا' if prison_position == 1 else 'عاجلة',
                        sla_option='24h' if prison_position == 1 else '3bd',
                        due_days=-1 if prison_position == 1 else 3,
                        status='escalated' if prison_position == 1 else 'waiting_region_approval',
                        remediation_recommendation='إجراء مطابقة عاجلة وإرفاق محضر الجرد المعتمد.',
                        department_response='تم البدء بالمطابقة وجاري رفع محضر الجرد النهائي.',
                        prison_director_action='تم توجيه الإدارة المختصة بسرعة المعالجة ورفع الإفادة.',
                        escalated=True if prison_position == 1 else False,
                        escalation_reason='تجاوز مدة SLA لملاحظة عالية الأثر.' if prison_position == 1 else None
                    )

                    add_observation(
                        prison_report=prison_report,
                        user=assigned_users[1],
                        department=it_dept,
                        observation_type='other',
                        title=f'عدم اكتمال الربط الإلكتروني لسجلات الأمانات - {prison.name}',
                        description='تبين عدم تحديث بعض السجلات الإلكترونية بما يتوافق مع بيانات الجرد اليدوي.',
                        category='تقني',
                        severity='متوسطة',
                        priority='مهمة',
                        sla_option='14bd',
                        due_days=14,
                        status='new',
                        remediation_recommendation='مراجعة التكامل بين السجل الإلكتروني ونموذج الجرد المعتمد.'
                    )

                elif mission_index == 3:
                    add_observation(
                        prison_report=prison_report,
                        user=assigned_users[0],
                        department=sec_dept,
                        criterion=criterion_1,
                        observation_type='criterion',
                        title=f'تأخر في توثيق بعض البلاغات الأمنية - {prison.name}',
                        description='لوحظ وجود تأخر في تسجيل بعض البلاغات في السجل الموحد ورفع المرفقات الداعمة.',
                        category='أمني',
                        severity='متوسطة',
                        priority='مهمة',
                        sla_option='7bd',
                        due_days=7,
                        status='waiting_central_review',
                        remediation_recommendation='توحيد آلية التوثيق وتدريب المناوبين على رفع البلاغات.',
                        department_response='تم تحديث آلية التوثيق ورفع إفادة أولية.',
                        prison_director_action='تم اعتماد الإفادة مبدئيًا ورفعها للمراجعة المركزية.'
                    )

                    add_observation(
                        prison_report=prison_report,
                        user=assigned_users[1],
                        department=ops_dept,
                        observation_type='other',
                        title=f'حاجة إلى تحديث خطة المناوبات - {prison.name}',
                        description='تحتاج خطة المناوبات إلى تحديث دوري لضمان وضوح المسؤوليات ونقاط التغطية.',
                        category='تشغيلي',
                        severity='منخفضة',
                        priority='عادية',
                        sla_option='30d',
                        due_days=30,
                        status='remediated',
                        remediation_recommendation='تحديث الخطة واعتمادها من صاحب الصلاحية.',
                        department_response='تم تحديث الخطة واعتمادها.',
                        closure_reason='تم التلافي وإرفاق الإثبات'
                    )

                elif mission_index == 4:
                    add_observation(
                        prison_report=prison_report,
                        user=assigned_users[0],
                        department=maint_dept,
                        criterion=criterion_2,
                        observation_type='criterion',
                        title=f'تكرار بلاغات صيانة في أحد المرافق - {prison.name}',
                        description='تكررت بلاغات الصيانة في موقع تشغيلي، مما يستدعي معالجة جذرية بدل المعالجة المؤقتة.',
                        category='مرافق وتجهيزات',
                        severity='عالية',
                        priority='عاجلة',
                        sla_option='5bd',
                        due_days=5,
                        status='closed_by_decision',
                        remediation_recommendation='إعداد معالجة جذرية للأعطال المتكررة وإرفاق تقرير فني.',
                        department_response='تم تنفيذ المعالجة الفنية وإرفاق تقرير مختصر.',
                        prison_director_action='تم التحقق من المعالجة واعتماد الإغلاق.',
                        closure_reason='تم التلافي وإرفاق الإثبات'
                    )

                    add_observation(
                        prison_report=prison_report,
                        user=assigned_users[1],
                        department=ops_dept,
                        observation_type='other',
                        title=f'تحسين آلية متابعة طلبات النزلاء - {prison.name}',
                        description='يوصى بتحسين آلية فرز ومتابعة الطلبات لتقليل زمن المعالجة.',
                        category='جودة',
                        severity='متوسطة',
                        priority='مهمة',
                        sla_option='14bd',
                        due_days=14,
                        status='remediated',
                        remediation_recommendation='تطوير نموذج متابعة موحد للطلبات.',
                        department_response='تم إعداد نموذج متابعة وتحسين آلية الإحالة.',
                        closure_reason='إفادة مقبولة من الإدارة المختصة'
                    )

                else:
                    add_observation(
                        prison_report=prison_report,
                        user=assigned_users[0],
                        department=safety_dept,
                        criterion=criterion_3,
                        observation_type='criterion',
                        title=f'ملاحظة حرجة مغلقة ضمن جولة المتابعة - {prison.name}',
                        description='تمت متابعة ملاحظة سابقة عالية الأثر والتأكد من معالجة السبب الجذري.',
                        category='امتثال',
                        severity='حرجة',
                        priority='عاجلة جدًا',
                        sla_option='24h',
                        due_days=-40,
                        status='closed',
                        remediation_recommendation='الاستمرار في المتابعة الدورية وتحديث مؤشرات الالتزام.',
                        department_response='تمت المعالجة ورفع الإثباتات.',
                        prison_director_action='تم التحقق من الإجراء ورفعه للإدارة المركزية.',
                        closure_reason='تم التلافي وإرفاق الإثبات'
                    )

                    add_observation(
                        prison_report=prison_report,
                        user=assigned_users[1],
                        department=it_dept,
                        observation_type='other',
                        title=f'توثيق إلكتروني مكتمل بعد المعالجة - {prison.name}',
                        description='تمت مراجعة التوثيق الإلكتروني بعد التلافي وتبين اكتماله.',
                        category='تقني',
                        severity='منخفضة',
                        priority='عادية',
                        sla_option='14bd',
                        due_days=-35,
                        status='resolved',
                        remediation_recommendation='اعتماد الإغلاق والمتابعة ضمن التقارير الدورية.',
                        department_response='تم اكتمال التوثيق.',
                        closure_reason='إفادة مقبولة من الإدارة المختصة'
                    )

                prison_report.refresh_score()

            db.session.flush()

    db.session.commit()