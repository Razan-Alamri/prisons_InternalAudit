from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, current_app
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from sqlalchemy import or_

from ...extensions import db
from ...permissions import roles_required
from ...utils import save_uploaded_files, compute_due_date, log_action

from ...models import (
    Mission, MissionRegion, MissionPrisonReport,
    Region, Prison, User, Template, TemplateSection, TemplateCriterion,
    MissionResponse, Observation, ObservationAction, Attachment, Department,
    SCORE_LABELS, OBS_STATUS, SLA_OPTIONS,
    MISSION_CLASSIFICATIONS, PRIORITY_LEVELS, ASSIGNMENT_MODES,
    AuditLog,
    ROLE_LABELS,
    MISSION_CLASSIFICATION_LABELS, PRIORITY_LEVEL_LABELS,
    MISSION_STATUS_LABELS, ASSIGNMENT_MODE_LABELS,
    MISSION_REGION_STATUS_LABELS, MISSION_PRISON_REPORT_STATUS_LABELS
)

missions_bp = Blueprint('missions', __name__, url_prefix='/missions')


def _next_reference():
    count = Mission.query.count() + 1
    return f'IA-{date.today().year}-{count:03d}'


def _score_options():
    return list(SCORE_LABELS.keys())


def _normalize_text(value):
    return ' '.join((value or '').strip().split())


def _safe_percent(value):
    if value is None:
        return '—'
    return f'{round(value, 1)}%'


def _executor_has_mission_access(mission, user):
    return any(
        user in pr.assignees
        for mr in mission.regions
        for pr in mr.prison_reports
    )


def _executor_has_prison_report_access(pr, user):
    return user in pr.assignees


def _deny_department_access_to_missions():
    if current_user.role in ['department_user', 'department_manager']:
        flash('لا تملك صلاحية الوصول إلى المهام والجولات.', 'danger')
        return redirect(url_for('missions.observations'))
    return None


def _build_auto_central_review_content(mission):
    total_regions = len(mission.regions)
    total_prisons = sum(len(mr.prison_reports) for mr in mission.regions)
    started_count = sum(mr.started_prisons_count for mr in mission.regions)
    submitted_count = sum(mr.completed_prisons_count for mr in mission.regions)
    open_observations = sum(mr.open_observations_count() for mr in mission.regions)

    scored_regions = [mr.score_percentage for mr in mission.regions if mr.score_percentage is not None]
    avg_score = round(sum(scored_regions) / len(scored_regions), 1) if scored_regions else None

    high_risk_regions = [mr.region.name for mr in mission.regions if mr.risk_level in ['مرتفعة', 'حرجة']]
    not_started_regions = [mr.region.name for mr in mission.regions if mr.started_prisons_count == 0]
    submitted_regions = [mr.region.name for mr in mission.regions if mr.status == 'submitted_to_central']

    summary_text = (
        f"نُفذت المهمة على عدد {total_regions} منطقة، وشملت {total_prisons} تقريرًا على مستوى السجون. "
        f"بدأ التنفيذ في {started_count} تقريرًا، وتم رفع {submitted_count} تقريرًا حتى تاريخه. "
        f"وبلغ عدد الملاحظات المفتوحة {open_observations} ملاحظة. "
    )

    if avg_score is not None:
        summary_text += f"كما بلغ متوسط الدرجة العامة للمناطق التي بدأ تنفيذها {_safe_percent(avg_score)}."
    else:
        summary_text += "ولم يبدأ التنفيذ الفعلي على التقارير بما يكفي لاحتساب متوسط الدرجة العامة."

    findings_parts = []

    if submitted_regions:
        findings_parts.append(
            f"تم استكمال ورفع نتائج بعض المناطق، ومن أبرزها: {'، '.join(submitted_regions[:5])}."
        )

    if high_risk_regions:
        findings_parts.append(
            f"أظهرت النتائج الحاجة إلى متابعة أكبر في المناطق ذات مستويات الخطورة الأعلى، ومنها: {'، '.join(high_risk_regions[:5])}."
        )

    if not_started_regions:
        findings_parts.append(
            f"لا تزال بعض المناطق في مرحلة ما قبل البدء أو التجهيز، ومنها: {'، '.join(not_started_regions[:5])}."
        )

    if open_observations > 0:
        findings_parts.append(
            "تركزت أبرز النتائج في استمرار وجود ملاحظات مفتوحة تتطلب المتابعة والمعالجة والإغلاق وفق الإجراءات المعتمدة."
        )

    if not findings_parts:
        findings_parts.append("لا توجد نتائج تفصيلية كافية حتى تاريخه، ويستمر استكمال التنفيذ والرفع على مستوى المناطق.")

    findings_text = " ".join(findings_parts)

    if submitted_count == total_prisons and total_prisons > 0 and open_observations == 0:
        recommendations_text = (
            "يوصى باعتماد نتائج المهمة ورفعها للمدير العام، نظرًا لاكتمال التنفيذ وعدم وجود ملاحظات مفتوحة مؤثرة."
        )
    elif submitted_count > 0:
        recommendations_text = (
            "يوصى باستكمال معالجة الملاحظات المفتوحة في المناطق غير المستوفية، والتحقق من الإغلاق قبل الرفع النهائي، "
            "مع إمكانية اعتماد الأجزاء المكتملة بحسب ما تراه إدارة المراجعة الداخلية."
        )
    else:
        recommendations_text = (
            "يوصى باستكمال التنفيذ والرفع من المناطق المستهدفة أولًا، ثم إعادة تقييم الجاهزية قبل اعتماد التقرير النهائي."
        )

    return {
        'final_summary': summary_text,
        'internal_audit_opinion': findings_text,
        'final_recommendations': recommendations_text,
    }


def _commitment_badge(due_date, status):
    if not due_date:
        return {'label': 'غير محدد', 'class': 'badge-neutral'}

    if status == 'submitted':
        return {'label': 'ملتزم', 'class': 'badge-risk-low'}

    remaining = (due_date - date.today()).days

    if remaining < 0:
        return {'label': 'متأخر', 'class': 'badge-risk-critical'}

    if remaining <= 3:
        return {'label': 'قريب الاستحقاق', 'class': 'badge-risk-med'}

    return {'label': 'ضمن المدة', 'class': 'badge-status'}


def _get_recent_report_logs(pr, limit=8):
    observation_ids = [o.id for o in pr.observations]

    query = AuditLog.query.filter(
        db.or_(
            db.and_(
                AuditLog.entity_type == 'mission_prison_report',
                AuditLog.entity_id == pr.id
            ),
            db.and_(
                AuditLog.entity_type == 'observation',
                AuditLog.entity_id.in_(observation_ids if observation_ids else [-1])
            )
        )
    ).order_by(AuditLog.created_at.desc())

    return query.limit(limit).all()


def _normalize_selected_entities(values):
    normalized = []

    for value in values:
        if not value:
            continue

        cleaned = str(value).strip()

        if not cleaned or cleaned == 'أخرى':
            continue

        if cleaned not in normalized:
            normalized.append(cleaned)

    return normalized


def _can_update_observation_from_report(pr, obs, user):
    if user.role in ['central_admin', 'central_operator', 'central_director']:
        return True

    if user.role == 'region_manager':
        return pr.mission_region.region_id == user.region_id

    if user.role == 'prison_director':
        return pr.mission_region.region_id == user.region_id

    if user.role in ['department_user', 'department_manager']:
        return obs.department_id == user.department_id

    if user.role == 'executor':
        return user in pr.assignees

    return False


