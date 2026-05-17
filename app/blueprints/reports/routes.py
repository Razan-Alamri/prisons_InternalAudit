from io import BytesIO
from flask import Blueprint, render_template, request, send_file
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from ...models import (
    Mission,
    MissionRegion,
    MissionPrisonReport,
    Observation,
    Region,
    Prison,
    Template,
    Department,
    User,
    MISSION_CLASSIFICATION_LABELS,
    MISSION_STATUS_LABELS,
    PRIORITY_LEVEL_LABELS,
    ASSIGNMENT_MODE_LABELS,
    MISSION_REGION_STATUS_LABELS,
)

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


REGION_SVG_ID_MAP = {
    'الرياض': 'SA01',
    'مكة المكرمة': 'SA02',
    'المدينة المنورة': 'SA03',
    'المنطقة الشرقية': 'SA04',
    'القصيم': 'SA05',
    'حائل': 'SA06',
    'تبوك': 'SA07',
    'الحدود الشمالية': 'SA08',
    'جازان': 'SA09',
    'نجران': 'SA10',
    'الباحة': 'SA11',
    'الجوف': 'SA12',
    'عسير': 'SA14',
}

# إزاحات بسيطة لمنع تداخل الليبلز
REGION_LABEL_OFFSETS = {
    'الرياض': {'dx': 10, 'dy': 8},
    'مكة المكرمة': {'dx': -18, 'dy': 8},
    'المدينة المنورة': {'dx': -28, 'dy': -4},
    'المنطقة الشرقية': {'dx': 34, 'dy': 10},
    'القصيم': {'dx': 0, 'dy': -10},
    'حائل': {'dx': -8, 'dy': -16},
    'تبوك': {'dx': -26, 'dy': -8},
    'الحدود الشمالية': {'dx': 8, 'dy': -18},
    'جازان': {'dx': -10, 'dy': 18},
    'نجران': {'dx': 20, 'dy': 16},
    'الباحة': {'dx': -8, 'dy': 8},
    'الجوف': {'dx': -12, 'dy': -18},
    'عسير': {'dx': 4, 'dy': 16},
}


def _risk_from_score(score):
    if score is None:
        return 'غير متاح'
    if score >= 85:
        return 'منخفضة'
    if score >= 70:
        return 'متوسطة'
    if score >= 50:
        return 'مرتفعة'
    return 'حرجة'


def _risk_key_from_label(risk_label):
    if risk_label == 'منخفضة':
        return 'low'
    if risk_label == 'متوسطة':
        return 'med'
    if risk_label == 'مرتفعة':
        return 'high'
    if risk_label == 'حرجة':
        return 'critical'
    return 'na'


