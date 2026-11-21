# Project Operations Foundation

## Backend architecture

FastAPI routes in `app/api/routes/projects.py` use the existing
`get_current_user` dependency and the existing SQLAlchemy session. Business
rules and authorization live in `app/services/project_operations.py`.
Pydantic request and response models live in `app/schemas/projects.py`.

## Authorization

- Organization reads require organization membership.
- Organization and project-management mutations require an owner or admin role.
- Project reads require project membership.
- Project task and knowledge mutations require project membership.
- Assignees must already be project members.
- Users do not receive access merely from knowing a resource ID.
- RLS policies and the inspected BYPASSRLS role remain unresolved; API
  authorization is therefore mandatory and must not be treated as optional.

## API groups

- Organizations and organization members: `/api/organizations`
- Projects and project members: `/api/projects`
- Project tasks: `/api/projects/{project_id}/tasks` and `/api/tasks/{task_id}`
- Milestones: `/api/projects/{project_id}/milestones` and `/api/milestones/{id}`
- Dependencies: `/api/tasks/{task_id}/dependencies`
- Meeting notes: `/api/projects/{project_id}/meeting-notes`
- Project document metadata: `/api/projects/{project_id}/documents`
- Dashboard metrics: `/api/projects/overview/metrics`

## Frontend

The existing chat application remains at `/app`. The project workspace is
available at `/projects` and `/projects/{projectId}`. It uses real organization,
project, task, milestone, member, document, meeting-note, and metrics APIs.
The UI does not display AI execution activity or metrics that the backend did
not produce.

## Testing

Run:

```powershell
$env:PYTHONPATH="backend"
$env:PAGETRAIL_GUARDRAILS="false"
python -m pytest backend/tests -q
npm --prefix frontend run build
```

No production migration or schema mutation was executed for this milestone.