@missions_bp.route('/')
@login_required
def index():
    denied = _deny_department_access_to_missions()
    if denied:
        return denied

    q = Mission.query.options(
        joinedload(Mission.regions).joinedload(MissionRegion.region),
        joinedload(Mission.template)
    ).order_by(Mission.created_at.desc())

    if current_user.role == 'director_general':
        q = q.filter(Mission.status.in_(['ready_for_dg', 'closed']))

    if current_user.role == 'executor':
        q = q.filter(
            Mission.regions.any(
                MissionRegion.prison_reports.any(
                    MissionPrisonReport.assignees.any(User.id == current_user.id)
                )
            )
        )

    search = (request.args.get('search') or '').strip()
    template_id = (request.args.get('template_id') or '').strip()
    mission_classification = (request.args.get('mission_classification') or '').strip()
    priority_level = (request.args.get('priority_level') or '').strip()
    status = (request.args.get('status') or '').strip()

    if search:
        q = q.filter(
            or_(
                Mission.title.ilike(f'%{search}%'),
                Mission.reference_no.ilike(f'%{search}%')
            )
        )

    if template_id:
        q = q.filter(Mission.template_id == int(template_id))

    if mission_classification:
        q = q.filter(Mission.mission_classification == mission_classification)

    if priority_level:
        q = q.filter(Mission.priority_level == priority_level)

    if status:
        q = q.filter(Mission.status == status)

    missions = q.all()
    templates = Template.query.filter_by(is_active=True).order_by(Template.name.asc()).all()

    stats = {
        'total': len(missions),
        'new': sum(1 for m in missions if m.status == 'created'),
        'in_progress': sum(1 for m in missions if m.status in ['in_progress', 'under_central_review', 'awaiting_remediation']),
        'critical': sum(1 for m in missions if m.priority_level == 'critical'),
        'ready_for_dg': sum(1 for m in missions if m.status == 'ready_for_dg'),
    }

    return render_template(
        'missions/index.html',
        missions=missions,
        templates=templates,
        stats=stats,
        mission_classification_labels=MISSION_CLASSIFICATION_LABELS,
        priority_level_labels=PRIORITY_LEVEL_LABELS,
        status_labels=MISSION_STATUS_LABELS,
        assignment_mode_labels=ASSIGNMENT_MODE_LABELS,
        filters={
            'search': search,
            'template_id': template_id,
            'mission_classification': mission_classification,
            'priority_level': priority_level,
            'status': status,
        }
    )


@missions_bp.route('/create', methods=['GET', 'POST'])
@login_required
@roles_required('central_admin', 'central_operator', 'central_director')
def create():
    templates = Template.query.filter_by(is_active=True).order_by(Template.name).all()
    regions = Region.query.options(joinedload(Region.prisons)).order_by(Region.name).all()
    candidate_users = User.query.filter(
        User.role == 'executor',
        User.is_active_user == True
    ).order_by(User.full_name).all()

    form_data = {
        'title': '',
        'template_id': '',
        'mission_classification': '',
        'priority_level': '',
        'planned_date': '',
        'due_date': '',
        'global_prison_scope': '',
        'assignment_mode': '',
        'task_instructions': '',
        'region_ids': [],
        'prison_scope': {},
        'selected_prisons': {},
        'selected_assignees': {}
    }

    if request.method == 'POST':
        form_data = {
            'title': request.form.get('title', ''),
            'template_id': request.form.get('template_id', ''),
            'mission_classification': request.form.get('mission_classification', ''),
            'priority_level': request.form.get('priority_level', ''),
            'planned_date': request.form.get('planned_date', ''),
            'due_date': request.form.get('due_date', ''),
            'global_prison_scope': request.form.get('global_prison_scope', ''),
            'assignment_mode': request.form.get('assignment_mode', ''),
            'task_instructions': request.form.get('task_instructions', ''),
            'region_ids': request.form.getlist('region_ids'),
            'prison_scope': {},
            'selected_prisons': {},
            'selected_assignees': {}
        }

        for region in regions:
            rid = str(region.id)
            form_data['prison_scope'][rid] = request.form.get(f'prison_scope_{rid}', 'defer')
            form_data['selected_prisons'][rid] = request.form.getlist(f'prisons_{rid}')
            form_data['selected_assignees'][rid] = request.form.getlist(f'central_assignees_{rid}')

        title = _normalize_text(form_data['title'])
        template_id = form_data['template_id']
        mission_classification = form_data['mission_classification']
        priority_level = form_data['priority_level']
        assignment_mode = form_data['assignment_mode']
        planned_date = form_data['planned_date']
        due_date = form_data['due_date']
        task_instructions = (form_data['task_instructions'] or '').strip()
        region_ids = form_data['region_ids']

        if not title:
            flash('عنوان المهمة حقل إلزامي.', 'danger')
            return render_template('missions/create.html', templates=templates, regions=regions, candidate_users=candidate_users, form_data=form_data)

        if not template_id:
            flash('اختيار النموذج حقل إلزامي.', 'danger')
            return render_template('missions/create.html', templates=templates, regions=regions, candidate_users=candidate_users, form_data=form_data)

        if not mission_classification:
            flash('تصنيف المهمة حقل إلزامي.', 'danger')
            return render_template('missions/create.html', templates=templates, regions=regions, candidate_users=candidate_users, form_data=form_data)

        if not priority_level:
            flash('أولوية التنفيذ حقل إلزامي.', 'danger')
            return render_template('missions/create.html', templates=templates, regions=regions, candidate_users=candidate_users, form_data=form_data)

        if not planned_date:
            flash('تاريخ التنفيذ المستهدف حقل إلزامي.', 'danger')
            return render_template('missions/create.html', templates=templates, regions=regions, candidate_users=candidate_users, form_data=form_data)

        if not due_date:
            flash('تاريخ الاستحقاق حقل إلزامي.', 'danger')
            return render_template('missions/create.html', templates=templates, regions=regions, candidate_users=candidate_users, form_data=form_data)

        if not form_data['global_prison_scope']:
            flash('نطاق السجون حقل إلزامي.', 'danger')
            return render_template('missions/create.html', templates=templates, regions=regions, candidate_users=candidate_users, form_data=form_data)

        if not assignment_mode:
            flash('آلية الإسناد حقل إلزامي.', 'danger')
            return render_template('missions/create.html', templates=templates, regions=regions, candidate_users=candidate_users, form_data=form_data)

        if not region_ids:
            flash('يجب اختيار منطقة واحدة على الأقل.', 'danger')
            return render_template('missions/create.html', templates=templates, regions=regions, candidate_users=candidate_users, form_data=form_data)

        try:
            planned_date_obj = date.fromisoformat(planned_date)
            due_date_obj = date.fromisoformat(due_date)
        except ValueError:
            flash('صيغة التاريخ غير صحيحة.', 'danger')
            return render_template('missions/create.html', templates=templates, regions=regions, candidate_users=candidate_users, form_data=form_data)

        if due_date_obj < planned_date_obj:
            flash('تاريخ الاستحقاق يجب أن يكون مساويًا أو بعد تاريخ التنفيذ المستهدف.', 'danger')
            return render_template('missions/create.html', templates=templates, regions=regions, candidate_users=candidate_users, form_data=form_data)

        mission = Mission(
            reference_no=_next_reference(),
            title=title,
            template_id=int(template_id),
            mission_classification=mission_classification,
            priority_level=priority_level,
            assignment_mode=assignment_mode,
            planned_date=planned_date_obj,
            due_date=due_date_obj,
            task_instructions=task_instructions or None,
            status='created',
            created_by=current_user.id
        )
        db.session.add(mission)
        db.session.flush()

        for rid in region_ids:
            region = db.session.get(Region, int(rid))
            if not region:
                db.session.rollback()
                flash('تعذر العثور على إحدى المناطق المحددة.', 'danger')
                return render_template('missions/create.html', templates=templates, regions=regions, candidate_users=candidate_users, form_data=form_data)

            prison_scope = request.form.get(f'prison_scope_{rid}') or request.form.get('global_prison_scope') or 'defer'
            selected_prison_ids = request.form.getlist(f'prisons_{rid}')
            selected_assignee_ids = request.form.getlist(f'central_assignees_{rid}')

            if assignment_mode == 'central_defined' and prison_scope != 'fixed':
                db.session.rollback()
                flash(f'عند اختيار الإسناد المسبق من إدارة المراجعة الداخلية يجب تحديد السجون مسبقًا في منطقة {region.name}.', 'danger')
                return render_template('missions/create.html', templates=templates, regions=regions, candidate_users=candidate_users, form_data=form_data)

            if assignment_mode in ['central_defined', 'central_with_region_completion'] and prison_scope == 'fixed' and not selected_assignee_ids:
                db.session.rollback()
                flash(f'تم اختيار إسناد مسبق في منطقة {region.name} بدون تحديد منفذين.', 'danger')
                return render_template('missions/create.html', templates=templates, regions=regions, candidate_users=candidate_users, form_data=form_data)

            mission_region = MissionRegion(
                mission=mission,
                region=region,
                status='pending_region_setup',
                allow_region_to_select_prisons=(prison_scope != 'fixed'),
                region_notes=''
            )
            db.session.add(mission_region)
            db.session.flush()

            if prison_scope == 'fixed':
                if not selected_prison_ids:
                    db.session.rollback()
                    flash(f'تم اختيار تحديد السجون الآن في منطقة {region.name} بدون اختيار أي سجن.', 'danger')
                    return render_template('missions/create.html', templates=templates, regions=regions, candidate_users=candidate_users, form_data=form_data)

                selected_users = []
                if selected_assignee_ids:
                    for uid in selected_assignee_ids:
                        user = db.session.get(User, int(uid))
                        if user:
                            selected_users.append(user)

                for pid in selected_prison_ids:
                    prison = db.session.get(Prison, int(pid))
                    if not prison:
                        continue

                    prison_report = MissionPrisonReport(
                        mission_region=mission_region,
                        prison=prison,
                        status='assigned' if selected_users else 'pending_assignment'
                    )

                    if selected_users:
                        prison_report.assignees = selected_users

                    db.session.add(prison_report)

                if selected_users:
                    mission_region.status = 'assigned'

            log_action(current_user.id, 'create_mission_region', 'mission_region', mission_region.id, f'إنشاء نطاق منطقة: {region.name}')

        db.session.flush()

        save_uploaded_files(
            request.files.getlist('attachments'),
            'mission',
            mission.id,
            current_user.id,
            Attachment
        )

        log_action(current_user.id, 'create_mission', 'mission', mission.id, 'إنشاء مهمة جديدة')
        db.session.commit()

        flash('تم إنشاء المهمة بنجاح.', 'success')
        return redirect(url_for('missions.detail', mission_id=mission.id))

    return render_template(
        'missions/create.html',
        templates=templates,
        regions=regions,
        candidate_users=candidate_users,
        form_data=form_data
    )


