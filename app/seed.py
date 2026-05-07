from datetime import date, datetime, timedelta

from .extensions import db
from .models import (
    Region, Prison, Department, User,
    Template, TemplateSection, TemplateCriterion,
    AnnualPlan, PlanItem,
    Mission, MissionRegion, MissionPrisonReport,
    MissionResponse, Observation, ObservationAction, AuditLog,
    SCORE_LABELS,
    mission_prison_assignees, plan_item_regions, plan_item_prisons
)


# =========================================================
# بيانات مرجعية ثابتة
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
# النماذج المعتمدة فقط
# - التقييم في النظام يبقى من 1 إلى 5 حسب SCORE_LABELS.
# - كلمة مفعل / غير مفعل في ملفات Word غير مستخدمة في النظام.
# =========================================================

SAFETY_TEMPLATE_CONFIG = {
    'name': 'نموذج جولة تفتيشية لنشاط مراجعة السلامة داخل السجون',
    'code': 'SAFETY-001',
    'description': 'النموذج المعتمد لجولة تفتيشية لنشاط مراجعة السلامة داخل السجون.',
    'sections': [
        {
            'title': 'الهدف الأول: الحوكمة والامتثال',
            'weight': 25,
            'criteria': [
                'التقيد بما ورد في تعميم سعادة مدير عام السجون رقم 924885 وتاريخ 3/6/1447هـ بشأن تطبيق لائحة مختص السلامة وتعزيز السلامة داخل السجون.',
                'التقيد بما ورد في تعميم سعادة مدير عام السجون رقم 158562 وتاريخ 12/9/1447هـ بشأن تشكيل فرق الطوارئ واستمرارية الأعمال لرفع الجاهزية التامة لمواجهة الأحداث والتهديدات التي قد تتعرض لها مقرات السجون.',
                'التأكد من وجود عقد لصيانة وسائل السلامة.',
                'التقيد بتعميم سعادة مدير عام السجون رقم 1015226 وتاريخ 10/8/1447هـ.',
            ],
        },
        {
            'title': 'الهدف الثاني: الموارد المؤسسية',
            'weight': 25,
            'criteria': [
                'التأكد من توفير طفايات الحريق في أماكنها المحددة وأنها صالحة للاستخدام.',
                'التأكد من وجود خطة إخلاء واضحة ومعتمدة يمكن تنفيذها عند حدوث حريق لا سمح الله.',
                'التأكد من إمكانية سهولة الوصول إلى مخارج الطوارئ وعدم وجود عوائق عند المخارج.',
                'التأكد من وجود إنذار حريق فعال وأنظمة رش آلي عند حدوث حريق ويعمل بكفاءة جيدة.',
                'التأكد من سلامة التمديدات الكهربائية وعدم وجود أسلاك كهربائية مكشوفة وغير آمنة والتأكد من وجود نظام فصل التيار عند حدوث التماس كهربائي عند هطول أمطار أو حمل زائد على المولدات.',
                'وجود مخارج طوارئ ولوحات إرشادية.',
                'وجود فرضيات إخلاء بشكل دوري.',
                'التأكد من التجهيزات الخاصة بالسلامة والإسعافات الأولية.',
                'وجود ساحات إخلاء ونقاط وصول الجهات المختصة لها.',
                'التأكد من إزالة العفش الزائد والتفتيش المستمر لجميع العنابر ووجود آلية واضحة للتخلص من العفش الزائد وعدم بقائه داخل السجن وبعيد عن مخارج الطوارئ.',
            ],
        },
        {
            'title': 'الهدف الثالث: تقييم الأداء',
            'weight': 25,
            'criteria': [
                'التأكد من وجود تدريب للعاملين على استخدام أدوات السلامة وكيفية التعامل عند حدوث أي طارئ.',
                'تنفيذ فرضيات إخلاء بشكل دوري.',
                'التأكد من تواجد مسؤول السلامة على مدار 24 ساعة.',
                'التأكد من وجود برامج توعوية للنزلاء والعاملين بإجراءات الطوارئ.',
            ],
        },
        {
            'title': 'الهدف الرابع: الدور الرقابي',
            'weight': 25,
            'criteria': [
                'التأكد من تقييم المخاطر بشكل دوري لتحديد مصادر الخطر المحتملة والعمل على تلافيها بشكل عاجل.',
                'التأكد من وجود نماذج تثبت متابعة مختص السلامة لكافة المواقع والتجهيزات وفعاليتها.',
                'التأكد من تفعيل دور الإدارة العامة للسلامة بجميع السجون والعمل المناط بها.',
            ],
        },
    ],
}


