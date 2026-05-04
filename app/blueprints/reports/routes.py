from io import BytesIO
from flask import Blueprint, send_file, render_template
from flask_login import login_required
from sqlalchemy.orm import joinedload
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from ...models import (
    Mission,
    MissionRegion,
    MissionPrisonReport,
    MISSION_CLASSIFICATION_LABELS,
    MISSION_STATUS_LABELS,
    PRIORITY_LEVEL_LABELS,
    ASSIGNMENT_MODE_LABELS,
    MISSION_REGION_STATUS_LABELS,
)

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


@reports_bp.route('/')
@login_required
def index():
    missions = Mission.query.order_by(Mission.updated_at.desc()).all()
    return render_template('reports/index.html', missions=missions, title='التقارير المجمعة')


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