@missions_bp.route('/<int:mission_id>')
@login_required
def detail(mission_id):
    denied = _deny_department_access_to_missions()
    if denied:
        return denied

    mission = Mission.query.options(
        joinedload(Mission.template).joinedload(Template.sections).joinedload(TemplateSection.criteria),
        joinedload(Mission.regions).joinedload(MissionRegion.region).joinedload(Region.prisons),
        joinedload(Mission.regions).joinedload(MissionRegion.prison_reports).joinedload(MissionPrisonReport.prison),
        joinedload(Mission.regions).joinedload(MissionRegion.prison_reports).joinedload(MissionPrisonReport.assignees),
        joinedload(Mission.regions).joinedload(MissionRegion.prison_reports).joinedload(MissionPrisonReport.observations)
    ).get_or_404(mission_id)

    if current_user.role == 'executor' and not _executor_has_mission_access(mission, current_user):
        flash('لا تملكين صلاحية الوصول إلى هذه المهمة.', 'danger')
        return redirect(url_for('dashboard.home'))

    visible_regions = []

    for mr in mission.regions:
        if current_user.role == 'executor':
            visible_reports = [pr for pr in mr.prison_reports if current_user in pr.assignees]
            if not visible_reports:
                continue
        else:
            visible_reports = list(mr.prison_reports)

        mr.visible_prison_reports = visible_reports
        visible_regions.append(mr)

    region_ids = [mr.id for mr in visible_regions] or [0]
    prison_report_ids = [pr.id for mr in visible_regions for pr in mr.visible_prison_reports] or [0]
    observation_ids = [o.id for mr in visible_regions for pr in mr.visible_prison_reports for o in pr.observations] or [0]

    entity_logs = AuditLog.query.filter(
        ((AuditLog.entity_type == 'mission') & (AuditLog.entity_id == mission.id)) |
        ((AuditLog.entity_type == 'mission_region') & (AuditLog.entity_id.in_(region_ids))) |
        ((AuditLog.entity_type == 'mission_prison_report') & (AuditLog.entity_id.in_(prison_report_ids))) |
        ((AuditLog.entity_type == 'observation') & (AuditLog.entity_id.in_(observation_ids)))
    ).order_by(AuditLog.created_at.desc()).limit(80).all()

    summary_kpis = {
        'regions_count': len(visible_regions),
        'prisons_count': sum(len(mr.visible_prison_reports) for mr in visible_regions),
        'started_count': sum(sum(1 for pr in mr.visible_prison_reports if pr.has_started) for mr in visible_regions),
        'submitted_count': sum(sum(1 for pr in mr.visible_prison_reports if pr.status == 'submitted') for mr in visible_regions),
        'open_observations_count': sum(
            sum(pr.open_observations_count() for pr in mr.visible_prison_reports) for mr in visible_regions
        ),
        'compliance_percentage': 0
    }

    if summary_kpis['prisons_count'] > 0:
        summary_kpis['compliance_percentage'] = round(
            (summary_kpis['submitted_count'] / summary_kpis['prisons_count']) * 100,
            1
        )

    region_summaries = []
    region_setup_data = {}

    if current_user.role in ['region_manager', 'central_admin', 'central_operator', 'central_director']:
        for mr in visible_regions:
            region_summaries.append({
                'id': mr.id,
                'name': mr.region.name
            })

            selected_prison_ids = [str(pr.prison_id) for pr in mr.prison_reports]
            selected_assignee_ids = sorted({
                str(user.id)
                for pr in mr.prison_reports
                for user in pr.assignees
            })

            users = User.query.filter(
                User.role == 'executor',
                User.is_active_user == True,
                db.or_(User.region_id == mr.region_id, User.org_unit_type == 'central')
            ).order_by(User.full_name).all()

            region_setup_data[str(mr.id)] = {
                'prisons': [{'id': p.id, 'name': p.name} for p in mr.region.prisons],
                'selected_prison_ids': selected_prison_ids,
                'selected_assignee_ids': selected_assignee_ids,
                'region_notes': mr.region_notes or '',
                'users': [
                    {
                        'id': u.id,
                        'name': u.full_name,
                        'meta': u.job_title or ROLE_LABELS.get(u.role, u.role)
                    }
                    for u in users
                ]
            }

    return render_template(
        'missions/detail.html',
        mission=mission,
        visible_regions=visible_regions,
        entity_logs=entity_logs,
        summary_kpis=summary_kpis,
        region_summaries=region_summaries,
        region_setup_data=region_setup_data
    )


