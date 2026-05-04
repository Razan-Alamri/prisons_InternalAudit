from __future__ import annotations

from collections import Counter, defaultdict
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models import (
    Mission,
    MissionRegion,
    MissionPrisonReport,
    Observation,
    Region,
    Prison,
    Department,
    User,
)


def _region_score(mr: MissionRegion) -> float:
    reports = [pr.score_percentage for pr in mr.prison_reports if pr.score_percentage is not None]
    if not reports:
        return 0.0
    return round(sum(reports) / len(reports), 2)


def _status_counts(observations):
    c = Counter([o.status for o in observations])
    labels_map = {
        'new': 'جديدة',
        'sent_to_department': 'محالة',
        'under_treatment': 'قيد المعالجة',
        'awaiting_prison_director': 'بانتظار مدير المنطقة',
        'awaiting_central': 'بانتظار المركزية',
        'resolved': 'تم التلافي',
        'closed': 'مغلقة'
    }
    return {
        'labels': [labels_map.get(k, k) for k in c.keys()] or ['لا توجد بيانات'],
        'values': list(c.values()) or [0]
    }


def _risk_by_region_q(region_id=None):
    q = MissionRegion.query.options(
        joinedload(MissionRegion.prison_reports),
        joinedload(MissionRegion.region)
    )
    if region_id:
        q = q.filter(MissionRegion.region_id == region_id)

    rows = q.all()
    grouped = defaultdict(list)

    for mr in rows:
        grouped[mr.region.name].append(_region_score(mr))

    labels = []
    values = []
    for region_name in sorted(grouped.keys()):
        vals = grouped[region_name]
        labels.append(region_name)
        values.append(round(sum(vals) / len(vals), 2) if vals else 0)

    return {
        'labels': labels or ['لا توجد بيانات'],
        'values': values or [0]
    }


def _open_obs_by_prison(region_id=None):
    q = MissionPrisonReport.query.options(
        joinedload(MissionPrisonReport.prison),
        joinedload(MissionPrisonReport.observations),
        joinedload(MissionPrisonReport.mission_region)
    )

    if region_id:
        q = q.join(MissionRegion, MissionPrisonReport.mission_region_id == MissionRegion.id).filter(
            MissionRegion.region_id == region_id
        )

    rows = []
    for pr in q.all():
        open_count = sum(1 for o in pr.observations if o.status not in ['closed', 'resolved'])
        rows.append((pr.prison.name, open_count))

    agg = defaultdict(int)
    for prison_name, count in rows:
        agg[prison_name] += count

    final_rows = sorted(agg.items(), key=lambda x: x[1], reverse=True)[:8]

    return {
        'labels': [r[0] for r in final_rows] or ['لا توجد بيانات'],
        'values': [r[1] for r in final_rows] or [0]
    }


def _trend_by_month(region_id=None, observations=None):
    monthly = defaultdict(int)

    if observations is not None:
        source = observations
    else:
        q = Observation.query.join(MissionPrisonReport, Observation.mission_prison_report_id == MissionPrisonReport.id)
        if region_id:
            q = q.join(MissionRegion, MissionPrisonReport.mission_region_id == MissionRegion.id).filter(
                MissionRegion.region_id == region_id
            )
        source = q.all()

    for o in source:
        if o.created_at:
            monthly[o.created_at.strftime('%Y-%m')] += 1

    keys = sorted(monthly.keys())[-6:]
    return {
        'labels': keys or ['لا توجد بيانات'],
        'values': [monthly[k] for k in keys] or [0]
    }


def _severity_dist(observations):
    order = ['منخفضة', 'متوسطة', 'مرتفعة', 'عالية', 'حرجة']
    c = Counter([o.severity for o in observations if o.severity])
    labels = [k for k in order if c.get(k)]
    vals = [c[k] for k in labels]
    return {
        'labels': labels or ['لا توجد بيانات'],
        'values': vals or [0]
    }