TREASURY_TEMPLATE_CONFIG = {
    'name': 'نموذج جولة تفتيشية لنشاط الأمانات النقدية والعينية',
    'code': 'TREASURY-001',
    'description': 'النموذج المعتمد لجولة تفتيشية لنشاط الأمانات النقدية والعينية.',
    'sections': [
        {
            'title': 'الهدف الأول: الحوكمة والامتثال',
            'weight': 25,
            'criteria': [
                'توفر عهد نقدية لا تقل عن 10% ولا تزيد عن 30% من مجموع الأمانات المودعة في الحسابات المخصصة لها.',
                'التقيد بما ورد في تعميم سعادة المدير العام رقم 1167879 وتاريخ 25/11/1444هـ المنظم لعمل الأمانات النقدية والعينية.',
                'إلمام العاملين بما ورد في تعميم سعادة المدير العام رقم 1167879 وتاريخ 25/11/1444هـ المنظم لعمل الأمانات النقدية والعينية.',
            ],
        },
        {
            'title': 'الهدف الثاني: الدور الرقابي',
            'weight': 25,
            'criteria': [
                'إعداد محضر الجرد الشهري والالتزام به.',
                'الجرد من قبل اللجنة المكلفة بالجرد بصفة شهرية.',
            ],
        },
        {
            'title': 'الهدف الثالث: تقييم الأداء',
            'weight': 25,
            'criteria': [
                'تضمين أكثر من توقيع لتصديق الشيكات للمبالغ المودعة بالبنك.',
                'تكليف ضابط بشعبة الأمانات النقدية والعينية.',
                'التأكد من عملية إرجاع جميع الأمانات المتبقية للنزلاء المبعدين والمفرج عنهم بموجب سند الاستلام الموجود لدى قسم الأمانات وأن يتم سحب المبالغ الموجودة في بطاقة النزيل وتسليمها فورًا.',
                'التأكد من مطابقة رصيد مبلغ البنك مع الصندوق حسب الجرد.',
                'قيام ضابط القضية بإشعار الأمانات بإطلاق السجين أو نقله قبل الموعد بـ 24 ساعة.',
                'التأكد من أن يتم إيداع أمانات النزلاء النقدية من قبل ذويهم في الحساب البنكي المعتمد للسجن ومنع تداول المبالغ النقدية.',
                'التأكد من استلام البيان الخاص بأمانات النزلاء، كشف حساب بنكي، المودعة بالبنك بصفة يومية وأن يتم شحنها في بطاقات النزلاء فورًا ومصادقة ضابط الأمانات على ذلك.',
                'شحن المبالغ النقدية مباشرة في بطاقة النزيل قبل دخوله السجن وتقييده في السجلات المخصصة لذلك وإعطاء النزيل سند يفيد بشحن المبلغ في بطاقته.',
                'يكون السحب من الحساب بموجب شيك فقط من المخولين ويحدد في متن الشيك الغرض من صرف الشيك.',
            ],
        },
        {
            'title': 'الهدف الرابع: الموارد المؤسسية',
            'weight': 25,
            'criteria': [
                'التأكد من وجود سندات الاستلام والتسليم والتقيد بها وحفظها بشكل واضح لسهولة الرجوع لها.',
                'صناديق مخصصة لحفظ الأمانات العينية.',
            ],
        },
    ],
}