@missions_bp.route('/region/<int:mission_region_id>/setup-inline', methods=['POST'])
@login_required
@roles_required('region_manager', 'central_admin', 'central_operator', 'central_director')
def region_setup_inline(mission_region_id):
    mr = MissionRegion.query.options(
        joinedload(MissionRegion.region).joinedload(Region.prisons),
        joinedload(MissionRegion.prison_reports).joinedload(MissionPrisonReport.assignees)
    ).get_or_404(mission_region_id)

    if current_user.role == 'region_manager' and current_user.region_id != mr.region_id:
        flash('لا يمكن الوصول إلى هذه المنطقة.', 'danger')
        return redirect(url_for('missions.detail', mission_id=mr.mission_id))

    selected_prison_ids = request.form.getlist('prison_ids')
    selected_assignee_ids = request.form.getlist('assignee_ids')

    if not selected_prison_ids:
        flash('يجب اختيار سجن واحد على الأقل.', 'danger')
        return redirect(url_for('missions.detail', mission_id=mr.mission_id))

    selected_users = []
    for uid in selected_assignee_ids:
        user = db.session.get(User, int(uid))
        if user:
            selected_users.append(user)

    existing_reports_by_prison = {r.prison_id: r for r in mr.prison_reports}

    for report in list(mr.prison_reports):
        if str(report.prison_id) not in selected_prison_ids:
            db.session.delete(report)

    for pid in selected_prison_ids:
        prison_id = int(pid)
        prison = db.session.get(Prison, prison_id)
        if not prison:
            continue

        if prison_id in existing_reports_by_prison:
            report = existing_reports_by_prison[prison_id]
        else:
            report = MissionPrisonReport(
                mission_region=mr,
                prison=prison
            )
            db.session.add(report)

        report.assignees = selected_users
        report.status = 'assigned' if selected_users else 'pending_assignment'

    mr.region_notes = request.form.get('region_notes') or None
    mr.status = 'assigned' if selected_users else 'pending_region_setup'

    db.session.flush()
    log_action(current_user.id, 'setup_region_task', 'mission_region', mr.id, 'تحديث تجهيز المنطقة من صفحة تفاصيل المهمة')
    db.session.commit()

    flash('تم حفظ تجهيز المنطقة.', 'success')
    return redirect(url_for('missions.detail', mission_id=mr.mission_id))


@missions_bp.route('/observations')
@login_required
def observations():
    q = Observation.query.options(
        joinedload(Observation.department),
        joinedload(Observation.mission_prison_report).joinedload(MissionPrisonReport.prison),
        joinedload(Observation.mission_prison_report)
            .joinedload(MissionPrisonReport.mission_region)
            .joinedload(MissionRegion.region),
        joinedload(Observation.mission_prison_report)
            .joinedload(MissionPrisonReport.mission_region)
            .joinedload(MissionRegion.mission)
    ).order_by(Observation.created_at.desc())

    status = (request.args.get('status') or '').strip()
    severity = (request.args.get('severity') or '').strip()
    q_text = (request.args.get('search') or '').strip()

    if current_user.role == 'executor':
        q = q.join(
            MissionPrisonReport,
            Observation.mission_prison_report_id == MissionPrisonReport.id
        ).filter(
            MissionPrisonReport.assignees.any(User.id == current_user.id)
        )

    elif current_user.role in ['region_manager', 'prison_director']:
        q = q.join(
            MissionPrisonReport,
            Observation.mission_prison_report_id == MissionPrisonReport.id
        ).join(
            MissionRegion,
            MissionPrisonReport.mission_region_id == MissionRegion.id
        ).filter(
            MissionRegion.region_id == current_user.region_id
        )

    elif current_user.role in ['department_user', 'department_manager']:
        q = q.filter(Observation.department_id == current_user.department_id)

    if status:
        q = q.filter(Observation.status == status)

    if severity:
        q = q.filter(Observation.severity == severity)

    if q_text:
        q = q.filter(
            or_(
                Observation.title.ilike(f'%{q_text}%'),
                Observation.description.ilike(f'%{q_text}%'),
                Observation.category.ilike(f'%{q_text}%'),
                Observation.remediation_recommendation.ilike(f'%{q_text}%')
            )
        )

    observations_list = q.all()
    today = date.today()

    closed_statuses = ['closed', 'resolved', 'remediated', 'closed_by_decision']

    stats = {
        'total': len(observations_list),
        'open': sum(
            1 for o in observations_list
            if o.status not in closed_statuses
        ),
        'overdue': sum(
            1 for o in observations_list
            if o.due_date
            and o.due_date < today
            and o.status not in closed_statuses
        ),
        'resolved': sum(
            1 for o in observations_list
            if o.status in closed_statuses
        ),
        'critical': sum(
            1 for o in observations_list
            if o.severity in ['حرجة', 'عالية', 'مرتفعة']
        ),
    }

    return render_template(
        'missions/observations.html',
        observations=observations_list,
        today=date.today(),
        stats=stats,
        filters={
            'status': status,
            'severity': severity,
            'search': q_text,
        },
        OBS_STATUS=OBS_STATUS
    )


@missions_bp.route('/<int:mission_id>/history')
@login_required
def history(mission_id):
    denied = _deny_department_access_to_missions()
    if denied:
        return denied

    mission = Mission.query.options(
        joinedload(Mission.regions).joinedload(MissionRegion.prison_reports).joinedload(MissionPrisonReport.assignees),
        joinedload(Mission.regions).joinedload(MissionRegion.prison_reports).joinedload(MissionPrisonReport.observations)
    ).get_or_404(mission_id)

    if current_user.role == 'executor' and not _executor_has_mission_access(mission, current_user):
        flash('لا تملكين صلاحية الوصول إلى سجل هذه المهمة.', 'danger')
        return redirect(url_for('dashboard.home'))

    if current_user.role == 'executor':
        prison_report_ids = [
            pr.id
            for mr in mission.regions
            for pr in mr.prison_reports
            if current_user in pr.assignees
        ] or [0]
        observation_ids = [
            o.id
            for mr in mission.regions
            for pr in mr.prison_reports
            if current_user in pr.assignees
            for o in pr.observations
        ] or [0]

        logs = AuditLog.query.filter(
            ((AuditLog.entity_type == 'mission_prison_report') & (AuditLog.entity_id.in_(prison_report_ids))) |
            ((AuditLog.entity_type == 'observation') & (AuditLog.entity_id.in_(observation_ids)))
        ).order_by(AuditLog.created_at.desc()).all()
    else:
        region_ids = [mr.id for mr in mission.regions] or [0]
        prison_report_ids = [pr.id for mr in mission.regions for pr in mr.prison_reports] or [0]
        observation_ids = [o.id for mr in mission.regions for pr in mr.prison_reports for o in pr.observations] or [0]

        logs = AuditLog.query.filter(
            ((AuditLog.entity_type == 'mission') & (AuditLog.entity_id == mission.id)) |
            ((AuditLog.entity_type == 'mission_region') & (AuditLog.entity_id.in_(region_ids))) |
            ((AuditLog.entity_type == 'mission_prison_report') & (AuditLog.entity_id.in_(prison_report_ids))) |
            ((AuditLog.entity_type == 'observation') & (AuditLog.entity_id.in_(observation_ids)))
        ).order_by(AuditLog.created_at.desc()).all()

    return render_template('missions/history.html', mission=mission, logs=logs)


