import re
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.models import (
    AuditLog,
    MeetingNote,
    Milestone,
    MilestoneStatus,
    Organization,
    OrganizationMember,
    Project,
    ProjectDocument,
    ProjectMember,
    ProjectMemberRole,
    ProjectStatus,
    Task,
    TaskDependency,
    TaskPriority,
    TaskStatus,
    User,
)


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Resource not found.")


def _forbidden() -> HTTPException:
    return HTTPException(status_code=403, detail="Permission denied.")


def _enum_values(enum_type) -> set[str]:
    return {member.value for member in enum_type}


def validate_enum(enum_type, value: str, field_name: str) -> str:
    if value not in _enum_values(enum_type):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid {field_name}.",
        )
    return value


def get_org(db: Session, organization_id: int) -> Organization:
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise _not_found()
    return organization


def get_org_membership(db: Session, organization_id: int, user_id: int) -> OrganizationMember | None:
    return db.query(OrganizationMember).filter_by(
        organization_id=organization_id,
        user_id=user_id,
    ).first()


def require_org_member(db: Session, organization_id: int, user: User) -> OrganizationMember:
    membership = get_org_membership(db, organization_id, user.id)
    if membership is None:
        raise _not_found()
    return membership


def require_org_manager(db: Session, organization_id: int, user: User) -> OrganizationMember:
    membership = require_org_member(db, organization_id, user)
    if membership.role not in {ProjectMemberRole.OWNER.value, ProjectMemberRole.ADMIN.value}:
        raise _forbidden()
    return membership


def get_project(db: Session, project_id: int, user: User) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise _not_found()
    require_project_member(db, project_id, user)
    return project


def get_project_membership(db: Session, project_id: int, user_id: int) -> ProjectMember | None:
    return db.query(ProjectMember).filter_by(
        project_id=project_id,
        user_id=user_id,
    ).first()


def require_project_member(db: Session, project_id: int, user: User) -> ProjectMember:
    membership = get_project_membership(db, project_id, user.id)
    if membership is None:
        raise _not_found()
    return membership


def require_project_manager(db: Session, project_id: int, user: User) -> ProjectMember:
    membership = require_project_member(db, project_id, user)
    if membership.role not in {ProjectMemberRole.OWNER.value, ProjectMemberRole.ADMIN.value}:
        raise _forbidden()
    return membership


def count_org_owners(db: Session, organization_id: int) -> int:
    return db.query(OrganizationMember).filter_by(
        organization_id=organization_id,
        role=ProjectMemberRole.OWNER.value,
    ).count()


def count_project_owners(db: Session, project_id: int) -> int:
    return db.query(ProjectMember).filter_by(
        project_id=project_id,
        role=ProjectMemberRole.OWNER.value,
    ).count()


def normalized_slug(name: str, requested: str | None) -> str:
    value = requested or name
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    if not slug:
        raise HTTPException(status_code=422, detail="A valid organization slug is required.")
    return slug[:255]


def create_organization(db: Session, user: User, name: str, slug: str | None) -> Organization:
    normalized = normalized_slug(name, slug)
    if db.query(Organization).filter_by(slug=normalized).first():
        raise HTTPException(status_code=409, detail="Organization slug already exists.")
    organization = Organization(
        name=name,
        slug=normalized,
        created_by=user.id,
    )
    db.add(organization)
    db.flush()
    return organization


def update_organization(db: Session, organization: Organization, user: User, data: dict) -> Organization:
    require_org_manager(db, organization.id, user)
    if "name" in data and data["name"] is not None:
        organization.name = data["name"]
    if "slug" in data and data["slug"] is not None:
        normalized = normalized_slug(organization.name, data["slug"])
        duplicate = db.query(Organization).filter(
            Organization.slug == normalized,
            Organization.id != organization.id,
        ).first()
        if duplicate:
            raise HTTPException(status_code=409, detail="Organization slug already exists.")
        organization.slug = normalized
    return organization


