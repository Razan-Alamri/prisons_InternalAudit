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


def _safe_avg(values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _closure_rate(total_count, closed_count):
    if total_count == 0:
        return 0
    return round((closed_count / total_count) * 100, 1)


@reports_bp.route('/')
@login_required
def index():
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

    region_id = (request.args.get('region_id') or '').strip()
    prison_id = (request.args.get('prison_id') or '').strip()
    template_id = (request.args.get('template_id') or '').strip()
    status = (request.args.get('status') or '').strip()

    if template_id.isdigit():
        q = q.filter(Mission.template_id == int(template_id))

    if status:
        q = q.filter(Mission.status == status)

    missions = q.all()

    if region_id.isdigit():
        selected_region_id = int(region_id)
        missions = [
            m for m in missions
            if any(mr.region_id == selected_region_id for mr in m.regions)
        ]
    else:
        selected_region_id = None

    if prison_id.isdigit():
        selected_prison_id = int(prison_id)
        missions = [
            m for m in missions
            if any(
                any(pr.prison_id == selected_prison_id for pr in mr.prison_reports)
                for mr in m.regions
            )
        ]
    else:
        selected_prison_id = None

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

                for obs in pr.observations:
                    filtered_observations.append(obs)

    missions_count = len({item['mission'].id for item in filtered_reports})
    regions_count = len({item['mission_region'].region_id for item in filtered_reports})
    prisons_count = len({item['prison_report'].prison_id for item in filtered_reports})

    report_scores = [item['prison_report'].score_percentage for item in filtered_reports if item['prison_report'].score_percentage is not None]
    overall_avg_score = _safe_avg(report_scores)

    observations_count = len(filtered_observations)
    critical_count = sum(1 for o in filtered_observations if o.severity in ['حرجة', 'عالية', 'مرتفعة'])
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
        dept_critical = sum(1 for o in dept_obs if o.severity in ['حرجة', 'عالية', 'مرتفعة'])

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
                }

            if pr.score_percentage is not None:
                region_groups[rid]['scores'].append(pr.score_percentage)

            pr_obs = pr.observations
            total_obs = len(pr_obs)
            closed_obs = sum(1 for o in pr_obs if o.status in closed_statuses)
            critical_obs = sum(1 for o in pr_obs if o.severity in ['حرجة', 'عالية', 'مرتفعة'])

            region_groups[rid]['observations_count'] += total_obs
            region_groups[rid]['closed_count'] += closed_obs
            region_groups[rid]['open_count'] += (total_obs - closed_obs)
            region_groups[rid]['critical_count'] += critical_obs

        for _, item in region_groups.items():
            avg_score = _safe_avg(item['scores'])
            region_rows.append({
                'region_name': item['region_name'],
                'avg_score': avg_score,
                'risk_level': _risk_from_score(avg_score),
                'observations_count': item['observations_count'],
                'open_count': item['open_count'],
                'critical_count': item['critical_count'],
                'closure_rate': _closure_rate(item['observations_count'], item['closed_count']),
            })

        region_rows.sort(key=lambda x: (x['avg_score'] is None, x['avg_score'] if x['avg_score'] is not None else 999))

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
                }

            if pr.score_percentage is not None:
                prison_groups[pid]['scores'].append(pr.score_percentage)

            pr_obs = pr.observations
            total_obs = len(pr_obs)
            closed_obs = sum(1 for o in pr_obs if o.status in closed_statuses)
            critical_obs = sum(1 for o in pr_obs if o.severity in ['حرجة', 'عالية', 'مرتفعة'])

            prison_groups[pid]['observations_count'] += total_obs
            prison_groups[pid]['closed_count'] += closed_obs
            prison_groups[pid]['open_count'] += (total_obs - closed_obs)
            prison_groups[pid]['critical_count'] += critical_obs

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
                'closure_rate': _closure_rate(item['observations_count'], item['closed_count']),
            })

        prison_rows.sort(key=lambda x: (-x['critical_count'], -(x['observations_count']), x['prison_name']))

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

    stats = {
        'missions_count': missions_count,
        'regions_count': regions_count,
        'prisons_count': prisons_count,
        'observations_count': observations_count,
        'critical_count': critical_count,
        'open_count': open_count,
        'overall_avg_score': overall_avg_score,
        'overall_closure_rate': overall_closure_rate,
        'overall_risk_level': _risk_from_score(overall_avg_score),
    }

    return render_template(
        'reports/index.html',
        title='التقارير',
        selected_scope_title=selected_scope_title,
        stats=stats,
        all_regions=all_regions,
        all_prisons=all_prisons,
        all_templates=all_templates,
        filters={
            'region_id': region_id,
            'prison_id': prison_id,
            'template_id': template_id,
            'status': status,
        },
        region_rows=region_rows,
        prison_rows=prison_rows,
        dept_rows=dept_rows,
        chart_labels=chart_labels,
        chart_scores=chart_scores,
        chart_open_obs=chart_open_obs,
        chart_critical=chart_critical,
    )


@reports_bp.route('/export/dashboard-excel')
@login_required
def export_dashboard_excel():
    wb = Workbook()
    ws = wb.active
    ws.title = 'Reports'
    ws.append(['التقارير'])
    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    return send_file(
        as_attachment=True,
        download_name='reports-dashboard.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@reports_bp.route('/export/dashboard-pdf')
@login_required
def export_dashboard_pdf():
    bio = BytesIO()
    c = canvas.Canvas(bio, pagesize=A4)
    c.setFont("Helvetica", 14)
    c.drawString(60, 800, "Reports Dashboard")
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
    width, height = A4
    y = height - 50

    def write_line(text, font='Helvetica', size=10, step=18):
        nonlocal y
        c.setFont(font, size)
        c.drawString(40, y, str(text))
        y -= step
        if y < 60:
            c.showPage()
            y = height - 50

    write_line(f"Mission Report: {mission.reference_no}", font='Helvetica-Bold', size=14, step=24)
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
            f"Obs: {observations_count}",
            font='Helvetica-Bold',
            size=10
        )

        for pr in mr.prison_reports:
            write_line(
                f"  - Prison: {pr.prison.name if pr.prison else '-'} | "
                f"Score: {pr.score_percentage if pr.score_percentage is not None else '-'} | "
                f"Obs: {len(pr.observations)}",
                size=9,
                step=16
            )

        write_line("")

    c.save()
    bio.seek(0)

    return send_file(
        bio,
        as_attachment=True,
        download_name=f'{mission.reference_no}.pdf',
        mimetype='application/pdf'
    )