@missions_bp.route('/region/<int:mission_region_id>/setup', methods=['GET', 'POST'])
@login_required
@roles_required('region_manager', 'central_admin', 'central_operator', 'central_director')
def region_setup(mission_region_id):
    mr = MissionRegion.query.options(
        joinedload(MissionRegion.region).joinedload(Region.prisons),
        joinedload(MissionRegion.prison_reports).joinedload(MissionPrisonReport.prison),
        joinedload(MissionRegion.prison_reports).joinedload(MissionPrisonReport.assignees),
        joinedload(MissionRegion.mission)
    ).get_or_404(mission_region_id)

    if current_user.role == 'region_manager' and current_user.region_id != mr.region_id:
        flash('لا يمكن الوصول إلى هذه المنطقة.', 'danger')
        return redirect(url_for('missions.index'))

    users = User.query.filter(
        User.role == 'executor',
        User.is_active_user == True,
        db.or_(User.region_id == mr.region_id, User.org_unit_type == 'central')
    ).order_by(User.full_name).all()

    if request.method == 'POST':
        selected_prison_ids = request.form.getlist('prison_ids')
        if not selected_prison_ids:
            flash('يجب اختيار سجن واحد على الأقل.', 'danger')
            return render_template('missions/region_setup.html', mr=mr, users=users)

        selected_assignee_ids = request.form.getlist('assignee_ids')
        selected_users = [db.session.get(User, int(uid)) for uid in selected_assignee_ids] if selected_assignee_ids else []

        existing_reports_by_prison = {r.prison_id: r for r in mr.prison_reports}

        for report in list(mr.prison_reports):
            if str(report.prison_id) not in selected_prison_ids:
                db.session.delete(report)

        for pid in selected_prison_ids:
            prison_id = int(pid)
            prison = db.session.get(Prison, prison_id)

            if prison_id in existing_reports_by_prison:
                report = existing_reports_by_prison[prison_id]
            else:
                report = MissionPrisonReport(
                    mission_region=mr,
                    prison=prison
                )
                db.session.add(report)

            report.assignees = selected_users
            report.status = 'assigned' if selected_users else 'pending_assignment'

        mr.region_notes = request.form.get('region_notes')
        mr.status = 'assigned' if selected_users else 'pending_region_setup'

        db.session.flush()
        log_action(current_user.id, 'setup_region_task', 'mission_region', mr.id, 'تحديد السجون والمنفذين على مستوى المنطقة')
        db.session.commit()

        flash('تم تحديث تجهيز المنطقة.', 'success')
        return redirect(url_for('missions.detail', mission_id=mr.mission_id))

    return render_template('missions/region_setup.html', mr=mr, users=users)