APPROVED_TEMPLATE_CONFIGS = [
    SAFETY_TEMPLATE_CONFIG,
    TREASURY_TEMPLATE_CONFIG,
]

APPROVED_TEMPLATE_CODES = [cfg['code'] for cfg in APPROVED_TEMPLATE_CONFIGS]


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
    user = User.query.filter_by(username=username).first()

    if not user:
        user = User(username=username)
        db.session.add(user)

    user.full_name = full_name
    user.role = role
    user.job_title = job_title
    user.region = region
    user.department = department
    user.org_unit_type = org_unit_type
    user.is_active_user = True
    user.set_password('123456')

    return user


def get_or_create_region(name):
    region = Region.query.filter_by(name=name).first()

    if not region:
        region = Region(name=name)
        db.session.add(region)
        db.session.flush()

    return region


def get_or_create_department(name, code):
    department = Department.query.filter_by(code=code).first()

    if not department:
        department = Department.query.filter_by(name=name).first()

    if not department:
        department = Department(name=name, code=code)
        db.session.add(department)

    department.name = name
    department.code = code
    db.session.flush()

    return department


def get_or_create_prison(name, region):
    prison = Prison.query.filter_by(name=name, region_id=region.id).first()

    if not prison:
        prison = Prison(name=name, region=region)
        db.session.add(prison)
        db.session.flush()

    return prison


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


def create_approved_template(config):
    template_name = config.get('name')
    template_code = config.get('code')
    template_description = config.get('description') or ''

    if not template_name:
        raise ValueError(f"اسم النموذج مفقود. config = {config}")

    if not template_code:
        raise ValueError(f"كود النموذج مفقود. config = {config}")

    template = Template(
        name=template_name,
        code=template_code,
        description=template_description,
        is_active=True
    )

    db.session.add(template)
    db.session.flush()

    for section_order, section_config in enumerate(config.get('sections', []), start=1):
        section_title = section_config.get('title')
        section_weight = section_config.get('weight', 0)

        if not section_title:
            raise ValueError(f"اسم الهدف مفقود في النموذج: {template_name}")

        section = TemplateSection(
            template=template,
            title=section_title,
            weight_percentage=section_weight,
            sort_order=section_order
        )

        db.session.add(section)
        db.session.flush()

        for criterion_order, criterion_text in enumerate(section_config.get('criteria', []), start=1):
            if not criterion_text:
                continue

            criterion = TemplateCriterion(
                section=section,
                text=criterion_text,
                sort_order=criterion_order
            )

            db.session.add(criterion)

    db.session.flush()
    return template


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

        # لا يوجد تصنيف للملاحظة في الشاشة.
        # هذا الحقل يبقى داخليًا فقط لأن الجدول عندك معرف category كحقل إلزامي.
        category='عام',

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


def delete_demo_operational_data():
    """
    تستخدم عند وجود قاعدة بيانات سابقة ولا نرغب بإعادة إنشائها كاملة.
    تحذف بيانات التشغيل التجريبية والنماذج والخطط فقط، وتترك المستخدمين والمناطق والسجون والإدارات.
    """

    db.session.execute(mission_prison_assignees.delete())
    db.session.execute(plan_item_regions.delete())
    db.session.execute(plan_item_prisons.delete())

    ObservationAction.query.delete(synchronize_session=False)
    AuditLog.query.delete(synchronize_session=False)
    Observation.query.delete(synchronize_session=False)
    MissionResponse.query.delete(synchronize_session=False)
    MissionPrisonReport.query.delete(synchronize_session=False)
    MissionRegion.query.delete(synchronize_session=False)
    Mission.query.delete(synchronize_session=False)

    PlanItem.query.delete(synchronize_session=False)
    AnnualPlan.query.delete(synchronize_session=False)

    TemplateCriterion.query.delete(synchronize_session=False)
    TemplateSection.query.delete(synchronize_session=False)
    Template.query.delete(synchronize_session=False)

    db.session.flush()


