from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.api.routes.auth import CurrentUser, get_db
from app.db.models import (
    DocumentProcessingStatus,
    MeetingNote,
    Milestone,
    Organization,
    OrganizationMember,
    Project,
    ProjectDocument,
    ProjectMember,
    ProjectMemberRole,
    Task,
    TaskDependency,
    TaskStatus,
    User,
)
from app.schemas.projects import (
    MeetingNoteCreate,
    MeetingNoteResponse,
    MeetingNoteUpdate,
    MilestoneCreate,
    MilestoneResponse,
    MilestoneUpdate,
    OrganizationCreate,
    OrganizationMemberCreate,
    OrganizationMemberResponse,
    OrganizationMemberUpdate,
    OrganizationResponse,
    OrganizationUpdate,
    ProjectCreate,
    ProjectMemberCreate,
    ProjectMemberResponse,
    ProjectMemberUpdate,
    ProjectResponse,
    ProjectUpdate,
    TaskCreate,
    TaskDependencyCreate,
    TaskDependencyResponse,
    TaskResponse,
    TaskUpdate,
    ProjectDocumentCreate,
    ProjectDocumentResponse,
)
from app.services.project_operations import (
    add_project_member,
    archive_project,
    count_org_owners,
    create_milestone,
    create_organization,
    create_project,
    create_task,
    cycle_exists,
    delete_milestone,
    delete_task,
    get_org,
    get_org_membership,
    get_project,
    remove_project_member,
    require_org_manager,
    require_org_member,
    require_project_manager,
    require_project_member,
    update_milestone,
    update_organization,
    update_project,
    update_project_member,
    update_task,
    validate_enum,
)


router = APIRouter(tags=["project operations"])


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Resource not found.")


def _org_membership(db: Session, organization_id: int, user_id: int) -> OrganizationMember:
    membership = get_org_membership(db, organization_id, user_id)
    if membership is None:
        raise _not_found()
    return membership