@missions_bp.route('/prison-report/<int:prison_report_id>/execute', methods=['GET', 'POST'])
@login_required
@roles_required('executor', 'region_manager', 'central_admin', 'central_operator', 'central_director')
def prison_execute(prison_report_id):
    pr = MissionPrisonReport.query.options(
        joinedload(MissionPrisonReport.mission_region).joinedload(MissionRegion.region),
        joinedload(MissionPrisonReport.mission_region)
            .joinedload(MissionRegion.mission)
            .joinedload(Mission.template)
            .joinedload(Template.sections)
            .joinedload(TemplateSection.criteria),
        joinedload(MissionPrisonReport.prison),
        joinedload(MissionPrisonReport.assignees),
        joinedload(MissionPrisonReport.responses),
        joinedload(MissionPrisonReport.observations).joinedload(Observation.department),
        joinedload(MissionPrisonReport.attachments)
    ).get_or_404(prison_report_id)

    if current_user.role == 'executor' and current_user not in pr.assignees:
        flash('هذا التقرير غير مسند لك.', 'danger')
        return redirect(url_for('dashboard.home'))

    departments = Department.query.order_by(Department.name).all()
    template = pr.mission_region.mission.template

    category_options = [
        'عام',
        'تشغيلي',
        'إجرائي',
        'سلامة',
        'أمني',
        'توثيق',
        'امتثال',
        'جودة',
        'مرافق وتجهيزات',
        'موارد بشرية',
        'تقني',
        'أخرى',
    ]

    day_options = ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت']

    if request.method == 'POST':
        form_action = (request.form.get('form_action') or 'save_draft').strip()

        # تحديث ملاحظة من نفس الصفحة
        # هذا الجزء لازم يكون قبل قراءة حقول الزيارة
        if form_action == 'update_observation':
            observation_id = (request.form.get('observation_id') or '').strip()
            new_status = (request.form.get('new_status') or '').strip()
            action_note = (request.form.get('action_note') or '').strip()
            closure_reason = (request.form.get('closure_reason') or '').strip()
            escalation_reason = (request.form.get('escalation_reason') or '').strip()

            if not observation_id.isdigit():
                flash('تعذر تحديد الملاحظة المطلوبة.', 'danger')
                return redirect(url_for('missions.prison_execute', prison_report_id=pr.id))

            obs = Observation.query.filter_by(
                id=int(observation_id),
                mission_prison_report_id=pr.id
            ).first_or_404()

            if not _can_update_observation_from_report(pr, obs, current_user):
                flash('لا تملك صلاحية تحديث هذه الملاحظة.', 'danger')
                return redirect(url_for('missions.prison_execute', prison_report_id=pr.id))

            if not new_status:
                flash('يجب اختيار حالة جديدة للملاحظة.', 'danger')
                return redirect(url_for('missions.prison_execute', prison_report_id=pr.id))

            if new_status in ['closed', 'resolved', 'closed_by_decision', 'remediated'] and not closure_reason:
                flash('يجب تحديد سبب الإقفال أو التلافي.', 'danger')
                return redirect(url_for('missions.prison_execute', prison_report_id=pr.id))

            if new_status == 'escalated' and not escalation_reason:
                flash('يجب تحديد سبب التصعيد.', 'danger')
                return redirect(url_for('missions.prison_execute', prison_report_id=pr.id))

            old_status = obs.status
            obs.status = new_status

            if new_status in ['closed', 'resolved', 'closed_by_decision', 'remediated']:
                obs.closed_at = datetime.utcnow()
                obs.closure_reason = closure_reason

            if new_status == 'escalated':
                obs.escalated = True
                obs.escalation_reason = escalation_reason
                obs.escalation_at = datetime.utcnow()

            action_record = ObservationAction(
                observation_id=obs.id,
                user_id=current_user.id,
                action_type='status_update',
                old_status=old_status,
                new_status=new_status,
                note=action_note or None,
                closure_reason=closure_reason or None,
                escalation_reason=escalation_reason or None
            )

            db.session.add(action_record)
            db.session.flush()

            save_uploaded_files(
                request.files.getlist('action_attachments'),
                'observation_action',
                action_record.id,
                current_user.id,
                Attachment
            )

            log_action(
                current_user.id,
                'update_observation_status',
                'observation',
                obs.id,
                f'تحديث حالة الملاحظة من {OBS_STATUS.get(old_status, old_status)} إلى {OBS_STATUS.get(new_status, new_status)}'
            )

            pr.refresh_score()
            db.session.commit()

            flash('تم تحديث الملاحظة بنجاح.', 'success')
            return redirect(url_for('missions.prison_execute', prison_report_id=pr.id))

        # بيانات الزيارة
        visit_date_raw = (request.form.get('visit_date') or '').strip()

        try:
            pr.visit_date = date.fromisoformat(visit_date_raw) if visit_date_raw else None
        except ValueError:
            flash('صيغة تاريخ الزيارة غير صحيحة.', 'danger')
            return redirect(url_for('missions.prison_execute', prison_report_id=pr.id))

        pr.visit_day_name = (request.form.get('visit_day_name') or '').strip() or None
        pr.visit_start_time = (request.form.get('visit_start_time') or '').strip() or None
        pr.visit_end_time = (request.form.get('visit_end_time') or '').strip() or None

        visit_count_raw = (request.form.get('visit_count') or '').strip()
        pr.visit_count = int(visit_count_raw) if visit_count_raw.isdigit() and int(visit_count_raw) > 0 else None

        selected_entities = _normalize_selected_entities(request.form.getlist('visited_entity'))
        pr.visited_entity = '، '.join(selected_entities) if selected_entities else None
        pr.visited_entity_other = (request.form.get('visited_entity_other') or '').strip() or None

        pr.report_summary = (request.form.get('report_summary') or '').strip() or None
        pr.recommendations = (request.form.get('recommendations') or '').strip() or None

        # حفظ التقييمات
        for section in template.sections:
            for criterion in section.criteria:
                field = f'score_{criterion.id}'
                label = (request.form.get(field) or '').strip()

                existing = MissionResponse.query.filter_by(
                    mission_prison_report_id=pr.id,
                    criterion_id=criterion.id
                ).first()

                if label:
                    if label not in SCORE_LABELS:
                        flash('قيمة تقييم غير صحيحة.', 'danger')
                        return redirect(url_for('missions.prison_execute', prison_report_id=pr.id))

                    if existing:
                        existing.score_label = label
                        existing.score_value = SCORE_LABELS[label]
                    else:
                        db.session.add(
                            MissionResponse(
                                mission_prison_report=pr,
                                criterion=criterion,
                                score_label=label,
                                score_value=SCORE_LABELS[label]
                            )
                        )

        # بيانات الملاحظة الجديدة
        obs_title = (request.form.get('obs_title') or '').strip()
        obs_description = (request.form.get('obs_description') or '').strip()
        department_id = (request.form.get('department_id') or '').strip()

        # لأن category إلزامي في قاعدة البيانات
        category = (request.form.get('category') or '').strip() or 'عام'

        severity = (request.form.get('severity') or '').strip()
        priority = (request.form.get('priority') or '').strip()
        sla_option = (request.form.get('sla_option') or '').strip()
        observation_type = (request.form.get('observation_type') or 'other').strip()
        remediation_recommendation = (request.form.get('remediation_recommendation') or '').strip() or None
        criterion_id_raw = (request.form.get('criterion_id') or '').strip()

        # 1) حفظ ملاحظة فقط
        if form_action == 'add_observation':
            missing_obs = []

            if not obs_title:
                missing_obs.append('عنوان الملاحظة')

            if not obs_description:
                missing_obs.append('وصف الملاحظة')

            if not department_id:
                missing_obs.append('الإدارة المختصة')

            if not severity:
                missing_obs.append('مستوى الخطورة')

            if not priority:
                missing_obs.append('الأولوية')

            if not sla_option:
                missing_obs.append('مدة المعالجة')

            if observation_type == 'criterion' and not criterion_id_raw:
                missing_obs.append('المعيار المرتبط')

            if missing_obs:
                flash('لا يمكن حفظ الملاحظة قبل استكمال: ' + '، '.join(missing_obs), 'danger')
                return redirect(url_for('missions.prison_execute', prison_report_id=pr.id))

            if department_id and not department_id.isdigit():
                flash('الإدارة المختصة غير صحيحة.', 'danger')
                return redirect(url_for('missions.prison_execute', prison_report_id=pr.id))

            if criterion_id_raw and not criterion_id_raw.isdigit():
                flash('المعيار المرتبط غير صحيح.', 'danger')
                return redirect(url_for('missions.prison_execute', prison_report_id=pr.id))

            obs = Observation(
                mission_prison_report=pr,
                observation_type=observation_type,
                criterion_id=int(criterion_id_raw) if criterion_id_raw else None,
                title=obs_title,
                description=obs_description,
                category=category,
                department_id=int(department_id),
                severity=severity,
                priority=priority,
                sla_option=sla_option,
                due_date=compute_due_date(sla_option),
                remediation_recommendation=remediation_recommendation,
                status='new'
            )

            db.session.add(obs)
            db.session.flush()

            save_uploaded_files(
                request.files.getlist('observation_attachments'),
                'observation',
                obs.id,
                current_user.id,
                Attachment
            )

            if pr.has_started:
                pr.status = 'in_progress'

            mr = pr.mission_region

            if any(r.has_started for r in mr.prison_reports):
                mr.status = 'in_progress'

            if mr.mission.status == 'created':
                mr.mission.status = 'in_progress'

            pr.refresh_score()

            log_action(
                current_user.id,
                'add_observation',
                'observation',
                obs.id,
                f'إضافة ملاحظة جديدة على تقرير السجن: {pr.prison.name}'
            )

            db.session.commit()

            flash('تم حفظ الملاحظة بنجاح.', 'success')
            return redirect(url_for('missions.prison_execute', prison_report_id=pr.id))

        # مرفقات عامة للتقرير
        save_uploaded_files(
            request.files.getlist('report_attachments'),
            'mission_prison_report',
            pr.id,
            current_user.id,
            Attachment
        )

        pr.refresh_score()

        # 2) حفظ مسودة
        if form_action == 'save_draft':
            if pr.has_started:
                pr.status = 'in_progress'

            mr = pr.mission_region

            if any(r.has_started for r in mr.prison_reports):
                mr.status = 'in_progress'

            if mr.mission.status == 'created':
                mr.mission.status = 'in_progress'

            log_action(
                current_user.id,
                'save_execution',
                'mission_prison_report',
                pr.id,
                'حفظ مسودة تقرير السجن'
            )

            db.session.commit()

            flash('تم حفظ مسودة التقرير بنجاح.', 'success')
            return redirect(url_for('missions.prison_execute', prison_report_id=pr.id))

        # 3) تسليم التقرير
        missing_fields = []

        if not pr.visited_entity and not pr.visited_entity_other:
            missing_fields.append('الجهات محل المراجعة')

        if not pr.visit_count:
            missing_fields.append('عدد مرات الزيارة')

        if not pr.visit_day_name:
            missing_fields.append('اليوم')

        if not pr.visit_date:
            missing_fields.append('التاريخ')

        if not pr.visit_start_time:
            missing_fields.append('وقت البداية')

        if not pr.visit_end_time:
            missing_fields.append('وقت النهاية')

        total_criteria = sum(len(section.criteria) for section in template.sections)

        answered_criteria = MissionResponse.query.filter_by(
            mission_prison_report_id=pr.id
        ).count()

        if total_criteria > 0 and answered_criteria < total_criteria:
            missing_fields.append('استكمال جميع معايير التقييم')

        if missing_fields:
            flash('لا يمكن تسليم التقرير قبل استكمال الحقول التالية: ' + '، '.join(missing_fields), 'danger')
            return redirect(url_for('missions.prison_execute', prison_report_id=pr.id))

        pr.status = 'submitted'
        pr.submitted_at = datetime.utcnow()

        mr = pr.mission_region

        if all(r.status == 'submitted' for r in mr.prison_reports):
            mr.status = 'submitted_to_central'
            mr.sent_to_central_at = datetime.utcnow()
        else:
            mr.status = 'in_progress'

        mission = mr.mission

        all_regions_submitted = all(
            region.status == 'submitted_to_central'
            for region in mission.regions
            if region.prison_reports
        )

        mission.status = 'under_central_review' if all_regions_submitted else 'in_progress'

        log_action(
            current_user.id,
            'submit_prison_report',
            'mission_prison_report',
            pr.id,
            'رفع وتسليم تقرير السجن'
        )

        db.session.commit()

        flash('تم رفع وتسليم التقرير بنجاح.', 'success')
        return redirect(url_for('missions.detail', mission_id=mr.mission_id))

    recent_logs = _get_recent_report_logs(pr)

    return render_template(
        'missions/prison_execute.html',
        pr=pr,
        departments=departments,
        score_options=_score_options(),
        sla_options=SLA_OPTIONS,
        category_options=category_options,
        day_options=day_options,
        recent_logs=recent_logs,
        OBS_STATUS=OBS_STATUS
    )

  