def central_dashboard(user=None):
    observations = Observation.query.all()
    mission_regions = MissionRegion.query.options(joinedload(MissionRegion.prison_reports)).all()
    prison_reports = MissionPrisonReport.query.all()

    scored_reports = [pr.score_percentage for pr in prison_reports if pr.score_percentage is not None]

    stats = {
        'missions_total': Mission.query.count(),
        'missions_open': Mission.query.filter(Mission.status != 'closed').count(),
        'regions_reports_pending': MissionRegion.query.filter(
            MissionRegion.status.in_(['submitted_to_central', 'awaiting_central_review', 'awaiting_remediation'])
        ).count(),
        'observations_open': sum(1 for o in observations if o.status not in ['closed', 'resolved']),
        'critical_observations': sum(1 for o in observations if o.severity in ['حرجة', 'عالية']),
        'plan_commitment_pct': round((Mission.query.count() / 48) * 100, 1) if Mission.query.count() else 0,
        'avg_closure_days': 7,
        'avg_score': round(sum(scored_reports) / len(scored_reports), 2) if scored_reports else 0,
        'regions_count': len({mr.region_id for mr in mission_regions}),
    }

    top_regions_rows = []
    for mr in mission_regions:
        obs_count = sum(len(pr.observations) for pr in mr.prison_reports)
        top_regions_rows.append((mr.region.name, obs_count))

    region_counter = defaultdict(int)
    for name, count in top_regions_rows:
        region_counter[name] += count
    top_regions = sorted(region_counter.items(), key=lambda x: x[1], reverse=True)[:8]

    top_departments = db.session.query(
        Department.name,
        func.count(Observation.id)
    ).join(
        Observation, Observation.department_id == Department.id
    ).group_by(
        Department.name
    ).order_by(
        func.count(Observation.id).desc()
    ).limit(8).all()

    charts = {
        'risk_by_region': _risk_by_region_q(),
        'obs_status': _status_counts(observations),
        'obs_severity': _severity_dist(observations),
        'trend_monthly': _trend_by_month(),
        'open_by_prison': _open_obs_by_prison(),
        'departments_load': {
            'labels': [n for n, _ in top_departments] or ['لا توجد بيانات'],
            'values': [c for _, c in top_departments] or [0]
        },
    }

    return stats, top_regions, top_departments, charts


def region_dashboard(user):
    mission_regions = MissionRegion.query.options(
        joinedload(MissionRegion.prison_reports).joinedload(MissionPrisonReport.observations)
    ).filter_by(region_id=user.region_id).all()

    prison_reports = [pr for mr in mission_regions for pr in mr.prison_reports]
    observations = [o for pr in prison_reports for o in pr.observations]

    scored_reports = [pr.score_percentage for pr in prison_reports if pr.score_percentage is not None]

    stats = {
        'assigned_regions_reports': len(mission_regions),
        'awaiting_setup': sum(1 for mr in mission_regions if mr.status == 'pending_region_setup'),
        'awaiting_execution': sum(1 for pr in prison_reports if pr.status in ['assigned', 'in_progress']),
        'awaiting_submit': sum(1 for pr in prison_reports if pr.status in ['in_progress', 'pending_assignment']),
        'open_observations': sum(1 for o in observations if o.status not in ['closed', 'resolved']),
        'coverage_prisons': len({pr.prison_id for pr in prison_reports}),
        'avg_score': round(sum(scored_reports) / len(scored_reports), 2) if scored_reports else 0,
    }

    charts = {
        'obs_status': _status_counts(observations),
        'risk_by_prison': _open_obs_by_prison(user.region_id),
        'trend_monthly': _trend_by_month(user.region_id),
        'severity_dist': _severity_dist(observations),
    }
    return stats, mission_regions, charts