def _safe_avg(values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _closure_rate(total_count, closed_count):
    if total_count == 0:
        return 0
    return round((closed_count / total_count) * 100, 1)


def _base_query():
    q = Mission.query.options(
        joinedload(Mission.template),
        joinedload(Mission.regions).joinedload(MissionRegion.region),
        joinedload(Mission.regions)
            .joinedload(MissionRegion.prison_reports)
            .joinedload(MissionPrisonReport.prison),
        joinedload(Mission.regions)
            .joinedload(MissionRegion.prison_reports)
            .joinedload(MissionPrisonReport.observations)
            .joinedload(Observation.department),
        joinedload(Mission.regions)
            .joinedload(MissionRegion.prison_reports)
            .joinedload(MissionPrisonReport.assignees),
    ).order_by(Mission.updated_at.desc())

    if current_user.role == 'director_general':
        q = q.filter(Mission.status.in_(['ready_for_dg', 'closed']))

    if current_user.role == 'region_manager':
        q = q.join(Mission.regions).filter(MissionRegion.region_id == current_user.region_id)

    if current_user.role == 'executor':
        q = q.filter(
            Mission.regions.any(
                MissionRegion.prison_reports.any(
                    MissionPrisonReport.assignees.any(User.id == current_user.id)
                )
            )
        )

    return q


def _collect_dashboard_data(region_id='', prison_id='', template_id='', status=''):
    q = _base_query()

    if template_id.isdigit():
        q = q.filter(Mission.template_id == int(template_id))

    if status:
        q = q.filter(Mission.status == status)

    missions = q.all()

    selected_region_id = int(region_id) if str(region_id).isdigit() else None
    selected_prison_id = int(prison_id) if str(prison_id).isdigit() else None

    if selected_region_id:
        missions = [
            m for m in missions
            if any(mr.region_id == selected_region_id for mr in m.regions)
        ]

    if selected_prison_id:
        missions = [
            m for m in missions
            if any(
                any(pr.prison_id == selected_prison_id for pr in mr.prison_reports)
                for mr in m.regions
            )
        ]

    all_regions = Region.query.order_by(Region.name).all()
    all_prisons = Prison.query.order_by(Prison.name).all()
    all_templates = Template.query.filter_by(is_active=True).order_by(Template.name).all()
    all_departments = Department.query.order_by(Department.name).all()

    closed_statuses = {'closed', 'resolved', 'remediated', 'closed_by_decision'}

    filtered_reports = []
    filtered_observations = []

    for mission in missions:
        for mr in mission.regions:
            if selected_region_id and mr.region_id != selected_region_id:
                continue

            for pr in mr.prison_reports:
                if selected_prison_id and pr.prison_id != selected_prison_id:
                    continue

                filtered_reports.append({
                    'mission': mission,
                    'mission_region': mr,
                    'prison_report': pr,
                })

                filtered_observations.extend(pr.observations)

    missions_count = len({item['mission'].id for item in filtered_reports})
    regions_count = len({item['mission_region'].region_id for item in filtered_reports})
    prisons_count = len({item['prison_report'].prison_id for item in filtered_reports})

    report_scores = [
        item['prison_report'].score_percentage
        for item in filtered_reports
        if item['prison_report'].score_percentage is not None
    ]
    overall_avg_score = _safe_avg(report_scores)

    observations_count = len(filtered_observations)
    critical_count = sum(1 for o in filtered_observations if o.severity in ['حرجة', 'عالية'])
    high_count = sum(1 for o in filtered_observations if o.severity == 'مرتفعة')
    medium_count = sum(1 for o in filtered_observations if o.severity == 'متوسطة')
    low_count = sum(1 for o in filtered_observations if o.severity == 'منخفضة')
    closed_count = sum(1 for o in filtered_observations if o.status in closed_statuses)
    open_count = observations_count - closed_count
    overall_closure_rate = _closure_rate(observations_count, closed_count)

    dept_rows = []
    for dept in all_departments:
        dept_obs = [o for o in filtered_observations if o.department_id == dept.id]
        if not dept_obs:
            continue

        dept_total = len(dept_obs)
        dept_closed = sum(1 for o in dept_obs if o.status in closed_statuses)
        dept_open = dept_total - dept_closed
        dept_critical = sum(1 for o in dept_obs if o.severity in ['حرجة', 'عالية'])

        dept_rows.append({
            'department_name': dept.name,
            'observations_count': dept_total,
            'open_count': dept_open,
            'closed_count': dept_closed,
            'critical_count': dept_critical,
            'closure_rate': _closure_rate(dept_total, dept_closed),
        })

    dept_rows.sort(key=lambda x: (-x['critical_count'], -x['observations_count'], x['department_name']))

    region_rows = []
    if not selected_region_id and not selected_prison_id:
        region_groups = {}

        for item in filtered_reports:
            mr = item['mission_region']
            pr = item['prison_report']
            rid = mr.region_id

            if rid not in region_groups:
                region_groups[rid] = {
                    'region_name': mr.region.name if mr.region else '—',
                    'scores': [],
                    'observations_count': 0,
                    'critical_count': 0,
                    'closed_count': 0,
                    'open_count': 0,
                    'high_count': 0,
                    'medium_count': 0,
                    'low_count': 0,
                }

            if pr.score_percentage is not None:
                region_groups[rid]['scores'].append(pr.score_percentage)

            pr_obs = pr.observations
            total_obs = len(pr_obs)
            closed_obs = sum(1 for o in pr_obs if o.status in closed_statuses)
            critical_obs = sum(1 for o in pr_obs if o.severity in ['حرجة', 'عالية'])
            high_obs = sum(1 for o in pr_obs if o.severity == 'مرتفعة')
            medium_obs = sum(1 for o in pr_obs if o.severity == 'متوسطة')
            low_obs = sum(1 for o in pr_obs if o.severity == 'منخفضة')

            region_groups[rid]['observations_count'] += total_obs
            region_groups[rid]['closed_count'] += closed_obs
            region_groups[rid]['open_count'] += (total_obs - closed_obs)
            region_groups[rid]['critical_count'] += critical_obs
            region_groups[rid]['high_count'] += high_obs
            region_groups[rid]['medium_count'] += medium_obs
            region_groups[rid]['low_count'] += low_obs

        for _, item in region_groups.items():
            avg_score = _safe_avg(item['scores'])
            region_rows.append({
                'region_name': item['region_name'],
                'avg_score': avg_score,
                'risk_level': _risk_from_score(avg_score),
                'observations_count': item['observations_count'],
                'open_count': item['open_count'],
                'critical_count': item['critical_count'],
                'high_count': item['high_count'],
                'medium_count': item['medium_count'],
                'low_count': item['low_count'],
                'closure_rate': _closure_rate(item['observations_count'], item['closed_count']),
            })

        region_rows.sort(key=lambda x: (
            x['avg_score'] is None,
            x['avg_score'] if x['avg_score'] is not None else 999
        ))

    prison_rows = []
    if selected_region_id and not selected_prison_id:
        prison_groups = {}

        for item in filtered_reports:
            pr = item['prison_report']
            mr = item['mission_region']
            pid = pr.prison_id

            if pid not in prison_groups:
                prison_groups[pid] = {
                    'prison_name': pr.prison.name if pr.prison else '—',
                    'region_name': mr.region.name if mr.region else '—',
                    'scores': [],
                    'observations_count': 0,
                    'critical_count': 0,
                    'closed_count': 0,
                    'open_count': 0,
                    'high_count': 0,
                    'medium_count': 0,
                    'low_count': 0,
                }

            if pr.score_percentage is not None:
                prison_groups[pid]['scores'].append(pr.score_percentage)

            pr_obs = pr.observations
            total_obs = len(pr_obs)
            closed_obs = sum(1 for o in pr_obs if o.status in closed_statuses)
            critical_obs = sum(1 for o in pr_obs if o.severity in ['حرجة', 'عالية'])
            high_obs = sum(1 for o in pr_obs if o.severity == 'مرتفعة')
            medium_obs = sum(1 for o in pr_obs if o.severity == 'متوسطة')
            low_obs = sum(1 for o in pr_obs if o.severity == 'منخفضة')

            prison_groups[pid]['observations_count'] += total_obs
            prison_groups[pid]['closed_count'] += closed_obs
            prison_groups[pid]['open_count'] += (total_obs - closed_obs)
            prison_groups[pid]['critical_count'] += critical_obs
            prison_groups[pid]['high_count'] += high_obs
            prison_groups[pid]['medium_count'] += medium_obs
            prison_groups[pid]['low_count'] += low_obs

        for _, item in prison_groups.items():
            avg_score = _safe_avg(item['scores'])
            prison_rows.append({
                'prison_name': item['prison_name'],
                'region_name': item['region_name'],
                'avg_score': avg_score,
                'risk_level': _risk_from_score(avg_score),
                'observations_count': item['observations_count'],
                'open_count': item['open_count'],
                'critical_count': item['critical_count'],
                'high_count': item['high_count'],
                'medium_count': item['medium_count'],
                'low_count': item['low_count'],
                'closure_rate': _closure_rate(item['observations_count'], item['closed_count']),
            })

        prison_rows.sort(key=lambda x: (-x['critical_count'], -x['observations_count'], x['prison_name']))

    selected_scope_title = 'التقارير'
    if selected_prison_id:
        prison_obj = next((p for p in all_prisons if p.id == selected_prison_id), None)
        if prison_obj:
            selected_scope_title = f'تقرير السجن: {prison_obj.name}'
    elif selected_region_id:
        region_obj = next((r for r in all_regions if r.id == selected_region_id), None)
        if region_obj:
            selected_scope_title = f'تقرير المنطقة: {region_obj.name}'

    chart_labels = []
    chart_scores = []
    chart_open_obs = []
    chart_critical = []

    if not selected_region_id and not selected_prison_id:
        chart_labels = [r['region_name'] for r in region_rows[:8]]
        chart_scores = [r['avg_score'] or 0 for r in region_rows[:8]]
        chart_open_obs = [r['open_count'] for r in region_rows[:8]]
        chart_critical = [r['critical_count'] for r in region_rows[:8]]
    elif selected_region_id and not selected_prison_id:
        chart_labels = [p['prison_name'] for p in prison_rows[:10]]
        chart_scores = [p['avg_score'] or 0 for p in prison_rows[:10]]
        chart_open_obs = [p['open_count'] for p in prison_rows[:10]]
        chart_critical = [p['critical_count'] for p in prison_rows[:10]]

    map_regions = []
    for row in region_rows:
        svg_id = REGION_SVG_ID_MAP.get(row['region_name'])
        if not svg_id:
            continue

        offsets = REGION_LABEL_OFFSETS.get(row['region_name'], {'dx': 0, 'dy': 0})

        map_regions.append({
            'svg_id': svg_id,
            'name': row['region_name'],
            'avg_score': row['avg_score'],
            'risk_label': row['risk_level'],
            'risk_key': _risk_key_from_label(row['risk_level']),
            'observations_count': row['observations_count'],
            'open_count': row['open_count'],
            'critical_count': row['critical_count'],
            'closure_rate': row['closure_rate'],
            'dx': offsets['dx'],
            'dy': offsets['dy'],
        })

    stats = {
        'missions_count': missions_count,
        'regions_count': regions_count,
        'prisons_count': prisons_count,
        'observations_count': observations_count,
        'critical_count': critical_count,
        'high_count': high_count,
        'medium_count': medium_count,
        'low_count': low_count,
        'open_count': open_count,
        'overall_avg_score': overall_avg_score,
        'overall_closure_rate': overall_closure_rate,
        'overall_risk_level': _risk_from_score(overall_avg_score),
    }

    return {
        'selected_scope_title': selected_scope_title,
        'stats': stats,
        'all_regions': all_regions,
        'all_prisons': all_prisons,
        'all_templates': all_templates,
        'filters': {
            'region_id': region_id,
            'prison_id': prison_id,
            'template_id': template_id,
            'status': status,
        },
        'region_rows': region_rows,
        'prison_rows': prison_rows,
        'dept_rows': dept_rows,
        'chart_labels': chart_labels,
        'chart_scores': chart_scores,
        'chart_open_obs': chart_open_obs,
        'chart_critical': chart_critical,
        'map_regions': map_regions,
    }


@reports_bp.route('/')
@login_required
def index():
    data = _collect_dashboard_data(
        region_id=(request.args.get('region_id') or '').strip(),
        prison_id=(request.args.get('prison_id') or '').strip(),
        template_id=(request.args.get('template_id') or '').strip(),
        status=(request.args.get('status') or '').strip(),
    )
    return render_template('reports/index.html', title='التقارير', **data)


@reports_bp.route('/export/dashboard-excel')
@login_required
def export_dashboard_excel():
    data = _collect_dashboard_data(
        region_id=(request.args.get('region_id') or '').strip(),
        prison_id=(request.args.get('prison_id') or '').strip(),
        template_id=(request.args.get('template_id') or '').strip(),
        status=(request.args.get('status') or '').strip(),
    )

    wb = Workbook()
    ws = wb.active
    ws.title = 'Dashboard'

    ws.append(['نطاق التقرير', data['selected_scope_title']])
    ws.append(['عدد المهام', data['stats']['missions_count']])
    ws.append(['عدد المناطق', data['stats']['regions_count']])
    ws.append(['عدد السجون', data['stats']['prisons_count']])
    ws.append(['إجمالي الملاحظات', data['stats']['observations_count']])
    ws.append(['الملاحظات المفتوحة', data['stats']['open_count']])
    ws.append(['الحرجة / العالية', data['stats']['critical_count']])
    ws.append(['مرتفعة', data['stats']['high_count']])
    ws.append(['متوسطة', data['stats']['medium_count']])
    ws.append(['منخفضة', data['stats']['low_count']])
    ws.append(['متوسط الدرجة', data['stats']['overall_avg_score'] if data['stats']['overall_avg_score'] is not None else '—'])
    ws.append(['نسبة الإغلاق', f"{data['stats']['overall_closure_rate']}%"])
    ws.append([])

    if data['region_rows']:
        ws.append(['المناطق'])
        ws.append(['المنطقة', 'متوسط الدرجة', 'مستوى الخطورة', 'إجمالي الملاحظات', 'المفتوحة', 'الحرجة / العالية', 'نسبة الإغلاق'])
        for row in data['region_rows']:
            ws.append([
                row['region_name'],
                row['avg_score'] if row['avg_score'] is not None else '—',
                row['risk_level'],
                row['observations_count'],
                row['open_count'],
                row['critical_count'],
                f"{row['closure_rate']}%",
            ])
        ws.append([])

    if data['prison_rows']:
        ws.append(['السجون'])
        ws.append(['السجن', 'المنطقة', 'متوسط الدرجة', 'مستوى الخطورة', 'إجمالي الملاحظات', 'المفتوحة', 'الحرجة / العالية', 'نسبة الإغلاق'])
        for row in data['prison_rows']:
            ws.append([
                row['prison_name'],
                row['region_name'],
                row['avg_score'] if row['avg_score'] is not None else '—',
                row['risk_level'],
                row['observations_count'],
                row['open_count'],
                row['critical_count'],
                f"{row['closure_rate']}%",
            ])
        ws.append([])

    if data['dept_rows']:
        ws.append(['الإدارات المعالجة'])
        ws.append(['الإدارة', 'إجمالي الملاحظات', 'المفتوحة', 'المغلقة', 'الحرجة / العالية', 'نسبة الإغلاق'])
        for row in data['dept_rows']:
            ws.append([
                row['department_name'],
                row['observations_count'],
                row['open_count'],
                row['closed_count'],
                row['critical_count'],
                f"{row['closure_rate']}%",
            ])

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)

    return send_file(
        bio,
        as_attachment=True,
        download_name='reports-dashboard.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@reports_bp.route('/export/dashboard-pdf')
@login_required
def export_dashboard_pdf():
    data = _collect_dashboard_data(
        region_id=(request.args.get('region_id') or '').strip(),
        prison_id=(request.args.get('prison_id') or '').strip(),
        template_id=(request.args.get('template_id') or '').strip(),
        status=(request.args.get('status') or '').strip(),
    )

    bio = BytesIO()
    c = canvas.Canvas(bio, pagesize=A4)
    _, height = A4
    y = height - 50

    def write_line(text, size=10, step=18):
        nonlocal y
        c.setFont("Helvetica", size)
        c.drawString(40, y, str(text))
        y -= step
        if y < 60:
            c.showPage()
            y = height - 50

    write_line("Reports Dashboard", size=14, step=24)
    write_line(f"Scope: {data['selected_scope_title']}")
    write_line(f"Missions: {data['stats']['missions_count']}")
    write_line(f"Regions: {data['stats']['regions_count']}")
    write_line(f"Prisons: {data['stats']['prisons_count']}")
    write_line(f"Observations: {data['stats']['observations_count']}")
    write_line(f"Open: {data['stats']['open_count']}")
    write_line(f"Critical/High: {data['stats']['critical_count']}")
    write_line(f"Avg Score: {data['stats']['overall_avg_score'] if data['stats']['overall_avg_score'] is not None else '-'}")
    write_line(f"Closure Rate: {data['stats']['overall_closure_rate']}%")
    write_line("")

    for row in data['region_rows'][:12]:
        write_line(
            f"Region: {row['region_name']} | Score: {row['avg_score'] if row['avg_score'] is not None else '-'} | Risk: {row['risk_level']} | Open: {row['open_count']}"
        )

    c.save()
    bio.seek(0)

    return send_file(
        bio,
        as_attachment=True,
        download_name='reports-dashboard.pdf',
        mimetype='application/pdf'
    )


@reports_bp.route('/mission/<int:mission_id>/excel')
@login_required
def mission_excel(mission_id):
    mission = Mission.query.options(
        joinedload(Mission.template),
        joinedload(Mission.regions).joinedload(MissionRegion.region),
        joinedload(Mission.regions).joinedload(MissionRegion.prison_reports).joinedload(MissionPrisonReport.prison),
        joinedload(Mission.regions).joinedload(MissionRegion.prison_reports).joinedload(MissionPrisonReport.observations),
    ).get_or_404(mission_id)

    wb = Workbook()
    ws = wb.active
    ws.title = 'Mission'

    ws.append(['رقم المرجع', mission.reference_no])
    ws.append(['العنوان', mission.title])
    ws.append(['النموذج', mission.template.name if mission.template else '—'])
    ws.append(['الحالة', MISSION_STATUS_LABELS.get(mission.status, mission.status)])
    ws.append(['التصنيف', MISSION_CLASSIFICATION_LABELS.get(mission.mission_classification, mission.mission_classification)])
    ws.append(['الأولوية', PRIORITY_LEVEL_LABELS.get(mission.priority_level, mission.priority_level)])
    ws.append(['آلية الإسناد', ASSIGNMENT_MODE_LABELS.get(mission.assignment_mode, mission.assignment_mode)])
    ws.append(['تاريخ التنفيذ المستهدف', str(mission.planned_date) if mission.planned_date else '—'])
    ws.append(['تاريخ الاستحقاق', str(mission.due_date) if mission.due_date else '—'])
    ws.append([])

    ws.append([
        'المنطقة',
        'حالة المنطقة',
        'السجون',
        'عدد السجون',
        'الدرجة',
        'مستوى المخاطر',
        'عدد الملاحظات'
    ])

    for mr in mission.regions:
        prison_names = '، '.join(pr.prison.name for pr in mr.prison_reports if pr.prison) or '—'
        observations_count = sum(len(pr.observations) for pr in mr.prison_reports)

        ws.append([
            mr.region.name if mr.region else '—',
            MISSION_REGION_STATUS_LABELS.get(mr.status, mr.status),
            prison_names,
            len(mr.prison_reports),
            mr.score_percentage if mr.score_percentage is not None else '—',
            mr.risk_level if mr.risk_level else 'لم يبدأ',
            observations_count,
        ])

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)

    return send_file(
        bio,
        as_attachment=True,
        download_name=f'{mission.reference_no}.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@reports_bp.route('/mission/<int:mission_id>/pdf')
@login_required
def mission_pdf(mission_id):
    mission = Mission.query.options(
        joinedload(Mission.template),
        joinedload(Mission.regions).joinedload(MissionRegion.region),
        joinedload(Mission.regions).joinedload(MissionRegion.prison_reports).joinedload(MissionPrisonReport.prison),
        joinedload(Mission.regions).joinedload(MissionRegion.prison_reports).joinedload(MissionPrisonReport.observations),
    ).get_or_404(mission_id)

    bio = BytesIO()
    c = canvas.Canvas(bio, pagesize=A4)
    _, height = A4
    y = height - 50

    def write_line(text, size=10, step=18):
        nonlocal y
        c.setFont("Helvetica", size)
        c.drawString(40, y, str(text))
        y -= step
        if y < 60:
            c.showPage()
            y = height - 50

    write_line(f"Mission Report: {mission.reference_no}", size=14, step=24)
    write_line(f"Title: {mission.title}")
    write_line(f"Template: {mission.template.name if mission.template else '-'}")
    write_line(f"Status: {MISSION_STATUS_LABELS.get(mission.status, mission.status)}")
    write_line(f"Classification: {MISSION_CLASSIFICATION_LABELS.get(mission.mission_classification, mission.mission_classification)}")
    write_line(f"Priority: {PRIORITY_LEVEL_LABELS.get(mission.priority_level, mission.priority_level)}")
    write_line(f"Assignment: {ASSIGNMENT_MODE_LABELS.get(mission.assignment_mode, mission.assignment_mode)}")
    write_line("")

    for mr in mission.regions:
        observations_count = sum(len(pr.observations) for pr in mr.prison_reports)

        write_line(
            f"Region: {mr.region.name if mr.region else '-'} | "
            f"Status: {MISSION_REGION_STATUS_LABELS.get(mr.status, mr.status)} | "
            f"Score: {mr.score_percentage if mr.score_percentage is not None else '-'} | "
            f"Risk: {mr.risk_level if mr.risk_level else 'Not started'} | "
            f"Obs: {observations_count}"
        )

    c.save()
    bio.seek(0)

    return send_file(
        bio,
        as_attachment=True,
        download_name=f'{mission.reference_no}.pdf',
        mimetype='application/pdf'
    )