@missions_bp.route('/prison-report/<int:prison_report_id>/view', methods=['GET', 'POST'])
@login_required
def prison_report_view(prison_report_id):
    denied = _deny_department_access_to_missions()
    if denied:
        return denied

    pr = MissionPrisonReport.query.options(
        joinedload(MissionPrisonReport.mission_region).joinedload(MissionRegion.region),
        joinedload(MissionPrisonReport.mission_region)
            .joinedload(MissionRegion.mission)
            .joinedload(Mission.template)
            .joinedload(Template.sections)
            .joinedload(TemplateSection.criteria),
        joinedload(MissionPrisonReport.prison),
        joinedload(MissionPrisonReport.assignees),
        joinedload(MissionPrisonReport.responses).joinedload(MissionResponse.criterion),
        joinedload(MissionPrisonReport.observations).joinedload(Observation.department),
        joinedload(MissionPrisonReport.attachments)
    ).get_or_404(prison_report_id)

    if current_user.role == 'executor':
        if current_user not in pr.assignees:
            flash('لا تملكين صلاحية استعراض هذا التقرير.', 'danger')
            return redirect(url_for('dashboard.home'))
        return redirect(url_for('missions.prison_execute', prison_report_id=pr.id))

    if current_user.role == 'region_manager' and current_user.region_id != pr.mission_region.region_id:
        flash('لا تملك صلاحية استعراض هذا التقرير.', 'danger')
        return redirect(url_for('dashboard.home'))

    if current_user.role == 'prison_director' and current_user.region_id != pr.mission_region.region_id:
        flash('لا تملك صلاحية استعراض هذا التقرير.', 'danger')
        return redirect(url_for('dashboard.home'))

    can_comment = current_user.role in ['central_admin', 'central_operator', 'central_director', 'region_manager', 'prison_director']
    recent_logs = _get_recent_report_logs(pr)

    comment_label = 'توجيه / ملاحظات'
    if current_user.role in ['central_admin', 'central_operator', 'central_director']:
        comment_label = 'تعليق الإدارة المركزية'
    elif current_user.role == 'region_manager':
        comment_label = 'ملاحظات مدير شعبة المنطقة'
    elif current_user.role == 'prison_director':
        comment_label = 'ملاحظات مدير سجون المنطقة'

    if request.method == 'POST':
        if not can_comment:
            flash('لا تملك صلاحية إضافة ملاحظات.', 'danger')
            return redirect(url_for('missions.prison_report_view', prison_report_id=pr.id))

        note = (request.form.get('central_comment') or '').strip()

        if not note:
            flash('حقل التوجيه أو الملاحظات مطلوب.', 'danger')
            return redirect(url_for('missions.prison_report_view', prison_report_id=pr.id))

        existing = (pr.central_comment or '').strip()
        actor = current_user.full_name
        stamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M')

        new_block = f'[{stamp}] {actor}: {note}'
        pr.central_comment = f'{existing}\n\n{new_block}' if existing else new_block
        pr.central_commented_at = datetime.utcnow()

        log_action(
            current_user.id,
            'add_report_note',
            'mission_prison_report',
            pr.id,
            f'إضافة توجيه/ملاحظات على تقرير السجن: {pr.prison.name}'
        )
        db.session.commit()

        flash('تم حفظ التوجيه/الملاحظات بنجاح.', 'success')
        return redirect(url_for('missions.prison_report_view', prison_report_id=pr.id))

    return render_template(
        'missions/prison_report_view.html',
        pr=pr,
        can_comment=can_comment,
        comment_label=comment_label,
        recent_logs=recent_logs,
        OBS_STATUS=OBS_STATUS
    )


@missions_bp.route('/prison-report/<int:prison_report_id>/submit', methods=['POST'])
@login_required
@roles_required('executor', 'region_manager', 'central_admin', 'central_operator', 'central_director')
def submit_prison_report(prison_report_id):
    denied = _deny_department_access_to_missions()
    if denied:
        return denied

    pr = MissionPrisonReport.query.options(
        joinedload(MissionPrisonReport.mission_region).joinedload(MissionRegion.mission),
        joinedload(MissionPrisonReport.responses)
    ).get_or_404(prison_report_id)

    if current_user.role == 'executor' and current_user not in pr.assignees:
        flash('لا يمكن تنفيذ هذا الإجراء.', 'danger')
        return redirect(url_for('dashboard.home'))

    if not pr.visit_day_name or not pr.visit_date or not pr.visit_start_time or not pr.visit_end_time or not pr.visited_entity:
        flash('يجب استكمال بيانات الزيارة الإلزامية قبل رفع التقرير.', 'danger')
        return redirect(url_for('missions.prison_execute', prison_report_id=pr.id))

    if not pr.responses:
        flash('يجب استكمال تقييم المعايير قبل رفع التقرير.', 'danger')
        return redirect(url_for('missions.prison_execute', prison_report_id=pr.id))

    pr.status = 'submitted'
    pr.submitted_at = datetime.utcnow()

    mr = pr.mission_region
    if all(r.status == 'submitted' for r in mr.prison_reports):
        mr.status = 'submitted_to_central'
        mr.sent_to_central_at = datetime.utcnow()
        if mr.mission.status == 'created':
            mr.mission.status = 'under_central_review'
        elif mr.mission.status == 'in_progress':
            mr.mission.status = 'under_central_review'

    log_action(current_user.id, 'submit_prison_report', 'mission_prison_report', pr.id, 'رفع تقرير السجن')
    db.session.commit()

    flash('تم رفع تقرير السجن.', 'success')
    return redirect(url_for('missions.detail', mission_id=mr.mission_id))