def create_project(db: Session, user: User, organization_id: int, name: str, description: str | None, status: str) -> Project:
    require_org_manager(db, organization_id, user)
    validate_enum(ProjectStatus, status, "status")
    project = Project(
        organization_id=organization_id,
        name=name,
        description=description,
        status=status,
        created_by=user.id,
    )
    db.add(project)
    db.flush()
    return project


def update_project(db: Session, project: Project, user: User, data: dict) -> Project:
    require_project_manager(db, project.id, user)
    for field in ("name", "description"):
        if field in data and data[field] is not None:
            setattr(project, field, data[field])
    if "status" in data and data["status"] is not None:
        project.status = validate_enum(ProjectStatus, data["status"], "status")
    project.updated_at = datetime.now(timezone.utc).isoformat()
    return project


def archive_project(db: Session, project: Project, user: User) -> Project:
    require_project_manager(db, project.id, user)
    project.status = ProjectStatus.ARCHIVED.value
    project.updated_at = datetime.now(timezone.utc).isoformat()
    return project


def add_project_member(db: Session, project: Project, user: User, member_user_id: int, role: str) -> ProjectMember:
    require_project_manager(db, project.id, user)
    validate_enum(ProjectMemberRole, role, "role")
    organization_member = get_org_membership(db, project.organization_id, member_user_id)
    if organization_member is None:
        raise HTTPException(status_code=422, detail="User must belong to the project organization.")
    if db.get(User, member_user_id) is None:
        raise _not_found()
    if get_project_membership(db, project.id, member_user_id):
        raise HTTPException(status_code=409, detail="User is already a project member.")
    membership = ProjectMember(
        project_id=project.id,
        user_id=member_user_id,
        role=role,
    )
    db.add(membership)
    db.flush()
    return membership


def update_project_member(db: Session, project: Project, user: User, member_user_id: int, role: str) -> ProjectMember:
    require_project_manager(db, project.id, user)
    validate_enum(ProjectMemberRole, role, "role")
    membership = get_project_membership(db, project.id, member_user_id)
    if membership is None:
        raise _not_found()
    if membership.role == ProjectMemberRole.OWNER.value and role != ProjectMemberRole.OWNER.value:
        if count_project_owners(db, project.id) <= 1:
            raise HTTPException(status_code=409, detail="The project must have an owner.")
    membership.role = role
    return membership


def remove_project_member(db: Session, project: Project, user: User, member_user_id: int) -> None:
    require_project_manager(db, project.id, user)
    membership = get_project_membership(db, project.id, member_user_id)
    if membership is None:
        raise _not_found()
    if membership.role == ProjectMemberRole.OWNER.value and count_project_owners(db, project.id) <= 1:
        raise HTTPException(status_code=409, detail="The project must have an owner.")
    db.delete(membership)


def create_task(db: Session, project: Project, user: User, data: dict) -> Task:
    require_project_member(db, project.id, user)
    status = validate_enum(TaskStatus, data.get("status", TaskStatus.TODO.value), "status")
    priority = validate_enum(TaskPriority, data.get("priority", TaskPriority.MEDIUM.value), "priority")
    assignee_id = data.get("assignee_id")
    if assignee_id is not None and get_project_membership(db, project.id, assignee_id) is None:
        raise HTTPException(status_code=422, detail="Assignee must belong to the project.")
    milestone_id = data.get("milestone_id")
    if milestone_id is not None:
        milestone = db.get(Milestone, milestone_id)
        if milestone is None or milestone.project_id != project.id:
            raise HTTPException(status_code=422, detail="Milestone must belong to the project.")
    task = Task(
        project_id=project.id,
        milestone_id=milestone_id,
        assignee_id=assignee_id,
        created_by=user.id,
        title=data["title"],
        description=data.get("description"),
        status=status,
        priority=priority,
        due_date=data.get("due_date"),
    )
    db.add(task)
    db.flush()
    return task