@router.post("/api/organizations", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_org(payload: OrganizationCreate, current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    organization = create_organization(db, current_user, payload.name, payload.slug)
    db.commit()
    db.refresh(organization)
    return organization


@router.get("/api/organizations", response_model=list[OrganizationResponse])
def list_organizations(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    organization_ids = [
        row.organization_id
        for row in db.query(OrganizationMember.organization_id)
        .filter(OrganizationMember.user_id == current_user.id)
        .offset(offset)
        .limit(limit)
        .all()
    ]
    if not organization_ids:
        return []
    return db.query(Organization).filter(Organization.id.in_(organization_ids)).all()


@router.get("/api/organizations/{organization_id}", response_model=OrganizationResponse)
def get_org_detail(organization_id: int, current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    require_org_member(db, organization_id, current_user)
    return get_org(db, organization_id)


@router.patch("/api/organizations/{organization_id}", response_model=OrganizationResponse)
def patch_org(
    organization_id: int,
    payload: OrganizationUpdate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    organization = get_org(db, organization_id)
    updated = update_organization(db, organization, current_user, payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(updated)
    return updated


@router.get("/api/organizations/{organization_id}/members", response_model=list[OrganizationMemberResponse])
def list_org_members(organization_id: int, current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    require_org_member(db, organization_id, current_user)
    return db.query(OrganizationMember).filter_by(organization_id=organization_id).all()


@router.post("/api/organizations/{organization_id}/members", response_model=OrganizationMemberResponse, status_code=status.HTTP_201_CREATED)
def add_org_member(
    organization_id: int,
    payload: OrganizationMemberCreate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    require_org_manager(db, organization_id, current_user)
    validate_enum(ProjectMemberRole, payload.role, "role")
    if db.get(User, payload.user_id) is None:
        raise _not_found()
    if get_org_membership(db, organization_id, payload.user_id):
        raise HTTPException(status_code=409, detail="User is already an organization member.")
    membership = OrganizationMember(
        organization_id=organization_id,
        user_id=payload.user_id,
        role=payload.role,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


@router.patch("/api/organizations/{organization_id}/members/{user_id}", response_model=OrganizationMemberResponse)
def patch_org_member(
    organization_id: int,
    user_id: int,
    payload: OrganizationMemberUpdate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    require_org_manager(db, organization_id, current_user)
    validate_enum(ProjectMemberRole, payload.role, "role")
    membership = get_org_membership(db, organization_id, user_id)
    if membership is None:
        raise _not_found()
    if membership.role == ProjectMemberRole.OWNER.value and payload.role != ProjectMemberRole.OWNER.value:
        if count_org_owners(db, organization_id) <= 1:
            raise HTTPException(status_code=409, detail="The organization must have an owner.")
    membership.role = payload.role
    db.commit()
    db.refresh(membership)
    return membership


@router.delete("/api/organizations/{organization_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_org_member(
    organization_id: int,
    user_id: int,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    require_org_manager(db, organization_id, current_user)
    membership = get_org_membership(db, organization_id, user_id)
    if membership is None:
        raise _not_found()
    if membership.role == ProjectMemberRole.OWNER.value and count_org_owners(db, organization_id) <= 1:
        raise HTTPException(status_code=409, detail="The organization must have an owner.")
    db.delete(membership)
    db.commit()


@router.get("/api/projects/overview/metrics")
def project_metrics(current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    project_ids = [
        row.project_id
        for row in db.query(ProjectMember.project_id)
        .filter(ProjectMember.user_id == current_user.id)
        .all()
    ]
    if not project_ids:
        return {
            "active_projects": 0,
            "total_tasks": 0,
            "completed_tasks": 0,
            "overdue_tasks": 0,
            "blocked_tasks": 0,
        }
    now = datetime.now(timezone.utc)
    tasks = db.query(Task).filter(Task.project_id.in_(project_ids)).all()
    return {
        "active_projects": db.query(Project).filter(Project.id.in_(project_ids), Project.status == "active").count(),
        "total_tasks": len(tasks),
        "completed_tasks": sum(task.status == TaskStatus.DONE.value for task in tasks),
        "overdue_tasks": sum(
            task.status != TaskStatus.DONE.value
            and task.due_date is not None
            and task.due_date.replace(tzinfo=timezone.utc) < now
            for task in tasks
        ),
        "blocked_tasks": sum(task.status == "blocked" for task in tasks),
    }


@router.post("/api/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project_endpoint(payload: ProjectCreate, current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    project = create_project(
        db,
        current_user,
        payload.organization_id,
        payload.name,
        payload.description,
        payload.status,
    )
    db.commit()
    db.refresh(project)
    return project


@router.get("/api/projects", response_model=list[ProjectResponse])
def list_projects(
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    status_filter: str | None = Query(default=None, alias="status"),
    organization_id: int | None = None,
    search: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    project_ids = [
        row.project_id
        for row in db.query(ProjectMember.project_id)
        .filter(ProjectMember.user_id == current_user.id)
        .all()
    ]
    query = db.query(Project).filter(Project.id.in_(project_ids))
    if status_filter:
        query = query.filter(Project.status == status_filter)
    if organization_id:
        query = query.filter(Project.organization_id == organization_id)
    if search:
        query = query.filter(Project.name.ilike(f"%{search}%"))
    return query.order_by(Project.updated_at.desc()).offset(offset).limit(limit).all()


@router.get("/api/projects/{project_id}", response_model=ProjectResponse)
def get_project_detail(project_id: int, current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    return get_project(db, project_id, current_user)


@router.patch("/api/projects/{project_id}", response_model=ProjectResponse)
def patch_project(
    project_id: int,
    payload: ProjectUpdate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    project = get_project(db, project_id, current_user)
    updated = update_project(db, project, current_user, payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(updated)
    return updated


@router.delete("/api/projects/{project_id}", response_model=ProjectResponse)
def delete_project(project_id: int, current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    project = get_project(db, project_id, current_user)
    archived = archive_project(db, project, current_user)
    db.commit()
    db.refresh(archived)
    return archived


@router.get("/api/projects/{project_id}/members", response_model=list[ProjectMemberResponse])
def list_project_members(project_id: int, current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    get_project(db, project_id, current_user)
    return db.query(ProjectMember).filter_by(project_id=project_id).all()


@router.post("/api/projects/{project_id}/members", response_model=ProjectMemberResponse, status_code=status.HTTP_201_CREATED)
def add_project_member_endpoint(
    project_id: int,
    payload: ProjectMemberCreate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    project = get_project(db, project_id, current_user)
    membership = add_project_member(db, project, current_user, payload.user_id, payload.role)
    db.commit()
    db.refresh(membership)
    return membership


@router.patch("/api/projects/{project_id}/members/{user_id}", response_model=ProjectMemberResponse)
def patch_project_member_endpoint(
    project_id: int,
    user_id: int,
    payload: ProjectMemberUpdate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    project = get_project(db, project_id, current_user)
    membership = update_project_member(db, project, current_user, user_id, payload.role)
    db.commit()
    db.refresh(membership)
    return membership


@router.delete("/api/projects/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_project_member_endpoint(
    project_id: int,
    user_id: int,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    project = get_project(db, project_id, current_user)
    remove_project_member(db, project, current_user, user_id)
    db.commit()


@router.post("/api/projects/{project_id}/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task_endpoint(
    project_id: int,
    payload: TaskCreate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    project = get_project(db, project_id, current_user)
    task = create_task(db, project, current_user, payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(task)
    return task


@router.get("/api/projects/{project_id}/tasks", response_model=list[TaskResponse])
def list_tasks(
    project_id: int,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    status_filter: str | None = Query(default=None, alias="status"),
    priority: str | None = None,
    assignee_id: int | None = None,
    milestone_id: int | None = None,
    due_before: datetime | None = None,
    due_after: datetime | None = None,
    search: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    get_project(db, project_id, current_user)
    query = db.query(Task).filter(Task.project_id == project_id)
    if status_filter:
        query = query.filter(Task.status == status_filter)
    if priority:
        query = query.filter(Task.priority == priority)
    if assignee_id is not None:
        query = query.filter(Task.assignee_id == assignee_id)
    if milestone_id is not None:
        query = query.filter(Task.milestone_id == milestone_id)
    if due_before:
        query = query.filter(Task.due_date <= due_before)
    if due_after:
        query = query.filter(Task.due_date >= due_after)
    if search:
        query = query.filter(
            or_(Task.title.ilike(f"%{search}%"), Task.description.ilike(f"%{search}%"))
        )
    return query.order_by(Task.created_at.desc()).offset(offset).limit(limit).all()


@router.get("/api/tasks/{task_id}", response_model=TaskResponse)
def get_task(task_id: int, current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    task = db.get(Task, task_id)
    if task is None:
        raise _not_found()
    get_project(db, task.project_id, current_user)
    return task


@router.patch("/api/tasks/{task_id}", response_model=TaskResponse)
def patch_task(
    task_id: int,
    payload: TaskUpdate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    task = db.get(Task, task_id)
    if task is None:
        raise _not_found()
    updated = update_task(db, task, current_user, payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(updated)
    return updated


@router.delete("/api/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task_endpoint(task_id: int, current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    task = db.get(Task, task_id)
    if task is None:
        raise _not_found()
    delete_task(db, task, current_user)
    db.commit()


@router.post("/api/projects/{project_id}/milestones", response_model=MilestoneResponse, status_code=status.HTTP_201_CREATED)
def create_milestone_endpoint(
    project_id: int,
    payload: MilestoneCreate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    project = get_project(db, project_id, current_user)
    milestone = create_milestone(db, project, current_user, payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(milestone)
    return milestone


@router.get("/api/projects/{project_id}/milestones", response_model=list[MilestoneResponse])
def list_milestones(
    project_id: int,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    get_project(db, project_id, current_user)
    return db.query(Milestone).filter_by(project_id=project_id).offset(offset).limit(limit).all()


@router.get("/api/milestones/{milestone_id}", response_model=MilestoneResponse)
def get_milestone(milestone_id: int, current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    milestone = db.get(Milestone, milestone_id)
    if milestone is None:
        raise _not_found()
    get_project(db, milestone.project_id, current_user)
    return milestone


@router.patch("/api/milestones/{milestone_id}", response_model=MilestoneResponse)
def patch_milestone(
    milestone_id: int,
    payload: MilestoneUpdate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    milestone = db.get(Milestone, milestone_id)
    if milestone is None:
        raise _not_found()
    updated = update_milestone(db, milestone, current_user, payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(updated)
    return updated


@router.delete("/api/milestones/{milestone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_milestone_endpoint(milestone_id: int, current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    milestone = db.get(Milestone, milestone_id)
    if milestone is None:
        raise _not_found()
    delete_milestone(db, milestone, current_user)
    db.commit()


@router.get("/api/tasks/{task_id}/dependencies", response_model=list[TaskDependencyResponse])
def list_dependencies(task_id: int, current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    task = db.get(Task, task_id)
    if task is None:
        raise _not_found()
    get_project(db, task.project_id, current_user)
    return db.query(TaskDependency).filter(TaskDependency.task_id == task_id).all()


@router.post("/api/tasks/{task_id}/dependencies", response_model=TaskDependencyResponse, status_code=status.HTTP_201_CREATED)
def add_dependency(
    task_id: int,
    payload: TaskDependencyCreate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    task = db.get(Task, task_id)
    dependency_task = db.get(Task, payload.depends_on_task_id)
    if task is None or dependency_task is None:
        raise _not_found()
    get_project(db, task.project_id, current_user)
    if task.project_id != dependency_task.project_id:
        raise HTTPException(status_code=422, detail="Dependencies must belong to the same project.")
    if task_id == payload.depends_on_task_id:
        raise HTTPException(status_code=422, detail="A task cannot depend on itself.")
    existing = db.query(TaskDependency).filter_by(
        task_id=task_id,
        depends_on_task_id=payload.depends_on_task_id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Dependency already exists.")
    if cycle_exists(db, task_id, payload.depends_on_task_id):
        raise HTTPException(status_code=409, detail="Dependency would create a cycle.")
    dependency = TaskDependency(
        task_id=task_id,
        depends_on_task_id=payload.depends_on_task_id,
        project_id=task.project_id,
        dependency_type=payload.dependency_type,
    )
    db.add(dependency)
    db.commit()
    db.refresh(dependency)
    return dependency


@router.delete("/api/task-dependencies/{dependency_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_dependency(dependency_id: int, current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    dependency = db.get(TaskDependency, dependency_id)
    if dependency is None:
        raise _not_found()
    get_project(db, dependency.project_id, current_user)
    db.delete(dependency)
    db.commit()


@router.post("/api/projects/{project_id}/meeting-notes", response_model=MeetingNoteResponse, status_code=status.HTTP_201_CREATED)
def create_meeting_note(
    project_id: int,
    payload: MeetingNoteCreate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    get_project(db, project_id, current_user)
    note = MeetingNote(
        project_id=project_id,
        created_by=current_user.id,
        title=payload.title,
        meeting_date=payload.meeting_date,
        raw_content=payload.raw_content,
        summary=payload.summary,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.get("/api/projects/{project_id}/meeting-notes", response_model=list[MeetingNoteResponse])
def list_meeting_notes(
    project_id: int,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    get_project(db, project_id, current_user)
    return db.query(MeetingNote).filter_by(project_id=project_id).order_by(MeetingNote.meeting_date.desc()).offset(offset).limit(limit).all()


@router.get("/api/meeting-notes/{note_id}", response_model=MeetingNoteResponse)
def get_meeting_note(note_id: int, current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    note = db.get(MeetingNote, note_id)
    if note is None:
        raise _not_found()
    get_project(db, note.project_id, current_user)
    return note


@router.patch("/api/meeting-notes/{note_id}", response_model=MeetingNoteResponse)
def patch_meeting_note(
    note_id: int,
    payload: MeetingNoteUpdate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    note = db.get(MeetingNote, note_id)
    if note is None:
        raise _not_found()
    get_project(db, note.project_id, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(note, field, value)
    note.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(note)
    return note


@router.delete("/api/meeting-notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meeting_note(note_id: int, current_user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    note = db.get(MeetingNote, note_id)
    if note is None:
        raise _not_found()
    get_project(db, note.project_id, current_user)
    db.delete(note)
    db.commit()


@router.post("/api/projects/{project_id}/documents", response_model=ProjectDocumentResponse, status_code=status.HTTP_201_CREATED)
def create_project_document(
    project_id: int,
    payload: ProjectDocumentCreate,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
):
    get_project(db, project_id, current_user)
    if payload.file_size > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Document must be smaller than 10 MB.")
    validate_enum(DocumentProcessingStatus, payload.processing_status, "processing_status")
    if db.query(ProjectDocument).filter_by(project_id=project_id, checksum=payload.checksum).first():
        raise HTTPException(status_code=409, detail="Document checksum already exists for this project.")
    document = ProjectDocument(
        project_id=project_id,
        uploaded_by=current_user.id,
        filename=payload.filename,
        storage_path=payload.storage_path,
        mime_type=payload.mime_type,
        file_size=payload.file_size,
        checksum=payload.checksum,
        processing_status=payload.processing_status,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.get("/api/projects/{project_id}/documents", response_model=list[ProjectDocumentResponse])
def list_project_documents(
    project_id: int,
    current_user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    get_project(db, project_id, current_user)
    return db.query(ProjectDocument).filter_by(project_id=project_id).offset(offset).limit(limit).all()