@missions_bp.route('/observation/<int:observation_id>', methods=['GET', 'POST'])
@login_required
def observation_detail(observation_id):
    observation = Observation.query.options(
        joinedload(Observation.mission_prison_report).joinedload(MissionPrisonReport.prison),
        joinedload(Observation.mission_prison_report).joinedload(MissionPrisonReport.assignees),
        joinedload(Observation.mission_prison_report).joinedload(MissionPrisonReport.mission_region).joinedload(MissionRegion.mission),
        joinedload(Observation.department),
        joinedload(Observation.criterion)
    ).get_or_404(observation_id)

    if current_user.role == 'executor' and current_user not in observation.mission_prison_report.assignees:
        flash('لا تملكين صلاحية الوصول إلى هذه الملاحظة.', 'danger')
        return redirect(url_for('dashboard.home'))

    if current_user.role == 'region_manager' and current_user.region_id != observation.mission_prison_report.mission_region.region_id:
        flash('لا تملك صلاحية الوصول إلى هذه الملاحظة.', 'danger')
        return redirect(url_for('dashboard.home'))

    if current_user.role == 'prison_director' and current_user.region_id != observation.mission_prison_report.mission_region.region_id:
        flash('لا تملك صلاحية الوصول إلى هذه الملاحظة.', 'danger')
        return redirect(url_for('dashboard.home'))

    if current_user.role in ['department_user', 'department_manager'] and current_user.department_id != observation.department_id:
        flash('لا تملك صلاحية الوصول إلى هذه الملاحظة.', 'danger')
        return redirect(url_for('dashboard.home'))

    if request.method == 'POST':
        action = request.form.get('action')

        if current_user.role in ['department_user', 'department_manager'] and current_user.department_id == observation.department_id:
            observation.department_response = request.form.get('department_response')
            observation.status = request.form.get('status') or 'under_treatment'

        elif current_user.role == 'prison_director' and current_user.region_id == observation.mission_prison_report.mission_region.region_id:
            observation.prison_director_action = request.form.get('prison_director_action')
            observation.status = request.form.get('status') or 'awaiting_central'

        elif current_user.role in ['central_admin', 'central_operator', 'central_director']:
            observation.status = request.form.get('status') or observation.status
            observation.closure_reason = request.form.get('closure_reason')
            observation.escalated = bool(request.form.get('escalated'))
            observation.escalation_reason = request.form.get('escalation_reason')
            observation.escalation_at = datetime.utcnow() if observation.escalated else None

        if request.form.get('closure_reason'):
            observation.closure_reason = request.form.get('closure_reason')

        save_uploaded_files(
            request.files.getlist('attachments'),
            'observation',
            observation.id,
            current_user.id,
            Attachment
        )

        log_action(current_user.id, 'update_observation', 'observation', observation.id, action or 'تحديث الملاحظة')
        db.session.commit()

        flash('تم تحديث الملاحظة.', 'success')
        return redirect(url_for('missions.observation_detail', observation_id=observation.id))

    return render_template('missions/observation_detail.html', observation=observation, obs_status=OBS_STATUS)


@missions_bp.route('/region/<int:mission_region_id>/prison-director', methods=['GET', 'POST'])
@login_required
@roles_required('prison_director', 'central_admin', 'central_operator', 'central_director')
def prison_director_review(mission_region_id):
    mr = MissionRegion.query.options(
        joinedload(MissionRegion.prison_reports).joinedload(MissionPrisonReport.prison),
        joinedload(MissionRegion.prison_reports).joinedload(MissionPrisonReport.observations).joinedload(Observation.department),
        joinedload(MissionRegion.region),
        joinedload(MissionRegion.mission)
    ).get_or_404(mission_region_id)

    if current_user.role == 'prison_director' and current_user.region_id != mr.region_id:
        flash('لا يمكن الوصول لهذا التقرير.', 'danger')
        return redirect(url_for('dashboard.home'))

    if request.method == 'POST':
        mr.prison_director_comments = request.form.get('prison_director_comments')

        for pr in mr.prison_reports:
            for obs in pr.observations:
                status = request.form.get(f'status_{obs.id}')
                if status:
                    obs.status = status

        log_action(current_user.id, 'prison_director_review', 'mission_region', mr.id, 'اعتماد ومتابعة ملاحظات المنطقة')
        db.session.commit()

        flash('تم تحديث مراجعة مدير سجون المنطقة.', 'success')
        return redirect(url_for('missions.prison_director_review', mission_region_id=mr.id))

    return render_template('missions/prison_director_review.html', mr=mr, obs_status=OBS_STATUS)


@missions_bp.route('/<int:mission_id>/central-review', methods=['GET', 'POST'])
@login_required
@roles_required('central_admin', 'central_operator', 'central_director')
def central_review(mission_id):
    mission = Mission.query.options(
        joinedload(Mission.regions).joinedload(MissionRegion.region),
        joinedload(Mission.regions).joinedload(MissionRegion.prison_reports).joinedload(MissionPrisonReport.prison),
        joinedload(Mission.regions).joinedload(MissionRegion.prison_reports).joinedload(MissionPrisonReport.observations)
    ).get_or_404(mission_id)

    if request.method == 'POST':
        action = request.form.get('central_action')

        if action == 'generate_draft':
            draft = _build_auto_central_review_content(mission)
            mission.final_summary = draft['final_summary']
            mission.internal_audit_opinion = draft['internal_audit_opinion']
            mission.final_recommendations = draft['final_recommendations']

            log_action(
                current_user.id,
                'generate_central_review_draft',
                'mission',
                mission.id,
                'توليد مسودة التقرير النهائي تلقائيًا'
            )
            db.session.commit()

            flash('تم توليد مسودة التقرير تلقائيًا.', 'success')
            return redirect(url_for('missions.central_review', mission_id=mission.id))

        mission.final_summary = (request.form.get('final_summary') or '').strip() or None
        mission.internal_audit_opinion = (request.form.get('internal_audit_opinion') or '').strip() or None
        mission.final_recommendations = (request.form.get('final_recommendations') or '').strip() or None

        if action == 'send_dg':
            mission.status = 'ready_for_dg'
            mission.sent_to_dg_at = datetime.utcnow()
        elif action == 'await_remediation':
            mission.status = 'awaiting_remediation'
        else:
            mission.status = 'under_central_review'

        log_action(current_user.id, 'central_review_mission', 'mission', mission.id, f'إجراء: {action}')
        db.session.commit()

        flash('تم تحديث التقرير النهائي بنجاح.', 'success')
        return redirect(url_for('missions.central_review', mission_id=mission.id))

    region_rows = []
    regional_actions_rows = []

    for mr in mission.regions:
        region_rows.append({
            'name': mr.region.name,
            'status_label': MISSION_REGION_STATUS_LABELS.get(mr.status, mr.status),
            'prisons_count': len(mr.prison_reports),
            'score_percentage': mr.score_percentage,
            'risk_level': mr.risk_level,
            'open_observations_count': mr.open_observations_count(),
        })

        if mr.prison_director_comments and mr.prison_director_comments.strip():
            regional_actions_rows.append({
                'name': mr.region.name,
                'action_text': mr.prison_director_comments.strip()
            })

    return render_template(
        'missions/central_review.html',
        mission=mission,
        region_rows=region_rows,
        regional_actions_rows=regional_actions_rows
    )


@missions_bp.route('/<int:mission_id>/dg-review', methods=['GET', 'POST'])
@login_required
@roles_required('director_general')
def dg_review(mission_id):
    mission = Mission.query.options(
        joinedload(Mission.regions).joinedload(MissionRegion.region)
    ).get_or_404(mission_id)

    if mission.status not in ['ready_for_dg', 'closed']:
        flash('هذا التقرير لم يرسل للمدير العام بعد.', 'warning')
        return redirect(url_for('dashboard.home'))

    if request.method == 'POST':
        mission.dg_decision = request.form.get('dg_decision')
        if request.form.get('action') == 'close':
            mission.status = 'closed'

        log_action(current_user.id, 'dg_review', 'mission', mission.id, 'قرار المدير العام')
        db.session.commit()

        flash('تم حفظ قرار المدير العام.', 'success')
        return redirect(url_for('missions.dg_review', mission_id=mission.id))

    return render_template('missions/dg_review.html', mission=mission)


@missions_bp.route('/attachments/<filename>')
@login_required
def attachment(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename, as_attachment=True)