def update_task(db: Session, task: Task, user: User, data: dict) -> Task:
    require_project_member(db, task.project_id, user)
    if "title" in data and data["title"] is not None:
        task.title = data["title"]
    if "description" in data:
        task.description = data["description"]
    if "status" in data and data["status"] is not None:
        task.status = validate_enum(TaskStatus, data["status"], "status")
    if "priority" in data and data["priority"] is not None:
        task.priority = validate_enum(TaskPriority, data["priority"], "priority")
    if "assignee_id" in data:
        assignee_id = data["assignee_id"]
        if assignee_id is not None and get_project_membership(db, task.project_id, assignee_id) is None:
            raise HTTPException(status_code=422, detail="Assignee must belong to the project.")
        task.assignee_id = assignee_id
    if "milestone_id" in data:
        milestone_id = data["milestone_id"]
        if milestone_id is not None:
            milestone = db.get(Milestone, milestone_id)
            if milestone is None or milestone.project_id != task.project_id:
                raise HTTPException(status_code=422, detail="Milestone must belong to the project.")
        task.milestone_id = milestone_id
    if "due_date" in data:
        task.due_date = data["due_date"]
    if "completed_at" in data:
        task.completed_at = data["completed_at"]
    elif "status" in data:
        task.completed_at = datetime.now(timezone.utc) if task.status == TaskStatus.DONE.value else None
    task.updated_at = datetime.now(timezone.utc).isoformat()
    return task


def delete_task(db: Session, task: Task, user: User) -> None:
    require_project_member(db, task.project_id, user)
    dependency_exists = db.query(TaskDependency).filter(
        or_(
            TaskDependency.task_id == task.id,
            TaskDependency.depends_on_task_id == task.id,
        )
    ).first()
    if dependency_exists:
        raise HTTPException(status_code=409, detail="Remove task dependencies before deleting the task.")
    db.delete(task)


def create_milestone(db: Session, project: Project, user: User, data: dict) -> Milestone:
    require_project_member(db, project.id, user)
    status = validate_enum(MilestoneStatus, data.get("status", MilestoneStatus.PENDING.value), "status")
    milestone = Milestone(
        project_id=project.id,
        title=data["title"],
        description=data.get("description"),
        status=status,
        start_date=data.get("start_date"),
        due_date=data.get("due_date"),
    )
    db.add(milestone)
    db.flush()
    return milestone


def update_milestone(db: Session, milestone: Milestone, user: User, data: dict) -> Milestone:
    require_project_member(db, milestone.project_id, user)
    for field in ("title", "description", "start_date", "due_date"):
        if field in data:
            setattr(milestone, field, data[field])
    if "status" in data and data["status"] is not None:
        milestone.status = validate_enum(MilestoneStatus, data["status"], "status")
    if "completed_at" in data:
        milestone.completed_at = data["completed_at"]
    elif "status" in data:
        milestone.completed_at = datetime.now(timezone.utc) if milestone.status == MilestoneStatus.COMPLETED.value else None
    milestone.updated_at = datetime.now(timezone.utc)
    return milestone


def delete_milestone(db: Session, milestone: Milestone, user: User) -> None:
    require_project_member(db, milestone.project_id, user)
    db.query(Task).filter(Task.milestone_id == milestone.id).update(
        {Task.milestone_id: None},
        synchronize_session=False,
    )
    db.delete(milestone)


def cycle_exists(db: Session, task_id: int, depends_on_task_id: int) -> bool:
    """A -> depends_on, reject if starting at depends_on can reach task_id."""
    adjacency = {}
    rows = db.query(TaskDependency.task_id, TaskDependency.depends_on_task_id).all()
    for source, destination in rows:
        adjacency.setdefault(source, set()).add(destination)

    stack = [depends_on_task_id]
    visited = set()
    while stack:
        node = stack.pop()
        if node == task_id:
            return True
        if node in visited:
            continue
        visited.add(node)
        stack.extend(adjacency.get(node, set()))
    return False