def executor_dashboard(current_user):
    assigned_reports = MissionPrisonReport.query.options(
        joinedload(MissionPrisonReport.prison),
        joinedload(MissionPrisonReport.assignees),
        joinedload(MissionPrisonReport.observations),
        joinedload(MissionPrisonReport.mission_region).joinedload(MissionRegion.region),
        joinedload(MissionPrisonReport.mission_region).joinedload(MissionRegion.mission).joinedload(Mission.template),
    ).filter(
        MissionPrisonReport.assignees.any(User.id == current_user.id)
    ).order_by(MissionPrisonReport.updated_at.desc()).all()

    observations = [obs for pr in assigned_reports for obs in pr.observations]

    scored_reports = [pr.score_percentage for pr in assigned_reports if pr.score_percentage is not None]
    avg_score = round(sum(scored_reports) / len(scored_reports), 1) if scored_reports else 0

    stats = {
        'assigned_reports': len(assigned_reports),
        'completed_reports': sum(1 for pr in assigned_reports if pr.status == 'submitted'),
        'observations_recorded': len(observations),
        'critical_observations': sum(1 for obs in observations if obs.severity == 'حرجة'),
        'avg_score': avg_score,
    }

    obs_status_counter = {}
    severity_counter = {}
    monthly_counter = {}
    report_status_counter = {}

    status_labels = {
        'pending_assignment': 'بانتظار الإسناد',
        'assigned': 'مسندة',
        'in_progress': 'قيد التنفيذ',
        'submitted': 'مرفوعة',
    }

    for pr in assigned_reports:
        report_status_counter[status_labels.get(pr.status, pr.status)] = report_status_counter.get(
            status_labels.get(pr.status, pr.status), 0
        ) + 1

    for obs in observations:
        obs_status_counter[obs.status] = obs_status_counter.get(obs.status, 0) + 1
        severity_counter[obs.severity] = severity_counter.get(obs.severity, 0) + 1

        month_key = obs.created_at.strftime('%Y-%m') if obs.created_at else 'غير محدد'
        monthly_counter[month_key] = monthly_counter.get(month_key, 0) + 1

    charts = {
        'obs_status': {
            'labels': list(obs_status_counter.keys()) or ['لا توجد بيانات'],
            'values': list(obs_status_counter.values()) or [0],
        },
        'severity_dist': {
            'labels': list(severity_counter.keys()) or ['لا توجد بيانات'],
            'values': list(severity_counter.values()) or [0],
        },
        'trend_monthly': {
            'labels': list(monthly_counter.keys()) or ['لا توجد بيانات'],
            'values': list(monthly_counter.values()) or [0],
        },
        'report_status': {
            'labels': list(report_status_counter.keys()) or ['لا توجد بيانات'],
            'values': list(report_status_counter.values()) or [0],
        }
    }

    return stats, assigned_reports, charts


def prison_director_dashboard(user):
    mission_regions = MissionRegion.query.options(
        joinedload(MissionRegion.prison_reports).joinedload(MissionPrisonReport.observations)
    ).filter_by(region_id=user.region_id).all()

    prison_reports = [pr for mr in mission_regions for pr in mr.prison_reports]
    observations = [o for pr in prison_reports for o in pr.observations]

    stats = {
        'open_observations': sum(1 for o in observations if o.status not in ['closed', 'resolved']),
        'awaiting_director': sum(1 for o in observations if o.status == 'awaiting_prison_director'),
        'resolved': sum(1 for o in observations if o.status == 'resolved'),
        'prisons_count': Prison.query.filter_by(region_id=user.region_id).count(),
        'high_risk_prisons': sum(1 for v in _open_obs_by_prison(user.region_id)['values'] if v >= 3),
    }

    charts = {
        'obs_status': _status_counts(observations),
        'risk_by_prison': _open_obs_by_prison(user.region_id),
        'trend_monthly': _trend_by_month(user.region_id),
        'severity_dist': _severity_dist(observations),
    }
    return stats, mission_regions, charts


def department_dashboard(user):
    observations = Observation.query.filter_by(department_id=user.department_id).all()
    today = db.session.execute(func.current_date()).scalar()

    stats = {
        'received': len(observations),
        'open': sum(1 for o in observations if o.status not in ['closed', 'resolved']),
        'under_treatment': sum(1 for o in observations if o.status == 'under_treatment'),
        'resolved': sum(1 for o in observations if o.status == 'resolved'),
        'overdue': sum(1 for o in observations if o.due_date and o.status not in ['closed', 'resolved'] and o.due_date < today),
    }

    charts = {
        'obs_status': _status_counts(observations),
        'severity_dist': _severity_dist(observations),
        'trend_monthly': _trend_by_month(observations=observations),
    }
    return stats, observations, charts


def dg_dashboard():
    ready_reports = Mission.query.filter(
        Mission.status.in_(['ready_for_dg', 'closed'])
    ).order_by(Mission.updated_at.desc()).all()

    observations = Observation.query.all()
    risk_chart = _risk_by_region_q()

    stats = {
        'final_reports_total': len(ready_reports),
        'closed_reports': sum(1 for m in ready_reports if m.status == 'closed'),
        'ready_for_review': sum(1 for m in ready_reports if m.status == 'ready_for_dg'),
        'open_observations': sum(1 for o in observations if o.status not in ['closed', 'resolved']),
        'avg_risk_index': round(
            sum(risk_chart['values']) / max(len(risk_chart['values']), 1),
            2
        ) if risk_chart['values'] else 0,
    }

    charts = {
        'risk_by_region': risk_chart,
        'obs_status': _status_counts(observations),
        'trend_monthly': _trend_by_month(),
        'severity_dist': _severity_dist(observations),
    }
    return stats, ready_reports, charts