def seed_reference_data():
    regions = {}
    departments = {}
    prisons = {}

    for region_name in REGIONS:
        regions[region_name] = get_or_create_region(region_name)

    db.session.flush()

    for department_name, department_code in DEPARTMENTS:
        departments[department_name] = get_or_create_department(department_name, department_code)

    db.session.flush()

    for region_name, prison_names in PRISONS.items():
        for prison_name in prison_names:
            prisons[prison_name] = get_or_create_prison(prison_name, regions[region_name])

    db.session.flush()

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

    return {
        'regions': regions,
        'departments': departments,
        'prisons': prisons,
        'central_admin': central_admin,
        'central_operator': central_operator,
        'central_operator_2': central_operator_2,
        'central_director': central_director,
        'dg': dg,
        'department_users': department_users,
        'region_managers': region_managers,
        'prison_directors': prison_directors,
        'executors': executors,
    }


def seed_templates():
    templates = {}

    for config in APPROVED_TEMPLATE_CONFIGS:
        template = create_approved_template(config)
        templates[config['code']] = template

    db.session.flush()
    return templates


def seed_plan_and_missions(context, templates):
    regions = context['regions']
    departments = context['departments']
    central_admin = context['central_admin']
    central_operator = context['central_operator']
    central_director = context['central_director']
    dg = context['dg']
    region_managers = context['region_managers']
    executors = context['executors']

    safety_template = templates['SAFETY-001']
    treasury_template = templates['TREASURY-001']

    annual_plan = AnnualPlan(
        title='الخطة السنوية لأعمال المراجعة الداخلية والرقابة بالسجون 2026',
        year=2026,
        notes='خطة تشغيلية تجريبية مبنية على النموذجين المعتمدين فقط: السلامة، والأمانات النقدية والعينية.'
    )
    
    db.session.add(annual_plan)
    db.session.flush()

    plan_items = [
        ('جولة تفتيشية لنشاط مراجعة السلامة داخل السجون - الربع الأول', safety_template, 15, ['الرياض', 'مكة المكرمة', 'عسير']),
        ('جولة تفتيشية لنشاط الأمانات النقدية والعينية - الربع الثاني', treasury_template, 45, ['المنطقة الشرقية', 'القصيم', 'المدينة المنورة']),
        ('جولة متابعة لملاحظات السلامة الحرجة', safety_template, 75, ['تبوك', 'حائل', 'الحدود الشمالية', 'الجوف']),
        ('جولة متابعة لملاحظات الأمانات النقدية والعينية', treasury_template, 110, ['جازان', 'نجران', 'الباحة']),
        ('جولة وطنية لمتابعة الملاحظات المتأخرة', safety_template, 150, REGIONS),
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

    mission_specs = [
        {
            'reference_no': 'IA-2026-001',
            'title': 'جولة تفتيشية لنشاط مراجعة السلامة داخل السجون - السجون الرئيسة',
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
            'title': 'جولة تفتيشية لنشاط الأمانات النقدية والعينية',
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
            'title': 'متابعة ملاحظات السلامة ذات الأثر العالي',
            'template': safety_template,
            'mission_classification': 'follow_up',
            'priority_level': 'medium',
            'assignment_mode': 'central_with_region_completion',
            'status': 'under_central_review',
            'regions': ['تبوك', 'حائل', 'الحدود الشمالية', 'الجوف'],
            'planned_offset': -18,
            'due_offset': 5,
        },
        {
            'reference_no': 'IA-2026-004',
            'title': 'متابعة ملاحظات الأمانات النقدية والعينية',
            'template': treasury_template,
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

                criterion_1 = get_first_criterion(template, 1, 0)
                criterion_2 = get_first_criterion(template, 1, 1)
                criterion_3 = get_first_criterion(template, 2, 0)

                if template.code == 'SAFETY-001':
                    if mission_index in [1, 3]:
                        add_observation(
                            prison_report=prison_report,
                            user=assigned_users[0],
                            department=safety_dept,
                            criterion=criterion_1,
                            observation_type='criterion',
                            title=f'قصور في جاهزية وسائل السلامة - {prison.name}',
                            description='لوحظ وجود نقص في بعض متطلبات السلامة التشغيلية، مع الحاجة إلى تحديث سجلات الفحص الدوري.',
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
                            description='توجد مواقع تحتاج إلى صيانة وقائية وتحديث بعض لوحات التوجيه والتنبيه.',
                            severity='متوسطة',
                            priority='مهمة',
                            sla_option='14bd',
                            due_days=14,
                            status='under_treatment',
                            remediation_recommendation='تنفيذ الصيانة الوقائية ورفع تقرير إقفال للمواقع المتأثرة.',
                            department_response='تمت جدولة أعمال الصيانة وجاري إرفاق الإثباتات بعد الانتهاء.'
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
                            severity='حرجة',
                            priority='عاجلة جدًا',
                            sla_option='24h',
                            due_days=-40,
                            status='closed_by_decision',
                            remediation_recommendation='الاستمرار في المتابعة الدورية وتحديث مؤشرات الالتزام.',
                            department_response='تمت المعالجة ورفع الإثباتات.',
                            prison_director_action='تم التحقق من الإجراء ورفعه لإدارة المراجعة الداخلية.',
                            closure_reason='تم التلافي وإرفاق الإثبات'
                        )

                        add_observation(
                            prison_report=prison_report,
                            user=assigned_users[1],
                            department=it_dept,
                            observation_type='other',
                            title=f'توثيق إلكتروني مكتمل بعد المعالجة - {prison.name}',
                            description='تمت مراجعة التوثيق الإلكتروني بعد التلافي وتبين اكتماله.',
                            severity='منخفضة',
                            priority='عادية',
                            sla_option='14bd',
                            due_days=-35,
                            status='remediated',
                            remediation_recommendation='اعتماد الإغلاق والمتابعة ضمن التقارير الدورية.',
                            department_response='تم اكتمال التوثيق.',
                            closure_reason='إفادة مقبولة من الإدارة المختصة'
                        )

                elif template.code == 'TREASURY-001':
                    add_observation(
                        prison_report=prison_report,
                        user=assigned_users[0],
                        department=wh_dept,
                        criterion=criterion_1,
                        observation_type='criterion',
                        title=f'فروقات في سجلات العهد والأمانات - {prison.name}',
                        description='تم رصد اختلافات محدودة بين السجل الورقي والسجل الإلكتروني لبعض العهد والأمانات.',
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
                        severity='متوسطة',
                        priority='مهمة',
                        sla_option='14bd',
                        due_days=14,
                        status='new',
                        remediation_recommendation='مراجعة التكامل بين السجل الإلكتروني ونموذج الجرد المعتمد.'
                    )

                prison_report.refresh_score()

            db.session.flush()

    db.session.commit()


# =========================================================
# التشغيل
# =========================================================

def seed_if_empty():
    """
    للاستخدام مع قاعدة بيانات جديدة فقط.
    """
    if User.query.first():
        return

    context = seed_reference_data()
    templates = seed_templates()
    seed_plan_and_missions(context, templates)


def refresh_approved_seed_data():
    """
    للاستخدام مع قاعدة بيانات قائمة بدون إعادة إنشاء كاملة.
    يحافظ على:
    - المستخدمين
    - المناطق
    - السجون
    - الإدارات

    ويعيد إنشاء:
    - النماذج المعتمدة فقط
    - الخطة السنوية
    - المهمات التجريبية
    - التقارير والملاحظات والسجل
    """
    delete_demo_operational_data()
    context = seed_reference_data()
    templates = seed_templates()
    seed_plan_and_missions(context, templates)
